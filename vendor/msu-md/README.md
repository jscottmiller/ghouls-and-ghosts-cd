# Vendored: msu-md driver

`msu-drv.bin` is the prebuilt MSU-MD Mode 1 driver by krikzz, vendored
unmodified from <https://github.com/krikzz/msu-md> (commit
`70a882d4e858c110cc359b6d2438f4891f8e1cc1`), under the MIT license in
`LICENSE`.

sha256: `3434f060f8bcbd1f004465df200e83b2636b2e52353d8103c57ea21c7bdd6124`

Usage: link the blob into the cart ROM and `jsr` its base address once at
boot. Returns 0 in `d0` on success, 1 if no Mega CD hardware was detected.
Commands are issued via `$A12010` (command), `$A12011` (argument),
`$A1201F` (command clock — increment to execute), `$A12020` (status:
0 ready, 1 init, 2 busy).
