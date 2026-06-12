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
| `$8D` (scripted) | 5 | level 1 theme | 01.flac |
| `$8E` | 6 | boss theme(?) — 1:06 loop in ArcadeTV's pack | |
| `$8F` (scripted) | 8 | level 2 theme | 02.flac |
| `$91` (scripted) | 10 | level 3 theme | 03.flac |
| `$92` (filtered) | 11 | **stage 3 boss** (confirmed in playtesting) | 11.flac |
| `$93` (scripted) | 12 | level 4 theme | 04.flac |
| `$94` | 13 | | |
| `$95` (scripted) | 14 | level 5 theme | 05.flac |
| `$96` | 15 | | |
| `$97` (scripted) | 17 | level 6 theme | 06.flac |
| `$98` | 16 | | |
| `$9A` | 18 | | |
| (boot/init hook) | 27 | title(?) | |

## Saturn rip tracks (listening worksheet)

Fill in: what tune is it (which Makaimura game / which theme), and which
game cue(s) it should cover. Durations suggest 10 substantial pieces and
7 jingles/short loops.

| File | Length | Identified as | Maps to cue(s) |
|---|---|---|---|
| 01.flac | 3:52 | level 1 theme (per Scott) | `$8D` |
| 02.flac | 3:47 | level 2 theme (per Scott) | `$8F` |
| 03.flac | 4:16 | level 3 theme (per Scott) | `$91` |
| 04.flac | 2:28 | level 4 theme (per Scott) | `$93` |
| 05.flac | 3:50 | level 5 theme (per Scott) | `$95` |
| 06.flac | 3:26 | level 6 theme (per Scott) | `$97` |
| 07.flac | 3:59 | | |
| 08.flac | 4:00 | | |
| 09.flac | 4:02 | | |
| 10.flac | 0:07 | jingle | |
| 11.flac | 1:46 | boss theme (per Scott) | `$92` (CD track 7); other boss IDs TBD |
| 12.flac | 1:02 | | |
| 13.flac | 0:50 | | |
| 14.flac | 1:02 | | |
| 15.flac | 4:14 | | |
| 16.flac | 1:02 | | |
| 17.flac | 0:14 | jingle | |
