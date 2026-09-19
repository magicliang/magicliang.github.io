#if defined(__GNUC__) || defined(__clang__)
#define NOINLINE __attribute__((noinline))
#else
#define NOINLINE
#endif

NOINLINE int helper(int z) {
    return z * 2 + 1;
}

NOINLINE int add_then_call(int x, int y) {
    int z = x + y;
    return helper(z) + z;
}

int main(void) {
    return add_then_call(3, 4) == 22 ? 0 : 1;
}
