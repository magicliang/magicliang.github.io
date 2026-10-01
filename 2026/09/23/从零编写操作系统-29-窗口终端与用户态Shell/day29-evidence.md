# Day 29 evidence

Date: 2026-09-20

## Source baseline

- Window-terminal implementation commit: `9fea4ca`
- Text kernel SHA-256: `26f1bc26360ddf4c9b7d984d4fc6706eaa445207ee4095a2386bda2dd7cf8386`
- Window-terminal kernel SHA-256: `5b5a68d52f37d4c768abb1f3b5e0fb6d30910b00d32b5ae55be9f58d7a354e42`
- Window-terminal disk image SHA-256: `8c23eefb8b9583945a3f521b91906aec7da5441fdab9f2ced4016a3a59414b81`
- `SHELL.EXE`/`day23-user.elf` SHA-256: `b44b54cef5743aaa2c8423492cc5d15e96f567802256cbcd25186a7b493bc8b9`
- Screenshot SHA-256: `cd4d73c40366d24c621ca1081e09e1fef3fa99b6bcd15e99a5f44ce50c0403a2`

The Day 29 image uses the graphics stage2 and overlays the same
`fat16-shell.bin` used by Day 23. The historical text Shell and Day 28 window
images remain separate test entrypoints.

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
make check-window-shell \
  QEMU=/tmp/build-an-os-tools/bin/qemu-system-i386 \
  GDB=/tmp/build-an-os-tools/bin/gdb-multiarch \
  BIOS=/tmp/build-an-os-tools/root2/usr/share/seabios/bios-256k.bin \
  QEMU_DATA=/tmp/build-an-os-tools/root2/usr/share/qemu
```

Exit status: 0.

## Executable identity and privilege

The test stopped at `disk_spawn_published` and then at the first Shell prompt.
It checked the ELF size against `build/day23-user.elf`, recorded the same
SHA-256 as the FAT image source, and observed the saved user return state:

```text
LOADED size=3792 sha256=b44b54cef5743aaa2c8423492cc5d15e96f567802256cbcd25186a7b493bc8b9 cs=1b eip=400000c7 prompts=1 refs=3
```

`CS=0x1b` is the existing user code selector. The EIP lies in the loaded user
window. At the prompt there is one live Shell process, two open-file objects
and three references for stdin/stdout/stderr. No command parser was added to
the kernel or UI.

## Input, output and backpressure

The graphical terminal owns two independent 64-byte rings. The UI pushes
parsed keyboard characters into the input ring and drains at most 16 output
bytes per pass. A Shell `read` blocks while the input ring is empty. A writer
blocks while the output ring is full, allowing the UI bootstrap task to drain
bytes and process pointer packets before waking it.

HMP injected this command sequence:

```text
echo hello
cat readme.txt
cat readme.txt | wc
exit
```

During the 1479-byte direct `cat`, the test also injected six relative mouse
movements. The final GDB observation was:

```text
FINAL input=51 output=1552 high=2/64 block=49/89 mouse=6 redraws=146 pipe=1/1 pblock=21/3 log=1552
```

The output high-water mark reached the exact capacity of 64 and writers
blocked 89 times. All 1552 accepted bytes were consumed. Six mouse packets
were handled and the cursor ended at `(260,93)` while output was being drained;
the UI produced 146 redraws. These are deterministic counters for this run,
not latency or throughput measurements.

The retained terminal stream contains the command echoes and results:

```text
# echo hello
hello
...
# cat readme.txt | wc
27 1479
# exit
```

The screenshot was taken from the real Mode 13h framebuffer at the final
marker, before the 16-page surface was released.

## Pipe and lifecycle

`cat README.TXT | wc` reused the Day 24 pipe path. It created and released one
pipe, with 21 read blocks and 3 write blocks. The Shell and its four command
processes were reaped. On Shell exit, the two terminal open-file objects closed
their input/output endpoints; the output queue was then fully drained.

The serial summary agrees with the GDB state:

```text
D29 UI mouse=6 at=260,93 redraws=146 chars=1552 wraps=28 scrolls=41
D29 TERMINAL input=51 output=1552 consumed=1552 high=2/64 block=49/89 endpoints=2
D29 ELF size=3792 reads=15 prompts=4 pipe=1/1 rblock=21 wblock=3
WINDOW SHELL OK FAT ELF, bounded terminal and responsive UI
```

At the final marker, live open-file objects and references were both zero,
pipe creation equaled release, and the Shell page baseline was restored. The
UI then released its 16 surface pages and checked the pre-UI page count.

## Cumulative regression

After the specialized check, these targets all exited zero:

```text
check-window-shell
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

The combined receipt is `docs/day29-cumulative.txt`.

The source archive SHA-256 is
`ecbdd9cd4fbd740c7ad968094c1f5d995ac1b599b1ac54f0fbd5bd699c441fdc`.
It contains no `build/` directory. A fresh extraction rebuilt the project and
passed the same specialized plus cumulative target set; the four rebuilt
kernel/image/screenshot hashes matched this record. The external receipt is
`docs/day29-zipcheck.txt` and was intentionally not written back into the ZIP.

The repository-wide legacy `make check` was also attempted. Its Day 7
`check-exceptions` script rejected the cumulative IDT because it still expects
all vectors from 34 upward to be absent, while the current kernel intentionally
installs IRQ12 at vector 44 and the DPL3 syscall gate at vector 128. This stale
expectation is outside the current 17-target cumulative set and is not reported
as a passing check.

## Evidence boundary

- The implementation has one fixed full-screen terminal window. It does not
  create or close windows dynamically. Endpoint cleanup is exercised when the
  Shell exits; close-during-blocked-read, close-during-blocked-write and
  repeated open/close window cycles remain unimplemented.
- Keyboard input is lossless only while the UI can transfer it before the
  existing PS/2 raw queue overflows. The terminal input ring reports drops;
  this run observed zero. There is no canonical line discipline or Ctrl-D.
- The output queue applies backpressure and does not silently discard bytes.
  The UI still uses full-frame copies and has no `poll/select`, dirty rectangle,
  dedicated user-space display server or multi-CPU synchronization.
- HMP input and QEMU screenshots make the regression deterministic. They do
  not validate physical VGA/PS/2 hardware or subjective interaction quality.
