#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p build outputs

cc -std=c11 -Wall -Wextra -pedantic -O2 src/rv32i_ref.c -o build/rv32i_ref
cc -std=c11 -Wall -Wextra -pedantic -O0 -fno-omit-frame-pointer -S src/abi_sample.c -o outputs/abi_sample_aarch64.s
cc -std=c11 -Wall -Wextra -pedantic -O0 -fno-omit-frame-pointer -c src/abi_sample.c -o build/abi_sample.o
/Library/Developer/CommandLineTools/usr/bin/llvm-objdump -d build/abi_sample.o > outputs/abi_sample_aarch64_objdump.txt

{
  date
  uname -a
  cc --version
  python3 --version
} > outputs/environment.txt

python3 src/alu_notes.py > outputs/alu_notes.txt

for program in sum branch_loop x0 signed_compare; do
  ./build/rv32i_ref "programs/${program}.hex" > "outputs/${program}.jsonl"
done

for program in fail_unsupported fail_misaligned fail_oob fail_store_text fail_text_junk fail_data_extra fail_data_overlap fail_branch_misaligned; do
  if ./build/rv32i_ref "programs/${program}.hex" > "outputs/${program}.jsonl" 2>&1; then
    echo "${program}: expected failure but succeeded" >&2
    exit 1
  fi
done

tail -n 1 outputs/sum.jsonl | grep '"mem148":25' >/dev/null
tail -n 1 outputs/branch_loop.jsonl | grep '"mem160":10' >/dev/null
tail -n 1 outputs/x0.jsonl | grep '"x0":0' >/dev/null
tail -n 1 outputs/x0.jsonl | grep '"x1":1' >/dev/null
tail -n 1 outputs/signed_compare.jsonl | grep '"x3":7' >/dev/null
grep '"error":"unsupported_i_type"' outputs/fail_unsupported.jsonl >/dev/null
grep '"error":"misaligned_lw"' outputs/fail_misaligned.jsonl >/dev/null
grep '"error":"load_out_of_bounds"' outputs/fail_oob.jsonl >/dev/null
grep '"error":"store_to_text"' outputs/fail_store_text.jsonl >/dev/null
grep 'bad instruction word' outputs/fail_text_junk.jsonl >/dev/null
grep "data line must be '<addr> <word>'" outputs/fail_data_extra.jsonl >/dev/null
grep 'bad data word' outputs/fail_data_overlap.jsonl >/dev/null
grep '"error":"branch_target_out_of_text"' outputs/fail_branch_misaligned.jsonl >/dev/null

echo "base regression: PASS"
