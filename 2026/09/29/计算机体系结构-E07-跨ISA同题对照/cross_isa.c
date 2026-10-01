#ifdef CROSS_ISA_TRACE
#include <stdio.h>
#endif

long cross_isa_sum(const long *values, long n, long scale) {
    long sum = 0;
    for (long i = 0; i < n; ++i) {
        sum += values[i] * scale + i;
#ifdef CROSS_ISA_TRACE
        fprintf(stderr, "i=%ld value=%ld term=%ld sum=%ld\n", i, values[i], values[i] * scale + i, sum);
#endif
    }
    return sum;
}
