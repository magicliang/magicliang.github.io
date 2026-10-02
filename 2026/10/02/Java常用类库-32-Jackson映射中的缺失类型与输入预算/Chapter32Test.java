package blog.libraries;

import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonToken;
import com.fasterxml.jackson.core.StreamReadConstraints;
import com.fasterxml.jackson.core.StreamReadFeature;
import com.fasterxml.jackson.core.exc.StreamConstraintsException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.exc.UnrecognizedPropertyException;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.Test;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;

public class Chapter32Test {
    public static final class Product {
        public String name;
        public BigDecimal price;
        public LocalDate availableOn;
    }
    public static final class Cycle { public Cycle self; }
    static ObjectMapper mapper() {
        return new ObjectMapper().registerModule(new JavaTimeModule())
                .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
    }
    @Test void missingNullAndUnknownHaveDifferentContracts() throws Exception {
        ObjectMapper mapper = mapper();
        JsonNode absent = mapper.readTree("{}");
        JsonNode explicit = mapper.readTree("{\"name\":null}");
        assertFalse(absent.has("name")); assertNull(absent.get("name"));
        assertTrue(absent.path("name").isMissingNode());
        assertTrue(explicit.has("name")); assertTrue(explicit.get("name").isNull());
        assertFalse(explicit.hasNonNull("name"));
        assertNull(mapper.readValue("{}", Product.class).name);
        assertNull(mapper.readValue("{\"name\":null}", Product.class).name);
        assertThrows(UnrecognizedPropertyException.class,
                () -> mapper.readValue("{\"extra\":1}", Product.class));
        assertNull(mapper.readerFor(Product.class)
                .without(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
                .<Product>readValue("{\"extra\":1}").name);
    }
    @Test void duplicateFieldsNeedAnExplicitPolicy() throws Exception {
        String json = "{\"name\":\"first\",\"name\":\"last\"}";
        assertEquals("last", mapper().readTree(json).get("name").textValue());
        ObjectMapper strict = new ObjectMapper(JsonFactory.builder()
                .enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION).build());
        assertThrows(IOException.class, () -> strict.readTree(json));
    }
    @Test void genericsDecimalAndDatesRetainIntendedTypes() throws Exception {
        ObjectMapper mapper = mapper();
        String json = "[{\"name\":\"A\",\"price\":0.10,\"availableOn\":\"2026-10-02\"}]";
        List<?> raw = mapper.readValue(json, List.class);
        assertTrue(raw.get(0) instanceof Map);
        List<Product> typed = mapper.readValue(json, new TypeReference<List<Product>>() {});
        assertEquals(new BigDecimal("0.10"), typed.get(0).price);
        assertEquals(LocalDate.of(2026, 10, 2), typed.get(0).availableOn);
        assertTrue(mapper.writeValueAsString(typed).contains("\"availableOn\":\"2026-10-02\""));
        assertTrue(mapper.readValue("0.1", Object.class) instanceof Double);
        assertTrue(mapper.readerFor(Object.class)
                .with(DeserializationFeature.USE_BIG_DECIMAL_FOR_FLOATS).readValue("0.1")
                instanceof BigDecimal);
        Cycle cycle = new Cycle(); cycle.self = cycle;
        assertThrows(IOException.class, () -> mapper.writeValueAsString(cycle));
    }
    @Test void streamingStillRequiresShapeAndInputBudgets() throws Exception {
        byte[] bytes = "[{\"price\":1.25},{\"price\":2.75}]".getBytes(StandardCharsets.UTF_8);
        assertTrue(bytes.length <= 128);
        BigDecimal sum = BigDecimal.ZERO;
        try (JsonParser parser = mapper().getFactory().createParser(new ByteArrayInputStream(bytes))) {
            while (parser.nextToken() != null) {
                if (parser.currentToken() == JsonToken.FIELD_NAME && "price".equals(parser.currentName())) {
                    assertEquals(JsonToken.VALUE_NUMBER_FLOAT, parser.nextToken());
                    sum = sum.add(parser.getDecimalValue());
                }
            }
        }
        assertEquals(new BigDecimal("4.00"), sum);
        ObjectMapper bounded = new ObjectMapper(JsonFactory.builder()
                .streamReadConstraints(StreamReadConstraints.builder().maxNestingDepth(3).build())
                .build());
        assertThrows(StreamConstraintsException.class, () -> bounded.readTree("[[[[0]]]]"));
        assertThrows(IllegalArgumentException.class, () -> readBudgeted(new byte[129], 128));
        assertEquals("A", readBudgeted("{\"name\":\"A\"}".getBytes(StandardCharsets.UTF_8), 128).get("name").textValue());
    }
    static JsonNode readBudgeted(byte[] input, int limit) throws IOException {
        if (input.length > limit) throw new IllegalArgumentException("input exceeds byte budget");
        return mapper().readTree(input);
    }
}
