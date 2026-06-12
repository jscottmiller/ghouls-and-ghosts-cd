# Track Map (work in progress)

Goal: map the game's music cues (left table) to the Saturn rip's tracks
(right table). **Status: unmapped — needs a listening pass.** No public
track list exists for the Saturn disc (the back cover has none), and the
rip files are just numbered, so identification is by ear.

Coverage warning: *Incredible Toons* remixes music from across the
Makaimura series, not just Daimakaimura. Some Ghouls'n Ghosts cues may have
no match in the 17 tracks. That's OK: any cue we don't map simply stays
unhooked and plays the original FM music (per-call-site hooks degrade
gracefully). ArcadeTV's patch needed ~23 distinct CD tracks for full
coverage, so with 17 sources we expect sharing and/or FM fallbacks.

## Cues that need audio (from docs/hooks.md)

In-game context labels are still TBD (need a logged playthrough); the IDs
and ArcadeTV's track multiplicity are known.

| Game music ID | ArcadeTV track | In-game context (TBD) | Saturn track |
|---|---|---|---|
| `$81`+level (stage start) | level+1 | stage themes 1–5(?) | |
| `$81` (direct site) | 1 | | |
| `$82` | 22 | | |
| `$83` | 7 | | |
| `$84`–`$87` (variants) | 3 | | |
| `$88` | 2 | | |
| `$89` | 20 | | |
| `$8A` | 19 | | |
| `$8B` | 4 | | |
| `$8C` | 21 | | |
| `$8D` (scripted) | 5 | | |
| `$8E` | 6 | | |
| `$8F` (scripted) | 8 | | |
| `$91` (scripted) | 10 | | |
| `$92` (filtered) | 11 | | |
| `$93` (scripted) | 12 | | |
| `$94` | 13 | | |
| `$95` (scripted) | 14 | | |
| `$96` | 15 | | |
| `$97` (scripted) | 17 | | |
| `$98` | 16 | | |
| `$9A` | 18 | | |
| (boot/init hook) | 27 | title(?) | |

## Saturn rip tracks (listening worksheet)

Fill in: what tune is it (which Makaimura game / which theme), and which
game cue(s) it should cover. Durations suggest 10 substantial pieces and
7 jingles/short loops.

| File | Length | Identified as | Maps to cue(s) |
|---|---|---|---|
| 01.flac | 3:52 | | |
| 02.flac | 3:47 | | |
| 03.flac | 4:16 | | |
| 04.flac | 2:28 | | |
| 05.flac | 3:50 | | |
| 06.flac | 3:26 | | |
| 07.flac | 3:59 | | |
| 08.flac | 4:00 | | |
| 09.flac | 4:02 | | |
| 10.flac | 0:07 | jingle | |
| 11.flac | 1:46 | | |
| 12.flac | 1:02 | | |
| 13.flac | 0:50 | | |
| 14.flac | 1:02 | | |
| 15.flac | 4:14 | | |
| 16.flac | 1:02 | | |
| 17.flac | 0:14 | jingle | |
