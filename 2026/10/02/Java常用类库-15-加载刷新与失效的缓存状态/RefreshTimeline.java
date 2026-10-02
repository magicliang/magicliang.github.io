import com.google.common.base.Ticker;
import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.cache.LoadingCache;
import com.google.common.util.concurrent.ListenableFuture;
import com.google.common.util.concurrent.SettableFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

public final class RefreshTimeline {
    private static final class Clock extends Ticker {
        private long nanos;
        public long read() { return nanos; }
    }

    public static void main(String[] args) throws Exception {
        Clock clock = new Clock();
        AtomicInteger reloads = new AtomicInteger();
        SettableFuture<String> next = SettableFuture.create();
        LoadingCache<String, String> cache = CacheBuilder.newBuilder()
                .ticker(clock).refreshAfterWrite(10, TimeUnit.SECONDS)
                .build(new CacheLoader<String, String>() {
                    public String load(String key) { return "v1"; }
                    public ListenableFuture<String> reload(String key, String old) {
                        reloads.incrementAndGet();
                        return next;
                    }
                });
        assert "v1".equals(cache.get("sku"));
        clock.nanos = TimeUnit.SECONDS.toNanos(11);
        assert reloads.get() == 0;
        assert "v1".equals(cache.get("sku"));
        assert reloads.get() == 1;
        assert "v1".equals(cache.get("sku"));
        assert reloads.get() == 1;
        next.set("v2");
        assert "v2".equals(cache.get("sku"));
        System.out.println("idle=0 reload, pending=v1, completed=v2");
    }
}
