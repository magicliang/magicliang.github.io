import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.retry.Retry;
import io.github.resilience4j.retry.RetryConfig;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;

public final class RetryOrder {
    public static void main(String[] args) {
        AtomicInteger calls = new AtomicInteger();
        Supplier<String> backend = () -> {
            if (calls.incrementAndGet() < 3) { throw new IllegalStateException("temporary"); }
            return "ok";
        };
        Retry retry = Retry.of("demo", RetryConfig.custom().maxAttempts(3)
                .waitDuration(Duration.ZERO).build());
        CircuitBreaker breaker = CircuitBreaker.of("demo", CircuitBreakerConfig.custom()
                .slidingWindowSize(1).minimumNumberOfCalls(1).build());
        String result = CircuitBreaker.decorateSupplier(breaker,
                Retry.decorateSupplier(retry, backend)).get();
        if (calls.get() != 3) { throw new AssertionError(); }
        System.out.println(result + ", physicalCalls=" + calls.get());
    }
}
