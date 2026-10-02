package blog.libraries;

import io.github.resilience4j.bulkhead.Bulkhead;
import io.github.resilience4j.bulkhead.BulkheadConfig;
import io.github.resilience4j.bulkhead.BulkheadFullException;
import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterConfig;
import io.github.resilience4j.retry.Retry;
import io.github.resilience4j.retry.RetryConfig;
import io.github.resilience4j.timelimiter.TimeLimiter;
import io.github.resilience4j.timelimiter.TimeLimiterConfig;
import java.time.Duration;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Extension07Test {
    static CircuitBreaker breaker(String name) {
        return CircuitBreaker.of(name, CircuitBreakerConfig.custom()
                .slidingWindowSize(1).minimumNumberOfCalls(1).failureRateThreshold(50)
                .permittedNumberOfCallsInHalfOpenState(1)
                .waitDurationInOpenState(Duration.ofHours(1)).build());
    }

    @Test void decorationOrderChangesPhysicalCallsAndBreakerAccounting() {
        Retry retry = Retry.of("three", RetryConfig.custom().maxAttempts(3)
                .waitDuration(Duration.ZERO).build());
        AtomicInteger innerCalls = new AtomicInteger();
        Supplier<String> failTwice = () -> {
            if (innerCalls.incrementAndGet() < 3) throw new IllegalStateException("temporary");
            return "ok";
        };
        CircuitBreaker innerBreaker = breaker("each-attempt");
        Supplier<String> retryOutside = Retry.decorateSupplier(retry,
                CircuitBreaker.decorateSupplier(innerBreaker, failTwice));
        assertThrows(CallNotPermittedException.class, retryOutside::get);
        assertEquals(1, innerCalls.get());
        assertEquals(CircuitBreaker.State.OPEN, innerBreaker.getState());
        AtomicInteger outerCalls = new AtomicInteger();
        Supplier<String> secondFailTwice = () -> {
            if (outerCalls.incrementAndGet() < 3) throw new IllegalStateException("temporary");
            return "ok";
        };
        CircuitBreaker outerBreaker = breaker("logical-call");
        String result = CircuitBreaker.decorateSupplier(outerBreaker,
                Retry.decorateSupplier(retry, secondFailTwice)).get();
        assertEquals("ok", result); assertEquals(3, outerCalls.get());
        assertEquals(CircuitBreaker.State.CLOSED, outerBreaker.getState());
        assertEquals(1, outerBreaker.getMetrics().getNumberOfSuccessfulCalls());
        assertEquals(0, outerBreaker.getMetrics().getNumberOfFailedCalls());
        System.out.println("E07 Retry(Breaker(call)): physical=1,OPEN; Breaker(Retry(call)): physical=3,CLOSED,recordedSuccess=1");
    }

    @Test void permitsAndBulkheadConcurrencyAreDifferentCounters() throws Exception {
        RateLimiter rate = RateLimiter.of("local", RateLimiterConfig.custom()
                .limitForPeriod(2).limitRefreshPeriod(Duration.ofHours(1))
                .timeoutDuration(Duration.ZERO).build());
        assertTrue(rate.acquirePermission()); assertTrue(rate.acquirePermission());
        assertFalse(rate.acquirePermission());
        assertEquals(0, rate.getMetrics().getAvailablePermissions());
        Bulkhead bulkhead = Bulkhead.of("two", BulkheadConfig.custom()
                .maxConcurrentCalls(2).maxWaitDuration(Duration.ZERO).build());
        ExecutorService pool = Executors.newFixedThreadPool(2);
        CountDownLatch entered = new CountDownLatch(2);
        CountDownLatch finish = new CountDownLatch(1);
        AtomicInteger active = new AtomicInteger();
        AtomicInteger peak = new AtomicInteger();
        Callable<Integer> task = Bulkhead.decorateCallable(bulkhead, () -> {
            int now = active.incrementAndGet(); peak.accumulateAndGet(now, Math::max);
            entered.countDown();
            try { assertTrue(finish.await(5, TimeUnit.SECONDS)); return now; }
            finally { active.decrementAndGet(); }
        });
        try {
            Future<Integer> a = pool.submit(task), b = pool.submit(task);
            assertTrue(entered.await(5, TimeUnit.SECONDS));
            assertEquals(2, active.get());
            assertThrows(BulkheadFullException.class, task::call);
            assertEquals(0, bulkhead.getMetrics().getAvailableConcurrentCalls());
            finish.countDown(); a.get(5, TimeUnit.SECONDS); b.get(5, TimeUnit.SECONDS);
            assertEquals(2, peak.get());
            assertEquals(2, bulkhead.getMetrics().getAvailableConcurrentCalls());
        } finally {
            finish.countDown(); pool.shutdownNow(); assertTrue(pool.awaitTermination(5, TimeUnit.SECONDS));
        }
        System.out.println("E07 rate accepted=2 rejected=1; bulkhead peak=2 third rejected, slots restored=2");
    }

    @Test void halfOpenProbeTransitionsAreExplicitlyControlled() {
        CircuitBreaker cb = breaker("probe");
        cb.onError(1, TimeUnit.MILLISECONDS, new IllegalStateException("down"));
        assertEquals(CircuitBreaker.State.OPEN, cb.getState());
        assertFalse(cb.tryAcquirePermission());
        cb.transitionToHalfOpenState();
        assertTrue(cb.tryAcquirePermission()); assertFalse(cb.tryAcquirePermission());
        cb.onSuccess(1, TimeUnit.MILLISECONDS);
        assertEquals(CircuitBreaker.State.CLOSED, cb.getState());
        cb.transitionToOpenState(); cb.transitionToHalfOpenState();
        assertTrue(cb.tryAcquirePermission());
        cb.onError(1, TimeUnit.MILLISECONDS, new IllegalStateException("still-down"));
        assertEquals(CircuitBreaker.State.OPEN, cb.getState());
        System.out.println("E07 OPEN -> HALF_OPEN successful probe -> CLOSED; failed probe -> OPEN");
    }

    @Test void timeoutRetryDuplicatesCompletedSideEffectsWithoutStoppingSupplier() throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2);
        CountDownLatch releaseResponses = new CountDownLatch(1);
        CountDownLatch finished = new CountDownLatch(2);
        AtomicInteger sideEffects = new AtomicInteger();
        AtomicInteger interrupts = new AtomicInteger();
        TimeLimiter limiter = TimeLimiter.of(TimeLimiterConfig.custom()
                .timeoutDuration(Duration.ofMillis(25)).cancelRunningFuture(true).build());
        Supplier<CompletableFuture<String>> source = () -> {
            CountDownLatch started = new CountDownLatch(1);
            CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
                sideEffects.incrementAndGet(); started.countDown();
                try {
                    if (!releaseResponses.await(5, TimeUnit.SECONDS)) throw new IllegalStateException("cleanup timeout");
                    return "response";
                } catch (InterruptedException ex) {
                    interrupts.incrementAndGet(); Thread.currentThread().interrupt(); throw new IllegalStateException(ex);
                } finally { finished.countDown(); }
            }, pool);
            try { assertTrue(started.await(5, TimeUnit.SECONDS)); }
            catch (InterruptedException ex) { Thread.currentThread().interrupt(); throw new IllegalStateException(ex); }
            return future;
        };
        Retry twice = Retry.of("timeout-twice", RetryConfig.custom().maxAttempts(2)
                .waitDuration(Duration.ZERO).retryExceptions(TimeoutException.class).build());
        Callable<String> request = Retry.decorateCallable(twice, limiter.decorateFutureSupplier(source));
        try {
            assertThrows(TimeoutException.class, request::call);
            assertEquals(2, sideEffects.get()); assertEquals(2, finished.getCount());
            releaseResponses.countDown(); assertTrue(finished.await(5, TimeUnit.SECONDS));
            assertEquals(0, interrupts.get());
        } finally {
            releaseResponses.countDown(); pool.shutdownNow(); assertTrue(pool.awaitTermination(5, TimeUnit.SECONDS));
        }
        System.out.println("E07 timeout retries=2 sideEffects=2, supplierInterrupts=0; response completion released by test");
    }
}
