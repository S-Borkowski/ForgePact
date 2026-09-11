#pragma once

#include "Common.hpp"

namespace ForgePact {

// Auto map-reveal: fill each zone's discovered grid once per zone/instance
// identity, instead of clearing it every N frames for the whole session (the
// original approach produced avoidable GameMaker calls during dense combat).
// Panel command: `reveal 1` / `reveal 0` (the panel's `map_reveal` checkbox).
//
// Two halves, both measured live 2026-09-11 (docs/map-reveal-research.md):
//
// 1. Fog.  `ds_grid_clear(minimapDiscoveredGrid, 1)`.  Measured: this alone
//    already reveals every *static* icon - mechanics, waypoints, dungeon
//    entrances, chests, shrines.  `isDiscovered` does NOT gate those icons
//    (setting it under fog changed nothing; clearing fog with it still 0
//    revealed them), so no per-object sweep is needed or done.
//
// 2. Mob packs.  Monsters were the one thing fog could not reveal, and the
//    reason turned out not to be a draw gate at all: most packs *do not
//    exist yet*.  `Enemy_Creator_*` spawners sit in the room and only give
//    birth once `distance_to_object(Player_obj)` drops under ~1050 px, so an
//    unexplored zone holds a few hundred creators and only the handful of
//    packs the player already walked past.  Measured in one zone: 310
//    spawners, all awake, 208 enemies - and 1273 enemies once the spawners
//    were told the player was adjacent.  So "reveal the whole map" needs the
//    zone populated, not a visibility flag flipped.
//
//    This opens a short window on each new zone during which ModuleMain's
//    `Hook_distance_to_object` answers 0 for creator instances (the Beacon's
//    proven `beaconspawn` trick, reused rather than reinvented).  The window
//    is bounded so the builtin returns to a single relaxed atomic read for
//    the rest of the zone, and the spawn is one-shot: the packs persist
//    afterwards, including across re-entry (measured), so nothing has to be
//    re-applied per frame.
class MapRevealManager {
public:
    static MapRevealManager& Instance() {
        static MapRevealManager s_Instance;
        return s_Instance;
    }

    bool IsEnabled() const { return m_Enabled; }
    void SetEnabled(bool enabled) {
        m_Enabled = enabled;
        if (!m_Enabled) { m_SpawnWindow.store(0, std::memory_order_relaxed); m_PacksPending = false; }
        else ResetIdentity();   // re-arm: the current zone gets a pass too
        Out(std::string("reveal: ") + (m_Enabled ? "ACIK" : "KAPALI"));
    }
    void Toggle() { SetEnabled(!m_Enabled); }

    // `reveal packs 0|1` - the pack half only.  Its own control because it is
    // the half that costs frame time: clearing fog is free, populating a zone
    // is not, and a player who only wants the map drawn should not have to
    // pay for monsters they did not ask for.  Panel: the nested
    // `map_reveal_packs` checkbox under "Reveal full map".
    bool PacksEnabled() const { return m_Packs; }
    void SetPacks(bool on) {
        m_Packs = on;
        if (!m_Packs) { m_SpawnWindow.store(0, std::memory_order_relaxed); m_PacksPending = false; }
        Out(std::string("reveal packs: ") + (m_Packs ? "ACIK" : "KAPALI"));
    }

    // Read by Hook_distance_to_object on a hot builtin path - one relaxed
    // atomic load, nothing else, and false for all but a few seconds per zone.
    bool WantsPackSpawn() const { return m_SpawnWindow.load(std::memory_order_relaxed) > 0; }

    // Diagnostics for `reveal stat`.
    long PacksZones() const { return m_ZonesPopulated; }
    int  SpawnWindowLeft() const { return m_SpawnWindow.load(std::memory_order_relaxed); }
    bool PacksPending() const { return m_PacksPending; }
    int  PendingTicks() const { return m_PendingTicks; }

    // Called every frame from the frame callback.  The zone-identity work is
    // throttled to once per ~20 frames so each new map clears quickly without
    // spamming GameMaker calls during dense combat; the spawn window has to
    // count down every frame, so it is handled before that throttle.
    void OnFrame(uint64_t frameCount) {
        if (!m_Enabled) return;
        int w = m_SpawnWindow.load(std::memory_order_relaxed);
        if (w > 0) m_SpawnWindow.store(w - 1, std::memory_order_relaxed);
        if ((frameCount % 20) != 0) return;
        try { Tick(); } catch (...) {}
        // Separate from Tick() on purpose: Tick() returns early once the zone
        // identity is unchanged, but a zone armed for packs still has to be
        // polled for readiness on later ticks.
        if (m_PacksPending) { try { TryOpenSpawnWindow(); } catch (...) {} }
    }

private:
    MapRevealManager() = default;
    bool m_Enabled{ false };
    bool m_Packs{ true };
    int64_t m_LastInstance{ INT64_MIN };
    int64_t m_LastGrid{ INT64_MIN };
    int64_t m_LastRoom{ INT64_MIN };
    // Long enough to cover the creators' own polling timer (observed
    // enemyCreatorTimer ~116, and a full zone populated in under 5 s), short
    // enough that the builtin is back to a bare atomic read well before the
    // player can cross the map.
    static constexpr int kSpawnWindowFrames = 900;   // ~15 s at 60 fps
    // Tick() runs every 20 frames, so this is ~10 minutes of asking before the
    // zone is written off as one whose creators never initialise.
    static constexpr int kPendingGiveUpTicks = 1800;
    std::atomic<int> m_SpawnWindow{ 0 };
    bool m_PacksPending{ false };
    int  m_PendingTicks{ 0 };
    long m_ZonesPopulated{ 0 };

