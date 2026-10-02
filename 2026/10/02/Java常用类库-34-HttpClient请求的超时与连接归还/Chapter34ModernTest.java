package blog.libraries;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import static org.junit.jupiter.api.Assertions.*;

public class Chapter34ModernTest {
    @Test void jdkClientConsumesStringBodyAndTreatsStatusAsData() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        ExecutorService executor = Executors.newFixedThreadPool(2);
        server.createContext("/", e -> {
            byte[] body = "unavailable".getBytes(StandardCharsets.UTF_8);
            e.sendResponseHeaders(503, body.length);
            try { e.getResponseBody().write(body); } finally { e.close(); }
        });
        server.start();
        try {
            HttpClient client = HttpClient.newBuilder().executor(executor).build();
            HttpResponse<String> response = client.send(HttpRequest.newBuilder(
                    URI.create("http://127.0.0.1:" + server.getAddress().getPort() + "/"))
                    .timeout(Duration.ofSeconds(2)).build(), HttpResponse.BodyHandlers.ofString());
            assertEquals(503, response.statusCode()); assertEquals("unavailable", response.body());
        } finally {
            server.stop(0); executor.shutdownNow(); assertTrue(executor.awaitTermination(5, TimeUnit.SECONDS));
        }
    }
    @Test void jdkRequestDeadlineIsNotAnApachePoolLeaseSetting() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        CountDownLatch release = new CountDownLatch(1);
        ExecutorService executor = Executors.newFixedThreadPool(2);
        server.createContext("/", e -> {
            try { release.await(3, TimeUnit.SECONDS); }
            catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
            finally { e.close(); }
        });
        server.start();
        try {
            HttpClient client = HttpClient.newBuilder().executor(executor).build();
            HttpRequest request = HttpRequest.newBuilder(
                    URI.create("http://127.0.0.1:" + server.getAddress().getPort() + "/"))
                    .timeout(Duration.ofMillis(150)).build();
            assertThrows(HttpTimeoutException.class, () -> client.send(request, HttpResponse.BodyHandlers.ofString()));
        } finally {
            release.countDown(); server.stop(0); executor.shutdownNow(); assertTrue(executor.awaitTermination(5, TimeUnit.SECONDS));
        }
    }
}
