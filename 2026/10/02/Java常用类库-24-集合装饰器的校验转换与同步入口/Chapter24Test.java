package blog.libraries;
import org.apache.commons.collections4.collection.PredicatedCollection;
import org.apache.commons.collections4.collection.TransformedCollection;
import org.apache.commons.collections4.collection.SynchronizedCollection;
import org.apache.commons.collections4.ListUtils;
import com.google.common.collect.Lists;
import org.junit.jupiter.api.Test;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Iterator;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import static org.junit.jupiter.api.Assertions.*;
public class Chapter24Test {
    @Test void predicateOnlyProtectsTheDecoratedEntrance() {
        List<String> source = new ArrayList<>();
        Collection<String> checked = PredicatedCollection.predicatedCollection(source, s -> s != null && !s.isEmpty());
        assertThrows(IllegalArgumentException.class, () -> checked.add(""));
        source.add(""); assertTrue(checked.contains(""));
        assertThrows(IllegalArgumentException.class, () -> PredicatedCollection.predicatedCollection(source, s -> !s.isEmpty()));
    }
    @Test void transformingDoesNotTransformExistingButTransformedDoes() {
        AtomicInteger calls = new AtomicInteger();
        List<String> source = new ArrayList<>(Arrays.asList(" a "));
        Collection<String> onWrite = TransformedCollection.transformingCollection(source, s -> { calls.incrementAndGet(); return s.trim(); });
        assertEquals(0, calls.get());
        onWrite.add(" b "); assertEquals(1, calls.get());
        assertEquals(Arrays.asList(" a ", "b"), source);
        assertFalse(onWrite.contains(" b ")); assertTrue(onWrite.contains("b"));
        onWrite.iterator().next(); onWrite.iterator().next(); assertEquals(1, calls.get());
        TransformedCollection.transformedCollection(source, s -> { calls.incrementAndGet(); return s.trim(); });
        assertEquals(Arrays.asList("a", "b"), source); assertEquals(3, calls.get());
    }
    @Test void lazyReadAndPartitionRemainViews() {
        AtomicInteger calls = new AtomicInteger();
        List<String> source = new ArrayList<>(Arrays.asList(" a ", " b ", " c "));
        List<String> lazy = Lists.transform(source, s -> { calls.incrementAndGet(); return s.trim(); });
        assertEquals("a", lazy.get(0)); assertEquals("a", lazy.get(0)); assertEquals(2, calls.get());
        List<List<String>> parts = ListUtils.partition(source, 2);
        source.set(0, "changed"); assertEquals("changed", parts.get(0).get(0));
        assertThrows(UnsupportedOperationException.class, () -> parts.add(new ArrayList<>()));
        parts.get(0).set(0, "via-part"); assertEquals("via-part", source.get(0));
    }
    static final class LockCheckingList extends ArrayList<String> {
        Object expectedLock;
        boolean addLocked;
        boolean iteratorLocked;
        @Override public boolean add(String value) { addLocked = Thread.holdsLock(expectedLock); return super.add(value); }
        @Override public Iterator<String> iterator() { iteratorLocked = Thread.holdsLock(expectedLock); return super.iterator(); }
    }
    @Test void synchronizedDecoratorDoesNotLockIteratorAutomatically() {
        LockCheckingList source = new LockCheckingList();
        Collection<String> guarded = SynchronizedCollection.synchronizedCollection(source);
        source.expectedLock = guarded;
        guarded.add("A"); assertTrue(source.addLocked);
        guarded.iterator(); assertFalse(source.iteratorLocked);
        synchronized (guarded) { for (String value : guarded) { assertEquals("A", value); } }
        assertTrue(source.iteratorLocked);
        source.add("B"); assertFalse(source.addLocked);
    }
}
