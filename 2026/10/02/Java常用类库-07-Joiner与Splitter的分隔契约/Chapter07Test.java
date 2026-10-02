package blog.libraries;

import com.google.common.base.Joiner;
import com.google.common.base.Splitter;
import org.junit.jupiter.api.Test;
import java.util.Arrays;
import java.util.Collections;
import static org.junit.jupiter.api.Assertions.*;

public class Chapter07Test {
    @Test void emptyFieldsAndJdkDefaults() {
        assertEquals(Arrays.asList("", "A", "", ""), Splitter.on(',').splitToList(",A,,"));
        assertArrayEquals(new String[]{"", "A"}, ",A,,".split(","));
        assertArrayEquals(new String[]{"", "A", "", ""}, ",A,,".split(",", -1));
        assertEquals(Collections.singletonList(""), Splitter.on(',').splitToList(""));
        assertEquals(Collections.emptyList(), Splitter.on(',').omitEmptyStrings().splitToList(""));
        assertEquals(Arrays.asList("A", "B"), Splitter.on(".").splitToList("A.B"));
        assertArrayEquals(new String[0], "A.B".split("."));
    }
    @Test void trimOmitLimitAndConfiguration() {
        Splitter plain = Splitter.on(',');
        plain.trimResults();
        assertEquals(Collections.singletonList(" A "), plain.splitToList(" A "));
        assertEquals(Arrays.asList("A", "B"), plain.omitEmptyStrings().trimResults().splitToList(" , A , , B , "));
        assertEquals(Arrays.asList("A", "B", "C,,D"), plain.trimResults().omitEmptyStrings().limit(3).splitToList(" A , , B ,, C,,D "));
        assertThrows(IllegalArgumentException.class, () -> plain.limit(0));
        assertThrows(NullPointerException.class, () -> plain.splitToList(null));
    }
    @Test void nullAndSeparatorCollisionsLoseInformation() {
        assertThrows(NullPointerException.class, () -> Joiner.on(',').join(Arrays.asList("A", null, "B")));
        assertEquals("A,B", Joiner.on(',').skipNulls().join(Arrays.asList("A", null, "B")));
        assertEquals("A,?,B", Joiner.on(',').useForNull("?").join(Arrays.asList("A", null, "B")));
        assertEquals(Joiner.on(',').join(Arrays.asList("A,B", "C")), Joiner.on(',').join(Arrays.asList("A", "B,C")));
        assertEquals("null", String.join(",", Arrays.asList((String) null)));
        assertEquals(3, Splitter.on(',').splitToList("\"A,B\",C").size());
    }
    @Test void mapsRejectDuplicateKeysAndExtraSeparators() {
        Splitter.MapSplitter strict = Splitter.on(';').withKeyValueSeparator('=');
        assertEquals("", strict.split("color=").get("color"));
        assertThrows(IllegalArgumentException.class, () -> strict.split("color=red;color=blue"));
        assertThrows(IllegalArgumentException.class, () -> strict.split("token=A=B"));
        assertEquals("A=B", Splitter.on(';').withKeyValueSeparator(Splitter.on('=').limit(2)).split("token=A=B").get("token"));
    }
}
