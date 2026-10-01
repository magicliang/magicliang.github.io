# Day 24 evidence

Date: 2026-09-20

## Source baseline

- Implementation commit: `1232e13cf73c099bb8b859c9ec470d3e19c11b24`
- Kernel image SHA-256: `13d578c4e459bacfb8cad29d0634ba5cb25b8ed520b849cea719cf1180e903cf`
- Shell kernel image SHA-256: `c64704e5b77db1428a657ed23762e02bb77a25a5ecf61e6dbf6e855e2464ceb9`
- Shell disk image SHA-256: `8d12036762b5937b9a7db28bb85efe9fe7c9d8e7b724e937758b1a315ec58b35`
- User ELF SHA-256: `b44b54cef5743aaa2c8423492cc5d15e96f567802256cbcd25186a7b493bc8b9`
- `README.TXT` SHA-256: `25fc6f4ce8493714e7056d2896c47e6a9f4c4db91a4b860dd474035542804798`

The implementation commit contains the pipe object, endpoint open-files,
syscall, Shell assembly, user commands, and the QEMU/GDB check. The article,
persisted logs, archive hash, and standalone verification are recorded in the
following documentation commit.

## Environment

- QEMU 8.2.2 (`Debian 1:8.2.2+ds-0ubuntu1.18`)
- SeaBIOS 1.16.3 package image
- GDB 15.1
- GCC 13.3.0
- GNU Binutils 2.42
- NASM 2.16.01
- Machine: `pc-i440fx-7.2`, TCG, `qemu32`, 1 CPU, 64 MiB

The unpacked toolchain under `/tmp/build-an-os-tools` is not part of the
delivery archive.

## Command

```sh
PATH=/tmp/build-an-os-tools/bin:$PATH \
LD_LIBRARY_PATH=/tmp/build-an-os-tools/root2/usr/lib/x86_64-linux-gnu:\
/tmp/build-an-os-tools/root2/lib/x86_64-linux-gnu \
QEMU_MODULE_DIR=/tmp/build-an-os-tools/root2/usr/lib/x86_64-linux-gnu/qemu \
make check-pipe \
  QEMU=/tmp/build-an-os-tools/bin/qemu-system-i386 \
  GDB=/tmp/build-an-os-tools/bin/gdb-multiarch \
  BIOS=/tmp/build-an-os-tools/root2/usr/share/seabios/bios-256k.bin \
  QEMU_DATA=/tmp/build-an-os-tools/root2/usr/share/qemu
```

Exit status: 0.

## Runtime observations

The HMP keyboard sequence runs:

```text
cat readme.txt | wc
echo abc|wc
cat readme.txt | head
cat readme.txt | nosuch
pipetest
echo x || wc
echo recovered
exit
```

The first command reports `27 1479`, matching the host file's line and byte
counts. The parser also accepts a pipe token without surrounding spaces. The
`head` probe consumes one byte and exits; its producer receives the custom
broken-pipe error and the Shell reports `left command failed`. When the second
spawn names a missing executable, the Shell closes both parent endpoints before
waiting for the already-blocked producer, then returns to a prompt.

`pipetest` first supplies an unmapped output pointer to `pipe`, then performs
four create/second-create/close cycles. The invalid pointer returns `EFAULT`
before allocation. While one pipe is live the second call returns `ENFILE`;
after both fds close the next creation succeeds. Its visible success marker is
`PIPE API OK`.

The final serial counters are:

```text
PIPE STATS creates=8 releases=8 rblock=22 wblock=6 eof=2 broken=2 read=1484 written=1612
SHELL OK prompts=8 pages=16048
```

The 1484 consumed bytes are 1479 from the complete file, four from `echo`, and
one from the early-exit probe. More bytes were committed by the two failed
pipelines and deliberately remained unread. Six writer blocks prove the 64-byte
buffer applied backpressure; 22 reader blocks show empty-buffer waits rather
than polling. Two complete pipelines reached EOF, and two producers observed a
closed read side. Every one of the eight successful pipe creations was released.

After `SHELL OK`, GDB attached to the still-running kernel and read the debug
symbols directly:

```text
STATE creates=8 releases=8 rblock=22 wblock=6 eof=2 broken=2 used=0 readers=0 writers=0
PASS: GDB observed blocking, EOF, broken-pipe wakeup and final reclamation
```

The final pipe slot has no bytes and neither endpoint is open. The shell exit
assertion also checks zero live open-files, zero file references, and recovery
to the original free-page count.

## Implemented contract

- One fixed 64-byte pipe and one read/write endpoint pair may exist at a time.
- fd inheritance increments endpoint open-file references. The pipe side closes
  only when the endpoint's final open-file reference disappears.
- Empty with a writer means block; empty without writers means EOF.
- Full with a reader means block; no readers means the custom `EPIPE` result.
- Reads and writes may be short. User programs loop until the requested transfer
  completes or an error occurs.
- Closing the final reader wakes all writers; closing the final writer wakes all
  readers. Every wake returns to a `while` condition check.
- `pipe()` validates the output pointer before allocating and installs both fd
  entries atomically. Allocation or fd failure rolls back both endpoint objects.
- The Shell starts both children before waiting and closes both parent copies.
  If the consumer spawn fails, it closes both copies before waiting for the
  producer.

## Boundaries

This is a teaching ABI, not a POSIX implementation. It has no SIGPIPE,
`PIPE_BUF` atomicity guarantee, nonblocking mode, `select`/`poll`, named pipes,
multiple simultaneous pipe objects, multi-stage pipelines, redirection,
background jobs, or job control. A write that finds some room may return a
short count; the user program must continue it.

The scheduler and wait queues assume one CPU. Interrupt masking protects the
condition check, queue insertion, ring indices, and endpoint state. The design
does not claim SMP safety or FIFO wake fairness.

## Cumulative regression

After the specialized run, the current tree passed `check-shell`, `check-fd`,
`check-fat`, `check-block`, `check-process`, `check-syscall`, `check-elf`,
`check-memory`, `check-runtime-limit`, and `check-keyboard`. These are runtime
QEMU/GDB checks. The target list is recorded in `docs/day24-cumulative.txt`.

## Standalone attachment verification

The frozen `os-day-24.zip` has SHA-256
`fa86c15e1ea6721ea9f7d01550dcc1a8ae731937b60c26e68d916474d59a71c6`.
It contains no `build/` directory. The archive was extracted into a fresh
temporary directory, rebuilt from scratch, and passed `check-pipe` plus all ten
cumulative targets listed above. Rebuilt `kernel.bin`, `kernel-shell.bin`,
`mbr-shell.img`, and `day23-user.elf` hashes match the source-tree values. The
concise receipt is `docs/day24-zipcheck.txt`; it was created after the archive
was frozen and is intentionally not embedded back into that archive.
