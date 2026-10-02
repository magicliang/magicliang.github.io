package blog.libraries;

import com.google.common.base.CharMatcher;
import com.google.common.base.Strings;
import org.junit.jupiter.api.Test;
import java.text.Normalizer;
import static org.junit.jupiter.api.Assertions.*;

public class Chapter08Test {
    @Test void matchingCountsUtf16Units() {
        String text = "A\uD83D\uDE00B";
        assertEquals(4, text.length());
        assertEquals(3, text.codePointCount(0, text.length()));
        assertEquals(2, CharMatcher.anyOf("\uD83D\uDE00").countIn(text));
        assertEquals("A??B", CharMatcher.anyOf("\uD83D\uDE00").replaceFrom(text, '?'));
        String broken = CharMatcher.is('\uD83D').removeFrom(text);
        assertEquals('\uDE00', broken.charAt(1));
        assertEquals("A?B", text.codePoints().collect(StringBuilder::new,
                (out, cp) -> out.appendCodePoint(cp == 0x1F600 ? '?' : cp), StringBuilder::append).toString());
    }
    @Test void codePointsStillDoNotNormalizeCombiningSequences() {
        String composed = "\u00E9";
        String decomposed = "e\u0301";
        assertNotEquals(composed, decomposed);
        assertEquals(2, decomposed.codePointCount(0, decomposed.length()));
        assertEquals(composed, Normalizer.normalize(decomposed, Normalizer.Form.NFC));
        assertEquals("e", CharMatcher.is('\u0301').removeFrom(decomposed));
        assertEquals(composed, CharMatcher.is('\u0301').removeFrom(composed));
    }
    @Test void prefixSuffixProtectPairsButNotGraphemeClusters() {
        assertEquals("", Strings.commonPrefix("\uD83D\uDE00", "\uD83D\uDE01"));
        assertEquals("", Strings.commonSuffix("\uD83D\uDE00", "\uD83E\uDE00"));
        assertEquals("e", Strings.commonPrefix("e\u0301", "e\u0300"));
        assertEquals("\uD83D\uDE00", Strings.padStart("\uD83D\uDE00", 2, '_'));
        assertEquals("_\uD83D\uDE00", Strings.padStart("\uD83D\uDE00", 3, '_'));
    }
    @Test void whitespaceAndNullConversionArePolicies() {
        assertEquals("A B", CharMatcher.whitespace().trimAndCollapseFrom("\u00A0 A\t\tB \u00A0", ' '));
        assertEquals("\u200BA\u200B", CharMatcher.whitespace().trimFrom("\u200BA\u200B"));
        assertEquals("", Strings.nullToEmpty(null));
        assertNull(Strings.emptyToNull(""));
        assertEquals(" ", Strings.emptyToNull(" "));
        assertThrows(NullPointerException.class, () -> CharMatcher.whitespace().removeFrom(null));
    }
}
