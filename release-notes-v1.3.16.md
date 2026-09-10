# ForgePact 1.3.16

## Headhunter fixes

Headhunter could stay inactive even with the plugin correctly installed and its
kill callbacks firing. On the inspected Steam build, the bundled YYToolkit's
player lookup read an incompatible room layout and failed to find the player.
ForgePact now uses the game's own instance resolver for this lookup and checks
that it returned the intended live player. It also accepts the typed instance
IDs returned by the current runner.

- Failed player lookups or buff calls no longer permanently consume a monster's
  Headhunter trigger. Successful deliveries still prevent duplicate buffs from
  multiple death callbacks.
- A separate monster-death callback provides a fallback when the usual kill or
  visual death-effect callback is unavailable.
- Combat activity summaries are logged automatically to help diagnose failures.

The panel executable is unchanged. The corrected `BloodPactPlugin.dll` is included
in this package; existing settings are retained.

## Verification

48 automated test methods passed, including 27 native C++ dispatch scenarios.
The full release-mode plugin compiled, and the packaged panel passed its
WebView2/UI/API startup check with an isolated profile. The player lookup and
identity checks also passed against the actual game functions executed in an
isolated memory copy.

**Live combat with this corrected DLL has not yet been verified.** These results
verify the observed lookup failure and its replacement, not every gameplay path
or every Hero Siege build.

## How to update

1. Close Hero Siege and the old ForgePact window.
2. Download and extract `ForgePact-1.3.16.zip`. Keep the whole folder together.
3. Open `ForgePact.exe` from the new folder, check Game Location, and click
   **Install Mod Plugin**.
4. Start Hero Siege again and enable Headhunter as usual.

Opening the new panel alone does not update the installed plugin. The game must
be restarted after installation to load the new DLL.
