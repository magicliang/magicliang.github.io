package blog.libraries;

import it.unimi.dsi.fastutil.ints.Int2IntMap;
import it.unimi.dsi.fastutil.ints.Int2IntOpenHashMap;
import it.unimi.dsi.fastutil.ints.Int2ObjectOpenHashMap;
import it.unimi.dsi.fastutil.objects.ObjectIterator;
import java.util.HashMap;
import java.util.Map;
import org.eclipse.collections.impl.map.mutable.primitive.IntIntHashMap;
import org.eclipse.collections.impl.map.mutable.primitive.IntObjectHashMap;
import org.junit.jupiter.api.Test;
import org.openjdk.jol.info.GraphLayout;
import org.openjdk.jol.vm.VM;
import static org.junit.jupiter.api.Assertions.*;

class Extension03Test {
    @Test
    void absenceMustNotBeInferredFromZeroOrNull() {
        Map<Integer, Integer> boxed = new HashMap<>();
        boxed.put(1, null);
        assertNull(boxed.get(1));
        assertNull(boxed.get(2));
        assertTrue(boxed.containsKey(1));
        assertFalse(boxed.containsKey(2));
        Int2IntOpenHashMap fast = new Int2IntOpenHashMap();
        fast.put(1, 0);
        assertEquals(0, fast.get(1));
        assertEquals(0, fast.get(2));
        assertTrue(fast.containsKey(1));
        assertFalse(fast.containsKey(2));
        fast.defaultReturnValue(-1);
        fast.put(3, -1);
        assertEquals(-1, fast.get(2));
        assertEquals(-1, fast.get(3));
        assertTrue(fast.containsKey(3));
        IntIntHashMap eclipse = new IntIntHashMap();
        eclipse.put(1, 0);
        assertEquals(0, eclipse.get(2));
        assertEquals(-1, eclipse.getIfAbsent(2, -1));
        assertEquals(0, eclipse.getIfAbsent(1, -1));
    }

    @Test
    void sameInputsHaveEqualIterationChecksumsButDifferentProtocols() {
        Map<Integer, Integer> boxed = new HashMap<>();
        Int2IntOpenHashMap fast = new Int2IntOpenHashMap();
        IntIntHashMap eclipse = new IntIntHashMap();
        long expected = 0;
        for (int i = 1000; i < 2024; i++) {
            boxed.put(i, i * 3); fast.put(i, i * 3); eclipse.put(i, i * 3);
            expected += i + i * 3L;
        }
        long jdkSum = 0;
        for (Map.Entry<Integer, Integer> entry : boxed.entrySet()) { jdkSum += entry.getKey() + entry.getValue(); }
        long fastSum = 0;
        ObjectIterator<Int2IntMap.Entry> iterator = fast.int2IntEntrySet().fastIterator();
        while (iterator.hasNext()) { Int2IntMap.Entry entry = iterator.next(); fastSum += entry.getIntKey() + entry.getIntValue(); }
        final long[] eclipseSum = {0};
        eclipse.forEachKeyValue((key, value) -> eclipseSum[0] += key + value);
        assertEquals(expected, jdkSum); assertEquals(expected, fastSum); assertEquals(expected, eclipseSum[0]);
        assertEquals(1024, boxed.size()); assertEquals(1024, fast.size()); assertEquals(1024, eclipse.size());
        System.out.println("E03 equal iteration checksum=" + expected);
    }

    @Test
    void objectGraphLayoutEstimateIsNotRetainedHeapOrAllocationRate() {
        Map<Integer, Integer> boxed = new HashMap<>();
        Int2ObjectOpenHashMap<Integer> fast = new Int2ObjectOpenHashMap<>();
        IntObjectHashMap<Integer> eclipse = new IntObjectHashMap<>();
        for (int i = 1000; i < 2024; i++) { Integer value = i * 3; boxed.put(i, value); fast.put(i, value); eclipse.put(i, value); }
        System.out.println("E03 JOL LAYOUT ESTIMATE ONLY; NOT GC retained heap or B/op");
        System.out.println(VM.current().details());
        Object[] maps = {boxed, fast, eclipse};
        for (Object map : maps) {
            GraphLayout layout = GraphLayout.parseInstance(map);
            assertTrue(layout.totalSize() > 0);
            System.out.println(map.getClass().getName() + " estimated graph bytes=" + layout.totalSize());
            System.out.println(layout.toFootprint());
        }
    }
}
