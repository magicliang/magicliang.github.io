#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

enum {
    DEFAULT_AOS_N = 1048576u,
    DEFAULT_MAT_N = 192u,
    DEFAULT_BLOCK = 32u,
    DEFAULT_REPS = 5u,
    MAX_AOS_N = 16777216u,
    MAX_MAT_N = 2048u,
    MAX_REPS = 1000u
};

typedef struct {
    float x;
    float y;
    float z;
    float w;
} Point;

static uint64_t nsec_now(void) {
#ifdef __APPLE__
    return clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
#else
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
        perror("clock_gettime");
        exit(2);
    }
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
#endif
}

static float aos_sum(const Point *points, size_t n) {
    float acc = 0.0f;
    for (size_t i = 0; i < n; i++) {
        acc += points[i].x;
    }
    return acc;
}

static float soa_sum(const float *x, size_t n) {
    float acc = 0.0f;
    for (size_t i = 0; i < n; i++) {
        acc += x[i];
    }
    return acc;
}

static float matmul_plain(const float *a, const float *b, float *c, size_t n) {
    memset(c, 0, n * n * sizeof(float));
    for (size_t i = 0; i < n; i++) {
        for (size_t k = 0; k < n; k++) {
            const float aik = a[i * n + k];
            for (size_t j = 0; j < n; j++) {
                c[i * n + j] += aik * b[k * n + j];
            }
        }
    }
    return c[(n / 2) * n + n / 2];
}

static float matmul_blocked(const float *a, const float *b, float *c, size_t n, size_t block) {
    memset(c, 0, n * n * sizeof(float));
    for (size_t ii = 0; ii < n; ii += block) {
        for (size_t kk = 0; kk < n; kk += block) {
            for (size_t jj = 0; jj < n; jj += block) {
                size_t imax = ii + block < n ? ii + block : n;
                size_t kmax = kk + block < n ? kk + block : n;
                size_t jmax = jj + block < n ? jj + block : n;
                for (size_t i = ii; i < imax; i++) {
                    for (size_t k = kk; k < kmax; k++) {
                        const float aik = a[i * n + k];
                        for (size_t j = jj; j < jmax; j++) {
                            c[i * n + j] += aik * b[k * n + j];
                        }
                    }
                }
            }
        }
    }
    return c[(n / 2) * n + n / 2];
}

static int parse_size_arg(const char *text, const char *name, size_t min, size_t max, size_t *out) {
    char *end = NULL;
    unsigned long long value;
    if (text[0] == '-' || text[0] == '\0') {
        fprintf(stderr, "%s must be an integer in [%zu, %zu]\n", name, min, max);
        return 0;
    }
    errno = 0;
    value = strtoull(text, &end, 10);
    if (errno != 0 || *end != '\0' || value < min || value > max) {
        fprintf(stderr, "%s must be an integer in [%zu, %zu]\n", name, min, max);
        return 0;
    }
    *out = (size_t)value;
    return 1;
}

static int checked_mul_size(size_t a, size_t b, size_t *out) {
    if (a != 0 && b > SIZE_MAX / a) {
        return 0;
    }
    *out = a * b;
    return 1;
}

static void *checked_alloc(size_t bytes) {
    void *p = malloc(bytes);
    if (!p) {
        fprintf(stderr, "allocation failed: %zu bytes\n", bytes);
        exit(2);
    }
    return p;
}

static void run_aos_soa(size_t n, size_t reps) {
    size_t point_bytes;
    size_t x_bytes;
    if (!checked_mul_size(n, sizeof(Point), &point_bytes) || !checked_mul_size(n, sizeof(float), &x_bytes)) {
        fprintf(stderr, "aos/soa allocation size overflow\n");
        exit(2);
    }
    Point *points = checked_alloc(point_bytes);
    float *x = checked_alloc(x_bytes);
    for (size_t i = 0; i < n; i++) {
        float v = (float)((i % 1024u) + 1u);
        points[i] = (Point){v, v + 1.0f, v + 2.0f, v + 3.0f};
        x[i] = v;
    }
    float check_a = aos_sum(points, n);
    float check_s = soa_sum(x, n);
    if (check_a != check_s) {
        fprintf(stderr, "aos/soa mismatch: %.8g %.8g\n", check_a, check_s);
        exit(1);
    }
    for (size_t rep = 0; rep < reps; rep++) {
        uint64_t t0 = nsec_now();
        volatile float a = aos_sum(points, n);
        uint64_t t1 = nsec_now();
        volatile float s = soa_sum(x, n);
        uint64_t t2 = nsec_now();
        printf("{\"case\":\"aos_soa\",\"rep\":%zu,\"n\":%zu,\"aos_ns\":%llu,\"soa_ns\":%llu,\"checksum\":%.8g}\n",
               rep, n, (unsigned long long)(t1 - t0), (unsigned long long)(t2 - t1), (double)(a + s));
    }
    free(points);
    free(x);
}

