package blog.libraries;

import com.github.benmanes.caffeine.cache.Caffeine;
import com.github.benmanes.caffeine.cache.LoadingCache;
import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.util.concurrent.SettableFuture;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.time.Duration;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

class Chapter31Test {
    @Test
    void missingAndFailedLoadsHaveDifferentContracts() {
        AtomicInteger calls = new AtomicInteger();
        LoadingCache<String, String> caffeine = Caffeine.newBuilder().build(key -> {
            calls.incrementAndGet();
            return null;
        });
        assertNull(caffeine.get("absent"));
        assertNull(caffeine.get("absent"));
        assertEquals(2, calls.get());
        assertEquals(0, caffeine.estimatedSize());
        com.google.common.cache.LoadingCache<String, String> guava = CacheBuilder.newBuilder()
                .build(new CacheLoader<String, String>() {
                    @Override public String load(String key) { return null; }
                });
        assertThrows(CacheLoader.InvalidCacheLoadException.class, () -> guava.get("absent"));
        LoadingCache<String, String> broken = Caffeine.newBuilder().build(key -> {
            throw new IOException("synthetic backend failure");
        });
        CompletionException caffeineError = assertThrows(CompletionException.class, () -> broken.get("x"));
        assertInstanceOf(IOException.class, caffeineError.getCause());
        com.google.common.cache.LoadingCache<String, String> brokenGuava = CacheBuilder.newBuilder()
                .build(new CacheLoader<String, String>() {
                    @Override public String load(String key) throws IOException {
                        throw new IOException("synthetic backend failure");
                    }
                });
        ExecutionException guavaError = assertThrows(ExecutionException.class, () -> brokenGuava.get("x"));
        assertInstanceOf(IOException.class, guavaError.getCause());
        System.out.println("C31 missing=Caffeine(null,not-cached,calls2)/Guava(InvalidCacheLoadException); checked=CompletionException/ExecutionException");
    }

    @Test
    void refreshAccessKeepsOldValueAndNullRefreshRemovesIt() {
        AtomicLong clock = new AtomicLong();
        AtomicInteger reloads = new AtomicInteger();
        AtomicReference<CompletableFuture<String>> pending = new AtomicReference<>();
        LoadingCache<String, String> cache = Caffeine.newBuilder().ticker(clock::get)
                .executor(Runnable::run).refreshAfterWrite(Duration.ofSeconds(10))
                .expireAfterWrite(Duration.ofSeconds(30))
                .build(new com.github.benmanes.caffeine.cache.CacheLoader<String, String>() {
                    @Override public String load(String key) { return "v1"; }
                    @Override public CompletableFuture<String> asyncReload(
                            String key, String oldValue, Executor executor) {
                        reloads.incrementAndGet();
                        CompletableFuture<String> next = new CompletableFuture<>();
                        pending.set(next);
                        return next;
                    }
                });
        assertEquals("v1", cache.get("sku"));
        clock.set(TimeUnit.SECONDS.toNanos(11));
        assertEquals(0, reloads.get());
        assertEquals("v1", cache.get("sku"));
        assertEquals(1, reloads.get());
        pending.get().completeExceptionally(new IOException("synthetic refresh failure"));
        assertEquals("v1", cache.get("sku"));
        assertEquals(2, reloads.get());
        pending.get().complete("v2");
        assertEquals("v2", cache.getIfPresent("sku"));
        clock.set(TimeUnit.SECONDS.toNanos(22));
        assertEquals("v2", cache.get("sku"));
        pending.get().complete(null);
        assertNull(cache.getIfPresent("sku"));
        System.out.println("C31 refresh: idle=0,pending=old,failure=old+retry,success=v2,null=removed");
    }

    @Test
    void invalidationDuringRefreshDiscardsCaffeineCompletionButGuavaRefills() throws Exception {
        CompletableFuture<String> caffeineNext = new CompletableFuture<>();
        LoadingCache<String, String> caffeine = Caffeine.newBuilder().executor(Runnable::run)
                .build(new com.github.benmanes.caffeine.cache.CacheLoader<String, String>() {
                    @Override public String load(String key) { return "initial"; }
                    @Override public CompletableFuture<String> asyncReload(
                            String key, String oldValue, Executor executor) { return caffeineNext; }
                });
        caffeine.put("sku", "old");
        CompletableFuture<String> observation = caffeine.refresh("sku");
        caffeine.invalidate("sku");
        caffeineNext.complete("late");
        assertEquals("late", observation.get(5, TimeUnit.SECONDS));
        assertNull(caffeine.getIfPresent("sku"));
        SettableFuture<String> guavaNext = SettableFuture.create();
        com.google.common.cache.LoadingCache<String, String> guava = CacheBuilder.newBuilder()
                .build(new CacheLoader<String, String>() {
                    @Override public String load(String key) { return "initial"; }
                    @Override public com.google.common.util.concurrent.ListenableFuture<String> reload(
                            String key, String oldValue) { return guavaNext; }
                });
        guava.put("sku", "old");
        guava.refresh("sku");
        guava.invalidate("sku");
        guavaNext.set("late");
        assertEquals("late", guava.getIfPresent("sku"));
        System.out.println("C31 refresh+invalidate+complete: future=late,Caffeine-absent,Guava-present-late");
    }

