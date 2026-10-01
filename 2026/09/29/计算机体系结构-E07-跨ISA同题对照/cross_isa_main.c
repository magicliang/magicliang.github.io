#include <stdio.h>

long cross_isa_sum(const long *values, long count, long scale);

int main(void) {
    const long values[] = {2, -1, 4, 0, 3};
    const long result = cross_isa_sum(values, 5, 3);
    printf("sum=%ld\n", result);
    return result == 34 ? 0 : 1;
}
