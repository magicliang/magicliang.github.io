# Day 30 evidence

Date: 2026-09-22

## Source baseline

- Integrated-demo implementation commit: `07d63e7`
- Final kernel binary SHA-256: `a5209e8fd220c64e3d7b3e3b2449d16e8f2f4e315db5562bc3e5c2a5390fc470`
- Final kernel ELF SHA-256: `80a6d0825b79c0749d2cfa5951a42c334a30a7d64a0742bc4399ad77cb3bd45e`
- Final disk image SHA-256: `4c4a315af550ee8f38dd8c1fa5fd2c067d2a4077d28b793b67fc36edae5e48d2`
- `DEMO.EXE` SHA-256: `a246a279682e38bea0a2613800599f69d4dd54161b6e2bf2dc95dbe6ae1f5474`
- First/reset/fresh screenshot SHA-256: `aa1eb7b93da3ab1f61eb6a41ea2d3a7dc888e5c9595d08fc21262cd5939eeead`

The Day 30 image is a separate final entrypoint. Historical images and their
test limits remain unchanged. The old process, fd and Shell demos still expose
four process slots; the final image exposes six so that the Shell, DEMO, two
COUNT children and BADPTR can coexist.

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
make check-final \
  QEMU=/tmp/build-an-os-tools/bin/qemu-system-i386 \
  GDB=/tmp/build-an-os-tools/bin/gdb-multiarch \
  BIOS=/tmp/build-an-os-tools/root2/usr/share/seabios/bios-256k.bin \
  QEMU_DATA=/tmp/build-an-os-tools/root2/usr/share/qemu
```

Exit status: 0.

The command starts one QEMU process, runs the full scenario, issues QMP
`system_reset`, repeats it in the same process, then stops that process and
repeats in a new QEMU process. It removes the normal `-no-reboot` flag only for
this test because reset is the behavior under test.

## Directory ABI and FAT-loaded programs

Day 30 adds syscall 12, `readdir(index, entry)`. The kernel copies a fixed
16-byte entry containing a printable 8.3 name, attributes and a 32-bit size.
The FAT implementation still exposes only the fixed root directory and filters
deleted, long-name, volume-label and subdirectory entries. It remains read-only.

The final FAT image contains 13 visible files. `LS.EXE` is the existing Day 23
multi-call user executable dispatched as `ls`; `DEMO.EXE` is a separate 1212
byte ELF loaded through the same FAT/file/ELF path. The retained terminal log
contains:

```text
# ls
README.TXT 1479
...
DEMO.EXE 1212
# cat readme.txt | wc
27 1479
```

The final GDB checks observed `fat_directory_files=13` and 16 directory-sector
reads. `day30_demo_reads=3` records the ELF header/program-header/load reads;
it is an implementation observation, not a general lower bound for ELF files.

## Fault order and surviving processes

`DEMO.EXE` creates two COUNT children and one BADPTR child. BADPTR faults on
address `0x00100000` with vector 14. The kernel snapshots both COUNT progress
values before publishing the BADPTR exit, waits until both values are larger,
and only then releases the counters. Each round produced ordered events:

```text
D30 BADPTR seq=1 pid=22 vector=14 cr2=100000 tick=703 survivors=2
D30 SURVIVORS seq=2 count=2 growth=1,1 tick=704 after-fault=1
```

The fresh-process sample completed both events within one 100 Hz clock tick,
so it printed `after-fault=0`; its event sequence was still `1 < 2`, and both
recorded progress values increased by one. Tick equality is therefore not used
as an ordering proof.

The terminal then showed:

```text
# demo
DEMO start: two counters and one bad pointer
DEMO pids count=20,21 badptr=22
DEMO badptr #PF isolated
DEMO OK: both counters advanced after fault
# echo after-reset
after-reset
# exit
```

The successful command after DEMO proves that the Shell regained control. It
does not claim recovery from a kernel fault: the page fault belonged to a user
process and followed the existing process-isolation path.

## Three-round replay

All three rounds reached the first prompt with the same saved user state:

```text
READY first cs=1b eip=400000c7 pages=16040 refs=3
READY warm-reset cs=1b eip=400000c7 pages=16040 refs=3
READY fresh-process cs=1b eip=400000c7 pages=16040 refs=3
```

After `exit`, all rounds reported the same semantic terminal state:

```text
FINAL first demo=1212/3 bad=22 seq=1<2 growth=1,1 dir=13/16 reaped=10 pages=16040 prompts=6
FINAL warm-reset demo=1212/3 bad=22 seq=1<2 growth=1,1 dir=13/16 reaped=10 pages=16040 prompts=6
FINAL fresh-process demo=1212/3 bad=22 seq=1<2 growth=1,1 dir=13/16 reaped=10 pages=16040 prompts=6
```

Each final breakpoint also asserted zero live open-file objects and references,
equal terminal produced/consumed bytes, two released terminal endpoints, at
least ten reaped processes, and equality between pre-UI and post-UI free-page
counts. Serial output ended with:

```text
D30 FINAL demo=1212/3 pid=19 reaped=10 dir=13/16 prompts=6 pages=16040
FINAL DEMO OK FAT ls, pipe, two survivors, cleanup
```

The QMP transcript records the accepted hard reset and three `screendump`
requests. The HMP transcript records every injected key and mouse command. The
three screenshots are byte-identical because each round ends at the same fixed
terminal contents and cursor state.

## Cumulative regression

After the specialized check, these current targets all exited zero:

```text
check-final
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

The combined receipt is `docs/day30-cumulative.txt`. The current run's Shell
check passed on its first attempt. An earlier development run needed a rerun
because the older fd demonstration has a scheduling-sensitive observation;
that incident is not counted as a passing run, and the retained final sequence
is entirely green.

The repository-wide legacy `make check` is not reported as passing. Its Day 7
`check-exceptions` expectation predates vector 44 for IRQ12 and vector 128 for
the DPL3 syscall gate. The current cumulative list uses the maintained targets
for those later mechanisms instead of weakening the old check.

The source archive SHA-256 is
`9c4a841efc8b6a51f9509586cdcd8889d8276ec9d8bcde9d7cdc4363e6dfbf3a`.
It contains no `build/` directory. A fresh extraction rebuilt the project and
passed the same 17-target sequence. `kernel-final.bin`, `mbr-final.img` and
`day30-user.elf` matched byte for byte. The debug `kernel-final.elf` hash differs
because DWARF records the absolute compilation directory; `DW_AT_comp_dir`
changed from the repository path to the temporary extraction path, while the
objcopied kernel binary remained identical. The external receipt is
`docs/day30-zipcheck.txt` and is intentionally not stored inside the archive.

## Evidence boundary

- QMP `system_reset` is a guest hard reset inside one QEMU process. The third
  round uses a new QEMU process, but neither path validates a physical power
  cycle or different firmware.
- HMP key and mouse injection gives a deterministic device path. It is not a
  subjective manual usability test and does not validate physical PS/2 or VGA
  hardware.
- The FAT layer remains a fixed, read-only FAT16 root with ASCII 8.3 names.
  There are no subdirectories, long names, writes, persistence protocol or
  crash recovery.
- Six task slots are sufficient for the frozen final scene, not a scalable
  process-table design. There is still one CPU, no SMP synchronization and no
  dynamic task-table growth.
- Equal counters and page totals at three fixed endpoints constrain leaks in
  this scenario. They do not prove absence of every delayed or unexercised
  lifetime bug.
