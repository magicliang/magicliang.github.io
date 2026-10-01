#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef struct { _Atomic uint64_t value; } compact_counter;
typedef struct { _Atomic uint64_t value; unsigned char pad[256 - sizeof(_Atomic uint64_t)]; } spaced_counter;
typedef struct {
    int id, threads, mode;
    uint64_t work;
    uint64_t *array;
    compact_counter *compact;
    spaced_counter *spaced;
} worker_arg;

static uint64_t parse_u64(const char *s, uint64_t lo, uint64_t hi, const char *name) {
    char *end = NULL;
    errno = 0;
    if (!s[0] || s[0] == '-') { fprintf(stderr, "%s must be in [%llu,%llu]\n", name, (unsigned long long)lo, (unsigned long long)hi); exit(2); }
    unsigned long long v = strtoull(s, &end, 10);
    if (errno || *end || v < lo || v > hi) { fprintf(stderr, "%s must be in [%llu,%llu]\n", name, (unsigned long long)lo, (unsigned long long)hi); exit(2); }
    return (uint64_t)v;
}

static void *worker(void *opaque) {
    worker_arg *a = opaque;
    uint64_t begin = a->work * (uint64_t)a->id / (uint64_t)a->threads;
    uint64_t end = a->work * (uint64_t)(a->id + 1) / (uint64_t)a->threads;
    if (a->mode == 0) {
        for (uint64_t i = begin; i < end; ++i) a->array[i] = i * 3u + 1u;
    } else if (a->mode == 1) {
        for (uint64_t i = begin; i < end; ++i) atomic_fetch_add_explicit(&a->compact[a->id].value, 1, memory_order_relaxed);
    } else {
        for (uint64_t i = begin; i < end; ++i) atomic_fetch_add_explicit(&a->spaced[a->id].value, 1, memory_order_relaxed);
    }
    return NULL;
}

static double seconds(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) exit(3);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--help") == 0) {
        puts("usage: scaling_bench THREADS WORK MODE; THREADS=1..64 WORK=1..100000000 MODE=independent|compact|spaced256");
        return 0;
    }
    if (argc != 4) return 2;
    int threads = (int)parse_u64(argv[1], 1, 64, "threads");
    uint64_t work = parse_u64(argv[2], 1, 100000000, "work");
    int mode = !strcmp(argv[3], "independent") ? 0 : !strcmp(argv[3], "compact") ? 1 : !strcmp(argv[3], "spaced256") ? 2 : -1;
    if (mode < 0) { fputs("unknown mode\n", stderr); return 2; }
    pthread_t *ids = calloc((size_t)threads, sizeof(*ids));
    worker_arg *args = calloc((size_t)threads, sizeof(*args));
    uint64_t *array = mode == 0 ? calloc((size_t)work, sizeof(*array)) : NULL;
    compact_counter *compact = mode == 1 ? calloc((size_t)threads, sizeof(*compact)) : NULL;
    spaced_counter *spaced = mode == 2 ? calloc((size_t)threads, sizeof(*spaced)) : NULL;
    if (!ids || !args || (mode == 0 && !array) || (mode == 1 && !compact) || (mode == 2 && !spaced)) return 3;
    double start = seconds();
    for (int i = 0; i < threads; ++i) {
        args[i] = (worker_arg){i, threads, mode, work, array, compact, spaced};
        if (pthread_create(&ids[i], NULL, worker, &args[i])) return 3;
    }
    for (int i = 0; i < threads; ++i) if (pthread_join(ids[i], NULL)) return 3;
    double elapsed = seconds() - start;
    uint64_t checksum = 0;
    if (mode == 0) for (uint64_t i = 0; i < work; ++i) checksum += array[i];
    if (mode == 1) for (int i = 0; i < threads; ++i) checksum += atomic_load_explicit(&compact[i].value, memory_order_relaxed);
    if (mode == 2) for (int i = 0; i < threads; ++i) checksum += atomic_load_explicit(&spaced[i].value, memory_order_relaxed);
    uint64_t expected = mode == 0 ? (3u * work * (work - 1u) / 2u + work) : work;
    printf("{\"mode\":\"%s\",\"threads\":%d,\"work\":%llu,\"seconds\":%.9f,\"checksum\":%llu,\"expected\":%llu,\"ok\":%s,\"atomic_lock_free\":%s,\"spaced_bytes\":%zu}\n", argv[3], threads, (unsigned long long)work, elapsed, (unsigned long long)checksum, (unsigned long long)expected, checksum == expected ? "true" : "false", atomic_is_lock_free(&(compact_counter){0}.value) ? "true" : "false", sizeof(spaced_counter));
    free(ids); free(args); free(array); free(compact); free(spaced);
    return checksum == expected ? 0 : 4;
}