    @Test
    void synchronousSameKeyLoadsShareWorkWithBoundedThreadCleanup() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        CountDownLatch entered = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        CountDownLatch secondStarted = new CountDownLatch(1);
        LoadingCache<String, String> cache = Caffeine.newBuilder().build(key -> {
            calls.incrementAndGet();
            entered.countDown();
            if (!release.await(5, TimeUnit.SECONDS)) throw new IOException("bounded load timeout");
            return "v1";
        });
        ExecutorService workers = Executors.newFixedThreadPool(2);
        try {
            Future<String> first = workers.submit(() -> cache.get("sku"));
            assertTrue(entered.await(5, TimeUnit.SECONDS));
            Future<String> second = workers.submit(() -> {
                secondStarted.countDown();
                return cache.get("sku");
            });
            assertTrue(secondStarted.await(5, TimeUnit.SECONDS));
            assertThrows(TimeoutException.class, () -> second.get(50, TimeUnit.MILLISECONDS));
            assertEquals(1, calls.get());
            release.countDown();
            assertEquals("v1", first.get(5, TimeUnit.SECONDS));
            assertEquals("v1", second.get(5, TimeUnit.SECONDS));
            assertEquals(1, calls.get());
        } finally {
            release.countDown();
            workers.shutdownNow();
            assertTrue(workers.awaitTermination(5, TimeUnit.SECONDS));
        }
        System.out.println("C31 concurrent=two-callers,same-key,one-load,both-v1");
    }

    @Test
    void asyncCancellationAffectsSharedFutureAndCompletionDependentCleanup() {
        CompletableFuture<String> backend = new CompletableFuture<>();
        com.github.benmanes.caffeine.cache.AsyncLoadingCache<String, String> cache =
                Caffeine.newBuilder().executor(Runnable::run).buildAsync((key, executor) -> backend);
        CompletableFuture<String> first = cache.get("sku");
        CompletableFuture<String> second = cache.get("sku");
        assertSame(first, second);
        assertTrue(first.cancel(false));
        assertTrue(second.isCancelled());
        assertNull(cache.getIfPresent("sku"));
        assertFalse(backend.complete("late"));
        System.out.println("C31 async: same-future=true,one-cancel=both-cancelled,mapping-removed,backend-completion=false");
    }

    @Test
    void notificationCausesAreDistinctAndExecutionUsesConfiguredExecutor() {
        java.util.List<String> events = new java.util.ArrayList<>();
        String thread = Thread.currentThread().getName();
        com.github.benmanes.caffeine.cache.Cache<String, String> cache = Caffeine.newBuilder()
                .executor(Runnable::run)
                .removalListener((String key, String value, com.github.benmanes.caffeine.cache.RemovalCause cause) ->
                        events.add(value + ":" + cause + ":" + Thread.currentThread().getName()))
                .build();
        cache.put("sku", "v1");
        cache.put("sku", "v2");
        cache.invalidate("sku");
        cache.cleanUp();
        assertEquals(java.util.Arrays.asList("v1:REPLACED:" + thread, "v2:EXPLICIT:" + thread), events);
        System.out.println("C31 notifications=REPLACED(v1),EXPLICIT(v2),thread=caller-with-direct-executor");
    }

    @Test
    void expiryAndCapacityAreObservedAfterMaintenanceWithoutChoosingEvictionVictim() {
        AtomicLong clock = new AtomicLong();
        com.github.benmanes.caffeine.cache.Cache<String, String> cache = Caffeine.newBuilder()
                .ticker(clock::get).executor(Runnable::run).maximumSize(2)
                .expireAfterWrite(Duration.ofSeconds(10)).recordStats().build();
        cache.put("a", "1");
        assertEquals("1", cache.getIfPresent("a"));
        assertNull(cache.getIfPresent("missing"));
        assertEquals(1, cache.stats().hitCount());
        assertEquals(1, cache.stats().missCount());
        clock.set(TimeUnit.SECONDS.toNanos(11));
        assertNull(cache.getIfPresent("a"));
        cache.cleanUp();
        assertEquals(0, cache.estimatedSize());
        cache.put("a", "1");
        cache.put("b", "2");
        cache.put("c", "3");
        cache.cleanUp();
        assertTrue(cache.estimatedSize() <= 2);
        assertTrue(cache.stats().evictionCount() >= 2);
        System.out.println("C31 TTL-hidden=true,cleanup-size=0,capacity<=2,eviction>=2,no-victim-contract");
    }
}
