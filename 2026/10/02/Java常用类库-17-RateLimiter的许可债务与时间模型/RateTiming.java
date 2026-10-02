import com.google.common.util.concurrent.RateLimiter;

public final class RateTiming {
    public static void main(String[] args) {
        RateLimiter limiter = RateLimiter.create(20.0);
        limiter.acquire();
        long start = System.nanoTime();
        double planned = limiter.acquire(3);
        long elapsed = System.nanoTime() - start;
        System.out.println("plannedSeconds=" + planned + ", elapsedNanos=" + elapsed);
    }
}
