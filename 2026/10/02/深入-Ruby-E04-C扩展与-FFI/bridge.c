#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include <pthread.h>
static _Atomic int live = 0;
void *owned_new(int size) {
    if (size < 1 || size > 1024) return NULL;
    void *ptr = malloc((size_t)size);
    if (ptr) { memset(ptr, 'A', (size_t)size); atomic_fetch_add(&live, 1); }
    return ptr;
}
void owned_free(void *ptr) { if (ptr) { free(ptr); atomic_fetch_sub(&live, 1); } }
int owned_live(void) { return atomic_load(&live); }
int checksum(const unsigned char *ptr, int size) {
    if (!ptr || size < 1 || size > 1024) return -1;
    int sum = 0; for (int i = 0; i < size; i++) sum += ptr[i]; return sum;
}
typedef struct {
    _Atomic int value;
    pthread_mutex_t lock;
    pthread_cond_t condition;
    int ready, safe;
} counter_t;
static void *update(void *ptr) {
    counter_t *counter = ptr;
    if (counter->safe) {
        for (int i = 0; i < 1000; i++) atomic_fetch_add(&counter->value, 1);
    } else {
        int old = atomic_load(&counter->value);
        pthread_mutex_lock(&counter->lock);
        counter->ready++;
        pthread_cond_broadcast(&counter->condition);
        while (counter->ready < 2) pthread_cond_wait(&counter->condition, &counter->lock);
        pthread_mutex_unlock(&counter->lock);
        atomic_store(&counter->value, old + 1);
    }
    return NULL;
}
int native_counter(int safe) {
    counter_t counter = { .value = 0, .lock = PTHREAD_MUTEX_INITIALIZER,
        .condition = PTHREAD_COND_INITIALIZER, .ready = 0, .safe = safe };
    pthread_t threads[2];
    /* Abort this isolated lab process if thread creation fails; never leave a barrier waiter. */
    if (pthread_create(&threads[0], NULL, update, &counter) != 0) abort();
    if (pthread_create(&threads[1], NULL, update, &counter) != 0) abort();
    pthread_join(threads[0], NULL); pthread_join(threads[1], NULL);
    pthread_cond_destroy(&counter.condition); pthread_mutex_destroy(&counter.lock);
    return atomic_load(&counter.value);
}
