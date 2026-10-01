# Day 22 evidence

Date: 2026-09-19

## Source baseline

- Base commit: `346525f3a5c1924da6c01f87ff168ee3bc1511cf`
- Kernel image SHA-256 after the final source assertion change: `44fa4a4324acc22ef69b8e185e672c3238bf0744b210cd645d4994fcb455d959`
- Disk image SHA-256: `15349fd7449d2260e3df91c93127b3f320fa3f27e6b0e75423cf4e2653fa5573`
- Day 22 user ELF SHA-256: `0fe8e6739c5c5ad32fc3a88e923ef3e6b17cf3ab37ad04b2c799e99f372d0b01`

The final attachment hash and standalone rebuild result are added after packaging. The Git commit containing this file is intentionally not self-referenced; use `git log -- <path>` to recover it.

## Environment

- QEMU 8.2.2 (`Debian 1:8.2.2+ds-0ubuntu1.18`)
- SeaBIOS 1.16.3 package image
- GDB 15.1
- GCC 13.3.0
- GNU Binutils 2.42
- NASM 2.16.01
- Machine: `pc-i440fx-7.2`, TCG, `qemu32`, 1 CPU, 64 MiB

The unpacked QEMU/GDB binaries live under `/tmp/build-an-os-tools` and are not delivery artifacts.

## Command

```sh
PATH=/tmp/build-an-os-tools/bin:$PATH \
LD_LIBRARY_PATH=/tmp/build-an-os-tools/root2/lib/x86_64-linux-gnu:\
/tmp/build-an-os-tools/root2/usr/lib/x86_64-linux-gnu \
QEMU_MODULE_DIR=/tmp/build-an-os-tools/root2/usr/lib/x86_64-linux-gnu/qemu \
make check-fd \
  QEMU=/tmp/build-an-os-tools/bin/qemu-system-i386 \
  GDB=/tmp/build-an-os-tools/bin/gdb-multiarch \
  BIOS=/tmp/build-an-os-tools/root2/usr/share/seabios/bios-256k.bin \
  QEMU_DATA=/tmp/build-an-os-tools/root2/usr/share/qemu
```

Exit status: 0.

## Normal run

`day22-fd-gdb.txt` records both checkpoints:

```text
PASS: faulting child closed every fd before ZOMBIE publication
PASS: independent/shared offsets, short EOF, limits, rollback, exit cleanup and page recovery verified
```

Final values checked by GDB:

```text
fd_passed=1
fd_terminal_mode=0
fd_root_status=22
fd_reaped=5
fd_exit_closes=14
fd_exit_tasks=5
fd_pointer_faults=5
file_peak_live=7
file_allocations=file_releases=16
free_pages=fd_initial_pages
```

The guest checks two independent opens, a shared parent/child offset, a page-faulting child, EOF and short reads, zero length, read/write permissions, fd reuse, fd/open-file table exhaustion, and five rejected user-buffer ranges. The full-file FNV-1a is `f34dc752` for 1479 bytes.

## Injected failure run

`day22-fd-fail-gdb.txt` records:

```text
PASS: six ELF allocation failures plus kernel-stack failure rolled back mapped refs, then recovered
```

The image observes `fd_spawn_rollbacks=7`, then performs a successful spawn/read/wait. File allocation/release and free-page counts return to their baselines.

## Terminal run

`day22-fd-terminal-blocked.txt` observes the reader in `BLOCKED`, with `trap_depth=1` and `waiting_on=&keyboard_waiters`. `day22-fd-terminal-idle.txt` observes a later PIT tick, no extra block attempt, idle `HLT=1`, and IF set. QEMU HMP then sends `a`, `b`, and Return through the emulated PS/2 controller.

`day22-fd-terminal-done.txt` records:

```text
PASS: terminal reader blocked in trap depth 1, idle PIT advanced, HMP keys produced ab\n
```

The user process performs three one-byte reads and reports `D22 TERMINAL read ab\n one byte at a time`. This validates the QEMU i8042 path, not a physical keyboard, canonical terminal mode, Ctrl-D, or multiple readers.

## Boundaries

- FAT corruption and non-contiguous chains are dynamically covered by Day 21 `check-fat`; Day 22 does not rerun a corrupt volume through the fd syscall layer.
- The implementation is single-CPU and relies on syscall trap depth plus preemption suppression to serialize the non-reentrant FAT workspace and shared offsets.
- Directory descriptors, seek, writable files, canonical terminal input, Ctrl-D, close-driven terminal EOF, SMP, and concurrent close-vs-read are not implemented.

## Cumulative regression

The cumulative run in `day22-cumulative.txt` records successful exits for:

```text
PASS check-fat
PASS check-block
PASS check-process
PASS check-syscall
PASS check-elf
PASS check-memory
PASS check-runtime-limit
PASS check-keyboard
```

These are real QEMU/GDB checks, not build-only targets. `check-fat` includes the non-contiguous chain and eleven corrupt-volume images; `check-block` includes timeout, missing DRQ, and device ERR; `check-runtime-limit` boots the exact 128 KiB file and 256 KiB runtime boundaries.

## Standalone attachment verification

`os-day-22.zip` SHA-256 is `068c86aa51a33813a837e4a91ab2646a9db72209825bd1d221563a21c787b8a0`. The archive contains no `build/` directory. It was extracted into a new `mktemp` directory and rebuilt from scratch before running `check-fd`, `check-fat`, `check-block`, `check-process`, `check-syscall`, `check-elf`, `check-memory`, `check-runtime-limit`, and `check-keyboard`; every target exited 0.

The rebuilt `kernel.bin`, `mbr.img`, and `day22-user.elf` hashes match the source workspace values above and all three files pass byte-for-byte `cmp`. Full output is saved as `docs/day22-zipcheck.txt`. This log verifies the already frozen ZIP, so it is intentionally kept outside the archive itself.
