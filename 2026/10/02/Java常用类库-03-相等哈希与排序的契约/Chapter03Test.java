package blog.libraries;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeSet;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter03Test {
    static final class Key {
        String merchant;
        final String sku;
        Key(String merchant, String sku) { this.merchant = merchant; this.sku = sku; }
        public boolean equals(Object other) {
            if (!(other instanceof Key)) { return false; }
            Key key = (Key) other;
            return Objects.equals(merchant, key.merchant) && Objects.equals(sku, key.sku);
        }
        public int hashCode() { return Objects.hash(merchant, sku); }
    }

    @Test void mutableHashKeyBecomesUnreachableUntilRestored() {
        Key key = new Key("A", "SKU-1");
        Map<Key, String> map = new HashMap<>();
        map.put(key, "product");
        key.merchant = "B";
        assertNull(map.get(key));
        assertEquals(1, map.size());
        assertSame(key, map.keySet().iterator().next());
        key.merchant = "A";
        assertEquals("product", map.get(new Key("A", "SKU-1")));
        System.out.println("03 mutable-key: size=1, lookup-after-change=null, restored=product");
    }

    @Test void comparisonZeroIsSortedSetIdentity() {
        BigDecimal a = new BigDecimal("1.0");
        BigDecimal b = new BigDecimal("1.00");
        assertNotEquals(a, b);
        assertEquals(0, a.compareTo(b));
        assertEquals(2, new HashSet<>(Arrays.asList(a, b)).size());
        assertEquals(1, new TreeSet<>(Arrays.asList(a, b)).size());
        Set<Key> bySku = new TreeSet<>(Comparator.comparing(k -> k.sku));
        assertTrue(bySku.add(new Key("A", "SKU-1")));
        assertFalse(bySku.add(new Key("B", "SKU-1")));
        Set<Key> byIdentity = new TreeSet<>(Comparator.comparing((Key k) -> k.merchant)
                .thenComparing(k -> k.sku));
        byIdentity.addAll(Arrays.asList(new Key("A", "SKU-1"), new Key("B", "SKU-1")));
        assertEquals(2, byIdentity.size());
        System.out.println("03 equality: decimal HashSet=2 TreeSet=1; sku-only=1 compound-key=2");
    }

    @Test void nullPlacementAndSubtractionOverflowAreSeparatePolicies() {
        List<String> values = new ArrayList<>(Arrays.asList("B", null, "A"));
        values.sort(Comparator.nullsFirst(Comparator.naturalOrder()));
        assertEquals(Arrays.asList(null, "A", "B"), values);
        values.sort(Comparator.nullsLast(Comparator.naturalOrder()));
        assertEquals(Arrays.asList("A", "B", null), values);
        assertThrows(NullPointerException.class, () -> Comparator.<String>naturalOrder().compare(null, "A"));
        assertTrue(Integer.MAX_VALUE - (-1) < 0);
        assertTrue(Integer.compare(Integer.MAX_VALUE, -1) > 0);
        System.out.println("03 ordering: null-first/null-last PASS; subtraction overflows, Integer.compare positive");
    }
}
