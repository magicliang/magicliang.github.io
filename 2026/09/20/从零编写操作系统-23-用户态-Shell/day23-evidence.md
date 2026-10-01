# Day 23 evidence

Date: 2026-09-20

## Source baseline

- Implementation commit: `abf986ca3e2b7339476c0109103ede15140c4643`
- Kernel image SHA-256: `6008f1ea3a8174218d02be8358902e88ca4e0b914b1dfc8a1341f65848ed034d`
- Shell disk image SHA-256: `5b2614ac43484617317726c071e31680680b7e16a1febdd86b0af3c8f01792d5`
- Day 23 user ELF SHA-256: `34d8c42838fb1656481a539e3398ca7faca1b6ba7b7a08ebd91118f5f83c5110`
- `README.TXT` SHA-256: `25fc6f4ce8493714e7056d2896c47e6a9f4c4db91a4b860dd474035542804798`

The implementation commit contains the kernel, user program, image builder, and
test harness. The article, persisted evidence, attachment, and a corrected test
lower bound are added by the following documentation commit. The attachment
hash and standalone rebuild result are intentionally recorded only after the
archive has been frozen.

## Environment

- QEMU 8.2.2 (`Debian 1:8.2.2+ds-0ubuntu1.18`)
- SeaBIOS 1.16.3 package image
- GDB 15.1
- GCC 13.3.0
- GNU Binutils 2.42
- NASM 2.16.01
- Machine: `pc-i440fx-7.2`, TCG, `qemu32`, 1 CPU, 64 MiB

The unpacked QEMU/GDB binaries live under `/tmp/build-an-os-tools` and are not
delivery artifacts.

## Command

```sh
PATH=/tmp/build-an-os-tools/bin:$PATH \
LD_LIBRARY_PATH=/tmp/build-an-os-tools/root2/usr/lib/x86_64-linux-gnu:\
/tmp/build-an-os-tools/root2/lib/x86_64-linux-gnu \
QEMU_MODULE_DIR=/tmp/build-an-os-tools/root2/usr/lib/x86_64-linux-gnu/qemu \
make check-shell \
  QEMU=/tmp/build-an-os-tools/bin/qemu-system-i386 \
  GDB=/tmp/build-an-os-tools/bin/gdb-multiarch \
  BIOS=/tmp/build-an-os-tools/root2/usr/share/seabios/bios-256k.bin \
  QEMU_DATA=/tmp/build-an-os-tools/root2/usr/share/qemu
```

Exit status: 0.

## FAT-backed ELF and initial stack

`readelf -l build/day23-user.elf` reports one `PT_LOAD` segment and entry
`0x40000080`. At the first `disk_spawn_published` breakpoint, GDB records:

```text
STATE sp=7fffffe0 argc=1 argv0=7ffffff6 reads=3 lba=2203 live=2 refs=6
PASS: FAT source, non-embedded ELF, argc/argv stack and staged descriptor refs verified
```

The three source reads are the ELF header, its single program header, and its
loadable segment. The original check required four reads and therefore rejected
this valid one-segment ELF before the interactive test. The lower bound is now
three; the assertion still proves that the loader used the file-backed callback
rather than the old embedded byte array.

The stack pointer is 16-byte aligned. It contains `argc=1`, an in-range `argv`
pointer, the `SHELL.EXE` string, and a null vector terminator. At publication,
the kernel and child temporarily hold six references to the two terminal
objects. The bootstrap task then closes its three descriptors, leaving the
Shell as their sole owner.

## Interactive run

`tools/check-shell.py` sends every key through the QEMU monitor's `sendkey`
command. The guest still receives them through the emulated i8042, IRQ1,
scan-code parser, terminal input queue, and `read(0, ...)` syscall. There is no
test-only input buffer.

The test covers:

- empty input and input containing only spaces;
- `echo` with one and two arguments;
- `cat README.TXT`, including byte-for-byte comparison with the host file;
- a missing executable followed by a successful command;
- `argc/argv` layout through `ARGTEST.EXE`;
- an ELF with a damaged magic byte followed by a successful command;
- a child page fault followed by a successful command;
- the seven-user-argument success boundary and eight-user-argument rejection;
- 31-byte token success and 32-byte token rejection;
- explicit rejection of pipe syntax in Day 23;
- the 95-byte line boundary and recovery;
- `exit`, final process reap, descriptor cleanup, and page recovery.

The final guest line is:

```text
SHELL OK prompts=20 pages=16049
```

No `PANIC` appears in the serial log. The prompt hook verifies after every
command that only the Shell process remains, exactly two terminal objects hold
three references, and the free-page count has returned to the prompt baseline.

## Boundaries

- Command parsing accepts only ASCII spaces as separators. Quotes, escapes,
  tabs, redirection, background jobs, command lists, wildcards, and pipelines
  are rejected.
- At most eight total arguments are accepted; each argument is at most 31
  bytes, and an input line is at most 95 bytes.
- Executable lookup is limited to the FAT16 root and the existing ASCII 8.3
  subset. A missing suffix is converted to `.EXE`; there is no PATH search.
- The same small ELF image dispatches Shell, `cat`, `echo`, argument checking,
  and the fault probe by `argv[0]`. This saves disk space; it is not dynamic
  linking or multicall compatibility with an existing Unix utility.
- Programs are foreground-only. The Shell spawns one child, waits for that PID,
  and then reads another line.
- QEMU HMP provides repeatable key injection. The run does not validate a
  physical keyboard, canonical terminal mode, or another virtual machine.

## Cumulative regression

After `check-shell`, the current tree also passed `check-fd`, `check-fat`,
`check-block`, `check-process`, `check-syscall`, `check-elf`, `check-memory`,
`check-runtime-limit`, and `check-keyboard`. These are QEMU/GDB runtime checks,
not compilation-only targets. A concise target list is kept in
`docs/day23-cumulative.txt`.

## Standalone attachment verification

The frozen `os-day-23.zip` has SHA-256
`5f4af72799f0d876218d62029fca483a47b2284f255ffa37c4f7f1c323ce1d3f` and
contains no `build/` directory. It was extracted into a fresh temporary
directory, rebuilt from scratch, and passed `check-shell`, `check-fd`,
`check-fat`, `check-block`, `check-process`, `check-syscall`, `check-elf`,
`check-memory`, `check-runtime-limit`, and `check-keyboard`. The rebuilt
kernel, Shell image, user ELF, and `README.TXT` hashes match the source-tree
values above. The concise result is recorded in `docs/day23-zipcheck.txt`;
that post-freeze receipt is intentionally not embedded back into the archive.
