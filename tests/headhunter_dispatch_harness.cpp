// The Python test inserts the real plugin functions below. Only the game API is
// replaced; no game process, character, installed DLL or release asset is touched.
#include <algorithm>
#include <atomic>
#include <deque>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include <cstdint>

enum { VALUE_REAL, VALUE_INT32, VALUE_INT64, VALUE_OBJECT, VALUE_REF, VALUE_STRING, VALUE_UNDEFINED };
struct CInstance;
struct RValue {
    int m_Kind = VALUE_UNDEFINED;
    double number = -1;
    CInstance* instance = nullptr;
    std::string text;
    RValue() = default;
    RValue(double n) : m_Kind(VALUE_REAL), number(n) {}
    RValue(const char* s) : m_Kind(VALUE_STRING), text(s) {}
    explicit RValue(CInstance* p) : m_Kind(VALUE_OBJECT), instance(p) {}
    double ToDouble() const {
        if (m_Kind == VALUE_OBJECT) throw std::runtime_error("object is not an instance id");
        return number;
    }
    bool ToBoolean() const { return number != 0; }
};
struct CInstance {
    int id;
    int object;
    bool alive = true;
    RValue ToRValue() const { return RValue(const_cast<CInstance*>(this)); }
};
using AurieStatus = int;
static bool AurieSuccess(int status) { return status == 0; }
static long InterlockedIncrement(volatile long* value) { return ++*const_cast<long*>(value); }
static long InterlockedExchange(volatile long* value, long next) { const long old = *value; *const_cast<long*>(value) = next; return old; }
static std::vector<CInstance*> instances;
static CInstance* findInstance(int id) {
    for (auto* instance : instances) if (instance->id == id && instance->alive) return instance;
    return nullptr;
}
static int returnedIdKind = VALUE_REAL;
struct FakeRunner {
    CInstance* resolve(const RValue& value) {
        if (value.m_Kind == VALUE_OBJECT) return value.instance && value.instance->alive ? value.instance : nullptr;
        return findInstance(static_cast<int>(value.number));
    }
    RValue CallBuiltin(const char* name, std::vector<RValue> args) {
        std::string key(name);
        if (key == "asset_get_index") return RValue(args[0].text == "Player_obj" ? 10.0 : -1.0);
        if (key == "object_is_ancestor") return RValue(args[0].number == 11 && args[1].number == 10 ? 1.0 : 0.0);
        auto* instance = resolve(args[0]);
        if (key == "instance_exists") return RValue(instance ? 1.0 : 0.0);
        if (key == "variable_instance_get" && instance) {
            if (args[1].text == "id") {
                RValue id(static_cast<double>(instance->id));
                id.m_Kind = returnedIdKind;
                return id;
            }
            if (args[1].text == "object_index") return RValue(static_cast<double>(instance->object));
        }
        throw std::runtime_error("invalid builtin access");
    }
    int GetInstanceObject(int32_t id, CInstance*& result) {
        result = findInstance(id);
        return result ? 0 : -1;
    }
};
static FakeRunner runner;
static FakeRunner* g_Yytk = &runner;
static std::atomic<bool> g_HhEnabled{true};
static std::deque<int> g_HhHandledOrder;
static std::set<int> g_HhHandledIds;
static CInstance* localPlayer = nullptr;
static bool localPlayerAsObject = false;
static bool deliverySucceeds = true;
static bool deliveryThrows = false;
static int attempts = 0;
static int delivered = 0;
static CInstance* lastPlayer = nullptr;
static bool CallerIsEnemyInstance(CInstance* instance) { return instance && instance->alive && instance->object == 20; }
static bool HhResolveLocalPlayer(RValue& result, std::string*) {
    if (!localPlayer || !localPlayer->alive) return false;
    result = localPlayerAsObject ? RValue(localPlayer) : RValue(static_cast<double>(localPlayer->id));
    return true;
}
static bool HhOnKill(CInstance* player, const RValue&) {
    ++attempts;
    lastPlayer = player;
    if (deliveryThrows) throw std::runtime_error("transient game API failure");
    if (deliverySucceeds) ++delivered;
    return deliverySucceeds;
}

