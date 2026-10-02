package com.google.common.util.concurrent;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter17Test {
    static final class Clock extends RateLimiter.SleepingStopwatch {
        long micros;
        protected long readMicros() { return micros; }
        protected void sleepMicrosUninterruptibly(long wait) { micros += wait; }
        void idle(long delta) { micros += delta; }
    }
    @Test void bulkDebtIsChargedToFollowingCalls() {
        Clock clock = new Clock();
        RateLimiter limiter = RateLimiter.create(2.0, clock);
        assertEquals(0.0, limiter.acquire(4), 1e-9);
        assertEquals(2.0, limiter.acquire(), 1e-9);
        assertEquals(0.5, limiter.acquire(), 1e-9);
        assertEquals(2500000, clock.micros);
        System.out.println("17 model bulk acquire(4),acquire(1),acquire(1): waits=[0,2.0,0.5] seconds");
    }
    @Test void idleBurstAndTryAcquireUseAvailabilityTime() {
        Clock clock = new Clock();
        RateLimiter limiter = RateLimiter.create(2.0, clock);
        clock.idle(3000000);
        assertEquals(0.0, limiter.acquire(2), 1e-9);
        assertEquals(0.0, limiter.acquire(), 1e-9);
        assertFalse(limiter.tryAcquire(1, 499, TimeUnit.MILLISECONDS));
        assertEquals(3000000, clock.micros);
        assertTrue(limiter.tryAcquire(1, 500, TimeUnit.MILLISECONDS));
        assertEquals(3500000, clock.micros);
        assertThrows(IllegalArgumentException.class, () -> limiter.acquire(0));
        System.out.println("17 model idle=3s: acquire2=0 acquire1=0 try499ms=false try500ms=true; clock=3.5s");
    }
    @Test void warmupPricesStoredPermitsDifferently() {
        Clock clock = new Clock();
        RateLimiter limiter = RateLimiter.create(2.0, 4, TimeUnit.SECONDS, 3.0, clock);
        double[] expected = {0, 1.375, 1.125, .875, .625, .5};
        for (double value : expected) { assertEquals(value, limiter.acquire(), 1e-9); }
        System.out.println("17 model warmup rate=2 period=4 coldFactor=3 waits=[0,1.375,1.125,0.875,0.625,0.5]");
    }
    @Test void realClockWaitAndConcurrentCallsAreObserved() throws Exception {
        RateLimiter limiter = RateLimiter.create(20.0);
        limiter.acquire();
        long start = System.nanoTime();
        double scheduled = limiter.acquire(3);
        long elapsed = System.nanoTime() - start;
        assertTrue(elapsed / 1e9 + .01 >= scheduled);
        System.out.println("17 real single scheduledSeconds=" + scheduled + " elapsedNanos=" + elapsed
                + " excessNanos=" + (elapsed - (long) (scheduled * 1e9)));
        ExecutorService pool = Executors.newFixedThreadPool(3);
        CountDownLatch startTogether = new CountDownLatch(1), acquired = new CountDownLatch(3), finish = new CountDownLatch(1);
        RateLimiter shared = RateLimiter.create(20.0);
        List<Future<Double>> futures = new ArrayList<>();
        try {
            for (int i = 0; i < 3; i++) { futures.add(pool.submit(() -> {
                startTogether.await(); double wait = shared.acquire(); acquired.countDown(); finish.await(); return wait;
            })); }
            startTogether.countDown();
            assertTrue(acquired.await(5, TimeUnit.SECONDS));
            Semaphore concurrent = new Semaphore(2);
            assertTrue(concurrent.tryAcquire()); assertTrue(concurrent.tryAcquire()); assertFalse(concurrent.tryAcquire());
            concurrent.release(2); assertEquals(2, concurrent.availablePermits());
            finish.countDown();
            List<Double> waits = new ArrayList<>();
            for (Future<Double> future : futures) { waits.add(future.get(5, TimeUnit.SECONDS)); }
            System.out.println("17 real concurrent: all3 acquired before finish; waits=" + waits + "; Semaphore(2) third=false");
        } finally { startTogether.countDown(); finish.countDown(); pool.shutdownNow(); assertTrue(pool.awaitTermination(5, TimeUnit.SECONDS)); }
    }
}
