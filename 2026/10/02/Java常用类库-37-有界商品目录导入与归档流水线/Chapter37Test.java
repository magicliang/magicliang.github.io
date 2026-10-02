package blog.libraries;

import blog.libraries.io.PrivateArchive;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InterruptedIOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.BooleanSupplier;
import java.util.function.IntFunction;
import java.util.stream.Stream;
import org.apache.hc.client5.http.classic.methods.HttpGet;
import org.apache.hc.client5.http.config.ConnectionConfig;
import org.apache.hc.client5.http.config.RequestConfig;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.client5.http.impl.io.PoolingHttpClientConnectionManager;
import org.apache.hc.core5.util.Timeout;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class Chapter37Test {
    @TempDir Path parent;
    static final String CSV = "merchant,sku,price\nA,one,9.99\nA,two,10.00\nB,one,0\n";
    static CatalogPipeline.Limits limits() { return new CatalogPipeline.Limits(10, 1024, 256, 4096, 4096); }
    static final class Input extends ByteArrayInputStream {
        boolean closed;
        Input(byte[] bytes) { super(bytes); }
        Input(String value) { this(value.getBytes(StandardCharsets.UTF_8)); }
        @Override public void close() throws IOException { closed = true; super.close(); }
    }
    static final class Reply {
        final int code; final byte[] bytes;
        Reply(int code, String text) { this(code, text.getBytes(StandardCharsets.UTF_8)); }
        Reply(int code, byte[] bytes) { this.code = code; this.bytes = bytes; }
    }
    static final class Endpoint implements AutoCloseable {
        final HttpServer server;
        final ExecutorService workers = Executors.newFixedThreadPool(2);
        final AtomicInteger calls = new AtomicInteger();
        Endpoint(IntFunction<Reply> reply) throws IOException {
            server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.setExecutor(workers);
            server.createContext("/detail", exchange -> {
                try {
                    Reply response = reply.apply(calls.incrementAndGet());
                    exchange.getResponseHeaders().set("Content-Type", "application/json; charset=UTF-8");
                    exchange.sendResponseHeaders(response.code, response.bytes.length);
                    exchange.getResponseBody().write(response.bytes);
                } finally { exchange.close(); }
            });
            server.start();
        }
        URI uri() { return URI.create("http://127.0.0.1:" + server.getAddress().getPort() + "/detail"); }
        @Override public void close() throws Exception {
            server.stop(0); workers.shutdownNow(); assertTrue(workers.awaitTermination(5, TimeUnit.SECONDS));
        }
    }
    static CloseableHttpClient client(PoolingHttpClientConnectionManager pool) {
        pool.setMaxTotal(1); pool.setDefaultMaxPerRoute(1);
        pool.setDefaultConnectionConfig(ConnectionConfig.custom().setConnectTimeout(Timeout.ofSeconds(2)).build());
        return HttpClients.custom().setConnectionManager(pool).disableAutomaticRetries().disableRedirectHandling()
                .setDefaultRequestConfig(RequestConfig.custom().setConnectionRequestTimeout(Timeout.ofSeconds(2))
                        .setResponseTimeout(Timeout.ofSeconds(2)).build()).build();
    }
    void assertEmpty() throws IOException {
        try (Stream<Path> files = Files.list(parent)) { assertEquals(0, files.count()); }
    }
    static Reply good() { return new Reply(200, "{\"label\":\"商品\"}"); }

    @Test void successPublishesImmutableQueriesAndOwnedArchiveThenCloses() throws Exception {
        try (Endpoint endpoint = new Endpoint(i -> good())) {
            PoolingHttpClientConnectionManager pool = new PoolingHttpClientConnectionManager();
            try (CloseableHttpClient client = client(pool)) {
                Input input = new Input(CSV);
                try (CatalogPipeline.Export result = CatalogPipeline.run(input, client, endpoint.uri(), parent, limits(), () -> false)) {
                    assertEquals(3, endpoint.calls.get()); assertEquals(2, result.index.size());
                    assertEquals(2, result.merchantCounts.count("A")); assertEquals(1, result.merchantCounts.count("B"));
                    assertEquals(2, result.underTen.size());
                    assertEquals("10.00", result.index.get("A").get("two").getPrice().toPlainString());
                    assertThrows(UnsupportedOperationException.class, () -> result.index.get("A").clear());
                    JsonNode report = new ObjectMapper().readTree(Files.readAllBytes(result.report));
                    assertEquals(3, report.size()); assertEquals("商品", report.get(0).get("label").asText());
                    Path extracted = PrivateArchive.extractZip(result.archive, parent,
                            new PrivateArchive.Limits(1, 4096, 4096, 4096, TimeUnit.SECONDS.toNanos(5)));
                    try { assertArrayEquals(Files.readAllBytes(result.report), Files.readAllBytes(extracted.resolve("report.json"))); }
                    finally { PrivateArchive.deleteTree(extracted); }
                }
                assertFalse(input.closed); assertEquals(0, pool.getTotalStats().getLeased());
                assertEquals(Integer.valueOf(200), client.execute(new HttpGet(endpoint.uri()), r -> Integer.valueOf(r.getCode())));
                input.close(); assertTrue(input.closed); assertEmpty();
            }
        }
        System.out.println("37 success: 3 HTTP enrichments, A=2 B=1, [0,10)=2, archive roundtrip identical; borrowed input/client retained; export cleaned");
    }

    @Test void invalidInputsAreRejectedBeforeHttpOrWorkspaceCreation() throws Exception {
        String[] invalid = {"merchant,sku,price\nA,x,1.001\n", "merchant,sku,price\nA,x,-1\n",
                "merchant,sku,price\nA,x,1e2\n", "merchant,sku,price\nA,x,1\nA,x,2\n",
                "merchant,sku,price\n ,x,1\n", "merchant,sku,price\nA,x,1,extra\n",
                "wrong,sku,price\nA,x,1\n", "merchant,sku,price\n\n"};
        try (Endpoint endpoint = new Endpoint(i -> good());
             CloseableHttpClient client = client(new PoolingHttpClientConnectionManager())) {
            for (String csv : invalid) {
                Input input = new Input(csv);
                assertThrows(IllegalArgumentException.class,
                        () -> CatalogPipeline.run(input, client, endpoint.uri(), parent, limits(), () -> false));
                assertFalse(input.closed); input.close(); assertEmpty();
            }
            Input malformed = new Input(new byte[] {(byte) 0xc3, 0x28});
            assertThrows(IOException.class, () -> CatalogPipeline.run(malformed, client, endpoint.uri(), parent, limits(), () -> false));
            assertFalse(malformed.closed); malformed.close();
            assertEquals(0, endpoint.calls.get()); assertEmpty();
        }
        System.out.println("37 invalid precision/negative/exponent/duplicate/id/columns/header/blank/UTF8: rejected before HTTP");
    }

    @Test void rowAndByteBudgetsFailWithoutClosingBorrowedInput() throws Exception {
        try (Endpoint endpoint = new Endpoint(i -> good());
             CloseableHttpClient client = client(new PoolingHttpClientConnectionManager())) {
            for (CatalogPipeline.Limits budget : Arrays.asList(new CatalogPipeline.Limits(1, 1024, 256, 4096, 4096),
                    new CatalogPipeline.Limits(10, 8, 256, 4096, 4096))) {
                Input input = new Input(CSV);
                assertThrows(IOException.class, () -> CatalogPipeline.run(input, client, endpoint.uri(), parent, budget, () -> false));
                assertFalse(input.closed); input.close(); assertEmpty();
            }
            assertEquals(0, endpoint.calls.get());
        }
        System.out.println("37 row/byte budgets rejected before HTTP; borrowed input ownership retained");
    }

    @Test void midPipelineHttpAndJsonFailuresReleaseLeaseAndRemoveWorkspace() throws Exception {
        for (Reply failure : Arrays.asList(new Reply(503, "down"), new Reply(200, new String(new char[300]).replace('\0', 'x')),
                new Reply(200, "{\"label\":\"a\",\"label\":\"b\"}"), new Reply(200, "{\"label\":\"a\"} {}"),
                new Reply(200, "{\"label\":42}"), new Reply(200, new byte[] {(byte) 0xc3, 0x28}))) {
            try (Endpoint endpoint = new Endpoint(i -> i == 1 ? good() : failure)) {
                PoolingHttpClientConnectionManager pool = new PoolingHttpClientConnectionManager();
                try (CloseableHttpClient client = client(pool)) {
                    Input input = new Input(CSV);
                    assertThrows(IOException.class, () -> CatalogPipeline.run(input, client, endpoint.uri(), parent, limits(), () -> false));
                    assertEquals(2, endpoint.calls.get()); assertEquals(0, pool.getTotalStats().getLeased());
                    assertFalse(input.closed); input.close(); assertEmpty();
                }
            }
        }
        System.out.println("37 after one enrichment: status/response bytes/duplicate JSON/trailing JSON/schema/UTF8 failures release pool and delete workspace");
    }

    @Test void cancellationBeforeImportDuringResponseAndAfterReportRollsBack() throws Exception {
        AtomicBoolean cancelled = new AtomicBoolean(true);
        try (Endpoint endpoint = new Endpoint(i -> { cancelled.set(true); return good(); })) {
            PoolingHttpClientConnectionManager pool = new PoolingHttpClientConnectionManager();
            try (CloseableHttpClient client = client(pool)) {
                Input before = new Input(CSV);
                assertThrows(InterruptedIOException.class, () -> CatalogPipeline.run(before, client, endpoint.uri(), parent, limits(), cancelled::get));
                assertEquals(0, endpoint.calls.get()); assertFalse(before.closed); before.close(); assertEmpty();
                cancelled.set(false);
                Input during = new Input(CSV);
                assertThrows(InterruptedIOException.class, () -> CatalogPipeline.run(during, client, endpoint.uri(), parent, limits(), cancelled::get));
                assertEquals(1, endpoint.calls.get()); assertEquals(0, pool.getTotalStats().getLeased());
                assertFalse(during.closed); during.close(); assertEmpty();
            }
        }
        try (Endpoint endpoint = new Endpoint(i -> good());
             CloseableHttpClient client = client(new PoolingHttpClientConnectionManager())) {
            BooleanSupplier afterReport = () -> {
                try (Stream<Path> paths = Files.walk(parent)) {
                    return paths.anyMatch(p -> p.getFileName().toString().equals("report.json"));
                } catch (IOException ex) { throw new IllegalStateException(ex); }
            };
            Input input = new Input(CSV);
            assertThrows(InterruptedIOException.class, () -> CatalogPipeline.run(input, client, endpoint.uri(), parent, limits(), afterReport));
            assertEquals(3, endpoint.calls.get()); assertFalse(input.closed); input.close(); assertEmpty();
        }
        System.out.println("37 cancellation checkpoints: before import, response stage, after report; no temporary outputs remain");
    }

    @Test void outputBudgetsAndStandaloneMainLeaveNoArtifacts() throws Exception {
        try (Endpoint endpoint = new Endpoint(i -> good());
             CloseableHttpClient client = client(new PoolingHttpClientConnectionManager())) {
            for (CatalogPipeline.Limits budget : Arrays.asList(new CatalogPipeline.Limits(10, 1024, 256, 8, 4096),
                    new CatalogPipeline.Limits(10, 1024, 256, 4096, 8))) {
                Input input = new Input(CSV);
                assertThrows(IOException.class, () -> CatalogPipeline.run(input, client, endpoint.uri(), parent, budget, () -> false));
                assertFalse(input.closed); input.close(); assertEmpty();
            }
            Path csv = Files.createTempFile("catalog-main-", ".csv");
            try {
                Files.write(csv, CSV.getBytes(StandardCharsets.UTF_8));
                CatalogPipeline.main(new String[] {csv.toString(), endpoint.uri().toString(), parent.toString()});
                assertEmpty();
            } finally { Files.delete(csv); }
        }
        System.out.println("37 report/ZIP output caps rollback; standalone main ran full loopback pipeline and cleaned export");
    }
}
