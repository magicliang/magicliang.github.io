package blog.libraries;
import com.google.common.base.CharMatcher;
import com.google.common.base.Splitter;
import org.apache.commons.lang3.StringUtils;
import org.junit.jupiter.api.Test;
import java.util.Arrays;
import static org.junit.jupiter.api.Assertions.*;
public class Chapter20Test {
    @Test void whitespacePolicies() {
        assertNull(StringUtils.trim(null));
        assertEquals("A", StringUtils.trim("\u0000A\u0000"));
        assertEquals("\u0000A\u0000", StringUtils.strip("\u0000A\u0000"));
        assertEquals("A", StringUtils.strip("\u2003A\u2003"));
        assertEquals("\u2003A\u2003", StringUtils.trim("\u2003A\u2003"));
        assertEquals("\u00A0A\u00A0", StringUtils.strip("\u00A0A\u00A0"));
        assertEquals("A", CharMatcher.whitespace().trimFrom("\u00A0A\u00A0"));
        for (String text : Arrays.asList("", " ", "\t", "\u00A0", "\u2003", "\u200B", "\uFEFF")) {
            assertEquals(text.length() == 0 || text.chars().allMatch(Character::isWhitespace), StringUtils.isBlank(text));
            assertEquals(text.trim(), StringUtils.trim(text));
        }
    }
    @Test void splitEmptyAndSeparatorSemantics() {
        assertNull(StringUtils.split(null, ','));
        assertArrayEquals(new String[0], StringUtils.split("", ','));
        assertArrayEquals(new String[]{"A"}, StringUtils.split(",A,,", ','));
        assertArrayEquals(new String[]{"", "A", "", ""}, StringUtils.splitPreserveAllTokens(",A,,", ','));
        assertEquals(Arrays.asList("", "A", "", ""), Splitter.on(',').splitToList(",A,,"));
        assertArrayEquals(new String[]{"A", "B", "C"}, StringUtils.split("A:B;C", ":;"));
        assertArrayEquals(new String[]{"A:B;C"}, StringUtils.splitByWholeSeparator("A:B;C", ":;"));
    }
    @Test void substringUsesUtf16AndClamps() {
        assertNull(StringUtils.substring(null, 1));
        assertEquals("BC", StringUtils.substring("ABC", -2));
        assertEquals("", StringUtils.substring("ABC", 9));
        assertEquals("ABC", StringUtils.substring("ABC", -9, 9));
        assertThrows(StringIndexOutOfBoundsException.class, () -> "ABC".substring(9));
        assertEquals('\uD83D', StringUtils.substring("\uD83D\uDE00", 0, 1).charAt(0));
    }
    @Test void defaultsCollapseDifferentStates() {
        assertEquals("fallback", StringUtils.defaultIfBlank(" ", "fallback"));
        assertEquals(" ", StringUtils.defaultIfEmpty(" ", "fallback"));
        assertEquals("\u00A0", StringUtils.defaultIfBlank("\u00A0", "fallback"));
        assertEquals("", StringUtils.defaultString(null));
        assertEquals("", StringUtils.defaultString(""));
    }
}
