package blog.libraries;

import com.sun.net.httpserver.HttpServer;
import org.apache.hc.client5.http.classic.methods.HttpGet;
import org.apache.hc.client5.http.config.RequestConfig;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.CloseableHttpResponse;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.client5.http.impl.io.PoolingHttpClientConnectionManager;
import org.apache.hc.core5.http.ConnectionRequestTimeoutException;
import org.apache.hc.core5.http.io.entity.EntityUtils;
import org.apache.hc.core5.util.Timeout;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import static org.junit.jupiter.api.Assertions.*;

public class Chapter34Test {
    static final class Endpoint implements AutoCloseable {
        final HttpServer server;
        final ExecutorService workers = Executors.newFixedThreadPool(3);
        final CountDownLatch slowEntered = new CountDownLatch(1);
        final CountDownLatch releaseSlow = new CountDownLatch(1);
        final AtomicInteger errors = new AtomicInteger();
        final AtomicInteger drops = new AtomicInteger();
        Endpoint() throws IOException {
            server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.setExecutor(workers);
            server.createContext("/ok", e -> {
                byte[] body = "data".getBytes(StandardCharsets.UTF_8);
                e.sendResponseHeaders(200, body.length);
                try { e.getResponseBody().write(body); } finally { e.close(); }
            });
            server.createContext("/slow", e -> {
                slowEntered.countDown();
                try { releaseSlow.await(3, TimeUnit.SECONDS); }
                catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
                finally { e.close(); }
            });
            server.createContext("/error", e -> {
                errors.incrementAndGet(); e.getResponseHeaders().add("Connection", "close");
                e.sendResponseHeaders(503, -1); e.close();
            });
            server.createContext("/drop", e -> { drops.incrementAndGet(); e.close(); });
            server.start();
        }
        String url(String path) { return "http://127.0.0.1:" + server.getAddress().getPort() + path; }
        public void close() {
            releaseSlow.countDown(); server.stop(0); workers.shutdownNow();
            try { assertTrue(workers.awaitTermination(5, TimeUnit.SECONDS)); }
            catch (InterruptedException e) { Thread.currentThread().interrupt(); throw new AssertionError(e); }
        }
    }
    static CloseableHttpClient client(PoolingHttpClientConnectionManager pool, int responseMillis) {
        pool.setMaxTotal(1); pool.setDefaultMaxPerRoute(1);
        return HttpClients.custom().setConnectionManager(pool).disableAutomaticRetries()
                .setDefaultRequestConfig(RequestConfig.custom()
                        .setConnectionRequestTimeout(Timeout.ofMilliseconds(150))
                        .setResponseTimeout(Timeout.ofMilliseconds(responseMillis)).build()).build();
    }
    @Test void unconsumedResponseHoldsLeaseUntilClosed() throws Exception {
        try (Endpoint endpoint = new Endpoint()) {
            PoolingHttpClientConnectionManager pool = new PoolingHttpClientConnectionManager();
            try (CloseableHttpClient client = client(pool, 1000)) {
                try (CloseableHttpResponse held = client.execute(new HttpGet(endpoint.url("/ok")))) {
                    assertEquals(1, pool.getTotalStats().getLeased());
                    assertThrows(ConnectionRequestTimeoutException.class,
                            () -> client.execute(new HttpGet(endpoint.url("/ok")), r -> r.getCode()));
                    assertEquals("data", EntityUtils.toString(held.getEntity()));
                }
                assertEquals(0, pool.getTotalStats().getLeased());
                int successStatus = client.execute(new HttpGet(endpoint.url("/ok")), r -> Integer.valueOf(r.getCode()));
                assertEquals(200, successStatus);
                assertEquals(0, pool.getTotalStats().getLeased());
            }
            assertEquals(0, pool.getTotalStats().getAvailable());
        }
    }
    @Test void responseTimeoutIsNotPoolLeaseTimeout() throws Exception {
        try (Endpoint endpoint = new Endpoint()) {
            PoolingHttpClientConnectionManager pool = new PoolingHttpClientConnectionManager();
            try (CloseableHttpClient client = client(pool, 150)) {
                assertThrows(SocketTimeoutException.class,
                        () -> client.execute(new HttpGet(endpoint.url("/slow")), r -> r.getCode()));
                assertTrue(endpoint.slowEntered.await(1, TimeUnit.SECONDS));
                assertEquals(0, pool.getTotalStats().getLeased());
            }
        }
    }
    @Test void statusAndDisconnectAreDifferentAndHandlerReleases() throws Exception {
        try (Endpoint endpoint = new Endpoint()) {
            PoolingHttpClientConnectionManager pool = new PoolingHttpClientConnectionManager();
            try (CloseableHttpClient client = client(pool, 1000)) {
                int errorStatus = client.execute(new HttpGet(endpoint.url("/error")), r -> Integer.valueOf(r.getCode()));
                assertEquals(503, errorStatus);
                assertEquals(1, endpoint.errors.get());
                assertThrows(IOException.class, () -> client.execute(new HttpGet(endpoint.url("/drop")), r -> r.getCode()));
                assertEquals(1, endpoint.drops.get());
                assertThrows(IllegalArgumentException.class,
                        () -> client.execute(new HttpGet(endpoint.url("/ok")), r -> { throw new IllegalArgumentException("handler failed"); }));
                assertEquals(0, pool.getTotalStats().getLeased());
            }
        }
    }
    @Test void cancellationEndsWaitingButDoesNotProveServerRollback() throws Exception {
        try (Endpoint endpoint = new Endpoint()) {
            PoolingHttpClientConnectionManager pool = new PoolingHttpClientConnectionManager();
            ExecutorService caller = Executors.newSingleThreadExecutor();
            try (CloseableHttpClient client = client(pool, 2000)) {
                HttpGet request = new HttpGet(endpoint.url("/slow"));
                Future<Integer> pending = caller.submit(() -> client.execute(request, r -> Integer.valueOf(r.getCode())));
                assertTrue(endpoint.slowEntered.await(2, TimeUnit.SECONDS));
                assertTrue(request.cancel());
                ExecutionException failed = assertThrows(ExecutionException.class, () -> pending.get(3, TimeUnit.SECONDS));
                assertTrue(failed.getCause() instanceof IOException);
                assertEquals(0, pool.getTotalStats().getLeased());
            } finally {
                caller.shutdownNow(); assertTrue(caller.awaitTermination(5, TimeUnit.SECONDS));
            }
        }
    }
}
