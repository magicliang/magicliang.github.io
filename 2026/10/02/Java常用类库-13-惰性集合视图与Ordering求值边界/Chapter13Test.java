package blog.libraries;

import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Ordering;
import com.google.common.collect.Sets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter13Test {
    @Test
    void transformedMapRecomputesOnAccessButSnapshotDoesNot() {
        Map<String, Integer> source = new LinkedHashMap<>();
        source.put("sku-a", 10);
        source.put("sku-b", 20);
        AtomicInteger calls = new AtomicInteger();
        Map<String, Integer> view = Maps.transformValues(source, price -> {
            calls.incrementAndGet();
            return price * 100;
        });
        assertEquals(0, calls.get());
        assertEquals(2, view.size());
        assertTrue(view.containsKey("sku-a"));
        assertEquals(0, calls.get());
        assertEquals(Integer.valueOf(1000), view.get("sku-a"));
        assertEquals(Integer.valueOf(1000), view.get("sku-a"));
        assertEquals(2, calls.get());
        view.values().forEach(value -> assertNotNull(value));
        view.values().forEach(value -> assertNotNull(value));
        assertEquals(6, calls.get());
        Map<String, Integer> snapshot = new LinkedHashMap<>(view);
        assertEquals(8, calls.get());
        source.put("sku-a", 30);
        assertEquals(Integer.valueOf(3000), view.get("sku-a"));
        assertEquals(Integer.valueOf(1000), snapshot.get("sku-a"));
        assertEquals(9, calls.get());
        assertThrows(UnsupportedOperationException.class, () -> view.put("sku-c", 300));
        view.remove("sku-b");
        assertFalse(source.containsKey("sku-b"));
        System.out.println("13 map calls: create=0 metadata=0 twiceGet=2 twiceTraverse=6 copy=8 changedGet=9");
    }

    @Test
    void iterableRepeatsWorkButCollectedStreamFreezesMembership() {
        List<Integer> source = new ArrayList<>(Arrays.asList(1, 2));
        AtomicInteger calls = new AtomicInteger();
        Iterable<Integer> transformed = Iterables.transform(source, value -> {
            calls.incrementAndGet();
            return value * 10;
        });
        assertEquals(0, calls.get());
        assertEquals(Arrays.asList(10, 20), Lists.newArrayList(transformed));
        assertEquals(Arrays.asList(10, 20), Lists.newArrayList(transformed));
        assertEquals(4, calls.get());
        List<Integer> snapshot = source.stream().map(value -> value * 10).collect(Collectors.toList());
        source.add(3);
        assertEquals(Arrays.asList(10, 20, 30), Lists.newArrayList(transformed));
        assertEquals(7, calls.get());
        assertEquals(Arrays.asList(10, 20), snapshot);
    }

    @Test
    void partitionAndSetOperationsShareSourceMembership() {
        List<Integer> source = new ArrayList<>(Arrays.asList(1, 2, 3));
        List<List<Integer>> partitions = Lists.partition(source, 2);
        assertEquals(Arrays.asList(1, 2), partitions.get(0));
        partitions.get(0).set(0, 9);
        assertEquals(Integer.valueOf(9), source.get(0));
        source.add(4);
        assertEquals(Arrays.asList(3, 4), partitions.get(1));
        assertThrows(UnsupportedOperationException.class, () -> partitions.add(new ArrayList<>()));
        assertThrows(IllegalArgumentException.class, () -> Lists.partition(source, 0));
        Set<String> left = new HashSet<>(Arrays.asList("sale", "new"));
        Set<String> right = new HashSet<>(Arrays.asList("sale"));
        Set<String> difference = Sets.difference(left, right);
        assertEquals(new HashSet<>(Arrays.asList("new")), difference);
        right.add("new");
        assertTrue(difference.isEmpty());
        assertThrows(UnsupportedOperationException.class, () -> difference.add("other"));
    }

    @Test
    void nullPlacementAndReverseOrderHaveDifferentComposition() {
        List<Integer> input = Arrays.asList(2, null, 1);
        List<Integer> first = Ordering.<Integer>natural().nullsFirst().reverse().sortedCopy(input);
        List<Integer> second = Ordering.<Integer>natural().reverse().nullsFirst().sortedCopy(input);
        assertEquals(Arrays.asList(2, 1, null), first);
        assertEquals(Arrays.asList(null, 2, 1), second);
        assertEquals(Arrays.asList(2, null, 1), input);
        assertThrows(NullPointerException.class, () -> Ordering.<Integer>natural().sortedCopy(input));
        System.out.println("13 ordering: nullsFirst.reverse=[2,1,null]; reverse.nullsFirst=[null,2,1]");
    }
}
