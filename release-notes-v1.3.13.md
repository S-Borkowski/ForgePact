# ForgePact 1.3.13

Works together with Hero Siege Item Editor 2.15.3.

## Fixed

- **Drop sliders no longer make every monster drop everything.** Since 1.3.10 the
  Orbs, Scrolls of Ra, Dimensional Shards, Battle Fragments, Colosseum Fragments and
  Ruby Keys sliders opened those drops for every monster in every zone, so fragments
  and scrolls rained everywhere. Now a slider only multiplies the drop where the game
  already drops it. The Relic slider no longer lets Prime Evil parts (Soul of Anguish,
  Despair, Corruption) through with the relics.
- **Monster Rarity and Tyrant's Crown no longer snowball.** Monsters that split when
  they die (worms, spiders and the like) or spawn a legion on death had their offspring
  raised again, and those split again, so the pack never ended. Anything a monster itself
  spawns is now left alone by the raise, and Monster Density does not multiply it either.
  The raise also no longer hands out the four affixes that create monsters on death
  (Fallen Angel, Fractal, Haunted, Possessed).
- **Gems work in forged items again.** Two things were wrong: the game checks an item's
  fingerprint before it accepts a gem, and a forged item failed that check; and when a gem
  did go in, its bonus was lost because ForgePact rewrote the item's stats after the game
  had added the gem. ForgePact now dresses the item before the gem step and refreshes the
  fingerprint afterwards, so gems can be inserted and their bonus counts.

## New

- **Type a value.** Click the number next to any slider to type the exact value you
  want. Enter applies it, Escape cancels. Handy where a slider skips numbers.

## How to update

Download the zip, unzip it, run ForgePact and press **Install** once. Start the game
after that; a game that was already open keeps the old plugin until it is restarted.

Use ForgePact only with an offline / EAC-disabled copy of Hero Siege.
