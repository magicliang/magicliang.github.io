#include <stdint.h>
#include <stdio.h>

uint32_t sum5(const uint32_t *a) {
    uint32_t sum = 0;
    for (uint32_t i = 0; i < 5; i++) {
        sum += a[i];
    }
    return sum;
}

int main(void) {
    const uint32_t a[5] = {3, 4, 5, 6, 7};
    printf("sum5=%u\n", sum5(a));
    return 0;
}
