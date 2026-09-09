# Headhunter event handling: local verification, 2026-09-10

## Report and evidence boundary

The supplied player log contains 85 enabled Headhunter status snapshots across
30 plugin starts. Every snapshot has zero kill-hook, death-effect and buff
counters. These snapshots were written when settings commands were processed;
the old player build did not periodically record combat counters. They do not
establish that combat happened before the last snapshot. All validation below
was performed locally; no player log is included here.

The log already includes the `deathEffect` field introduced by the 1.3.15
change. Simply assuming the older missing-killer fix was absent is not justified.
The missing optional BloodPact modifier config does not disable the later
`headhunter force` command.

## Locally reproduced failure cases

The actual old C++ dispatch functions were compiled with controlled game API
responses. Six scenarios failed before the source change:

- An event with no resolvable player claimed the enemy ID and blocked a later
  event that did have a player.
- A failed buff attempt claimed the enemy ID permanently.
- An exception after claiming an ID prevented a later retry.
- A projectile in the killer/other context was accepted as the player.
- A supported object-form local player was coerced directly into a numeric ID.
- A non-monster dispatch reached the buff delivery callback.

These are source-level failure reproductions, not proof that the supplied
player's particular session encountered one of those six paths. The test game
API deliberately exercises unsuccessful and alternative supported responses.

## Source changes

- Resolve live instance IDs through the runner, validate player/enemy roles,
  and support both enemy-self and player-self dispatch shapes.
- Read the dying enemy before the original kill-proc can clean up its state.
  Always call the original exactly once; the unrelated drop callbacks are kept.
- Claim an enemy only after a player is resolved. Release a failed delivery's
  claim; retain successful delivery claims so multiple triggers cannot repeat
  the same buffs. The cache stays bounded at 256 enemies.
- Count/label a buff only after its application call reports success. A partial
  success retains the claim, including when a later label operation throws.
- Add the named `EnemyDestroyDeathEffects` script as a fallback independent of
  whether `Enemy_Death_Effect_obj` is created. Keep the visual fallback as well.
- Install Headhunter's own fallback hooks when it is enabled, without depending
  on Density, Tyrant's Crown or Special Content. Remain disabled if no trigger
  can be installed.
- Automatically record compact activity summaries after combat, at most once
  per 30 seconds. Startup-only, unchanged and disabled sessions stay quiet.
  The player no longer needs to reapply settings to produce a combat snapshot.

## Verification performed here

`python -m unittest discover -s tests -v` includes a native C++ test that compiles
the actual dispatch, trigger, enable and activity-summary functions from
`plugin/ModuleMain.cpp`. Only the game API boundary is replaced. Its 21 scenarios
cover delayed player resolution, failed/throwing delivery, context validation,
object references, player subclasses, missing arguments, both call shapes,
original-call ordering, multiple death paths, no visual effect, fallback-only
startup, all triggers missing, disabled behavior, bounded memory and log throttling.

The complete plugin also compiles with `FORGEPACT_RELEASE` into an isolated test
output directory. The shipped plugin DLL, installed game EXE and distributed
ForgePact EXE are not replaced. No release packaging or upload is performed.

Read-only native inspection verified the fallback routine's presence in the
local clean executable with SHA-256
`c6ecc069cfc02e105c988d48f9469f4e2e6260ad44c41dab8001f2612b8b3db4`:
`EnemyDestroyKillProc` at RVA `0x188c330` and `EnemyDestroyDeathEffects` at
`0x187dba0`. Raw disassembly and game data are not part of this document.

This patch has not been newly exercised in a live game session. Older local
game logs demonstrate that the earlier primary path did apply buffs locally,
but those logs are not presented as tests of this patch. A passing API-boundary
test or compilation is not a claim that every game build's hooks are verified,
or that the supplied player's exact root cause has been proven.