#define PERF_SCOPE(counter) ((void)0)
using KillHook = RValue& (*)(CInstance*, CInstance*, RValue&, int, RValue**);
static int originalCalls = 0;
static bool originalRemovesEnemy = false;
static RValue& originalKill(CInstance* self, CInstance*, RValue& result, int, RValue**) {
    ++originalCalls;
    if (originalRemovesEnemy) self->alive = false;
    return result;
}
static KillHook g_Orig_EnemyDestroyKillProc = originalKill;
using PVOID = void*;
static KillHook g_Orig_HhDeathEffects = originalKill;
static volatile long g_HhDeathScriptCalls = 0;
static volatile long g_HhAltTrigger = 0;
static int statusReports = 0;
static double nowMs = 0;
static double HhNowMs() { return nowMs; }
static void HeadhunterStatus(bool includeMap) { if (includeMap) throw std::runtime_error("automatic log included full mapping"); ++statusReports; }
static volatile long g_HhHookCalls = 0, g_HhLastArgc = -1;
static void SignatureDropOnKill(CInstance*) {}
static void AngelicDropOnKill(CInstance*) {}
static bool g_HhHookInstalled = false;
static void* g_OrigICD = nullptr;
static void* g_OrigICL = nullptr;
static bool primaryAvailable = true, fallbackAvailable = true;
static int createInstallCalls = 0;
static bool deathScriptAvailable = true;
static bool HookOneScript(const char*, const char*, PVOID, KillHook* original) {
    *original = deathScriptAvailable ? originalKill : nullptr;
    return deathScriptAvailable;
}
static void InstallHeadhunterHook() { g_HhHookInstalled = primaryAvailable; }
static void InstallCreateHooks() {
    ++createInstallCalls;
    g_OrigICD = fallbackAvailable ? &runner : nullptr;
    g_OrigICL = fallbackAvailable ? &runner : nullptr;
}

// PRODUCTION_FUNCTIONS