static void run_matmul(size_t n, size_t block, size_t reps) {
    size_t elem_count;
    size_t bytes;
    if (!checked_mul_size(n, n, &elem_count) || !checked_mul_size(elem_count, sizeof(float), &bytes)) {
        fprintf(stderr, "matmul allocation size overflow\n");
        exit(2);
    }
    float *a = checked_alloc(bytes);
    float *b = checked_alloc(bytes);
    float *c0 = checked_alloc(bytes);
    float *c1 = checked_alloc(bytes);
    for (size_t i = 0; i < n * n; i++) {
        a[i] = (float)((int)(i % 17u) - 8) / 17.0f;
        b[i] = (float)((int)(i % 13u) - 6) / 13.0f;
    }
    float p = matmul_plain(a, b, c0, n);
    float q = matmul_blocked(a, b, c1, n, block);
    double max_diff = 0.0;
    for (size_t i = 0; i < n * n; i++) {
        double d = c0[i] > c1[i] ? c0[i] - c1[i] : c1[i] - c0[i];
        if (d > max_diff) {
            max_diff = d;
        }
    }
    if (max_diff > 0.001) {
        fprintf(stderr, "matmul mismatch: center %.8g %.8g max_diff %.8g\n", p, q, max_diff);
        exit(1);
    }
    for (size_t rep = 0; rep < reps; rep++) {
        uint64_t t0 = nsec_now();
        volatile float plain = matmul_plain(a, b, c0, n);
        uint64_t t1 = nsec_now();
        volatile float blocked = matmul_blocked(a, b, c1, n, block);
        uint64_t t2 = nsec_now();
        printf("{\"case\":\"matmul\",\"rep\":%zu,\"n\":%zu,\"block\":%zu,\"plain_ns\":%llu,\"blocked_ns\":%llu,\"checksum\":%.8g}\n",
               rep, n, block, (unsigned long long)(t1 - t0), (unsigned long long)(t2 - t1), (double)(plain + blocked));
    }
    free(a);
    free(b);
    free(c0);
    free(c1);
}

static void print_usage(const char *prog) {
    fprintf(stderr, "usage: %s [aos_soa_n<=%u] [matmul_n<=%u] [block<=matmul_n] [reps<=%u]\n",
            prog, MAX_AOS_N, MAX_MAT_N, MAX_REPS);
}

int main(int argc, char **argv) {
    size_t n = DEFAULT_AOS_N;
    size_t mat_n = DEFAULT_MAT_N;
    size_t block = DEFAULT_BLOCK;
    size_t reps = DEFAULT_REPS;
    if (argc > 1 && strcmp(argv[1], "--help") == 0) {
        print_usage(argv[0]);
        return 0;
    }
    if (argc > 5) {
        print_usage(argv[0]);
        return 2;
    }
    if (argc > 1 && !parse_size_arg(argv[1], "aos_soa_n", 1, MAX_AOS_N, &n)) {
        return 2;
    }
    if (argc > 2 && !parse_size_arg(argv[2], "matmul_n", 1, MAX_MAT_N, &mat_n)) {
        return 2;
    }
    if (argc > 3 && !parse_size_arg(argv[3], "block", 1, MAX_MAT_N, &block)) {
        return 2;
    }
    if (argc > 4 && !parse_size_arg(argv[4], "reps", 1, MAX_REPS, &reps)) {
        return 2;
    }
    if (block > mat_n) {
        fprintf(stderr, "block must be <= matmul_n\n");
        return 2;
    }
    run_aos_soa(n, reps);
    run_matmul(mat_n, block, reps);
    return 0;
}
