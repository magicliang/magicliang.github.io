package blog.libraries;
import org.apache.commons.collections4.bag.HashBag;
import org.apache.commons.collections4.multimap.ArrayListValuedHashMap;
import org.apache.commons.collections4.multimap.HashSetValuedHashMap;
import org.apache.commons.collections4.bidimap.DualHashBidiMap;
import com.google.common.collect.HashMultiset;
import com.google.common.collect.HashBiMap;
import org.junit.jupiter.api.Test;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;
public class Chapter23Test {
    @Test void bagCountsIterationAndRemoveContract() {
        HashBag<String> bag = new HashBag<>();
        bag.add("A", 3); bag.add("B"); bag.add(null);
        assertEquals(5, bag.size());
        assertEquals(3, bag.getCount("A"));
        Map<String, Integer> counts = new HashMap<>();
        for (String value : bag) { counts.merge(value, 1, Integer::sum); }
        assertEquals(Integer.valueOf(3), counts.get("A"));
        assertEquals(Integer.valueOf(1), counts.get(null));
        assertTrue(bag.remove("A"));
        assertEquals(0, bag.getCount("A"));
        HashMultiset<String> guava = HashMultiset.create(Arrays.asList("A", "A", "A"));
        guava.remove("A");
        assertEquals(2, guava.count("A"));
    }
    @Test void iteratorRemoveDeletesOneOccurrence() {
        HashBag<String> bag = new HashBag<>(); bag.add("A", 3);
        Iterator<String> iterator = bag.iterator(); iterator.next(); iterator.remove();
        assertEquals(2, bag.getCount("A"));
        assertFalse(bag.containsAll(Arrays.asList("A", "A", "A")));
    }
    @Test void multivaluedViewsAndNulls() {
        ArrayListValuedHashMap<String, String> list = new ArrayListValuedHashMap<>();
        HashSetValuedHashMap<String, String> set = new HashSetValuedHashMap<>();
        for (String value : Arrays.asList("B", "A", "B")) { list.put("shop", value); set.put("shop", value); }
        assertEquals(Arrays.asList("B", "A", "B"), list.get("shop"));
        assertEquals(3, list.size()); assertEquals(2, set.size());
        assertNull(list.asMap().get("absent"));
        list.get("absent").add("C"); assertTrue(list.containsKey("absent"));
        list.get("absent").clear(); assertFalse(list.containsKey("absent"));
        list.put(null, null); set.put(null, null);
        assertTrue(list.containsMapping(null, null)); assertTrue(set.containsMapping(null, null));
    }
    @Test void bidiDuplicateValueRemovesPreviousKeyUnlikeGuavaPut() {
        DualHashBidiMap<String, String> commons = new DualHashBidiMap<>();
        commons.put("A", "x"); commons.put("B", "x");
        assertFalse(commons.containsKey("A")); assertEquals(1, commons.size());
        commons.inverseBidiMap().put("y", "C");
        assertEquals("y", commons.get("C"));
        commons.inverseBidiMap().remove("x"); assertFalse(commons.containsKey("B"));
        commons.put(null, null); assertTrue(commons.containsKey(null));
        HashBiMap<String, String> guava = HashBiMap.create(); guava.put("A", "x");
        assertThrows(IllegalArgumentException.class, () -> guava.put("B", "x"));
        guava.forcePut("B", "x"); assertEquals("x", guava.get("B"));
    }
}
