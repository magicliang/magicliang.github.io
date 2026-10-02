package blog.libraries;

import com.github.benmanes.caffeine.cache.CacheLoader;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.github.benmanes.caffeine.cache.LoadingCache;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;

public final class CacheMigrationDemo {
    public static void main(String[] args) {
        CompletableFuture<String> pending = new CompletableFuture<>();
        LoadingCache<String, String> cache = Caffeine.newBuilder().executor(Runnable::run)
                .build(new CacheLoader<String, String>() {
                    @Override public String load(String key) { return "initial"; }
                    @Override public CompletableFuture<String> asyncReload(
                            String key, String oldValue, Executor executor) { return pending; }
                });
        cache.put("sku", "old");
        CompletableFuture<String> observed = cache.refresh("sku");
        cache.invalidate("sku");
        pending.complete("late");
        if (!"late".equals(observed.join()) || cache.getIfPresent("sku") != null) {
            throw new AssertionError("refresh result and cache contents are different contracts");
        }
        System.out.println("refresh-result=late, cache=absent");
    }
}
