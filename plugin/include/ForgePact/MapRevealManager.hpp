#pragma once

#include "Common.hpp"

namespace ForgePact {

// Auto map-reveal: fill each zone's discovered grid once per zone/instance
// identity, instead of clearing it every N frames for the whole session (the
// original approach produced avoidable GameMaker calls during dense combat).
// Panel command: `reveal 1` / `reveal 0` (the panel's `map_reveal` checkbox).
class MapRevealManager {
public:
    static MapRevealManager& Instance() {
        static MapRevealManager s_Instance;
        return s_Instance;
    }

    bool IsEnabled() const { return m_Enabled; }
    void SetEnabled(bool enabled) {
        m_Enabled = enabled;
        Out(std::string("reveal: ") + (m_Enabled ? "ACIK" : "KAPALI"));
    }
    void Toggle() { SetEnabled(!m_Enabled); }

    // Called every frame from the frame callback; internally throttled to
    // once per ~20 frames so each new map clears quickly without spamming
    // GameMaker calls during dense combat.
    void OnFrame(uint64_t frameCount) {
        if (!m_Enabled || (frameCount % 20) != 0) return;
        try { Tick(); } catch (...) {}
    }

private:
    MapRevealManager() = default;
    bool m_Enabled{ false };
    int64_t m_LastInstance{ INT64_MIN };
    int64_t m_LastGrid{ INT64_MIN };
    int64_t m_LastRoom{ INT64_MIN };

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
    }
};

} // namespace ForgePact
