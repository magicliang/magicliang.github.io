# Day 25 evidence

Date: 2026-09-20

## Source baseline

- Implementation commit: `df4c9944997eebf65c67cf40d68419d690622e31`
- Text kernel SHA-256: `1c6c5d3f5858f1c7e627d7762e596e8c8e757f23d15aad81c6f583f82a06d8f1`
- Graphics kernel SHA-256: `a689373d1c66320fef602628c3214ae4cd82b7eeae2646b9b2544ed2e3dd5c3f`
- Graphics disk image SHA-256: `b3bf46c1c682967ff47eed1eb3ac2491cb7f7ba5326cb464171368714fe2329d`
- Screenshot SHA-256: `5a9fb76ec28c3403f8cba750c1028bd7bccbb0f5d0ad56625fa720be2f79d53e`

The implementation commit contains the separate graphics stage2 and kernel
image, BootInfo v2, bounded pixel writer, forced video failure image, and the
QEMU/GDB check. It leaves all historical text images on BootInfo v1.

## Environment

- QEMU 8.2.2 (`Debian 1:8.2.2+ds-0ubuntu1.18`)
- SeaBIOS 1.16.3 package image
- GDB 15.1
- GCC 13.3.0 and GNU Binutils 2.42
- NASM 2.16.01
- Machine: `pc-i440fx-7.2`, TCG, `qemu32`, 1 CPU, 64 MiB

The unpacked toolchain under `/tmp/build-an-os-tools` is an execution
dependency of this environment and is not included in the attachment.

## Specialized command

```sh
PATH=/tmp/build-an-os-tools/bin:$PATH \
LD_LIBRARY_PATH=/tmp/build-an-os-tools/root2/usr/lib/x86_64-linux-gnu:\
/tmp/build-an-os-tools/root2/lib/x86_64-linux-gnu \
QEMU_MODULE_DIR=/tmp/build-an-os-tools/root2/usr/lib/x86_64-linux-gnu/qemu \
make check-graphics \
  QEMU=/tmp/build-an-os-tools/bin/qemu-system-i386 \
  GDB=/tmp/build-an-os-tools/bin/gdb-multiarch \
  BIOS=/tmp/build-an-os-tools/root2/usr/share/seabios/bios-256k.bin \
  QEMU_DATA=/tmp/build-an-os-tools/root2/usr/share/qemu
```

Exit status: 0.

## Runtime observations

The normal graphics image reports that stage2 selected Mode 13h, entered
protected mode with BootInfo v2, and reached the bounded drawing demo:

```text
D25 VIDEO MODE 13h
D04 PM OK - BootInfo v2
D25 GRAPHICS base=0xa0000 320x200 pitch=320 bpp=8 pixels=185120 rejected=2 hash=4130a99d
GRAPHICS OK framebuffer reserved and bounds checked
```

The complete log is `docs/day25-graphics-serial.txt`, SHA-256
`81be47ca6f5a2c53d2177dbced6d30e186674bad3db76e2314ba3bd885bbb404`.
The pixel count includes the initial full-frame pattern, six rectangles, and
the four border passes. It is an operation count rather than a distinct-pixel
count. The FNV-1a hash covers exactly 64,000 framebuffer bytes.

GDB stopped at `graphics_demo_done` and read the kernel symbols, VGA memory,
and allocator bitmap:

```text
STATE base=0xa0000 size=320x200 pitch=320 mode=0x13 bpp=8 pixels=185120 rejected=2 guard=0 hash=0x4130a99d
PASS: BootInfo v2, framebuffer pixels, bounds and allocator exclusion verified
```

The check asserts the four border corners, one inner yellow pixel, and a center
white pixel directly from guest address `0xA0000`. It also checks that page
number `0xA0` is absent from the allocator's eligible bitmap. Two calls at
`(320, 0)` and `(0, 200)` were rejected, and the byte immediately after the
64,000-byte frame retained its original value. The GDB record is
`docs/day25-graphics-gdb.txt`, SHA-256
`5ffa77e02b744b2a65b7f8eb1add4e30c774d776993b605b5075aea9e6437e67`.

QEMU `screendump` produced `docs/day25-screen.png`. Its PNG dimensions are
640x400 because QEMU doubles the legacy 320x200 scanout on export. The check
does not infer guest geometry from that host image: guest width, height, pitch,
and key bytes are verified separately through BootInfo and GDB.

## Failure path

`mbr-graphics-fail.img` uses the same stage2 code with a build-time fault that
makes the mode readback fail. Stage2 restores BIOS mode 3, writes the diagnostic
to text VGA and COM1, and halts before protected-mode entry:

```text
D25 VIDEO FAIL
```

The failure log contains neither `D04 PM OK` nor `D25 GRAPHICS`. This proves
that the injected setup failure is fail-closed rather than a normal graphics
boot followed by a warning. The record is
`docs/day25-graphics-fail-serial.txt`.

## Implemented contract

- Historical text images publish the original 40-byte BootInfo v1 contract.
- The separate graphics image publishes a 40-byte BootInfo v2 contract with
  physical base `0xA0000`, width 320, height 200, pitch 320, mode `0x13`, and
  depth 8 bits per pixel.
- Stage2 calls BIOS video services only in real mode. It reads the current mode
  back with `INT 10h/AH=0Fh` before publishing v2.
- The graphics kernel accepts only the exact v2 contract before touching VGA
  memory. Text kernels continue to require v1.
- Pixel coordinates are checked against width and height before address
  calculation. The current rectangles are known to fit; later clipping is a
  Day 26 concern.
- VGA memory below 1 MiB remains identity mapped and excluded from the physical
  page allocator. Both properties are checked at runtime.
- COM1 remains the diagnostic truth after switching away from text mode.

## Boundaries

Mode 13h is 320x200 with one byte per pixel. The byte is a palette index, not
an eight-bit RGB encoding. This implementation uses the BIOS default palette
and does not program the DAC. It has no VBE, high-resolution linear
framebuffer, double buffering, clipping of arbitrary signed rectangles, font,
text layout, vertical synchronization, GPU acceleration, or real-hardware
coverage.

The forced failure is a deterministic test of this project's readback branch.
It does not prove that `INT 10h/AH=00h` exposes every possible BIOS failure;
the fixed SeaBIOS implementation does not propagate its internal set-mode
failure as a general status code.

## Cumulative regression

After the specialized run, the same tree passed `check-pm`, `check-pipe`,
`check-shell`, `check-fd`, `check-fat`, `check-block`, `check-process`,
`check-syscall`, `check-elf`, `check-memory`, `check-runtime-limit`, and
`check-keyboard`. These are QEMU/GDB runtime checks, not compile-only targets.
The full output is `docs/day25-cumulative.txt`.

## Standalone attachment verification

The frozen `os-day-25.zip` has SHA-256
`57e512a88ef1490d47fb21c82f388670e0d1f684a696bfb9ef18411ed18b53a5`.
It contains no `build/` directory. It was extracted into a fresh temporary
directory, rebuilt from scratch, and passed `check-graphics` plus all twelve
cumulative targets listed above. Rebuilt `kernel.bin`, `kernel-graphics.bin`,
and `mbr-graphics.img` hashes match the source-tree values. The full receipt is
`docs/day25-zipcheck.txt`; it was created after the archive was frozen and is
intentionally not inserted back into the ZIP whose hash it describes.
