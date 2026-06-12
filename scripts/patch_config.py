"""Declarative patch configuration: which game cues map to which CD tracks.

Edit this file as more Saturn tracks get identified in docs/track-map.md,
then rebuild. Cues not mapped here fall back to the original FM music
(with a CD-stop issued so a looping CD track doesn't bleed into FM scenes).
"""

# Game music ID -> (CD track number, loop?) for cues with CD audio.
# CD track numbers refer to the cue sheet built by build_disc.py.
#
# The six level themes are scripted cues dispatched at $39CE.
# $92 is a mid-level cue adjacent to the level 3/4 themes (suspected level
# variant); mapped to the level 3 arrangement for musical continuity.
LEVEL_THEMES = {
    0x8D: (1, True),   # level 1 <- 01.flac
    0x8F: (2, True),   # level 2 <- 02.flac
    0x91: (3, True),   # level 3 <- 03.flac
    0x93: (4, True),   # level 4 <- 04.flac
    0x95: (5, True),   # level 5 <- 05.flac
    0x97: (6, True),   # level 6 <- 06.flac
}
FILTER_92_TRACK = (3, True)  # ID $92 special case, handled inside $878

# Audio source files (repo-relative), in CD track order.
AUDIO_TRACKS = [f"assets/audio/{n:02d}.flac" for n in range(1, 7)]

# Output naming. ROM, cue, AND soundpack bin must all share one basename —
# the Mega Everdrive Pro requires exact-match filenames for all three.
OUTPUT_BASENAME = "GhoulsnGhostsCD"
SOUNDPACK_NAME = f"{OUTPUT_BASENAME}.bin"

# Original ROM facts.
ROM_FILE = "assets/rom/Ghouls'n Ghosts (World) (Rev A).md"
ROM_CRC32 = 0x4F2561D5
ROM_SIZE = 0x0A0000
PADDED_SIZE = 0x100000          # patched ROM padded to 1 MB
CODE_BASE = 0x0A0000            # appended code starts right after the ROM

# Game routine addresses (see docs/hooks.md).
SOUND_SEND_1C04 = 0x0856        # central send, writes d0.b -> Z80 $1C04
SOUND_SEND_1C06 = 0x0878        # central send, writes d0.b -> Z80 $1C06
SOUND_INIT_CE6 = 0x0CE6         # sound/Z80 driver init
ORIGINAL_ENTRY = 0x0208         # original reset PC

# FM-fallback music call sites: cues with no CD track yet. Each gets a
# CD-stop before the original FM trigger. kind:
#   'imm'      - move.w/move.b #ID,d0 + bsr.w <send>   (8 bytes -> jsr+nop)
#   'imm_tail' - move.w #ID,d0 + bra.w <send>          (8 bytes -> jmp+nop)
#   'computed' - arithmetic on d0 + bsr.w <send>       (8 bytes -> jsr+nop)
#   'jsr'      - move.w #ID,d0 + jsr <send>.l          (retarget jsr addr)
#   'jmp'      - move.w #ID,d0 + jmp <send>.l          (retarget jmp addr)
FM_FALLBACK_SITES = [
    # addr,    kind,       id_or_op,           send routine
    (0x001FC2, "imm",      0x81,               SOUND_SEND_1C04),
    (0x0020AC, "imm",      0x88,               SOUND_SEND_1C04),
    (0x0020F8, "imm",      0x88,               SOUND_SEND_1C04),
    (0x0023D8, "computed", "addi_b_0x84",      SOUND_SEND_1C04),
    (0x0024D8, "computed", "addi_w_0x81",      SOUND_SEND_1C04),
    (0x006722, "imm",      0x8B,               SOUND_SEND_1C06),
    (0x00693A, "imm",      0x82,               SOUND_SEND_1C06),
    (0x006A5A, "imm",      0x8C,               SOUND_SEND_1C06),
    (0x006D8A, "imm_tail", 0x8E,               SOUND_SEND_1C06),
    (0x007534, "jsr",      0x8A,               SOUND_SEND_1C06),
    (0x00757E, "jsr",      0x9A,               SOUND_SEND_1C06),
    (0x0092CA, "jsr",      0x98,               SOUND_SEND_1C06),
    (0x01B38C, "jsr",      0x83,               SOUND_SEND_1C06),
    (0x03B674, "jsr",      0x94,               SOUND_SEND_1C06),
    (0x03EAAE, "jmp",      0x96,               SOUND_SEND_1C06),
]

SCRIPTED_DISPATCH_SITE = 0x0039CE   # andi.w #$ff,d0 + bsr.w $878
FILTER_SITE = 0x00088A              # move.b d0,$A01C06.l inside $878
PAUSE_SITE = 0x0008FC               # move.w #1,$F63A.w in pause handler
RESUME_SITE = 0x000978              # move.w #0,$F63A.w in resume handler
TITLE_SITE = 0x001DB6               # bsr.w $CE6 + busreq in title/init path

# CD command words (command byte high, argument byte low).
CMD_PLAY = 0x1100
CMD_PLAY_LOOP = 0x1200
CMD_PAUSE_FADE = 0x1314    # pause, ~0.27 s fade (matches ArcadeTV)
CMD_STOP = 0x130A          # pause w/ short fade, used as "stop"
CMD_RESUME = 0x1400
CMD_VOLUME_MAX = 0x15FF
