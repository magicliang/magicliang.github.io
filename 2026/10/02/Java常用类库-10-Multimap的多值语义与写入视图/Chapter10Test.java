package blog.libraries;

import com.google.common.collect.ArrayListMultimap;
import com.google.common.collect.HashMultimap;
import org.junit.jupiter.api.Test;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;

public class Chapter10Test {
    @Test void duplicateAndSizePolicies() {
        ArrayListMultimap<String, String> list = ArrayListMultimap.create();
        HashMultimap<String, String> set = HashMultimap.create();
        for (String value : Arrays.asList("B", "A", "B")) { list.put("shop", value); set.put("shop", value); }
        assertEquals(Arrays.asList("B", "A", "B"), list.get("shop"));
        assertEquals(3, list.size());
        assertEquals(1, list.keySet().size());
        assertEquals(2, set.size());
        assertTrue(set.get("shop").containsAll(Arrays.asList("A", "B")));
        list.put(null, null);
        set.put(null, null);
        assertTrue(list.containsEntry(null, null));
        assertTrue(set.containsEntry(null, null));
    }
    @Test void absentViewsAttachAndDetach() {
        ArrayListMultimap<String, String> map = ArrayListMultimap.create();
        List<String> values = map.get("shop");
        assertTrue(values.isEmpty());
        assertFalse(map.containsKey("shop"));
        assertNull(map.asMap().get("shop"));
        values.add("A");
        assertTrue(map.containsEntry("shop", "A"));
        map.asMap().get("shop").add("B");
        assertEquals(Arrays.asList("A", "B"), values);
        values.remove("A");
        assertEquals(1, map.size());
        values.clear();
        assertFalse(map.containsKey("shop"));
        map.put("shop", "C");
        assertEquals(Arrays.asList("C"), values);
        assertThrows(UnsupportedOperationException.class, () -> map.asMap().put("other", Arrays.asList("D")));
    }
    @Test void removalResultIsDetachedButAllCollectionViewsAreLive() {
        ArrayListMultimap<String, String> map = ArrayListMultimap.create();
        map.putAll("shop", Arrays.asList("A", "B"));
        Collection<String> removed = map.asMap().remove("shop");
        assertEquals(Arrays.asList("A", "B"), removed);
        map.put("shop", "C");
        assertEquals(Arrays.asList("A", "B"), removed);
        map.values().remove("C");
        assertFalse(map.containsKey("shop"));
        map.put("shop", "D");
        java.util.Iterator<Map.Entry<String, String>> entries = map.entries().iterator();
        entries.next();
        entries.remove();
        assertTrue(map.isEmpty());
        map.put("shop", "E");
        map.keySet().remove("shop");
        assertTrue(map.isEmpty());
    }
    @Test void ordinaryMapCanRepresentAnEmptyGroup() {
        Map<String, List<String>> ordinary = new HashMap<>();
        ordinary.put("shop", new java.util.ArrayList<>());
        assertTrue(ordinary.containsKey("shop"));
        ArrayListMultimap<String, String> multi = ArrayListMultimap.create();
        multi.putAll("shop", ordinary.get("shop"));
        assertFalse(multi.containsKey("shop"));
    }
}
