# Day 27 evidence

Date: 2026-09-21

## Source baseline

- Mouse implementation commits: `967ffaa` and `b8a6fc0`
- Text kernel SHA-256: `5468e046b0325a91be4d9b38a3e88e52da80e27992c69da9fa180634bb6f6371`
- Mouse kernel SHA-256: `7df69117138b4f0ba6a6d1356596f447478e2eb6b077138e5457e8d9235f50fd`
- Mouse disk image SHA-256: `4e2ce99606f0b9882d8d010be3ed61329a90f8cf680554400bfbe0ac564b4e8c`
- Screenshot SHA-256: `7d955d855929569da7d6d40cbaebb7e6b969d36046bd9cffe33e45b7ab0d4743`

The Day 27 image is separate from the historical text, graphics and graphics
text images. It keeps the Day 25 BootInfo v2 framebuffer contract and the Day
26 paged surface, then enables the 8042 auxiliary port and IRQ12.

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
make check-mouse \
  QEMU=/tmp/build-an-os-tools/bin/qemu-system-i386 \
  GDB=/tmp/build-an-os-tools/bin/gdb-multiarch \
  BIOS=/tmp/build-an-os-tools/root2/usr/share/seabios/bios-256k.bin \
  QEMU_DATA=/tmp/build-an-os-tools/root2/usr/share/qemu
```

Exit status: 0.

## Controller initialization and shared routing

The controller was configured with keyboard translation disabled, IRQ1 and
IRQ12 enabled, the auxiliary port open, and both device sources still sharing
the single `0x60` output buffer. Mouse reset returned ACK `0xfa`, BAT `0xaa` and
ID `0x00`. The test deliberately converted the first enable-reporting ACK into
a RESEND response after consuming it, then sent `0xf4` again and received the
second ACK:

```text
INIT ack=2 bat=0xaa id=0 resend=1 selftest=2/3/1
```

The IRQ receiver reads status once and data once, routes by status bit 5, and
never gives keyboard and mouse handlers independent reads from `0x60`. During
the final run, six keyboard bytes produced the requested `kbd` string while 147
mouse bytes were routed separately; neither keyboard byte was dropped:

```text
D27 SHARED keyboard=kbd kirq=6 krouted=6 kdropped=0 meoi=147/147
```

## Packet state and recovery

The host parser test and guest self-test cover signed X/Y decoding, screen-Y
inversion, a lost second byte, a byte with bit 3 clear at packet start, an
inserted `0xfa`, an overflow flag and a following legal packet. The guest
self-test records two accepted packets, three synchronization losses and one
overflow rejection.

The live QEMU run paused the consumer while HMP injected movement. Its 64-byte
raw queue overflowed after 78 mouse IRQs:

```text
QUEUE dropped=12 irqs=78 routed=78
```

Resuming the consumer discarded the incomplete queue, reset the packet state
once, and accepted later packets. The final observation was:

```text
STATE pos=319,199 edges=0xf buttons=0x7 changes=6 packets=23 reset=1 irq=147 route=147 eoi=147/147 keys=kbd
```

The retained edge mask proves the pointer reached left, right, top and bottom.
The final coordinate is deliberately the lower-right corner; the crosshair is
drawn through the same signed clipping primitive as other Day 26 shapes. Button
mask `7` and six changes cover press and release for left, middle and right.

## IRQ12 frame and cascaded EOI

The IDT and assembly stub table extend through vector 44. GDB stopped in the
real IRQ12 handler and checked the existing 68-byte same-CPL frame:

```text
IRQ frame vector=44 error=0 cs=8 saved_if=1 handler_if_df=0
```

The normal handler sent one EOI to the slave and one to the master for every
IRQ12. `info pic` then showed both ISR registers clear. Two isolated fault
images establish why both writes are required:

```text
STALLED irq=1 slave_eoi=0 master_eoi=1
pic1: irr=10 imr=ef isr=10

STALLED irq=1 slave_eoi=1 master_eoi=0
pic0: irr=05 imr=f9 isr=04
```

In each image a second HMP movement produced no second IRQ12. Omitting the
slave EOI left IRQ12 in the slave ISR; omitting the master EOI left the cascade
IRQ2 in the master ISR.

## Display result

The 320x200 surface is redrawn and flushed after accepted keyboard or mouse
events. QEMU's doubled legacy scanout produced a 640x400 PNG. The final frame
shows `kbd` from the keyboard path and the clipped yellow crosshair at the
lower-right mouse boundary. The screenshot hash is listed above.

## Cumulative regression

After the specialized check, the following targets all exited zero on the
final source:

```text
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

The combined receipt is `docs/day27-cumulative.txt`. A prior exploratory run
hit the existing timing-sensitive Day 22 guest assertion once; rerunning the
specialized test and the complete final regression produced the recorded clean
results. No source change was made to hide or bypass that assertion.

## Evidence boundary

- The controller behavior is verified only for the fixed QEMU/SeaBIOS machine.
  Real 8042-compatible controllers may require different timing and recovery.
- The parser accepts only standard three-byte ID 0 packets. It does not enable
  wheel or five-button extensions.
- Bit 3 identifies a candidate first byte only while the parser is waiting for
  a new packet. A raw byte stream cannot always recover uniquely after arbitrary
  loss because data bytes may also have bit 3 set. Queue overflow therefore
  resets the whole partial packet and discards the queued fragment.
- The test's overflow-bit and stray-ACK cases are deterministic injections.
  QEMU's normal relative movement path limits deltas and does not generate the
  classic overflow bits for these HMP events.
- Redrawing still copies the full 64,000-byte frame and does not synchronize to
  vertical retrace. Day 27 measures correctness, not input-to-photon latency.
