package blog.libraries;
import org.apache.commons.lang3.BooleanUtils;
import org.apache.commons.lang3.EnumUtils;
import org.apache.commons.lang3.Validate;
import org.apache.commons.lang3.math.NumberUtils;
import org.junit.jupiter.api.Test;
import java.math.BigDecimal;
import static org.junit.jupiter.api.Assertions.*;
public class Chapter21Test {
    enum Mode { SAFE, FAST }
    @Test void fallbackHidesInvalidAndOverflow() {
        for (String input : new String[]{null, "", "bad", " 2", "2147483648", "1e3"}) {
            assertEquals(-1, NumberUtils.toInt(input, -1));
            assertThrows(NumberFormatException.class, () -> Integer.parseInt(input));
        }
        assertEquals(0, NumberUtils.toInt("bad"));
        assertEquals(0, NumberUtils.toInt("0"));
    }
    @Test void numericGrammarsDiffer() {
        assertTrue(NumberUtils.isCreatable("1e3"));
        assertEquals(1000.0, NumberUtils.createNumber("1e3").doubleValue());
        assertEquals(16, NumberUtils.createNumber("0x10").intValue());
        assertFalse(NumberUtils.isCreatable("09"));
        assertEquals(9, NumberUtils.toInt("09"));
        assertEquals(new BigDecimal("1E+3"), new BigDecimal("1e3"));
        assertThrows(NumberFormatException.class, () -> new BigDecimal("0x10"));
    }
    @Test void nullableBooleanPreservesUnknownOnlyUntilDefaulted() {
        assertEquals(Boolean.TRUE, BooleanUtils.toBooleanObject("yes"));
        assertEquals(Boolean.FALSE, BooleanUtils.toBooleanObject("off"));
        assertNull(BooleanUtils.toBooleanObject("maybe"));
        assertFalse(BooleanUtils.toBoolean("maybe"));
        assertFalse(Boolean.parseBoolean("yes"));
        assertFalse(BooleanUtils.toBooleanDefaultIfNull(null, false));
        assertThrows(IllegalArgumentException.class, () -> BooleanUtils.toBoolean("maybe", "yes", "no"));
    }
    @Test void enumAndValidationSeparateMissingFromBad() {
        assertNull(EnumUtils.getEnum(Mode.class, "safe"));
        assertEquals(Mode.SAFE, EnumUtils.getEnumIgnoreCase(Mode.class, "safe"));
        assertEquals(Mode.SAFE, EnumUtils.getEnum(Mode.class, "unknown", Mode.SAFE));
        assertThrows(IllegalArgumentException.class, () -> Mode.valueOf("unknown"));
        assertThrows(NullPointerException.class, () -> Validate.notNull(null, "missing quantity"));
        IllegalArgumentException failure = assertThrows(IllegalArgumentException.class, () -> Validate.isTrue(-1 >= 0, "quantity out of range"));
        assertEquals("quantity out of range", failure.getMessage());
    }
}
