import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.ListenableFuture;
import com.google.common.util.concurrent.SettableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

public final class FutureTransform {
    public static void main(String[] args) throws Exception {
        ExecutorService executor = Executors.newSingleThreadExecutor();
        try {
            SettableFuture<String> source = SettableFuture.create();
            ListenableFuture<Integer> result = Futures.transform(source, String::length, executor);
            source.set("SKU-1");
            if (result.get(5, TimeUnit.SECONDS) != 5) { throw new AssertionError(); }
            System.out.println("converted=5");
        } finally {
            executor.shutdownNow();
            if (!executor.awaitTermination(5, TimeUnit.SECONDS)) {
                throw new IllegalStateException("executor did not stop");
            }
        }
    }
}
