#!/usr/bin/env python3
"""Contract tests for the Pet Quest Collector mod scaffolding.

See ForgePact/docs/pet-quest-collector-plan.md. As of 2026-09-10 this mod is
scaffolding only: the toggle, panel row, and a read-only candidate-counting
tick exist, but the actual collect call and accepted-quest gate are pending a
live-game research pass (Phase 0 in the plan) that cannot be done from a pure
Python/static test. These tests pin the baseline (mod off -> zero overhead,
matching test_release_hook_contract.py's all-off invariant) and the
scaffolding target (toggle reaches the plugin and is armed correctly) without
asserting behavior nobody has measured yet.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FORGEPACT_DIR = REPO_ROOT / "ForgePact"
SRC_DIR = FORGEPACT_DIR / "src"
PLUGIN_SRC = FORGEPACT_DIR / "plugin" / "ModuleMain.cpp"
FORGEPACT_INCLUDE_DIR = FORGEPACT_DIR / "plugin" / "include" / "ForgePact"
SDK_PY_PATH = REPO_ROOT / "hs-game-sdk" / "python"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(SDK_PY_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PY_PATH))

import forgepact  # noqa: E402


class TestPetQuestCollectorContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plugin_code = PLUGIN_SRC.read_text(encoding="utf-8")
        cls.panel_code = (SRC_DIR / "forgepact.py").read_text(encoding="utf-8")
        cls.header = (FORGEPACT_INCLUDE_DIR / "PetQuestCollectorMod.hpp").read_text(encoding="utf-8")

    # ---- baseline: mod off, zero overhead --------------------------------

    def test_defaults_has_pet_quest_pickup_off(self):
        self.assertIn("mod_pet_quest_pickup", forgepact.DEFAULTS)
        self.assertFalse(forgepact.DEFAULTS["mod_pet_quest_pickup"])

    def test_build_cmds_omits_petquest_when_disabled(self):
        cfg = dict(forgepact.DEFAULTS)
        cfg["mod_pet_quest_pickup"] = False
        self.assertNotIn("petquest 1", forgepact.build_cmds(cfg))

    def test_no_hook_is_installed_by_the_collect_tick(self):
        # Unlike relicfilter, the plan says no hook is needed for the actual
        # collect mechanism (Phase 2), so there must be no arm/pending
        # lifecycle for it in PetQuestCollectorTick specifically. A separate,
        # research-only CheckPlayerInteraction *trace* hook (Phase 0.1, purely
        # observational - see test_citrace_* below) is a deliberate exception
        # and lives outside the tick.
        tick = self.plugin_code.split("static void PetQuestCollectorTick()", 1)[1]
        tick = tick[:tick.index("static void PetQuestCollectorStats()")]
        self.assertNotIn("HookOneScript", tick)

    def test_citrace_hooks_are_research_build_only_and_read_only(self):
        # Phase 0.1: the single gating measurement. Must never ship, and must
        # never influence whether an interaction succeeds - it only observes.
        # MEASURED 2026-09-10: CheckPlayerInteraction (the plan's assumed
        # name) never fired on a real collect, so this traces several
        # UseKey-/Interact-/Pickup-shaped candidates at once instead of one.
        self.assertIn("#define CITRACE_HOOK_NAMED(SAFE, SCRIPTNAME)", self.plugin_code)
        macro_body = self.plugin_code.split("#define CITRACE_HOOK_NAMED(SAFE, SCRIPTNAME)", 1)[1][:900]
        self.assertIn("g_OrigCi_##SAFE ? g_OrigCi_##SAFE(S, O, R, argc, A) : R", macro_body)
        for candidate in ("CheckPlayerInteraction", "CheckUseKey", "PlayerInteracting", "LootBlocksUseKey", "PickupLoot"):
            self.assertIn(f"CITRACE_HOOK({candidate})", self.plugin_code)
            self.assertIn(f'HookOneScript("{candidate}"', self.plugin_code)
        # Plan §3's "one chokepoint" finding: the only script-table entries
        # inside Quest_Object_Parent_obj's own Create event, traced once the
        # five named candidates above measured 0 calls on a real collect.
        for anon_id in ("1400", "1584", "2113", "2786", "3858", "4737", "5164"):
            script_name = f"anon@{anon_id}@gml_Object_Quest_Object_Parent_obj_Create_0"
            self.assertIn(f'HookOneScript("{script_name}"', self.plugin_code)
        guard = self.plugin_code.split("static std::atomic<bool> g_CiTraceOn{ false };", 1)[0][-300:]
        self.assertIn("#ifndef FORGEPACT_RELEASE", guard)
        self.assertIn('lc == "citrace"', self.plugin_code)

    def test_citrace_builtin_variant_is_read_only_and_filtered(self):
        # Plan B2 variant: all 12 named-script hooks measured 0 calls, so this
        # hooks keyboard_check_pressed/mouse_check_button_pressed directly.
        # Must still be pass-through (original always called first, result
        # never modified) and must not log unconditionally - both builtins
        # are far hotter than any named script here.
        for builtin in ("keyboard_check_pressed", "mouse_check_button_pressed"):
            self.assertIn(f'HookBuiltin("{builtin}"', self.plugin_code)
        # Window widened 2026-09-11: the Phase C1 stack-walk hook-in and its
        # rationale comment sit between the pass-through call and the filter,
        # so a 700-char slice no longer reaches kCiBuiltinFirstN.
        kcp = self.plugin_code.split("static void Hook_Ci_KeyboardCheckPressed(", 1)[1][:1800]
        self.assertIn("if (g_OrigCi_KeyboardCheckPressed) g_OrigCi_KeyboardCheckPressed(Result, S, O, argc, Args);", kcp)
        self.assertIn("kCiBuiltinFirstN", kcp)
        self.assertIn("CiKeyLooksLikeInteract", kcp)
        mcbp = self.plugin_code.split("static void Hook_Ci_MouseCheckButtonPressed(", 1)[1][:500]
        self.assertIn("if (g_OrigCi_MouseCheckButtonPressed) g_OrigCi_MouseCheckButtonPressed(Result, S, O, argc, Args);", mcbp)

    def test_tick_only_runs_while_enabled(self):
        gate = self.plugin_code.split("PetQuestCollectorTick();", 1)[0][-400:]
        self.assertIn("PetQuestCollectorMod::Instance().IsEnabled()", gate)

    # ---- target: toggle scaffolding reaches the plugin --------------------

    def test_build_cmds_emits_petquest_when_enabled(self):
        cfg = dict(forgepact.DEFAULTS)
        cfg["mod_pet_quest_pickup"] = True
        self.assertIn("petquest 1", forgepact.build_cmds(cfg))

    def test_petquest_is_a_player_command(self):
        # Classic failure mode per the plan: a release build silently rejects
        # an unlisted command, so the toggle would appear to work and do
        # nothing.
        self.assertIn('"petquest"', self.plugin_code)
        commands_block = self.plugin_code.split("kPlayerCommands = {", 1)[1][:800]
        self.assertIn("petquest", commands_block)

    def test_header_declares_enabled_flag(self):
        self.assertIn("std::atomic<bool> m_Enabled{ false };", self.header)

    def test_plugin_handles_petquest_command(self):
        self.assertIn('lc == "petquest"', self.plugin_code)
        self.assertIn("PetQuestCollectorMod::Instance().SetEnabled(", self.plugin_code)

    def test_petquest_has_exactly_one_command_branch(self):
        self.assertEqual(self.plugin_code.count('lc == "petquest"'), 1)

    def test_petquest_stat_is_research_build_only(self):
        branch = self.plugin_code.split('lc == "petquest"', 1)[1][:400]
        self.assertIn("#ifndef FORGEPACT_RELEASE", branch)
        self.assertIn('pv == "stat"', branch)

    def test_html_contains_mods_tab_control(self):
        self.assertIn('data-tab="mods"', forgepact.HTML)
        self.assertIn('id="mod_pet_quest_pickup"', forgepact.HTML)
        self.assertIn("Pet collects quest items", forgepact.HTML)

    def test_control_lives_in_the_mods_tab(self):
        html = forgepact.HTML
        pos = html.index('id="mod_pet_quest_pickup"')
        tab_start = html.rfind('data-tab="', 0, pos)
        self.assertNotEqual(tab_start, -1)
        tab = html[tab_start + len('data-tab="'): html.index('"', tab_start + len('data-tab="'))]
        self.assertEqual(tab, "mods")

    def test_panel_sends_live_command_when_toggled(self):
        self.assertIn('key == "mod_pet_quest_pickup"', self.panel_code)
        self.assertIn('f"petquest {1 if cfg[\'mod_pet_quest_pickup\'] else 0}"', self.panel_code)

    # ---- hierarchy: guards the collector's target set against a future ----
    # ---- hs-game-sdk regeneration that changes the object hierarchy.   ----

    def test_collector_targets_the_quest_object_family(self):
        self.assertIn("Quest_Object_Parent_obj", self.plugin_code)
        family_tick = self.plugin_code.split("static void PetQuestCollectorTick()", 1)[1][:2200]
        self.assertIn("instance_number", family_tick)
        self.assertIn("instance_find", family_tick)
        self.assertIn("g_QuestObjParentIdx", family_tick)

    def test_named_non_carriable_props_are_excluded(self):
        # Plan §11: these three are confirmed members of the family that are
        # not carriable quest items.
        for excluded in ("Civilian_NPC_obj", "Boat_Quest_obj", "Black_Hole_Quest_obj"):
            self.assertIn(excluded, self.plugin_code)

    def test_excluded_family_members_really_are_descendants(self):
        # If hs-game-sdk regenerates and one of these stops being a descendant
        # of Quest_Object_Parent_obj, the exclusion list documented in the
        # header/plugin comments is stale - fail here, not silently in-game.
        try:
            from hs_game_sdk import is_descendant_of
        except ImportError:
            self.skipTest("hs_game_sdk python bindings not importable")
        for excluded in ("Civilian_NPC_obj", "Boat_Quest_obj", "Black_Hole_Quest_obj"):
            self.assertTrue(
                is_descendant_of(excluded, "Quest_Object_Parent_obj"),
                f"{excluded} is no longer a Quest_Object_Parent_obj descendant - "
                "update the plugin's exclusion list and this test",
            )

    def test_props_outside_the_family_are_not_targeted(self):
        # These sit outside Quest_Object_Parent_obj (plan §3) and must not be
        # enumerated by the collector at all.
        try:
            from hs_game_sdk import is_descendant_of
        except ImportError:
            self.skipTest("hs_game_sdk python bindings not importable")
        for outside in (
            "Quest_Potion_Cauldron_obj",
            "Quest_Naga_Temple_Pedestal_obj",
            "Quest_Monster_Spawner_obj",
            "Quest_Manager_obj",
            "Quest_Object_Collision_obj",
        ):
            self.assertFalse(is_descendant_of(outside, "Quest_Object_Parent_obj"))

    # ---- honesty: the collect mechanism must not silently claim to work ---

    def _tick(self):
        tick = self.plugin_code.split("static void PetQuestCollectorTick()", 1)[1]
        return tick[: tick.index("static void PetQuestCollectorStats()")]

    # Superseded test_collect_call_is_not_yet_implemented, which asserted the
    # tick still carried its TODO and mutated nothing. That gate existed to
    # hold the line until a mechanism was confirmed AND the objective was seen
    # to advance. Both happened on 2026-09-11 (quest counter 7/15 -> 8/15), so
    # the gate has done its job and is replaced by the invariants that keep
    # the now-live collect honest.

    def test_tick_collects_only_through_the_confirmed_call(self):
        # One call shape in this file, and it is the measured one. If the tick
        # ever grows a second way to remove a quest item, that is a bug.
        tick = self._tick()
        self.assertIn("PetQuestCollectOne", tick)
        self.assertNotIn("instance_destroy", tick)
        self.assertNotIn("instance_deactivate", tick)
        self.assertNotIn("CallGameScriptEx", tick)
        body = self._function_body("PetQuestCollectOne")
        self.assertIn("InvokeMethodValueNative", body)
        self.assertIn("m_Questpickup", body)

    def test_tick_reapplies_the_games_own_gates_per_item(self):
        # canPickup and lootType == 0 are the game's own gates. They must be
        # re-read from the live instance at collect time, never cached from
        # selection - an item can stop being collectable while the pet walks.
        gate = self._function_body("PetQuestItemIsCollectable")
        self.assertIn("canPickup", gate)
        self.assertIn("lootType", gate)
        self.assertIn("m_Questpickup", gate)
        collect = self._function_body("PetQuestCollectOne")
        self.assertIn("PetQuestItemIsCollectable", collect)

    def test_tick_uses_the_measured_other_not_the_player(self):
        # `other` = Loot_Manager_obj was measured; the static read guessed the
        # player and was wrong. Pinned so it cannot drift back to the guess,
        # and the collect refuses rather than substituting when none is live.
        collect = self._function_body("PetQuestCollectOne")
        self.assertIn("g_LootManagerObjIdx", collect)
        self.assertIn("g_PetQuestNoLootMgr", collect)

    def test_tick_collects_one_item_at_a_time_with_a_cooldown(self):
        # Plan §4 rule 4 as a shipped behaviour: the tick walks the pet to one
        # target and collects it, rather than sweeping every item on screen in
        # a single frame.
        tick = self._tick()
        self.assertIn("g_PetQuestCooldown", tick)
        self.assertIn("PetQuestPhase::Travel", tick)
        self.assertEqual(tick.count("PetQuestCollectOne("), 2)  # arrival + timeout, no sweep

    def test_pet_must_be_out_for_the_mod_to_collect(self):
        # It is "the pet collects quest items". No pet, no collecting - which
        # also keeps it from running in menus and cutscenes.
        tick = self._tick()
        self.assertIn("g_CompanionObjIdx", tick)
        self.assertIn("VALUE_UNDEFINED", tick)

    def test_collect_argument_is_the_measured_value_and_tunable(self):
        # 1 is what the real collect passed. What m_Questpickup does with it
        # was never read, so it is reproduced rather than inferred - and it is
        # adjustable live so a multi-value item can be tested without a build.
        self.assertIn("g_PetQuestArg{ 1.0 }", self.plugin_code)
        dispatch = self.plugin_code.split('lc == "petquest"', 1)[1][:1600]
        self.assertIn('pv.rfind("arg", 0)', dispatch)


    # ---- Plan C Phase C0: research tooling that INVOKES game code ---------
    # docs/pet-quest-collector-plan-c-direct-invocation.md. Every prior phase
    # of this investigation was read-only; C0.2 onward is the first code in it
    # that can remove a quest item without crediting its objective, which the
    # original plan's §11 calls worse than no mod at all. These tests pin the
    # invariants that make that acceptable: it can never reach a player build,
    # it can never fire without an explicit confirmation token, and it always
    # reports enough to tell "the objective advanced" from "the item vanished".

    C0_MUTATING_HELPERS = (
        "CiInvokeMethodValue",
        "CiInvokeItemMethod",
        "CiInvokeGlobalMethod",
        "CiEventPerform",
        "CiActivateObject",
    )
    C0_READONLY_HELPERS = (
        "CiDumpNearestQuestItem",
        "CiReportMethods",
        "CiDumpNamedObject",
        "CiDumpPlayer",
        "CiReportHoverGlobals",
        "CiSweepGlobals",
    )

    def _citrace_dispatch(self):
        """The body of the `citrace` command branch in RunCommand."""
        branch = self.plugin_code.split('lc == "citrace"', 1)[1]
        return branch[: branch.index("#endif")]

    def _citrace_subcommand(self, sub):
        """The whole `if (subLc == "<sub>") { ... }` block, to its closing."""
        dispatch = self._citrace_dispatch()
        block = dispatch.split(f'subLc == "{sub}"', 1)[1]
        nxt = block.find('        if (subLc == "')
        return block if nxt == -1 else block[:nxt]

    def _function_body(self, name):
        """Source of `static <ret> name(...) { ... }` up to the next top-level static.

        Skips forward declarations: several of these helpers are declared
        early (so an earlier hook can call them) and defined much later, and
        matching the declaration would silently test an empty body.
        """
        needle = f" {name}("
        pos = -1
        while True:
            pos = self.plugin_code.find(needle, pos + 1)
            self.assertNotEqual(pos, -1, f"no definition of {name} found")
            after = self.plugin_code[pos:]
            head = after[: after.index("\n{")] if "\n{" in after[:2000] else ""
            if head and ";" not in head:
                break
        end = after.index("\nstatic ", 1)
        return after[:end]

    def test_c0_tooling_exists_for_every_checklist_item(self):
        # C0.1-C0.6 each need a subcommand; C0.7 deliberately needs no new
        # code (petquest stat already counts what it asks for). Batched into
        # one build per agents.md's "hook every candidate in the same build"
        # rule and the plan's §6 live-session cost row - seven checklist
        # items, one relaunch, not seven.
        dispatch = self._citrace_dispatch()
        for sub in ("item", "methods", "dumpobj", "player", "globals", "sweep",
                    "invoke", "event", "eventobj", "activate"):
            self.assertIn(f'subLc == "{sub}"', dispatch, f"citrace {sub} is missing")

    def test_c0_tooling_is_research_build_only(self):
        # Same invariant test_release_hook_contract.py enforces globally,
        # asserted here against the specific helpers that can mutate quest
        # state: for each, the nearest preceding preprocessor directive must
        # be the guard opening, not a guard that already closed.
        for helper in self.C0_MUTATING_HELPERS + self.C0_READONLY_HELPERS:
            definition = self.plugin_code.index(f"static void {helper}(")
            before = self.plugin_code[:definition]
            self.assertGreater(
                before.rindex("#ifndef FORGEPACT_RELEASE"),
                before.rindex("#endif"),
                f"{helper} is outside the FORGEPACT_RELEASE guard - it would compile into a player build",
            )

    def test_citrace_is_not_a_player_command(self):
        # The classic failure mode inverted: `citrace` must NOT be in
        # kPlayerCommands, so even a hand-written cmd.txt cannot reach any of
        # this from a shipped build.
        commands_block = self.plugin_code.split("kPlayerCommands = {", 1)[1]
        commands_block = commands_block[: commands_block.index("}")]
        self.assertNotIn("citrace", commands_block)

    def test_every_mutating_c0_subcommand_requires_confirm(self):
        # Plan §4: a literal `confirm` token, so a stray or half-pasted line
        # in cmd.txt fails closed instead of invoking unverified game code.
        for sub in ("invoke", "event", "eventobj", "activate"):
            self.assertIn(
                "CiConfirmed(",
                self._citrace_subcommand(sub),
                f"citrace {sub} can fire without confirmation",
            )

    def test_confirm_gate_fails_closed(self):
        # CiConfirmed must reject anything that is not the literal word, and
        # must be what prints the safety banner - so the plan's manual
        # preconditions are stated before the first mutation, every session.
        gate = self._function_body("CiConfirmed")
        self.assertIn('Lower(token) == "confirm"', gate)
        self.assertIn("CiSafetyBanner();", gate)
        self.assertIn("return false;", gate)

    def test_read_only_c0_subcommands_do_not_require_confirm(self):
        # The inverse invariant: gating the read-only dumps behind `confirm`
        # too would train the tester to type it reflexively, which is exactly
        # how the gate stops working.
        for sub in ("item", "methods", "player", "globals"):
            self.assertNotIn("CiConfirmed(", self._citrace_subcommand(sub))

    def test_mutations_report_item_flags_and_progress_before_and_after(self):
        # Plan §4 rule 3 and §6's second risk row: an item vanishing without
        # its objective advancing is worse than no mod, so every mutating
        # command must capture the marker flags and a progress read on both
        # sides, not just observe the disappearance.
        for helper in ("CiInvokeMethodValue", "CiEventPerform"):
            body = self._function_body(helper)
            self.assertGreaterEqual(body.count("CiItemFlags("), 2, f"{helper} lacks before/after flags")
            self.assertIn("CiQuestFamilyCount()", body)
            self.assertIn("CiQuestProgressReport(", body)

    def test_invoke_tries_paths_as_fallbacks_never_as_a_sequence(self):
        # Plan §4 rule 4: "one item, one call, one observation". The candidate
        # invocation paths guard each other with `called`, and nothing here
        # may iterate the six m_Quest* names - that list belongs to the
        # read-only reporter alone.
        body = self._function_body("CiInvokeMethodValue")
        self.assertIn("bool called = false, hitAv = false;", body)
        # The candidate paths are walked in order and abandoned the moment one
        # completes - that break is what keeps this one call, not nine.
        self.assertIn("for (const CiInvokePathInfo& p : kCiInvokePaths)", body)
        self.assertIn("if (r == CiPathResult::Invoked) { called = true; break; }", body)
        # Every path the 2026-09-11 session measured must still be offered.
        runner = self._function_body("CiRunInvokePath")
        for path in ('CallBuiltin("script_execute"', 'CallBuiltinEx(res, "script_execute"',
                     'CallBuiltin("method_get_index"', 'CallBuiltin("method_call"',
                     "CallGameScript(full", "CallGameScriptEx(res, full",
                     "InvokeWithObject(objectType"):
            self.assertIn(path, runner)
        for helper in ("CiInvokeMethodValue", "CiInvokeItemMethod", "CiInvokeGlobalMethod"):
            self.assertNotIn("kCiQuestMethodNames", self._function_body(helper))

    def test_with_context_enumerates_by_type_but_acts_on_one_instance(self):
        # MEASURED 2026-09-11: InvokeWithObject's Object parameter is an
        # object TYPE index, not a specific instance's id (confirmed live -
        # passing an instance id produced AURIE_OBJECT_NOT_FOUND). So this
        # path may enter the callback once per live instance of that type in
        # the room, not just the hovered one - the id-match guard is what
        # keeps plan 4 rule 4 ("one item, one call") true regardless: every
        # non-matching instance must be skipped, and the real target acted on
        # at most once even if entered more than once.
        runner = self._function_body("CiRunInvokePath")
        self.assertIn("bool ok = false, av = false, matched = false;", runner)
        self.assertIn("if (matched) return;", runner)
        self.assertIn("if (sid.ToDouble() != targetId) return;", runner)
        self.assertIn("matched = true;", runner)

    def test_auto_stops_at_the_first_access_violation(self):
        # MEASURED 2026-09-11: every cold call shape faults inside the game's
        # own code. Walking all nine by default would trigger nine access
        # violations in the runtime to learn nothing, so `auto` stops at the
        # first and only an explicit `all` sweeps past it.
        body = self._function_body("CiInvokeMethodValue")
        self.assertIn('const bool sweepAll = (pref == "all");', body)
        self.assertIn("if (r == CiPathResult::AccessViolation && !sweepAll) { hitAv = true; break; }", body)
        runner = self._function_body("CiRunInvokePath")
        self.assertIn("CiPathResult::AccessViolation", runner)

    def test_the_measured_call_shape_is_offered_first(self):
        # Superseded test_with_context_path_is_offered_first. That one pinned
        # InvokeWithObject first because it was the last *untried* shape; it
        # has since been tried and is negative, and a live round (citrace
        # nativetrace, 2026-09-11) measured what the game actually does -
        # the runtime's call-a-method-value helper, with the item as self.
        # An `auto` run must reach the shape known to work before spending
        # faults on the nine measured-negative ones.
        table = self.plugin_code.split("kCiInvokePaths[] = {", 1)[1]
        table = table[: table.index("};")]
        first = table.strip().splitlines()[0]
        self.assertIn('"native"', first)
        self.assertIn("NativeMethodValue", first)
        # The disproven shapes stay available so a future session can re-run
        # them without a rebuild - they are demoted, not deleted.
        self.assertIn('"with"', table)
        self.assertIn('"scriptex"', table)

    def test_invoke_accepts_arguments(self):
        # Every call in the first live round passed zero arguments, which is
        # the most likely reason a script dereferencing arg[0] would fault.
        # Nothing reports a script's arity, so arguments have to be suppliable
        # by hand.
        parser = self._function_body("CiParseInvokeArg")
        for keyword in ('lc == "player"', 'lc == "item"', 'lc == "noone"'):
            self.assertIn(keyword, parser)
        self.assertIn("const std::vector<RValue>& extraArgs", self._function_body("CiInvokeMethodValue"))

    def test_invoke_reports_why_a_path_failed(self):
        # The first version printed a bare "EXCEPTION" for every failure, which
        # cost a full live round to narrow down by hand (2026-09-11). Each path
        # must now say which call threw and, where the runtime provides one,
        # what it said.
        runner = self._function_body("CiRunInvokePath")
        self.assertIn("catch (const std::exception& e)", runner)
        self.assertIn("e.what()", runner)
        self.assertIn("catch (...)", runner)

    def test_progress_read_uses_the_call_form_that_works(self):
        # MEASURED 2026-09-11: CallGameScriptEx throws in this runtime while
        # the non-Ex CallGameScript works. The progress read must use the
        # working form, and must keep saying the signature is unverified.
        body = self._function_body("CiQuestProgressReport")
        self.assertIn("CallGameScript(scr", body)
        # The call form, not the word - the comment above it explains why the
        # Ex variant is avoided and legitimately names it.
        self.assertNotIn("g_Yytk->CallGameScriptEx", body)
        self.assertIn("unverified sig", body)

    # ---- Plan C Phase C1: native-analysis infrastructure -----------------

    def test_c1_tools_are_research_build_only(self):
        # symdump writes a full symbol table and stackwalk captures return
        # addresses - both are pure research instrumentation and must never
        # reach a player build. Same guard check as the C0 helpers.
        for helper in ("SymDump", "CiCaptureStackWalk"):
            definition = self.plugin_code.index(f"static void {helper}(")
            before = self.plugin_code[:definition]
            self.assertGreater(
                before.rindex("#ifndef FORGEPACT_RELEASE"),
                before.rindex("#endif"),
                f"{helper} is outside the FORGEPACT_RELEASE guard",
            )
        # Both are reached through `citrace`, which is not a player command,
        # so there is no second door into them either.
        dispatch = self._citrace_dispatch()
        self.assertIn('subLc == "symdump"', dispatch)
        self.assertIn('subLc == "stackwalk"', dispatch)

    def test_symdump_bounds_its_frame_cost(self):
        # It runs inside one FrameCallback, so an unbounded index sweep would
        # be a visible stall. The range is capped and pageable instead.
        body = self._function_body("SymDump")
        self.assertIn("kMaxSpan", body)
        self.assertIn("script_get_name", body)
        self.assertIn("GetNamedRoutinePointer", body)

    def test_stackwalk_is_armed_not_always_on(self):
        # It fires from inside a hot builtin hook, so it must cost one atomic
        # load when idle and must be an explicit, counted-down request rather
        # than something that logs on every keypress.
        body = self._function_body("CiCaptureStackWalk")
        self.assertIn("g_CiStackWalkLeft", body)
        self.assertIn("RtlCaptureStackBackTrace", body)
        hook = self.plugin_code.split("static void Hook_Ci_KeyboardCheckPressed(", 1)[1][:1800]
        self.assertIn("CiCaptureStackWalk(", hook)

    # ---- citrace collect: Phase C2's gate, the measured call --------------

    def test_collect_requires_confirm_and_reports_both_sides(self):
        # It is the first command that can credit a quest objective, so it is
        # gated exactly like the other mutating ones, and it reports flags and
        # progress on both sides via the shared invoke reporter.
        block = self._citrace_subcommand("collect")
        self.assertIn("CiConfirmed", block)
        self.assertIn("CiCollectNearestQuestItem", block)
        body = self._function_body("CiCollectNearestQuestItem")
        self.assertIn("CiInvokeMethodValue", body)

    def test_collect_reproduces_the_measured_context_not_a_guess(self):
        # The live round measured self=item, other=Loot_Manager_obj, one real
        # argument. `other` was the part the static read got wrong (it said
        # the player), so it is pinned here against regressing to the guess.
        body = self._function_body("CiCollectNearestQuestItem")
        self.assertIn("Loot_Manager_obj", body)
        self.assertIn("m_Questpickup", body)
        self.assertNotIn("other=player", body)

    def test_collect_defaults_to_the_measured_path_and_argument(self):
        # Default path `native` and default argument 1, both as measured. A
        # tester can override either, but the default must not drift to an
        # untested shape.
        block = self._citrace_subcommand("collect")
        self.assertIn('"native"', block)
        body = self._function_body("CiCollectNearestQuestItem")
        self.assertIn("args.push_back(RValue(1.0))", body)

    def test_collect_reproduces_the_games_own_gates(self):
        # The real call site gates on canPickup and lootType == 0. Calling
        # m_Questpickup on an item the game would have skipped is precisely
        # how an objective gets credited for something uncollectable, so both
        # gates are reproduced and the command refuses rather than proceeding.
        body = self._function_body("CiCollectNearestQuestItem")
        self.assertIn("canPickup", body)
        self.assertIn("lootType", body)
        self.assertEqual(body.count("refused"), 2)

    def test_collect_is_research_build_only(self):
        for helper in ("CiCollectNearestQuestItem", "CiFirstInstanceOfObject"):
            definition = self.plugin_code.index(f" {helper}(")
            before = self.plugin_code[:definition]
            self.assertGreater(
                before.rindex("#ifndef FORGEPACT_RELEASE"),
                before.rindex("#endif"),
                f"{helper} is outside the FORGEPACT_RELEASE guard",
            )

    def test_native_path_uses_the_measured_helper_address(self):
        # The call goes to the runtime helper the live round trampolined
        # through, at the RVA read off its decompiled body - and the address
        # is printed on every call so a build mismatch surfaces as a wrong
        # address rather than a crash.
        self.assertIn("kQuestPickupCallFnRva = 0xB489070ull", self.plugin_code)
        paths = self._function_body("CiRunInvokePath")
        self.assertIn("kCiCallMethodFnRva", paths)
        self.assertIn("exe+0x%llX", paths)
        # The research command and the shipped mod must make the identical
        # call, or a green `citrace collect` stops being evidence about the
        # mod - so the research path routes through the shipped helper.
        self.assertIn("InvokeMethodValueNative", paths)

    # ---- citrace nativetrace: the instrument the table hooks could not be --

    def test_nativetrace_exists_and_is_read_only(self):
        # The confirmation step the static read calls for (research doc,
        # "Reading the compiled code" §10). It only counts and logs, so unlike
        # the C0.2 invoke path it must NOT sit behind the confirm gate - that
        # gate is for mutation, and there is none here.
        block = self._citrace_subcommand("nativetrace")
        self.assertIn("CiNativeTraceInstall", block)
        self.assertIn("CiNativeTraceReport", block)
        self.assertNotIn("confirm", block)

    def test_nativetrace_is_research_build_only(self):
        for helper in ("CiNativeTraceInstall", "CiNativeTraceReport", "CiNativeTraceReset"):
            definition = self.plugin_code.index(f"static void {helper}(")
            before = self.plugin_code[:definition]
            self.assertGreater(
                before.rindex("#ifndef FORGEPACT_RELEASE"),
                before.rindex("#endif"),
                f"{helper} is outside the FORGEPACT_RELEASE guard",
            )

    def test_nativetrace_patches_the_address_not_the_script_table(self):
        # The whole point. HookOneScript assigns m_ScriptFunction, which a
        # compile-time-bound `call rel32` never reads - that is why every
        # table hook on this chain measured 0. The native path must use
        # MmCreateHook (patches the bytes at the function itself) and must not
        # touch the table entry.
        body = self._function_body("CiNativeTraceInstall")
        self.assertIn("MmCreateHook", body)
        self.assertNotIn("m_ScriptFunction", body)

    def test_nativetrace_never_patches_our_own_table_detour(self):
        # If `citrace 1` ran first, the script-table entry holds this plugin's
        # table-swap detour, not the game's function. Patching that would
        # produce a hook that fires only when the blind hook fires, i.e.
        # never - silently reproducing the very artefact being tested for.
        body = self._function_body("CiNativeAddressOf")
        self.assertIn("tableOrig", body)
        prefer = body.index("tableOrig")
        lookup = body.index("GetNamedRoutinePointer")
        self.assertLess(prefer, lookup, "the saved original must be preferred over the live table entry")

    def test_nativetrace_reports_both_counters(self):
        # The comparison is the measurement: a native count that climbs while
        # the table count stays at 0 is what demonstrates the blindness,
        # rather than merely asserting it.
        body = self._function_body("CiNativeTraceReport")
        self.assertIn("nativeCalls", body)
        self.assertIn("tableCalls", body)

    def test_nativetrace_keeps_a_control_target(self):
        # CheckPlayerInteraction runs from every interactable's Step event, so
        # it must fire constantly. If it did not, the new instrument would be
        # as suspect as the old one - so it has to be among the targets.
        targets = self.plugin_code.split("g_CiNatTargets[] = {", 1)[1]
        targets = targets[: targets.index("};")]
        self.assertIn("CheckPlayerInteraction", targets)
        for name in ("PlayerMouseAction", "update_quest", "anon@2786@"):
            self.assertIn(name, targets, f"{name} is missing from the native trace targets")

    def test_nativetrace_bounds_its_logging_per_target(self):
        # One of these detours sits on a hot path. A shared budget would let
        # it drown out.txt before the interesting one-shot call is logged, so
        # each target gets its own small budget and always keeps counting.
        self.assertIn("kCiNatLogBudget", self.plugin_code)
        macro = self.plugin_code.split("#define CINATIVE_HOOK(", 1)[1]
        macro = macro[: macro.index("CINATIVE_HOOK(PlayerMouseAction")]
        self.assertIn("g_CiNatLogged_", macro)
        self.assertIn("InterlockedIncrement(&g_CiNatCalls_", macro)

    def test_collect_call_still_absent_from_the_tick(self):
        # C0 is research tooling only. Nothing in it may leak into
        # PetQuestCollectorTick until a live round confirms a mechanism AND
        # the objective advancing (plan Phase C2).
        tick = self.plugin_code.split("static void PetQuestCollectorTick()", 1)[1]
        tick = tick[: tick.index("static void PetQuestCollectorStats()")]
        for helper in self.C0_MUTATING_HELPERS:
            self.assertNotIn(helper, tick)
        self.assertNotIn("event_perform", tick)
        self.assertNotIn("script_execute", tick)


if __name__ == "__main__":
    unittest.main()
