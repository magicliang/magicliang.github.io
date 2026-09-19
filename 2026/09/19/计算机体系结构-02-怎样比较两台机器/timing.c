#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

enum { N = 1 << 20, REPEATS = 9, PASSES = 128 };

static volatile uint64_t sink;

static uint64_t now_ns(void) {
#ifdef __APPLE__
    return clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
#endif
}

static uint64_t sum_array(const uint32_t *a, size_t n) {
    uint64_t acc = 0;
    for (size_t pass = 0; pass < PASSES; pass++) {
        for (size_t i = 0; i < n; i++) {
            acc += a[i];
        }
    }
    return acc;
}

static int cmp_u64(const void *a, const void *b) {
    uint64_t x = *(const uint64_t *)a;
    uint64_t y = *(const uint64_t *)b;
    return (x > y) - (x < y);
}

int main(void) {
    uint32_t *a = malloc((size_t)N * sizeof *a);
    if (!a) return 2;

    uint64_t one_pass = 0;
    for (size_t i = 0; i < N; i++) {
        a[i] = (uint32_t)((i * 2654435761u) ^ (i >> 3));
        one_pass += a[i];
    }
    uint64_t expected = one_pass * (uint64_t)PASSES;
    uint64_t warmup = sum_array(a, N);
    if (warmup != expected) {
        fprintf(stderr, "warmup checksum mismatch: got=%llu expected=%llu\n",
                (unsigned long long)warmup, (unsigned long long)expected);
        free(a);
        return 1;
    }

    uint64_t times[REPEATS];
    printf("n=%d passes=%d bytes=%zu expected=%llu warmup_ok=yes\n",
           N, PASSES, (size_t)N * sizeof *a,
           (unsigned long long)expected);
    for (int r = 0; r < REPEATS; r++) {
        uint64_t t0 = now_ns();
        uint64_t got = sum_array(a, N);
        uint64_t t1 = now_ns();
        if (got != expected) {
            fprintf(stderr, "checksum mismatch on run %d: got=%llu expected=%llu\n",
                    r + 1, (unsigned long long)got,
                    (unsigned long long)expected);
            free(a);
            return 1;
        }
        sink = got;
        times[r] = t1 - t0;
        printf("run=%d ns=%llu checksum=%llu ok=yes\n",
               r + 1, (unsigned long long)times[r],
               (unsigned long long)got);
    }

    qsort(times, REPEATS, sizeof times[0], cmp_u64);
    printf("min_ns=%llu median_ns=%llu max_ns=%llu sink=%llu\n",
           (unsigned long long)times[0],
           (unsigned long long)times[REPEATS / 2],
           (unsigned long long)times[REPEATS - 1],
           (unsigned long long)sink);
    free(a);
    return 0;
}
