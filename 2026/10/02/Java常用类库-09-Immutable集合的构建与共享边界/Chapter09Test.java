package blog.libraries;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.ImmutableMap;
import org.junit.jupiter.api.Test;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import static org.junit.jupiter.api.Assertions.*;

public class Chapter09Test {
    @Test void nullDuplicatesAndOrder() {
        assertThrows(NullPointerException.class, () -> ImmutableList.copyOf(Arrays.asList("A", null)));
        assertThrows(NullPointerException.class, () -> ImmutableSet.copyOf(Arrays.asList("A", null)));
        assertThrows(NullPointerException.class, () -> ImmutableMap.of("A", (String) null));
        assertEquals(Arrays.asList("B", "A", "B"), ImmutableList.of("B", "A", "B"));
        assertEquals(Arrays.asList("B", "A"), ImmutableSet.of("B", "A", "B").asList());
        ImmutableMap.Builder<String, Integer> duplicate = ImmutableMap.<String, Integer>builder().put("B", 1).put("A", 2).put("B", 3);
        assertThrows(IllegalArgumentException.class, duplicate::buildOrThrow);
        assertEquals(Integer.valueOf(3), duplicate.buildKeepingLast().get("B"));
        assertEquals(Arrays.asList("B", "A"), ImmutableMap.of("B", 1, "A", 2).keySet().asList());
    }
    @Test void buildersAccumulateWithoutChangingEarlierProducts() {
        ImmutableList.Builder<String> list = ImmutableList.builder();
        ImmutableList<String> first = list.add("A").build();
        assertEquals(Arrays.asList("A", "B"), list.add("B").build());
        assertEquals(Collections.singletonList("A"), first);
        ImmutableSet.Builder<String> set = ImmutableSet.builder();
        ImmutableSet<String> firstSet = set.add("A").build();
        assertEquals(ImmutableSet.of("A", "B"), set.add("B", "A").build());
        assertEquals(ImmutableSet.of("A"), firstSet);
        ImmutableMap.Builder<String, Integer> map = ImmutableMap.builder();
        ImmutableMap<String, Integer> firstMap = map.put("A", 1).buildOrThrow();
        assertEquals(2, map.put("B", 2).buildOrThrow().size());
        assertEquals(ImmutableMap.of("A", 1), firstMap);
    }
    @Test void snapshotsIsolateStructureOnly() {
        StringBuilder item = new StringBuilder("A");
        List<StringBuilder> source = new ArrayList<>(Collections.singletonList(item));
        List<StringBuilder> view = Collections.unmodifiableList(source);
        ImmutableList<StringBuilder> frozen = ImmutableList.copyOf(source);
        source.add(new StringBuilder("B"));
        assertEquals(2, view.size());
        assertEquals(1, frozen.size());
        item.append("2");
        assertEquals("A2", frozen.get(0).toString());
        assertThrows(UnsupportedOperationException.class, () -> frozen.add(item));
    }
    @Test void concurrentElementMutationRemainsObservableWithSynchronization() throws Exception {
        AtomicReference<String> item = new AtomicReference<>("old");
        ImmutableList<AtomicReference<String>> frozen = ImmutableList.of(item);
        CountDownLatch changed = new CountDownLatch(1);
        Thread writer = new Thread(() -> { item.set("new"); changed.countDown(); });
        writer.start();
        try {
            assertTrue(changed.await(5, TimeUnit.SECONDS));
            assertEquals("new", frozen.get(0).get());
        } finally {
            writer.join(5000);
        }
        assertFalse(writer.isAlive());
    }
}
