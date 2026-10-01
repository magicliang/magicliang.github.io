# Day 28 evidence

Date: 2026-09-20

## Source baseline

- Window implementation commit: `657eca7`
- Text kernel SHA-256: `5468e046b0325a91be4d9b38a3e88e52da80e27992c69da9fa180634bb6f6371`
- Window kernel SHA-256: `55dcc10a20fe997859712bbc87ebeafc8de46c5574dd59670a596bd369383d59`
- Window disk image SHA-256: `13541dcaf4d677c61d7d00e8081854d0231113d7fbcffeb959bdbd2805577331`
- Screenshot SHA-256: `231ce0b3b464850d8159efbc6eeefc0038743aa4d9f155f20c10fb5f8538b17a`

The Day 28 image is separate from the historical text, graphics, graphics-text
and mouse images. It reuses the Day 26 paged surface and the Day 27 keyboard
and mouse queues without changing their earlier test entrypoints.

## Environment

- QEMU 8.2.2 (`Debian 1:8.2.2+ds-0ubuntu1.18`)
- SeaBIOS 1.16.3 package image
- GDB 15.1
- GCC 13.3.0 and GNU Binutils 2.42
- NASM 2.16.01
- Machine: `pc-i440fx-7.2`, TCG, `qemu32`, 1 CPU, 64 MiB

The unpacked tools under `/tmp/build-an-os-tools` are an execution dependency
of this environment and are not included in the attachment.

## Specialized command

```sh
PATH=/tmp/build-an-os-tools/bin:$PATH \
LD_LIBRARY_PATH=/tmp/build-an-os-tools/root2/usr/lib/x86_64-linux-gnu:\
/tmp/build-an-os-tools/root2/lib/x86_64-linux-gnu \
QEMU_MODULE_DIR=/tmp/build-an-os-tools/root2/usr/lib/x86_64-linux-gnu/qemu \
make check-window \
  QEMU=/tmp/build-an-os-tools/bin/qemu-system-i386 \
  GDB=/tmp/build-an-os-tools/bin/gdb-multiarch \
  BIOS=/tmp/build-an-os-tools/root2/usr/share/seabios/bios-256k.bin \
  QEMU_DATA=/tmp/build-an-os-tools/root2/usr/share/qemu
```

Exit status: 0.

## Initial composition

The image creates two fixed records. A starts at `(20,40)` with size `150x100`;
B starts at `(105,70)` with size `180x110`. The Z array stores bottom to top,
so its initial value is `[A,B]`, and B owns keyboard focus. GDB stopped after
the first complete composition and checked both the model and a pixel in the
overlap:

```text
INITIAL A=20,40 B=105,70 focus=1 z=0,1 overlap=2
```

The overlap pixel has B's body color, which establishes the initial draw order
on the real VGA framebuffer rather than only inspecting bookkeeping fields.

## Focus, Z order and dragging

The HMP test injected this sequence into QEMU's PS/2 devices:

```text
mouse_move -120 -55
mouse_button 1
mouse_move 30 20
mouse_button 0
sendkey a 20
mouse_move 150 10
mouse_button 1
mouse_button 0
sendkey b 20
```

The first movement places the pointer at `(40,45)`, inside A's title bar.
Pressing the left button focuses A, moves it to the top and captures the drag
offset `(20,5)`. The following movement therefore places A at `(50,60)` even
though hit testing is no longer repeated during the drag. Releasing the button
clears capture. The second click lands in B's exposed title bar, focuses B and
restores `[A,B]` as the Z order.

The final GDB observation was:

```text
FINAL A=50,60 B=105,70 focus=1 top=1 drag=-1 changes=2/2 text=a/b pixels=3/2 packets=8 redraws=10
```

`changes=2/2` records two focus transitions and two Z-order changes. The
per-window buffers contain `a` and `b`, proving that each keyboard character
went to the window that held focus at the time. The serial-side state agrees:

```text
D28 WINDOWS A=50,60 B=105,70 focus=1 top=1 drag=-1
D28 EVENTS focus_changes=2 z_changes=2 packets=8 redraws=10
D28 INPUT A=a/1 B=b/1
WINDOW OK z-order, focus, drag, restore and routed input
```

## Occlusion restoration

Every state change reconstructs the frame as desktop, bottom-to-top complete
windows, then mouse pointer. The test reads two framebuffer bytes after A has
moved and B has returned to the top:

- `(20,40)` is `3`, the desktop color. It was A's old top-left corner.
- `(120,90)` is `2`, B's body color in the new overlap.

No old framebuffer region is copied to recover either pixel. Both values come
from replaying the retained scene model into the off-screen surface and then
flushing 64,000 bytes.

## Cumulative regression

After the specialized check, the following targets all exited zero:

```text
check-window
check-mouse
check-graphics-text
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

The combined receipt is `docs/day28-cumulative.txt`.

## Evidence boundary

- The implementation deliberately contains two fixed windows and a two-entry
  Z array. It does not allocate, close, resize or dynamically enumerate windows.
- Only the title bar starts a drag. The whole window is clamped inside the
  320x200 desktop; partial off-screen placement is not implemented.
- Input handling and composition run in one kernel loop. There is no user-space
  window protocol, multi-CPU synchronization or compositor task boundary yet.
- Every accepted input change repaints and copies the full 64,000-byte frame.
  Ten redraws were observed in this scripted case, but no latency benchmark was
  performed and no claim about interactive performance follows from that count.
- HMP provides deterministic device input for regression. It does not measure
  the feel of dragging with a physical mouse or validate real VGA/PS/2 hardware.
