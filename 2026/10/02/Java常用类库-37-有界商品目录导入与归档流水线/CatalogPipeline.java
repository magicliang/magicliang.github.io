package blog.libraries;

import blog.libraries.io.BoundedIo;
import blog.libraries.io.PrivateArchive;
import blog.libraries.io.SafePaths;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableMultiset;
import com.google.common.collect.Range;
import java.io.ByteArrayOutputStream;
import java.io.FilterInputStream;
import java.io.FilterOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InterruptedIOException;
import java.io.OutputStream;
import java.math.BigDecimal;
import java.net.URI;
import java.net.URISyntaxException;
import java.nio.ByteBuffer;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.BooleanSupplier;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.apache.commons.csv.DuplicateHeaderMode;
import org.apache.hc.client5.http.classic.methods.HttpGet;
import org.apache.hc.client5.http.config.ConnectionConfig;
import org.apache.hc.client5.http.config.RequestConfig;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.client5.http.impl.io.PoolingHttpClientConnectionManagerBuilder;
import org.apache.hc.core5.http.ClassicHttpResponse;
import org.apache.hc.core5.util.Timeout;

/** Synchronous, bounded example. Input and client are borrowed; returned export owns its directory. */
public final class CatalogPipeline {
    private CatalogPipeline() { }

    public static final class Limits {
        final int rows;
        final int inputBytes;
        final int responseBytes;
        final int reportBytes;
        final int archiveBytes;
        public Limits(int rows, int inputBytes, int responseBytes, int reportBytes, int archiveBytes) {
            if (rows < 1 || inputBytes < 1 || responseBytes < 1 || reportBytes < 1 || archiveBytes < 1) {
                throw new IllegalArgumentException("budgets must be positive");
            }
            this.rows = rows; this.inputBytes = inputBytes; this.responseBytes = responseBytes;
            this.reportBytes = reportBytes; this.archiveBytes = archiveBytes;
        }
    }

    public static final class Export implements AutoCloseable {
        public final Path directory;
        public final Path report;
        public final Path archive;
        public final ImmutableMap<String, ImmutableMap<String, Product>> index;
        public final ImmutableMultiset<String> merchantCounts;
        public final ImmutableList<Product> underTen;
        private boolean closed;
        private Export(Path directory, Path report, Path archive,
                       ImmutableMap<String, ImmutableMap<String, Product>> index,
                       ImmutableMultiset<String> counts, ImmutableList<Product> underTen) {
            this.directory = directory; this.report = report; this.archive = archive;
            this.index = index; this.merchantCounts = counts; this.underTen = underTen;
        }
        @Override public void close() throws IOException {
            if (!closed) { PrivateArchive.deleteTree(directory); closed = true; }
        }
    }

