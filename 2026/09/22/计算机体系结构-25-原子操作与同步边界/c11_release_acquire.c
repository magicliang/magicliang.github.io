#include <assert.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

enum { ITERATIONS = 2000 };

static atomic_int flag;
static int payload;

static void *producer(void *arg) {
    (void)arg;
    payload = 42;
    atomic_store_explicit(&flag, 1, memory_order_release);
    return NULL;
}

static void *consumer(void *arg) {
    int *observed = (int *)arg;
    while (atomic_load_explicit(&flag, memory_order_acquire) != 1) {
    }
    *observed = payload;
    return NULL;
}

int main(void) {
    int failures = 0;
    for (int i = 0; i < ITERATIONS; i++) {
        atomic_store_explicit(&flag, 0, memory_order_relaxed);
        payload = 0;

        int observed = -1;
        pthread_t prod;
        pthread_t cons;
        if (pthread_create(&cons, NULL, consumer, &observed) != 0) {
            perror("pthread_create consumer");
            return 2;
        }
        if (pthread_create(&prod, NULL, producer, NULL) != 0) {
            perror("pthread_create producer");
            return 2;
        }
        pthread_join(prod, NULL);
        pthread_join(cons, NULL);
        if (observed != 42) {
            failures++;
        }
    }

    printf("c11_release_acquire: iterations=%d failures=%d expected_payload=42\n", ITERATIONS, failures);
    assert(failures == 0);
    return failures == 0 ? 0 : 1;
}
