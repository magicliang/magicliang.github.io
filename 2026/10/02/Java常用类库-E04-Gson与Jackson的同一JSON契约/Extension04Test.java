package blog.libraries;

import blog.libraries.io.BoundedIo;
import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.StreamReadFeature;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.Strictness;
import com.google.gson.ToNumberPolicy;
import com.google.gson.TypeAdapter;
import com.google.gson.reflect.TypeToken;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonWriter;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.StringReader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Extension04Test {
    public static class Product { public Integer quantity = 7; public String name; }
    public static class Exposure { private String secret = "synthetic"; public String getDisplay() { return "public"; } }
    public static class Cycle { public Cycle self; }
    private Gson gson() { return new GsonBuilder().setStrictness(Strictness.STRICT).create(); }
    private ObjectMapper jackson() { return new ObjectMapper(); }

    @Test
    void missingNullUnknownAndExposureHaveSeparateContracts() throws Exception {
        assertEquals(7, gson().fromJson("{}", Product.class).quantity);
        assertEquals(7, jackson().readValue("{}", Product.class).quantity);
        assertNull(gson().fromJson("{\"quantity\":null}", Product.class).quantity);
        assertNull(jackson().readValue("{\"quantity\":null}", Product.class).quantity);
        assertEquals(7, gson().fromJson("{\"unknown\":1}", Product.class).quantity);
        assertThrows(com.fasterxml.jackson.databind.exc.UnrecognizedPropertyException.class,
                () -> jackson().readValue("{\"unknown\":1}", Product.class));
        assertEquals(7, jackson().disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES).readValue("{\"unknown\":1}", Product.class).quantity);
        assertTrue(gson().toJson(new Exposure()).contains("synthetic"));
        assertFalse(jackson().writeValueAsString(new Exposure()).contains("synthetic"));
        assertEquals("{\"display\":\"public\"}", jackson().writeValueAsString(new Exposure()));
    }

    @Test
    void genericNumericDateAndTreesCanShareAnExplicitContract() throws Exception {
        String input = "[{\"quantity\":3,\"name\":\"商品\"}]";
        List<Product> gs = gson().fromJson(input, new TypeToken<List<Product>>() { }.getType());
        List<Product> js = jackson().readValue(input, new TypeReference<List<Product>>() { });
        assertEquals(gs.get(0).quantity, js.get(0).quantity); assertEquals(gs.get(0).name, js.get(0).name);
        String number = "{\"amount\":0.1234567890123456789}";
        Map<?, ?> gm = new GsonBuilder().setObjectToNumberStrategy(ToNumberPolicy.BIG_DECIMAL).create().fromJson(number, Map.class);
        Map<?, ?> jm = jackson().enable(DeserializationFeature.USE_BIG_DECIMAL_FOR_FLOATS).readValue(number, Map.class);
        assertEquals(new BigDecimal("0.1234567890123456789"), gm.get("amount")); assertEquals(gm.get("amount"), jm.get("amount"));
        Instant time = Instant.parse("2026-10-02T00:00:00Z");
        ObjectMapper dates = jackson().registerModule(new JavaTimeModule()).disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        assertEquals("{\"seconds\":1790899200,\"nanos\":0}", gson().toJson(time));
        Gson isoDates = new GsonBuilder().registerTypeAdapter(Instant.class, new TypeAdapter<Instant>() {
            @Override public void write(JsonWriter out, Instant value) throws IOException { out.value(value.toString()); }
            @Override public Instant read(JsonReader in) throws IOException { return Instant.parse(in.nextString()); }
        }.nullSafe()).create();
        assertEquals(isoDates.toJson(time), dates.writeValueAsString(time));
        assertEquals(time, isoDates.fromJson(isoDates.toJson(time), Instant.class));
        assertEquals(time, gson().fromJson(gson().toJson(time), Instant.class));
        JsonObject gt = JsonParser.parseString("{\"quantity\":null}").getAsJsonObject();
        JsonNode jt = jackson().readTree("{\"quantity\":null}");
        assertTrue(gt.has("quantity")); assertTrue(gt.get("quantity").isJsonNull());
        assertTrue(jt.has("quantity")); assertTrue(jt.get("quantity").isNull());
        assertFalse(gt.has("name")); assertFalse(jt.has("name"));
    }

    @Test
    void duplicatePolicyNeedsMoreThanStrictJsonGrammar() throws Exception {
        String duplicate = "{\"quantity\":1,\"quantity\":2}";
        assertEquals(2, gson().fromJson(duplicate, Product.class).quantity);
        assertEquals(2, jackson().readValue(duplicate, Product.class).quantity);
        ObjectMapper strict = new ObjectMapper(JsonFactory.builder().enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION).build());
        assertThrows(IOException.class, () -> strict.readValue(duplicate, Product.class));
        assertThrows(IOException.class, () -> gsonRootObject(duplicate));
        assertEquals(1, gsonRootObject("{\"quantity\":1}").get("quantity").getAsInt());
        assertThrows(com.google.gson.JsonSyntaxException.class, () -> gson().fromJson("{\"quantity\":1.5}", Product.class));
        assertEquals(1, jackson().readValue("{\"quantity\":1.5}", Product.class).quantity);
        assertThrows(IOException.class, () -> jackson().disable(DeserializationFeature.ACCEPT_FLOAT_AS_INT)
                .readValue("{\"quantity\":1.5}", Product.class));
    }

    private static JsonObject gsonRootObject(String text) throws IOException {
        try (JsonReader reader = new JsonReader(new StringReader(text))) {
            reader.setStrictness(Strictness.STRICT); reader.beginObject();
            Set<String> names = new HashSet<>(); JsonObject result = new JsonObject();
            while (reader.hasNext()) {
                String name = reader.nextName();
                if (!names.add(name)) { throw new IOException("duplicate root field"); }
                JsonElement value = JsonParser.parseReader(reader); result.add(name, value);
            }
            reader.endObject();
            if (reader.peek() != com.google.gson.stream.JsonToken.END_DOCUMENT) { throw new IOException("trailing input"); }
            return result;
        }
    }

    @Test
    void byteBudgetPrecedesTreeMaterializationAndCyclesAreNotIdentityGraphs() throws Exception {
        byte[] bytes = "{\"quantity\":3}".getBytes(StandardCharsets.UTF_8);
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        assertThrows(IOException.class, () -> BoundedIo.copy(new ByteArrayInputStream(bytes), output, 4));
        Cycle cycle = new Cycle(); cycle.self = cycle;
        assertEquals("{}", gson().toJson(cycle));
        assertThrows(com.fasterxml.jackson.databind.exc.InvalidDefinitionException.class, () -> jackson().writeValueAsString(cycle));
        // Gson skips a direct self field; this says nothing about longer cycles.
    }
}
