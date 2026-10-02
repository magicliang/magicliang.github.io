package blog.libraries;

import com.google.common.base.Ticker;
import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.cache.LoadingCache;
import com.google.common.util.concurrent.ListenableFuture;
import com.google.common.util.concurrent.SettableFuture;
import com.google.common.util.concurrent.UncheckedExecutionException;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

class Chapter15Test {
    static final class Clock extends Ticker {
        private final AtomicLong nanos = new AtomicLong();

        @Override
        public long read() {
            return nanos.get();
        }

        void advance(long seconds) {
            nanos.addAndGet(TimeUnit.SECONDS.toNanos(seconds));
        }
    }

    @Test
    void sameKeyMissesShareOneBlockedLoad() throws Exception {
        AtomicInteger loads = new AtomicInteger();
        CountDownLatch entered = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        CountDownLatch secondStarted = new CountDownLatch(1);
        LoadingCache<String, String> cache = CacheBuilder.newBuilder().build(new CacheLoader<String, String>() {
            @Override
            public String load(String key) throws Exception {
                loads.incrementAndGet();
                entered.countDown();
                if (!release.await(5, TimeUnit.SECONDS)) throw new IOException("test load timed out");
                return "detail-" + key;
            }
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
            assertEquals(1, loads.get());
            release.countDown();
            assertEquals("detail-sku", first.get(5, TimeUnit.SECONDS));
            assertEquals("detail-sku", second.get(5, TimeUnit.SECONDS));
            assertEquals(1, loads.get());
            System.out.println("C15 same-key=two-callers, blocked-before-release=true, loads=1, both=detail-sku");
        } finally {
            release.countDown();
            workers.shutdownNow();
            assertTrue(workers.awaitTermination(5, TimeUnit.SECONDS));
        }
    }

    @Test
    void refreshNeedsAccessAndKeepsOldValueWhilePendingOrFailed() throws Exception {
        Clock clock = new Clock();
        AtomicInteger loads = new AtomicInteger();
        AtomicInteger reloads = new AtomicInteger();
        AtomicReference<SettableFuture<String>> pending = new AtomicReference<>();
        LoadingCache<String, String> cache = CacheBuilder.newBuilder().ticker(clock)
                .refreshAfterWrite(10, TimeUnit.SECONDS).expireAfterWrite(30, TimeUnit.SECONDS)
                .build(new CacheLoader<String, String>() {
                    @Override
                    public String load(String key) {
                        return "v" + loads.incrementAndGet();
                    }

                    @Override
                    public ListenableFuture<String> reload(String key, String oldValue) {
                        reloads.incrementAndGet();
                        SettableFuture<String> next = SettableFuture.create();
                        pending.set(next);
                        return next;
                    }
                });
        assertEquals("v1", cache.get("sku"));
        clock.advance(11);
        assertEquals(0, reloads.get());
        assertEquals("v1", cache.get("sku"));
        assertEquals("v1", cache.get("sku"));
        assertEquals(1, reloads.get());
        pending.get().setException(new IOException("synthetic refresh failure"));
        assertEquals("v1", cache.get("sku"));
        assertEquals(2, reloads.get());
        pending.get().set("v2");
        assertEquals("v2", cache.get("sku"));
        assertEquals(1, loads.get());
        clock.advance(31);
        assertEquals("v2", cache.get("sku"));
        assertEquals(2, loads.get());
        System.out.println("C15 idle11s=reload0, access=reload1, pending=old, failed=old+retry, completed=v2, expired=load2");
    }

    @Test
    void expirationHidesEntryBeforePhysicalCleanup() {
        Clock clock = new Clock();
        Cache<String, String> cache = CacheBuilder.newBuilder().ticker(clock)
                .expireAfterWrite(10, TimeUnit.SECONDS).build();
        cache.put("sku", "v1");
        clock.advance(11);
        long physicalBeforeAccess = cache.size();
        assertNull(cache.getIfPresent("sku"));
        cache.cleanUp();
        assertEquals(0, cache.size());
        System.out.println("C15 expired-visible=null, size-before-access-observation=" + physicalBeforeAccess + ", size-after-cleanup=0");
    }

    @Test
    void checkedUncheckedAndNullFailuresHaveDifferentBoundaries() {
        LoadingCache<String, String> checked = CacheBuilder.newBuilder().build(new CacheLoader<String, String>() {
            @Override
            public String load(String key) throws IOException {
                throw new IOException("backend unavailable");
            }
        });
        assertTrue(assertThrows(ExecutionException.class, () -> checked.get("sku")).getCause() instanceof IOException);
        assertTrue(assertThrows(UncheckedExecutionException.class, () -> checked.getUnchecked("sku")).getCause() instanceof IOException);
        LoadingCache<String, String> nullLoader = CacheBuilder.newBuilder().build(new CacheLoader<String, String>() {
            @Override
            public String load(String key) {
                return null;
            }
        });
        assertThrows(CacheLoader.InvalidCacheLoadException.class, () -> nullLoader.get("sku"));
        System.out.println("C15 checked=get:ExecutionException/getUnchecked:UncheckedExecutionException, null=InvalidCacheLoadException");
    }

    @Test
    void invalidationIsNotCancellationAndCapacityIsASeparateBudget() throws Exception {
        CountDownLatch entered = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        LoadingCache<String, String> cache = CacheBuilder.newBuilder().build(new CacheLoader<String, String>() {
            @Override
            public String load(String key) throws Exception {
                entered.countDown();
                if (!release.await(5, TimeUnit.SECONDS)) throw new IOException("test load timed out");
                return "started-before-invalidation";
            }
        });
        ExecutorService worker = Executors.newSingleThreadExecutor();
        try {
            Future<String> result = worker.submit(() -> cache.get("sku"));
            assertTrue(entered.await(5, TimeUnit.SECONDS));
            cache.invalidate("sku");
            assertFalse(result.isDone());
            release.countDown();
            assertEquals("started-before-invalidation", result.get(5, TimeUnit.SECONDS));
            System.out.println("C15 invalidate-during-load=load-not-cancelled, post-load-visible-observation=" + cache.getIfPresent("sku"));
        } finally {
            release.countDown();
            worker.shutdownNow();
            assertTrue(worker.awaitTermination(5, TimeUnit.SECONDS));
        }
        Cache<String, String> bounded = CacheBuilder.newBuilder().maximumSize(2).recordStats().build();
        bounded.put("a", "1");
        bounded.put("b", "2");
        bounded.put("c", "3");
        bounded.cleanUp();
        assertTrue(bounded.size() <= 2);
        assertTrue(bounded.stats().evictionCount() >= 1);
        System.out.println("C15 maximumSize2=size" + bounded.size() + ", evictions=" + bounded.stats().evictionCount());
    }
}
