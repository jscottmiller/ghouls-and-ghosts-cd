# Sound Hook Map

Reverse-engineered from the game ROM plus a diff of ArcadeTV's MSU-MD v1.0
BPS patch (target CRC32 `4F2561D5` — identical to our `(World) (Rev A)` ROM,
which GoodGen calls `(UE) (REV02)`). We will write our own implementation,
but this records the proven hook points and technique.

## The game's sound architecture

- Z80 sound driver (pre-SMPS, Capcom mod), uploaded at boot.
- Two central 68k send routines, each wrapped in Z80 bus req/release:
  - **`$000856`** — writes the byte in `d0` to Z80 RAM **`$A01C04`**
  - **`$000878`** — writes the byte in `d0` to Z80 RAM **`$A01C06`**
- Music IDs are `$81..$9A`-ish; SFX use the same routines with other IDs.
- Sending **`$FF`** to the driver silences music (this is how FM music is
  muted without touching SFX).
- Sending **`$AE`** is the driver's pause/mute-all command (used on pause).
- Pause/unpause handlers at **`$0008FC`** (sets flag `$F63A.w` = 1) and
  **`$000978`** (clears it) — natural CD pause/resume hook sites.
- Z80/driver init near **`$001DB6`** (`bsr $CE6`) — natural place to start
  title music / re-init after reset.

## Patch technique (ArcadeTV's, mirroring krikzz's MIT sample)

- ROM padded 640 KB → 1 MB; all new code/data in `$0A0000+`:
  - `$0A0000` — krikzz `msu-drv.bin` blob; `jsr $A0000` once at boot
    (after TMSS), then send `$15FF` (volume max).
  - `$0A0750+` — one small stub per music cue:
    `moveq #track,d0` / `ori.w #$1100,d0` (or `#$1200` for looped) /
    `bsr send` / `jsr $856-or-$878` (d0 is `$FF` by then → FM music muted).
  - send routine: spin until `$A12020` == 0, `move.w d0,$A12010`
    (command byte high, argument byte low), `addq.b #1,$A1201F`.
- Header/boot changes:
  - reset vector `$000004` → new entry (TMSS, driver init, `jmp $208`)
  - header system name → `SEGA MEGASD` (MegaSD detection), ROM end
    `$0001A4` → `$0FFFFF`
  - boot checksum branch at `$000252` nopped out
- Pause hook `$0008FC` → send `$AE` to Z80 (mutes FM SFX too) + CD cmd
  `$1314` (pause, ~0.27 s fade). Resume hook `$000978` → CD cmd `$1400`,
  then restore the `$F63A` flag write it displaced.
- One special case: music ID `$92` on the `$878` path triggers CD track
  `$0B` looped instead of a 1:1 stub (handled in a filter at the `$00088A`
  hook inside `$878` itself).

## Music cue → call-site map

"once"/"loop" = CD command `$11`/`$12`. Track numbers are ArcadeTV's
X68000 soundpack layout (28 tracks); ours will differ.

| Call site | Game music ID | CD track | Mode | Notes |
|---|---|---|---|---|
| `$001FC0` | `$81` | 1 | once | |
| `$0020AC`, `$0020F8` | `$88` | 2 | once | two call sites, same stub |
| `$0023D8` | `$84`–`$87` (computed `andi #3` + `$84`) | 3 | once | variants collapsed to one track |
| `$006722` | `$8B` | 4 | once | |
| `$0039CE` | scripted stream: `$8D/$8F/$91/$93/$95/$97` | 5/8/10/12/14/17 | loop | dispatcher; other IDs pass through to `$878` |
| `$006D8A` | `$8E` | 6 | loop | |
| `$01B38C` | `$83` | 7 | once | |
| `$00A1F8` | `$89` | 20 | once | tail-call (`jmp`) |
| `$03B67B` | `$94` | 13 | loop | only the `jsr` retargeted; ID load kept |
| `$03EAAE` | `$96` | 15 | loop | tail-call (`jmp`) |
| `$0092CA` | `$98` | 16 | once | |
| `$00757E` | `$9A` | 18 | once | |
| `$007534` | `$8A` | 19 | once | |
| `$006A5A` | `$8C` | 21 | once | |
| `$0024D8` | `$81` + level (from `$FEC6.w`) | level + 1 | once | stage-theme dispatch by level number |
| `$001DB6` (init) | — | 27 | once | played from the driver-init hook (title?) |
| `$00693A` | `$82` | 22 | once | |
| (filter in `$878`) | `$92` | 11 | loop | special-cased |
| — | — | 9, 17 (standalone) | loop | stubs present but no callers found; likely unused |

Open items: label every cue with its in-game context (play test with
logging — the music IDs are known, the scenes aren't). Then rebuild this
table against our Saturn-rip track layout (17 source tracks vs. ArcadeTV's
28 — some cues will share tracks).
