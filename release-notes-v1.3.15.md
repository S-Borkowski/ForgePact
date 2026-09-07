# ForgePact 1.3.15

Works together with Hero Siege Item Editor 2.15.3.

## Fixed

- **Tyrant's Crown and Monster Rarity did nothing in 1.3.14.** The protection added for
  monsters that split when they die was far too wide: it also covered every monster the
  game's own spawners create, which is nearly all of them, so no monster was ever raised.
  Measured before the fix: 3370 monsters, 0 raised. After: 790 monsters, 63 raised to rare
  and 106 given an extra affix. The protection now only covers monsters that another
  monster spawned, which is what it was meant to do.

## Also

- The Headhunter status line now reports how often the game's kill event reached ForgePact,
  so a report of "the belt does nothing" can be answered from the log instead of guesswork.

Nothing else changed since 1.3.14.

## How to update

Download the zip, unzip it, run ForgePact and press **Install** once. Start the game
after that; a game that was already open keeps the old plugin until it is restarted.

Use ForgePact only with an offline / EAC-disabled copy of Hero Siege.
