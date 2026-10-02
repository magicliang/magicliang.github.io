package blog.libraries;

import com.google.common.base.CharMatcher;
import com.google.common.base.Strings;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;
import java.util.stream.Stream;
import org.apache.commons.lang3.StringUtils;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import static org.junit.jupiter.api.Assertions.*;

class Chapter01Test {
    // Independent contract table: trim-empty, Java whitespace, Unicode space, Guava whitespace.
    static Stream<Arguments> cases() {
        return Stream.of(
            Arguments.of("empty", "", true, true, true, true),
            Arguments.of("SPACE", " ", true, true, true, true),
            Arguments.of("TAB", "\t", true, true, false, true),
            Arguments.of("CRLF", "\r\n", true, true, false, true),
            Arguments.of("NUL", "\u0000", true, false, false, false),
            Arguments.of("FS", "\u001c", true, true, false, false),
            Arguments.of("NBSP", "\u00a0", false, false, true, true),
            Arguments.of("FIGURE_SPACE", "\u2007", false, false, true, true),
            Arguments.of("NARROW_NBSP", "\u202f", false, false, true, true),
            Arguments.of("EM_SPACE", "\u2003", false, true, true, true),
            Arguments.of("ZERO_WIDTH_SPACE", "\u200b", false, false, false, false),
            Arguments.of("IDEOGRAPHIC_SPACE", "\u3000", false, true, true, true),
            Arguments.of("NEL", "\u0085", false, false, false, true),
            Arguments.of("LETTER", " A\t", false, false, false, false),
            Arguments.of("SUPPLEMENTARY", "\ud83d\ude00", false, false, false, false),
            Arguments.of("LONE_HIGH_SURROGATE", "\ud83d", false, false, false, false),
            Arguments.of("SPACE_AND_SURROGATE", " \ud83d", false, false, false, false)
        );
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("cases")
    void whitespaceContracts(String name, String value, boolean trimEmpty,
            boolean javaWhitespace, boolean unicodeSpace, boolean guavaWhitespace) throws Exception {
        boolean trim = value.trim().isEmpty();
        boolean jdk = value.codePoints().allMatch(Character::isWhitespace);
        boolean space = value.codePoints().allMatch(Character::isSpaceChar);
        boolean guava = CharMatcher.whitespace().matchesAllOf(value);
        boolean commons = StringUtils.isBlank(value);
        assertEquals(trimEmpty, trim, name + " trim");
        assertEquals(javaWhitespace, jdk, name + " Character.isWhitespace");
        assertEquals(unicodeSpace, space, name + " Character.isSpaceChar");
        assertEquals(guavaWhitespace, guava, name + " Guava whitespace");
        assertEquals(javaWhitespace, commons, name + " Commons blank");
        assertEquals(value.length() == 0, Strings.isNullOrEmpty(value));
        String modern = "NOT_AVAILABLE";
        try {
            Method isBlank = String.class.getMethod("isBlank");
            boolean actual = (Boolean) isBlank.invoke(value);
            assertEquals(javaWhitespace, actual, name + " modern String.isBlank");
            modern = Boolean.toString(actual);
        } catch (NoSuchMethodException expectedOnJava8) {
            assertEquals("1.8", System.getProperty("java.specification.version"));
        }
        System.out.printf("01|%s|length=%d|codePoints=%d|trim=%s|jdkWS=%s|spaceChar=%s|guava=%s|commons=%s|isBlank=%s%n",
                name, value.length(), value.codePointCount(0, value.length()), trim, jdk, space, guava, commons, modern);
    }

    @Test
    void absenceIsNotAnEmptyValue() {
        Map<String, String> fields = new HashMap<>();
        assertNull(fields.get("name"));
        assertFalse(fields.containsKey("name"));
        fields.put("name", null);
        assertNull(fields.get("name"));
        assertTrue(fields.containsKey("name"));
        fields.put("name", "");
        assertEquals("", fields.get("name"));
        assertTrue(Strings.isNullOrEmpty(null));
        assertTrue(StringUtils.isEmpty(null));
        assertTrue(StringUtils.isBlank(null));
        assertEquals("", Strings.nullToEmpty(null));
        assertNull(Strings.emptyToNull(""));
        assertEquals(" ", Strings.emptyToNull(" "));
        assertThrows(NullPointerException.class, () -> CharMatcher.whitespace().matchesAllOf(null));
        assertThrows(NullPointerException.class, () -> ((String) null).trim());
        System.out.println("01|absence|null/absent/empty distinguished; null API contracts asserted");
    }

    @Test
    void unicodeVersionBoundaryIsExplicit() throws Exception {
        String mongolianSeparator = "\u180e";
        String runtime = System.getProperty("java.specification.version");
        assertTrue("1.8".equals(runtime) || "21".equals(runtime), "This comparison is pinned to JDK 8 and 21");
        boolean expectedJava = "1.8".equals(runtime);
        assertEquals(expectedJava, Character.isWhitespace(0x180e));
        assertEquals(expectedJava, Character.isSpaceChar(0x180e));
        assertEquals(expectedJava, StringUtils.isBlank(mongolianSeparator));
        assertFalse(CharMatcher.whitespace().matchesAllOf(mongolianSeparator));
        assertFalse(mongolianSeparator.trim().isEmpty());
        if ("21".equals(runtime)) {
            assertEquals(Boolean.FALSE, String.class.getMethod("isBlank").invoke(mongolianSeparator));
        }
        System.out.printf("01|U+180E|runtime=%s|jdkWS=%s|spaceChar=%s|commons=%s|guava=false%n",
                runtime, Character.isWhitespace(0x180e), Character.isSpaceChar(0x180e), StringUtils.isBlank(mongolianSeparator));
    }

    static String requireSku(String raw) {
        if (raw == null || !raw.matches("[A-Z0-9][A-Z0-9-]{0,31}")) {
            throw new IllegalArgumentException("SKU must be 1..32 ASCII uppercase letters/digits/hyphens, starting alphanumeric");
        }
        return raw;
    }

    @Test
    void identifiersAreRejectedWithoutSilentRepair() {
        String valid = new String("BOOK-01");
        assertSame(valid, requireSku(valid));
        for (String invalid : new String[] {null, "", " ", " BOOK-01", "BOOK-01\u00a0", "BOOK\u200b-01", "\ud83d", "book-01"}) {
            assertThrows(IllegalArgumentException.class, () -> requireSku(invalid));
        }
        assertEquals("BOOK-01", " BOOK-01".trim());
        assertEquals("BOOK-01", CharMatcher.whitespace().trimFrom("BOOK-01\u00a0"));
        System.out.println("01|sku|valid original preserved; 8 invalid values rejected; trim collision demonstrated");
    }
}
