package blog.libraries;

import java.util.HashMap;
import java.util.Map;
import org.apache.commons.text.StringEscapeUtils;
import org.apache.commons.text.StringSubstitutor;
import org.apache.commons.text.similarity.LevenshteinDistance;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter27Test {
    @Test
    void escapingMustMatchTheDestinationContext() {
        assertEquals("&lt;b&gt;&amp;&quot;'", StringEscapeUtils.escapeHtml4("<b>&\"'"));
        assertEquals("'", StringEscapeUtils.escapeHtml4("'"));
        assertEquals("\\\"\\n", StringEscapeUtils.escapeJson("\"\n"));
        assertEquals("\\'", StringEscapeUtils.escapeEcmaScript("'"));
        assertEquals("ab", StringEscapeUtils.escapeXml10("a\u0000b"));
        assertTrue(StringEscapeUtils.escapeJson("</script>").contains("<"));
    }

    @Test
    void mapLookupCannotReadEnvironmentAndUndefinedIsAnError() {
        Map<String, String> values = new HashMap<>();
        values.put("sku", "SKU-1");
        values.put("label", "${sku}");
        StringSubstitutor safe = new StringSubstitutor(values)
                .setEnableUndefinedVariableException(true)
                .setValueDelimiterMatcher(null)
                .setDisableSubstitutionInValues(true)
                .setEnableSubstitutionInVariables(false);
        assertEquals("item=SKU-1", safe.replace("item=${sku}"));
        assertEquals("${sku}", safe.replace("${label}"));
        assertThrows(IllegalArgumentException.class, () -> safe.replace("${env:SYNTHETIC_ONLY}"));
        assertThrows(IllegalArgumentException.class, () -> safe.replace("${unknown}"));
        assertThrows(IllegalArgumentException.class, () -> safe.replace("${unknown:-fallback}"));
        StringSubstitutor recursive = new StringSubstitutor(values);
        assertEquals("SKU-1", recursive.replace("${label}"));
        values.put("cycle", "${cycle}");
        assertThrows(IllegalStateException.class, () -> recursive.replace("${cycle}"));
    }

    @Test
    void distanceThresholdIsNotAnInputLengthBudget() {
        LevenshteinDistance distance = new LevenshteinDistance(2);
        assertEquals(Integer.valueOf(1), distance.apply("SKU-1", "SKU-2"));
        assertEquals(Integer.valueOf(-1), distance.apply("abcd", "wxyz"));
        assertThrows(IllegalArgumentException.class, () -> boundedDistance("abcd", "ab", 3));
        assertEquals(1, boundedDistance("abc", "abd", 3));
        System.out.println("27 policy: map-only lookup, unresolved reject, value recursion disabled, input length bounded");
    }

    private static int boundedDistance(String left, String right, int maxChars) {
        if (left.length() > maxChars || right.length() > maxChars) {
            throw new IllegalArgumentException("text length exceeded");
        }
        return new LevenshteinDistance(2).apply(left, right);
    }
}
