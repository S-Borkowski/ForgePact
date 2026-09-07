# ForgePact 1.3.14

Works together with Hero Siege Item Editor 2.15.3.

## New

- **Angelic / Unholy drops.** Offline the game never rolls for Angelic or Unholy items.
  The Loot tab now has an Angelic / Unholy slider: on every monster kill ForgePact rolls
  its own die, and on a hit the game itself builds one of its 49 real Angelic and Unholy
  uniques (no developer or event pieces) and drops it where the monster died. x2 is one
  die per kill at the Angelic Key's own rate (1 in 7,500); every step above adds a die,
  and you can click the value to type an exact number. x1 is off.

## Fixed

- **Monsters that split on death no longer multiply forever.** The 1.3.13 protection for
  monster-born monsters was not matching them; Tyrant's Crown and Monster Rarity kept
  raising split spiders and worms, and every raised one split again. Fixed and confirmed in
  Corrupted Cave (4-3). Monster Density also leaves spawners spawned by other spawners alone.
- Small clean-ups: the panel's command file is read six times a second instead of every
  frame, and item measurements only run for forged items.

## How to update

Download the zip, unzip it, run ForgePact and press **Install** once. Start the game
after that; a game that was already open keeps the old plugin until it is restarted.

Use ForgePact only with an offline / EAC-disabled copy of Hero Siege.
