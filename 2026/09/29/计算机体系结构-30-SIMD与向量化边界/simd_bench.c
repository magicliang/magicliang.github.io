#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifndef KERNEL_NAME
#define KERNEL_NAME add_kernel
#endif

__attribute__((noinline)) static void KERNEL_NAME(const float *restrict a, const float *restrict b, float *restrict c, size_t n) {
    for (size_t i = 0; i < n; ++i) c[i] = a[i] + b[i];
}

static long parse_long(const char *s, long lo, long hi, const char *name) {
    char *end = NULL; errno = 0;
    if (!s[0] || s[0] == '-') { fprintf(stderr, "%s out of range\n", name); exit(2); }
    long v = strtol(s, &end, 10);
    if (errno || *end || v < lo || v > hi) { fprintf(stderr, "%s out of range\n", name); exit(2); }
    return v;
}
static double now(void) { struct timespec t; if (clock_gettime(CLOCK_MONOTONIC, &t)) exit(3); return t.tv_sec + t.tv_nsec / 1e9; }

int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "--help")) { puts("usage: simd_bench N REPS ROUNDS; N=1..10000000 REPS=1..1000000 ROUNDS=1..64"); return 0; }
    if (argc != 4) return 2;
    size_t n = (size_t)parse_long(argv[1], 1, 10000000, "n");
    long reps = parse_long(argv[2], 1, 1000000, "reps");
    long rounds = parse_long(argv[3], 1, 64, "rounds");
    float *a = aligned_alloc(64, ((n * sizeof(float) + 63) / 64) * 64);
    float *b = aligned_alloc(64, ((n * sizeof(float) + 63) / 64) * 64);
    float *c = aligned_alloc(64, ((n * sizeof(float) + 63) / 64) * 64);
    if (!a || !b || !c) return 3;
    for (size_t i = 0; i < n; ++i) { a[i] = (float)(i % 17); b[i] = (float)(i % 13); }
    KERNEL_NAME(a,b,c,n);
    for (size_t i = 0; i < n; ++i) if (c[i] != a[i] + b[i]) return 4;
    for (long round = 0; round < rounds; ++round) {
        double start = now();
        for (long rep = 0; rep < reps; ++rep) { KERNEL_NAME(a,b,c,n); __asm__ volatile("" ::: "memory"); }
        double elapsed = now() - start;
        double checksum = 0; for (size_t i = 0; i < n; ++i) checksum += c[i];
        printf("{\"round\":%ld,\"n\":%zu,\"reps\":%ld,\"seconds\":%.9f,\"checksum\":%.0f,\"tail\":%zu}\n", round, n, reps, elapsed, checksum, n % 8);
    }
    free(a); free(b); free(c); return 0;
}
