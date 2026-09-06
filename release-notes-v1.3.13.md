# ForgePact 1.3.13

Works together with Hero Siege Item Editor 2.15.3.

## Fixed

- **Drop sliders no longer make every monster drop everything.** Since 1.3.10 the
  Orbs, Scrolls of Ra, Dimensional Shards, Battle Fragments, Colosseum Fragments and
  Ruby Keys sliders opened those drops for every monster in every zone, so fragments
  and scrolls rained everywhere. Now a slider only multiplies the drop where the game
  already drops it. The Relic slider no longer lets Prime Evil parts (Soul of Anguish,
  Despair, Corruption) through with the relics.
- **Monster Rarity no longer snowballs.** Raised monsters could receive affixes that
  create new monsters when they die or make copies of themselves (Fallen Angel, Fractal,
  Haunted, Possessed). Each new monster was raised again, so the more you killed, the
  more there were. Those four affixes are no longer handed out by the raise.
- **Forged items can be socketed and upgraded again.** The game checks an item's
  fingerprint before it accepts a gem or a star upgrade; a forged item failed that
  check once per game session. ForgePact now refreshes the fingerprint after it dresses
  an item.

## New

- **Type a value.** Click the number next to any slider to type the exact value you
  want. Enter applies it, Escape cancels. Handy where a slider skips numbers.

## How to update

Download the zip, unzip it, run ForgePact and press **Install** once. Start the game
after that; a game that was already open keeps the old plugin until it is restarted.

Use ForgePact only with an offline / EAC-disabled copy of Hero Siege.
