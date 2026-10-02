package blog.libraries.processors;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaCompiler;
import javax.tools.JavaFileObject;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class ProcessorContractTest {
    @TempDir Path temp;

    @Test
    void createMatchesManualContractAndNullSourceReturnsNull() {
        ProductInput input = new ProductInput(); input.setName("sku"); input.setCount(3);
        input.setTags(new ArrayList<>(Arrays.asList("a")));
        ProductView expected = new ProductView("sku", 3, new ArrayList<>(input.getTags()));
        ProductView mapped = ProductMapper.INSTANCE.create(input);
        assertEquals(expected, mapped); assertNotSame(input.getTags(), mapped.getTags());
        input.getTags().add("b"); assertEquals(Arrays.asList("a"), mapped.getTags());
        assertNull(ProductMapper.INSTANCE.create(null));
    }

    @Test
    void updateDefaultNullAndIgnoreHaveDifferentMeanings() {
        ProductInput absent = new ProductInput();
        ProductView overwrite = new ProductView("old", 7, new ArrayList<>(Arrays.asList("a")));
        ProductView patch = new ProductView("old", 7, new ArrayList<>(Arrays.asList("a")));
        ProductMapper.INSTANCE.overwrite(absent, overwrite);
        ProductMapper.INSTANCE.patch(absent, patch);
        assertNull(overwrite.getName()); assertNull(overwrite.getCount()); assertNull(overwrite.getTags());
        assertEquals("old", patch.getName()); assertEquals(7, patch.getCount()); assertEquals(Arrays.asList("a"), patch.getTags());
        ProductMapper.INSTANCE.overwrite(null, patch); assertEquals("old", patch.getName());
    }

    @Test
    void builderSharesValuesAndGeneratedHashCodeDoesNotFreezeKeys() {
        List<String> tags = new ArrayList<>(Arrays.asList("a"));
        ProductView value = ProductView.builder().name("sku").count(3).tags(tags).build();
        assertSame(tags, value.getTags()); tags.add("b"); assertEquals(2, value.getTags().size());
        Set<ProductView> set = new HashSet<>(); set.add(value);
        int before = value.hashCode(); value.setCount(4); assertNotEquals(before, value.hashCode());
        assertFalse(set.contains(value)); assertSame(value, set.iterator().next());
    }

    @Test
    void missingTargetFieldIsARealCompilerDiagnostic() throws IOException {
        Path source = temp.resolve("Bad.java");
        String code = "import org.mapstruct.*; @Mapper(unmappedTargetPolicy=ReportingPolicy.ERROR) interface Bad { "
                + "Target map(Source value); class Source { public String name; } class Target { public String name; public String extra; } }";
        Files.write(source, code.getBytes(StandardCharsets.UTF_8));
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler(); assertNotNull(compiler);
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        try (StandardJavaFileManager files = compiler.getStandardFileManager(diagnostics, null, StandardCharsets.UTF_8)) {
            String classpath = System.getProperty("surefire.test.class.path", System.getProperty("java.class.path"));
            List<String> options = Arrays.asList("-classpath", classpath, "-processor", "org.mapstruct.ap.MappingProcessor", "-d", temp.toString(), "-s", temp.toString());
            boolean result = compiler.getTask(null, files, diagnostics, options, null, files.getJavaFileObjects(source.toFile())).call();
            assertFalse(result);
            String messages = diagnostics.getDiagnostics().toString();
            assertTrue(messages.contains("Unmapped target property")); assertTrue(messages.contains("extra"));
            System.out.println("E08 EXPECTED COMPILER FAILURE: " + messages);
        }
    }
}
