long cross_isa_sum(const long *values, long n, long scale) {
    long sum = 0;
    for (long i = 0; i < n; ++i) {
        sum += values[i] * scale + i;
    }
    return sum;
}
