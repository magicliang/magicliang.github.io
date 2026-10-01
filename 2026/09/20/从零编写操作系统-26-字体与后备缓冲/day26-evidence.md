# Day 26 evidence

Date: 2026-09-20

## Source baseline

- Implementation commit: `aacc1a350cb32eeb647669770112568e8e81f25b`
- Text kernel SHA-256: `1c6c5d3f5858f1c7e627d7762e596e8c8e757f23d15aad81c6f583f82a06d8f1`
- Graphics text kernel SHA-256: `95d3b1bf57ddf620a25db0681c409337506e55366bf07b51eafe6f47c2758008`
- Graphics text disk image SHA-256: `a73be1c6290e3cc2b7571365ffaa089602c6ee6d85d067b37f7a31ccfc87b5b6`
- Screenshot SHA-256: `90e06a60579f6546ef7d0d6127dbdd810a906d04021ff1ef5e71d3bf98c91892`

The implementation adds a separate `mbr-graphics-text.img`. Historical text
images remain on BootInfo v1, and the Day 25 graphics image remains a separate
BootInfo v2 regression target.

## Font provenance

The committed table keeps printable U+0020 through U+007E from
`dhepper/font8x8` `font8x8_basic.h`, pinned to commit
`8e279d2d864e79128e96188a6b9526cfa3fbfef9`. The upstream README describes the
font as Public Domain. `third_party/font8x8-NOTICE.txt` preserves that statement,
the author, URL and commit. This record does not make an independent legal
determination. Bytes outside printable ASCII are replaced with `?`; this is not
UTF-8 or Chinese text support.

## Environment

- QEMU 8.2.2 (`Debian 1:8.2.2+ds-0ubuntu1.18`)
- SeaBIOS 1.16.3 package image
- GDB 15.1
- GCC 13.3.0 and GNU Binutils 2.42
- NASM 2.16.01
- Machine: `pc-i440fx-7.2`, TCG, `qemu32`, 1 CPU, 64 MiB

The unpacked toolchain under `/tmp/build-an-os-tools` is an execution dependency
of this environment and is not included in the attachment.

## Specialized command

```sh
PATH=/tmp/build-an-os-tools/bin:$PATH \
LD_LIBRARY_PATH=/tmp/build-an-os-tools/root2/usr/lib/x86_64-linux-gnu:\
/tmp/build-an-os-tools/root2/lib/x86_64-linux-gnu \
QEMU_MODULE_DIR=/tmp/build-an-os-tools/root2/usr/lib/x86_64-linux-gnu/qemu \
make check-graphics-text \
  QEMU=/tmp/build-an-os-tools/bin/qemu-system-i386 \
  GDB=/tmp/build-an-os-tools/bin/gdb-multiarch \
  BIOS=/tmp/build-an-os-tools/root2/usr/share/seabios/bios-256k.bin \
  QEMU_DATA=/tmp/build-an-os-tools/root2/usr/share/qemu
```

Exit status: 0.

## Runtime observations

The graphics text image reached the Day 26 completion breakpoint with these
values:

```text
STATE pages=16 rollback=7 free=16046/16030/16046 clip=2/2 pixels=204 guard=0 wrap=1 scroll=8 cursor=6,10 hash=0xd84d1c49
PASS: paged backbuffer, rollback, clipping, glyph, terminal and flush verified
```

The serial log independently reports:

```text
D25 VIDEO MODE 13h
D04 PM OK - BootInfo v2
D26 BACKBUFFER pages=16 rollback=7 free=16046/16030/16046
D26 CLIP clipped=2 rejected=2 pixels=204 guard=0
D26 TEXT wraps=1 scrolls=8 cursor=6,10 A=c,1e,33,33,3f,33,33,0
D26 FRAME hash=d84d1c49
GRAPHICS TEXT OK clipped, rendered, flushed and freed
```

The free-page sequence proves two ownership paths. A forced failure before the
eighth allocation returned all seven acquired pages (`16046` before and after).
The normal surface then held 16 pages (`16030`) and returned all of them after
the framebuffer copy (`16046`).

The clip probe called the same rectangle primitive with `INT32_MIN`, dimensions
of `UINT32_MAX`, a rectangle wholly outside the display, and an 8x8 rectangle
crossing the bottom-right corner. The two intersecting calls wrote exactly 200
and 4 pixels. The unused 1,536 bytes at the end of the 16-page surface retained
the `0xA5` guard value.

GDB read all 64,000 framebuffer bytes and recomputed FNV-1a `0xd84d1c49`, equal
to the hash computed over the paged surface before the copy. It also checked the
eight rows of `A` (`0c 1e 33 33 3f 33 33 00`) and corresponding foreground and
background pixels. The QEMU screenshot is 640x400 because the 320x200 legacy
scanout is doubled by `screendump`.

## Loader bounds

`kernel-graphics-text.bin` is 92,128 bytes, below the 128 KiB file limit. Its
ELF program headers report a 92,096-byte executable segment and a data segment
with 37,424 bytes of memory; the complete runtime image remains below the
existing 256 KiB limit. The 64,000-byte frame is not static BSS: it is allocated
as 16 physical pages at runtime.

## Cumulative regression

After the specialized check, the following targets all exited zero:

```text
check-graphics
check-pm
check-pipe
check-shell
check-fd
check-fat
check-block
check-process
check-syscall
check-elf
check-memory
check-runtime-limit
check-keyboard
```

The combined log is `docs/day26-cumulative.txt`. It demonstrates that the new
translation unit did not change Day 25 framebuffer bytes or the older text,
storage, process and user-mode paths.

## Frozen attachment verification

- `os-day-26.zip` SHA-256: `32addbe3f40b5435114d9d0c233b40f760e61534320712f1f59d044762713ad2`
- The archive contains no `build/` directory.
- A new temporary directory extracted the archive and ran `build`,
  `check-graphics-text`, `check-graphics`, and the thirteen cumulative targets.
  Every target exited zero.
- The rebuilt text kernel, graphics text kernel and graphics text disk image
  matched the pre-freeze SHA-256 values byte for byte.

The post-freeze receipt is `docs/day26-zipcheck.txt`. It is intentionally not
inserted back into the ZIP, because doing so would change the artifact whose
hash the receipt records.

## Evidence boundary

- The surface gives drawing code a stable off-screen frame. Copying 64,000 bytes
  to VGA memory is not synchronized with vertical retrace, so the experiment
  does not prove tear-free presentation.
- The page vector removes the need for physically contiguous frames, but it is
  not a contiguous virtual mapping. Every byte access performs a page lookup.
- The terminal is 40x25 fixed cells with one 8x8 font and indexed colors. It has
  no Unicode shaping, font fallback, variable width, scrollback history or
  user-mode terminal protocol.
- The screenshot proves the QEMU display consumed the bytes. Bounds and rollback
  claims come from guest assertions and GDB state, not from the screenshot.
