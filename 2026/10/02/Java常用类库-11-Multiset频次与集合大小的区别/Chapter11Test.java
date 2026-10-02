package blog.libraries;

import com.google.common.collect.HashMultiset;
import com.google.common.collect.Multiset;
import com.google.common.collect.Multisets;
import com.google.common.collect.TreeMultiset;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Set;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter11Test {
    @Test
    void tagCountsAreOccurrencesNotDistinctElements() {
        Multiset<String> tags = HashMultiset.create(Arrays.asList("sale", "sale", "new"));
        assertEquals(3, tags.size());
        assertEquals(2, tags.elementSet().size());
        assertEquals(2, tags.add("sale", 3));
        assertEquals(5, tags.remove("sale", 2));
        assertEquals(3, tags.count("sale"));
        assertEquals(3, tags.remove("sale", 99));
        assertEquals(0, tags.count("sale"));
        assertEquals(1, tags.size());
        System.out.println("11 counts: size=3 distinct=2; add old=2; remove old=5; clamp old=3 final=0");
    }

    @Test
    void removalSurfaceDeterminesMultiplicity() {
        Multiset<String> tags = HashMultiset.create(Arrays.asList("sale", "sale", "new"));
        Iterator<String> occurrences = tags.iterator();
        String removed = occurrences.next();
        int before = tags.count(removed);
        occurrences.remove();
        assertEquals(before - 1, tags.count(removed));
        tags.setCount("sale", 4);
        Set<String> elements = tags.elementSet();
        assertTrue(elements.remove("sale"));
        assertEquals(0, tags.count("sale"));
        tags.setCount("sale", 3);
        Multiset.Entry<String> entry = tags.entrySet().stream()
                .filter(value -> value.getElement().equals("sale")).findFirst().get();
        tags.add("sale", 2);
        assertEquals(5, entry.getCount());
        assertFalse(tags.entrySet().remove(Multisets.immutableEntry("sale", 3)));
        assertTrue(tags.entrySet().remove(Multisets.immutableEntry("sale", 5)));
        assertEquals(0, tags.count("sale"));
    }

    @Test
    void countBoundariesRejectOverflowButTotalSizeSaturates() {
        Multiset<String> counts = HashMultiset.create();
        counts.add("sale", Integer.MAX_VALUE);
        assertThrows(IllegalArgumentException.class, () -> counts.add("sale", 1));
        assertEquals(Integer.MAX_VALUE, counts.count("sale"));
        counts.add("new", 1);
        assertEquals(Integer.MAX_VALUE, counts.size());
        long total = counts.entrySet().stream().mapToLong(Multiset.Entry::getCount).sum();
        assertEquals(2147483648L, total);
        assertThrows(IllegalArgumentException.class, () -> counts.remove("sale", -1));
        assertThrows(IllegalArgumentException.class, () -> counts.setCount("new", -1));
        assertFalse(counts.setCount("new", 2, 0));
        assertTrue(counts.setCount("new", 1, 0));
        assertFalse(counts.contains("new"));
        System.out.println("11 boundary: size=2147483647 summedCounts=2147483648");
    }

    @Test
    void collectionContainsAndRemoveAllIgnoreRequestedCounts() {
        Multiset<String> stock = HashMultiset.create(Arrays.asList("sale", "sale"));
        Multiset<String> demand = HashMultiset.create(Arrays.asList("sale", "sale", "sale"));
        assertTrue(stock.containsAll(demand));
        assertFalse(Multisets.containsOccurrences(stock, demand));
        stock.removeAll(Arrays.asList("sale"));
        assertTrue(stock.isEmpty());
    }

    @Test
    void comparatorDefinesSortedIdentityAndNullPolicyIsConcrete() {
        Multiset<String> hashed = HashMultiset.create();
        hashed.add(null);
        assertEquals(1, hashed.count(null));
        TreeMultiset<String> sorted = TreeMultiset.create(String.CASE_INSENSITIVE_ORDER);
        sorted.add("SKU");
        sorted.add("sku");
        assertEquals(2, sorted.count("SkU"));
        assertEquals(1, sorted.elementSet().size());
        assertThrows(NullPointerException.class, () -> TreeMultiset.<String>create().add(null));
    }
}
