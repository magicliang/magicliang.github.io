#include <float.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

struct Padded {
    uint8_t tag;
    uint32_t value;
};

static double grouped_left(const volatile double *v) {
    return (v[0] + v[1]) + v[2];
}

static double grouped_right(const volatile double *v) {
    return v[0] + (v[1] + v[2]);
}

int main(void) {
    _Static_assert(sizeof(float) == sizeof(uint32_t), "this example needs 32-bit float");

    uint32_t word = 0x01020304u;
    unsigned char bytes[sizeof word];
    memcpy(bytes, &word, sizeof bytes);

    uint32_t one_bits = 0x3f800000u;
    float one = 0.0f;
    memcpy(&one, &one_bits, sizeof one);

    uint32_t wrap = UINT32_MAX;
    wrap += 1u;

    volatile double sample[3] = {1e20, -1e20, 3.14};
    double left = grouped_left(sample);
    double right = grouped_right(sample);

    printf("host_byte_order_probe=0x%02x%02x%02x%02x\n",
           bytes[0], bytes[1], bytes[2], bytes[3]);
    printf("uint32_bits_0x3f800000_as_float=%.1f\n", one);
    printf("uint32_max_plus_one=%u\n", wrap);
    printf("float_env=FLT_RADIX:%d FLT_MANT_DIG:%d DBL_MANT_DIG:%d\n",
           FLT_RADIX, FLT_MANT_DIG, DBL_MANT_DIG);
    printf("struct_padded_size=%zu align=%zu offset_value=%zu\n",
           sizeof(struct Padded), _Alignof(struct Padded),
           offsetof(struct Padded, value));
    printf("float_left=%.17g\n", left);
    printf("float_right=%.17g\n", right);
    printf("float_non_associative=%s\n", left == right ? "false" : "true");
    if (one != 1.0f || wrap != 0 || left == right) {
        return 1;
    }
    if (sizeof(struct Padded) < offsetof(struct Padded, value) + sizeof(uint32_t)) {
        return 1;
    }
    return 0;
}
