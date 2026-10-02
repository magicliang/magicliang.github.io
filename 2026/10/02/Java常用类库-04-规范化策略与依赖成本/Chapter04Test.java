package blog.libraries;

import com.google.common.base.CharMatcher;
import java.util.Locale;
import java.util.Objects;
import org.apache.commons.lang3.StringUtils;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter04Test {
    static String jdk(String raw) {
        return Objects.requireNonNull(raw, "merchant").trim().toUpperCase(Locale.ROOT);
    }
    static String commons(String raw) {
        return StringUtils.strip(Objects.requireNonNull(raw, "merchant")).toUpperCase(Locale.ROOT);
    }
    static String guava(String raw) {
        return CharMatcher.whitespace().trimFrom(Objects.requireNonNull(raw, "merchant"))
                .toUpperCase(Locale.ROOT);
    }
    @Test void normalizationIsEquivalentOnlyOnTheDeclaredAsciiSubset() {
        for (String input : new String[] {"", "  ", " acme ", "SKU-1", "\tacme\r\n"}) {
            assertEquals(jdk(input), commons(input));
            assertEquals(jdk(input), guava(input));
        }
        assertEquals("\u00a0ACME\u00a0", jdk("\u00a0acme\u00a0"));
        assertEquals("\u00a0ACME\u00a0", commons("\u00a0acme\u00a0"));
        assertEquals("ACME", guava("\u00a0acme\u00a0"));
        assertEquals("ACME", jdk("\u001cacme\u001c"));
        assertEquals("ACME", commons("\u001cacme\u001c"));
        assertEquals("\u001cACME\u001c", guava("\u001cacme\u001c"));
        assertThrows(NullPointerException.class, () -> jdk(null));
        assertThrows(NullPointerException.class, () -> commons(null));
        assertThrows(NullPointerException.class, () -> guava(null));
        System.out.println("04 normalization: ASCII subset=equal; NBSP and U+001C differ; null rejected");
    }
    @Test void rootLocaleAndPublicReturnTypeAreExplicit() {
        assertEquals("I", "i".toUpperCase(Locale.ROOT));
        assertEquals("\u0130", "i".toUpperCase(Locale.forLanguageTag("tr")));
        assertEquals(String.class, jdk(" acme ").getClass());
        assertEquals("ACME", jdk(" acme "));
        assertEquals("SS", jdk("\u00df"));
        System.out.println("04 locale: ROOT i=I, tr i=U+0130, sharp-s expands to SS");
    }
}
