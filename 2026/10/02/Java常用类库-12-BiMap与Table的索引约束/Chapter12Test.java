package blog.libraries;

import com.google.common.collect.BiMap;
import com.google.common.collect.HashBiMap;
import com.google.common.collect.HashBasedTable;
import com.google.common.collect.Table;
import java.util.Map;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter12Test {
    @Test
    void duplicateValueIsRejectedBeforeMutation() {
        BiMap<String, String> ids = HashBiMap.create();
        ids.put("sku-a", "external-1");
        ids.put("sku-b", "external-2");
        assertThrows(IllegalArgumentException.class, () -> ids.put("sku-a", "external-2"));
        assertEquals("external-1", ids.get("sku-a"));
        assertEquals("sku-b", ids.inverse().get("external-2"));
        assertEquals(2, ids.size());
    }

    @Test
    void forcePutCanDeleteTwoOldAssociationsAndReturnOnlyOneValue() {
        BiMap<String, String> ids = HashBiMap.create();
        ids.put("sku-a", "external-1");
        ids.put("sku-b", "external-2");
        assertEquals("external-1", ids.forcePut("sku-a", "external-2"));
        assertEquals(1, ids.size());
        assertFalse(ids.containsKey("sku-b"));
        assertFalse(ids.inverse().containsKey("external-1"));
        assertEquals("sku-a", ids.inverse().get("external-2"));
        System.out.println("12 forcePut: {sku-a=external-1, sku-b=external-2} -> {sku-a=external-2}");
    }

    @Test
    void inverseIsWritableSharedDataAndNullNeedsContainsKey() {
        BiMap<String, String> ids = HashBiMap.create();
        ids.put("sku-a", "external-1");
        BiMap<String, String> inverse = ids.inverse();
        assertSame(ids, inverse.inverse());
        inverse.put("external-2", "sku-b");
        assertEquals("external-2", ids.get("sku-b"));
        inverse.remove("external-1");
        assertFalse(ids.containsKey("sku-a"));
        ids.put("missing-reference", null);
        assertNull(ids.get("missing-reference"));
        assertTrue(ids.containsKey("missing-reference"));
        assertFalse(ids.containsKey("absent"));
        assertThrows(IllegalArgumentException.class, () -> ids.put("other", null));
    }

    @Test
    void rowAndColumnViewsWriteThroughAndMissingRowCanBecomePresent() {
        Table<String, String, Integer> prices = HashBasedTable.create();
        Map<String, Integer> row = prices.row("merchant-a");
        assertTrue(row.isEmpty());
        assertFalse(prices.containsRow("merchant-a"));
        row.put("sku-a", 100);
        prices.put("merchant-b", "sku-a", 200);
        Map<String, Integer> column = prices.column("sku-a");
        assertEquals(2, column.size());
        assertEquals(Integer.valueOf(100), column.put("merchant-a", 150));
        assertEquals(Integer.valueOf(150), row.get("sku-a"));
        row.remove("sku-a");
        assertFalse(prices.containsRow("merchant-a"));
        assertFalse(column.containsKey("merchant-a"));
        assertEquals(1, prices.size());
        assertNull(prices.get("absent", "sku-a"));
        assertTrue(prices.row("absent").isEmpty());
        System.out.println("12 table: absent row -> write row -> edit column -> remove row; cells=1");
    }

    @Test
    void tableRejectsNullsAndWholeRowReplacement() {
        Table<String, String, Integer> prices = HashBasedTable.create();
        assertThrows(NullPointerException.class, () -> prices.put(null, "sku", 100));
        assertThrows(NullPointerException.class, () -> prices.put("merchant", null, 100));
        assertThrows(NullPointerException.class, () -> prices.put("merchant", "sku", null));
        assertThrows(UnsupportedOperationException.class,
                () -> prices.rowMap().put("merchant", java.util.Collections.singletonMap("sku", 100)));
    }
}