static void reset() {
    returnedIdKind = VALUE_REAL;
    g_HhEnabled = true;
    g_HhHandledIds.clear(); g_HhHandledOrder.clear();
    localPlayer = nullptr; localPlayerAsObject = false;
    deliverySucceeds = true; deliveryThrows = false;
    attempts = 0; delivered = 0; lastPlayer = nullptr;
    originalCalls = 0; originalRemovesEnemy = false;
    g_HhHookInstalled = false; g_OrigICD = nullptr; g_OrigICL = nullptr;
    primaryAvailable = true; fallbackAvailable = true; createInstallCalls = 0;
    deathScriptAvailable = true; g_Orig_HhDeathEffects = originalKill; g_HhDeathScriptCalls = 0;
    g_HhHookCalls = 0; g_HhAltTrigger = 0; statusReports = 0; nowMs = 0;
}
static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    CInstance enemy{100,20}, player{200,10}, projectile{300,30}, childPlayer{201,11};
    instances = {&enemy,&player,&projectile,&childPlayer};
    reset();
    const std::string test = argv[1];
    try {
        if (test == "missing_player_retry") {
            HhSteal(&enemy, nullptr, nullptr);
            localPlayer = &player;
            HhSteal(&enemy, nullptr, nullptr);
            require(delivered == 1, "first event without a player consumed the later valid event");
        } else if (test == "failed_buff_retry") {
            deliverySucceeds = false; HhSteal(&enemy, &player, nullptr);
            deliverySucceeds = true; HhSteal(&enemy, &player, nullptr);
            require(delivered == 1 && attempts == 2, "failed buff application permanently consumed the kill");
        } else if (test == "exception_retry") {
            deliveryThrows = true; HhSteal(&enemy, &player, nullptr);
            deliveryThrows = false; HhSteal(&enemy, &player, nullptr);
            require(delivered == 1, "exception permanently consumed the kill");
        } else if (test == "projectile_context") {
            localPlayer = &player;
            HhSteal(&enemy, &projectile, &projectile);
            require(delivered == 1 && lastPlayer == &player, "projectile accepted as the buff player");
        } else if (test == "object_player_reference") {
            localPlayer = &player; localPlayerAsObject = true;
            HhSteal(&enemy, nullptr, nullptr);
            require(delivered == 1, "local player object coerced to a numeric instance id");
        } else if (test == "typed_instance_id_killer") {
            returnedIdKind = VALUE_REF;
            RValue result, killer(static_cast<double>(player.id));
            killer.m_Kind = VALUE_REF;
            RValue* arguments[] = {nullptr,nullptr,&killer};
            Hook_EnemyDestroyKillProc(&enemy,nullptr,result,3,arguments);
            require(delivered == 1 && lastPlayer == &player && originalCalls == 1,
                "runner's typed instance id rejected before buff delivery");
        } else if (test == "typed_instance_id_local_fallback") {
            returnedIdKind = VALUE_REF;
            localPlayer = &player; localPlayerAsObject = true;
            RValue result;
            Hook_HhDeathEffects(&enemy,nullptr,result,0,nullptr);
            require(delivered == 1 && lastPlayer == &player && originalCalls == 1,
                "typed id from local-player lookup silenced all death fallbacks");
        } else if (test == "deduplicate_success") {
            HhSteal(&enemy, &player, nullptr);
            HhSteal(&enemy, nullptr, &player);
            require(delivered == 1 && attempts == 1, "same kill delivered twice");
        } else if (test == "reject_non_enemy") {
            HhSteal(&projectile, &player, nullptr);
            require(delivered == 0, "non-monster event granted a buff");
        } else if (test == "disabled") {
            g_HhEnabled = false; HhSteal(&enemy, &player, nullptr);
            require(delivered == 0 && g_HhHandledIds.empty(), "disabled mechanic consumed an event");
        } else if (test == "player_subclass") {
            HhSteal(&enemy, &childPlayer, nullptr);
            require(delivered == 1 && lastPlayer == &childPlayer, "valid player subclass rejected");
        } else if (test == "bounded_cache") {
            for (int i=0; i<1000; ++i) { enemy.id=1000+i; HhSteal(&enemy,&player,nullptr); }
            require(delivered == 1000 && g_HhHandledIds.size() <= 256 && g_HhHandledOrder.size() <= 256, "unbounded kill cache");
        } else if (test == "capture_before_cleanup") {
            originalRemovesEnemy = true;
            RValue result, killer(&player); RValue* arguments[] = {nullptr,nullptr,&killer};
            Hook_EnemyDestroyKillProc(&enemy,nullptr,result,3,arguments);
            require(delivered == 1 && originalCalls == 1 && !enemy.alive, "enemy was read after original cleanup or original was skipped");
        } else if (test == "player_self_call_shape") {
            RValue result, victim(&enemy); RValue* arguments[] = {nullptr,nullptr,&victim};
            Hook_EnemyDestroyKillProc(&player,nullptr,result,3,arguments);
            require(delivered == 1 && lastPlayer == &player && originalCalls == 1, "player-self kill dispatch lost the victim");
        } else if (test == "kill_without_arguments") {
            localPlayer = &player;
            RValue result;
            Hook_EnemyDestroyKillProc(&enemy,nullptr,result,0,nullptr);
            require(delivered == 1 && originalCalls == 1, "missing arguments silenced the kill hook");
        } else if (test == "death_without_visual_effect") {
            localPlayer = &player;
            RValue result;
            Hook_HhDeathEffects(&enemy,nullptr,result,0,nullptr);
            require(delivered == 1 && originalCalls == 1, "death script required the visual object or primary kill hook");
        } else if (test == "both_death_paths") {
            localPlayer = &player;
            RValue result;
            Hook_HhDeathEffects(&enemy,nullptr,result,0,nullptr);
            Hook_EnemyDestroyKillProc(&enemy,nullptr,result,0,nullptr);
            require(delivered == 1 && originalCalls == 2, "death script and kill proc applied duplicate buffs");
        } else if (test == "automatic_combat_log") {
            HeadhunterActivityTick();
            require(statusReports == 0, "startup noise logged as combat");
            g_HhHookCalls = 1; HeadhunterActivityTick();
            require(statusReports == 1, "combat required manual settings reapply to appear in log");
            g_HhHookCalls = 2; nowMs = 1000; HeadhunterActivityTick();
            require(statusReports == 1, "combat log rate limit failed");
            nowMs = 30000; HeadhunterActivityTick();
            require(statusReports == 2, "new combat summary never flushed");
            nowMs = 60000; HeadhunterActivityTick();
            require(statusReports == 2, "unchanged counters repeatedly logged");
        } else if (test == "disabled_combat_log") {
            g_HhEnabled = false; g_HhHookCalls = 4; HeadhunterActivityTick();
            require(statusReports == 0, "disabled mechanic emitted combat summaries");
#ifdef HAS_ENABLE_HEADHUNTER
        } else if (test == "standalone_fallback_install") {
            EnableHeadhunter();
            require(g_HhEnabled && createInstallCalls == 1 && g_OrigICD && g_OrigICL, "Headhunter relied on another feature to install the fallback");
        } else if (test == "fallback_without_primary") {
            primaryAvailable = false;
            EnableHeadhunter();
            require(g_HhEnabled && !g_HhHookInstalled && g_OrigICD, "usable fallback disabled when primary hook failed");
        } else if (test == "no_trigger_available") {
            primaryAvailable = false; fallbackAvailable = false; deathScriptAvailable = false; g_Orig_HhDeathEffects = nullptr;
            EnableHeadhunter();
            require(!g_HhEnabled, "mechanic advertised as enabled without any trigger");
        } else if (test == "death_script_only") {
            primaryAvailable = false; fallbackAvailable = false; g_Orig_HhDeathEffects = nullptr;
            EnableHeadhunter();
            require(g_HhEnabled && g_Orig_HhDeathEffects, "death script could not act as the sole available trigger");
#endif
        } else return 2;
        std::cout << "PASS " << test << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << test << ": " << error.what() << '\n';
        return 1;
    }
}