    public static Export run(InputStream borrowedInput, CloseableHttpClient borrowedClient,
                             URI trustedEndpoint, Path trustedParent, Limits limits,
                             BooleanSupplier cancelled) throws IOException {
        Objects.requireNonNull(borrowedInput); Objects.requireNonNull(borrowedClient);
        Objects.requireNonNull(limits); Objects.requireNonNull(cancelled);
        if (trustedEndpoint.getHost() == null || trustedEndpoint.getRawQuery() != null
                || trustedEndpoint.getFragment() != null || trustedEndpoint.getUserInfo() != null
                || !("http".equals(trustedEndpoint.getScheme()) || "https".equals(trustedEndpoint.getScheme()))) {
            throw new IllegalArgumentException("trusted endpoint must be an HTTP(S) URL without query");
        }
        check(cancelled);
        String csv = strictUtf8(readBounded(borrowedInput, limits.inputBytes, cancelled));
        List<Product> products = new ArrayList<>();
        CSVFormat format = CSVFormat.DEFAULT.builder().setHeader().setSkipHeaderRecord(true)
                .setDuplicateHeaderMode(DuplicateHeaderMode.DISALLOW).setIgnoreEmptyLines(false).get();
        try (CSVParser parser = CSVParser.parse(csv, format)) {
            if (!parser.getHeaderNames().equals(Arrays.asList("merchant", "sku", "price"))) {
                throw new IllegalArgumentException("expected merchant,sku,price header");
            }
            for (CSVRecord record : parser) {
                check(cancelled);
                if (products.size() >= limits.rows) throw new IOException("row budget exceeded");
                if (record.size() != 3 || !record.get(0).matches("[A-Za-z0-9_-]{1,64}")
                        || !record.get(1).matches("[A-Za-z0-9_-]{1,64}")
                        || !record.get(2).matches("[0-9]{1,10}(\\.[0-9]{1,2})?")) {
                    throw new IllegalArgumentException("invalid record " + record.getRecordNumber());
                }
                products.add(new Product(record.get(0), record.get(1), new BigDecimal(record.get(2))));
            }
        }
        Map<String, List<Product>> grouped = Catalog.groupByMerchant(products);
        ImmutableMap.Builder<String, ImmutableMap<String, Product>> index = ImmutableMap.builder();
        ImmutableMultiset.Builder<String> counts = ImmutableMultiset.builder();
        ImmutableList.Builder<Product> low = ImmutableList.builder();
        Range<BigDecimal> lowRange = Range.closedOpen(BigDecimal.ZERO, new BigDecimal("10.00"));
        for (Map.Entry<String, List<Product>> group : grouped.entrySet()) {
            ImmutableMap.Builder<String, Product> merchant = ImmutableMap.builder();
            for (Product product : group.getValue()) {
                merchant.put(product.getProductId(), product); counts.add(product.getMerchantId());
                if (lowRange.contains(product.getPrice())) low.add(product);
            }
            index.put(group.getKey(), merchant.buildOrThrow());
        }
        check(cancelled);
        Path workspace = Files.createTempDirectory(trustedParent.toRealPath(), "catalog-");
        try {
            ObjectMapper mapper = new ObjectMapper().enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
                    .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
            List<Map<String, Object>> rows = new ArrayList<>();
            for (Product product : products) {
                check(cancelled);
                URI uri;
                try {
                    uri = new URI(trustedEndpoint.getScheme(), null, trustedEndpoint.getHost(),
                            trustedEndpoint.getPort(), trustedEndpoint.getPath(),
                            "merchant=" + product.getMerchantId() + "&sku=" + product.getProductId(), null);
                } catch (URISyntaxException invalid) { throw new IOException(invalid); }
                JsonNode detail;
                try (ClassicHttpResponse response = borrowedClient.executeOpen(null, new HttpGet(uri), null)) {
                    if (response.getCode() != 200 || response.getEntity() == null) {
                        throw new IOException("detail HTTP status " + response.getCode());
                    }
                    try (InputStream body = response.getEntity().getContent()) {
                        detail = mapper.readTree(strictUtf8(readBounded(body, limits.responseBytes, cancelled)));
                    }
                }
                check(cancelled);
                if (detail == null || !detail.isObject() || detail.size() != 1
                        || !detail.path("label").isTextual() || detail.path("label").textValue().length() > 128) {
                    throw new IOException("invalid detail JSON schema");
                }
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("merchant", product.getMerchantId()); row.put("sku", product.getProductId());
                row.put("price", product.getPrice()); row.put("label", detail.get("label").textValue());
                rows.add(row);
            }
            Path report = SafePaths.resolveNewFile(workspace, "report.json");
            try (OutputStream file = Files.newOutputStream(report, StandardOpenOption.CREATE_NEW);
                 OutputStream bounded = limitedOutput(file, limits.reportBytes)) {
                mapper.writeValue(bounded, rows);
            }
            check(cancelled);
            Path archive = SafePaths.resolveNewFile(workspace, "report.zip");
            try (OutputStream file = Files.newOutputStream(archive, StandardOpenOption.CREATE_NEW);
                 OutputStream bounded = limitedOutput(file, limits.archiveBytes);
                 ZipOutputStream zip = new ZipOutputStream(bounded);
                 InputStream reportInput = Files.newInputStream(report)) {
                zip.putNextEntry(new ZipEntry("report.json"));
                BoundedIo.copy(checkedInput(reportInput, cancelled), zip, limits.reportBytes);
                zip.closeEntry();
            }
            check(cancelled);
            return new Export(workspace, report, archive, index.buildOrThrow(), counts.build(), low.build());
        } catch (IOException | RuntimeException | Error failure) {
            try { PrivateArchive.deleteTree(workspace); }
            catch (IOException cleanup) { failure.addSuppressed(cleanup); }
            throw failure;
        }
    }

    private static String strictUtf8(byte[] bytes) throws IOException {
        return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
    }

    private static byte[] readBounded(InputStream input, int max, BooleanSupplier cancelled) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        BoundedIo.copy(checkedInput(input, cancelled), output, max);
        return output.toByteArray();
    }

    private static InputStream checkedInput(InputStream input, BooleanSupplier cancelled) {
        return new FilterInputStream(input) {
            @Override public int read(byte[] b, int o, int l) throws IOException {
                check(cancelled); int n = in.read(b, o, l); check(cancelled); return n;
            }
            @Override public int read() throws IOException {
                check(cancelled); int n = in.read(); check(cancelled); return n;
            }
        };
    }

    private static OutputStream limitedOutput(OutputStream output, int maximum) {
        return new FilterOutputStream(output) {
            private long count;
            @Override public void write(int b) throws IOException {
                if (count == maximum) throw new IOException("output byte budget exceeded");
                out.write(b); count++;
            }
            @Override public void write(byte[] b, int o, int l) throws IOException {
                if (l > maximum - count) throw new IOException("output byte budget exceeded");
                out.write(b, o, l); count += l;
            }
        };
    }

    private static void check(BooleanSupplier cancelled) throws InterruptedIOException {
        if (Thread.currentThread().isInterrupted() || cancelled.getAsBoolean()) {
            throw new InterruptedIOException("pipeline cancelled at cooperative checkpoint");
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("CSV_FILE TRUSTED_DETAIL_URL TRUSTED_OUTPUT_PARENT");
        try (InputStream input = Files.newInputStream(Paths.get(args[0]));
             CloseableHttpClient client = HttpClients.custom().disableAutomaticRetries().disableRedirectHandling()
                     .setConnectionManager(PoolingHttpClientConnectionManagerBuilder.create()
                             .setDefaultConnectionConfig(ConnectionConfig.custom()
                                     .setConnectTimeout(Timeout.ofSeconds(2)).build()).build())
                     .setDefaultRequestConfig(RequestConfig.custom().setConnectionRequestTimeout(Timeout.ofSeconds(2))
                             .setResponseTimeout(Timeout.ofSeconds(2)).build()).build();
             Export export = run(input, client, URI.create(args[1]), Paths.get(args[2]),
                     new Limits(100, 65536, 4096, 65536, 70000), () -> false)) {
            System.out.println(new String(Files.readAllBytes(export.report), StandardCharsets.UTF_8));
            System.out.println("temporary archive bytes=" + Files.size(export.archive));
        }
    }
}