    void ResetIdentity() {
        m_LastInstance = INT64_MIN;
        m_LastGrid = INT64_MIN;
        m_LastRoom = INT64_MIN;
    }

    void Tick() {
        RValue oi = g_Yytk->CallBuiltin("asset_get_index", { RValue("objMinimap") });
        RValue id = g_Yytk->CallBuiltin("instance_find", { oi, RValue(0.0) });
        if (id.ToDouble() < 0) { ResetIdentity(); return; }
        RValue ex0 = g_Yytk->CallBuiltin("variable_instance_exists", { id, RValue("minimapDiscoveredGrid") });
        if (!ex0.ToBoolean()) { ResetIdentity(); return; }
        RValue grid = g_Yytk->CallBuiltin("variable_instance_get", { id, RValue("minimapDiscoveredGrid") });
        double gid = grid.ToDouble();
        if (gid < 0) { ResetIdentity(); return; }
        RValue ex = g_Yytk->CallBuiltin("ds_exists", { RValue(gid), RValue(1.0) });
        if (!ex.ToBoolean()) { ResetIdentity(); return; }

        int64_t roomKey = INT64_MIN;
        CInstance* global = nullptr;
        if (AurieSuccess(g_Yytk->GetGlobalInstance(&global)) && global) {
            RValue* room = nullptr;
            if (AurieSuccess(g_Yytk->GetInstanceMember(RValue(global), "room", room)) && room) {
                try { roomKey = static_cast<int64_t>(std::llround(room->ToDouble())); } catch (...) {}
            }
        }

        const int64_t instanceKey = static_cast<int64_t>(std::llround(id.ToDouble()));
        const int64_t gridKey = static_cast<int64_t>(std::llround(gid));
        if (instanceKey == m_LastInstance && gridKey == m_LastGrid && roomKey == m_LastRoom) return;

        g_Yytk->CallBuiltin("ds_grid_clear", { RValue(gid), RValue(1.0) });
        m_LastInstance = instanceKey;
        m_LastGrid = gridKey;
        m_LastRoom = roomKey;

        // New zone: arm the pack pass, but do NOT start lying yet - see
        // TryOpenSpawnWindow.  The zone-identity change fires while the new
        // room is still loading, and lying that early does real damage.
        if (m_Packs) { m_PacksPending = true; m_PendingTicks = 0; }
    }

    // MEASURED 2026-09-11, the hard way: opening the window straight from the
    // zone-identity change left two zones with `enemyCreatorTimer` *undefined*
    // on every `Enemy_Creator_obj`, no packs spawned, and - the part that
    // makes it a real bug rather than a miss - **no packs spawning naturally
    // afterwards either**, when walking onto them. The spawners were not
    // merely un-triggered, they were spent: answering `distance_to_object`
    // with 0 before a creator has finished initialising makes it take its
    // spawn branch once, early, and come out inert. The mod would have left
    // zones emptier than vanilla.
    //
    // So readiness is *asked about*, not waited out with a guessed delay:
    // a live creator has to report a real `enemyCreatorTimer` (the healthy
    // zone read 116) before the lie is allowed to start. If the creators in
    // some zone never become ready, the window simply never opens and vanilla
    // behaviour is untouched, which is the right failure direction.
    void TryOpenSpawnWindow() {
        if (++m_PendingTicks > kPendingGiveUpTicks) { m_PacksPending = false; return; }

        RValue po = g_Yytk->CallBuiltin("asset_get_index", { RValue("Player_obj") });
        if (po.ToDouble() < 0) return;
        if (g_Yytk->CallBuiltin("instance_number", { po }).ToDouble() < 1.0) return;   // still loading

        RValue co = g_Yytk->CallBuiltin("asset_get_index", { RValue("Enemy_Creator_obj") });
        if (co.ToDouble() < 0) { m_PacksPending = false; return; }
        const int n = (int)g_Yytk->CallBuiltin("instance_number", { co }).ToDouble();
        if (n < 1) { m_PacksPending = false; return; }   // nothing to populate here

        RValue inst = g_Yytk->CallBuiltin("instance_find", { co, RValue(0.0) });
        RValue t = g_Yytk->CallBuiltin("variable_instance_get", { inst, RValue("enemyCreatorTimer") });
        const bool ready = (t.m_Kind == VALUE_REAL || t.m_Kind == VALUE_INT32 || t.m_Kind == VALUE_INT64);
        if (!ready) return;   // creators still initialising - check again next tick

        m_SpawnWindow.store(kSpawnWindowFrames, std::memory_order_relaxed);
        m_PacksPending = false;
        ++m_ZonesPopulated;
    }
};

} // namespace ForgePact
