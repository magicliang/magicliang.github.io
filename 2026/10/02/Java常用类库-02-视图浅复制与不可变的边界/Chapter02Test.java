package blog.libraries;

import com.google.common.collect.ImmutableList;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter02Test {
    static final class Item {
        String name;
        Item(String name) { this.name = name; }
    }

    @Test void sourceEditsReachViewButNotCopies() {
        Item first = new Item("A");
        List<Item> source = new ArrayList<>(Arrays.asList(first));
        List<Item> view = Collections.unmodifiableList(source);
        List<Item> copy = new ArrayList<>(source);
        ImmutableList<Item> frozen = ImmutableList.copyOf(source);
        source.add(new Item("B"));
        assertEquals(2, view.size());
        assertEquals(1, copy.size());
        assertEquals(1, frozen.size());
        Item replacement = new Item("C");
        source.set(0, replacement);
        assertSame(replacement, view.get(0));
        assertSame(first, copy.get(0));
        assertSame(first, frozen.get(0));
        source.remove(0);
        assertEquals("B", view.get(0).name);
        assertSame(first, copy.get(0));
        assertSame(first, frozen.get(0));
    }

    @Test void allContainersShareMutableElement() {
        Item item = new Item("before");
        List<Item> source = new ArrayList<>(Arrays.asList(item));
        List<Item> view = Collections.unmodifiableList(source);
        List<Item> copy = new ArrayList<>(source);
        ImmutableList<Item> frozen = ImmutableList.copyOf(source);
        item.name = "after";
        assertEquals("after", view.get(0).name);
        assertEquals("after", copy.get(0).name);
        assertEquals("after", frozen.get(0).name);
        frozen.get(0).name = "through-frozen";
        assertEquals("through-frozen", source.get(0).name);
    }

    @Test void unsupportedWritesAndMutableCopy() {
        List<String> source = new ArrayList<>(Arrays.asList("A", "B"));
        List<String> view = Collections.unmodifiableList(source);
        List<String> copy = new ArrayList<>(source);
        List<String> frozen = ImmutableList.copyOf(source);
        for (List<String> list : Arrays.asList(view, frozen)) {
            assertThrows(UnsupportedOperationException.class, () -> list.add("C"));
            assertThrows(UnsupportedOperationException.class, () -> list.set(0, "C"));
            assertThrows(UnsupportedOperationException.class, () -> list.remove(0));
        }
        copy.set(0, "C");
        assertEquals("A", source.get(0));
        assertEquals("C", copy.get(0));
    }

    @Test void nullPolicyDiffers() {
        List<String> source = new ArrayList<>(Arrays.asList("A", null));
        assertNull(Collections.unmodifiableList(source).get(1));
        assertNull(new ArrayList<>(source).get(1));
        assertThrows(NullPointerException.class, () -> ImmutableList.copyOf(source));
    }

    @Test void immutableReuseIsVersionSpecificObservation() {
        ImmutableList<String> original = ImmutableList.of("A", "B", "C");
        ImmutableList<String> result = ImmutableList.copyOf(original);
        assertEquals(original, result);
        System.out.println("CH02 fullImmutableReused=" + (original == result));
        ImmutableList<String> subList = original.subList(0, 2);
        ImmutableList<String> subCopy = ImmutableList.copyOf(subList);
        assertEquals(Arrays.asList("A", "B"), subCopy);
        System.out.println("CH02 partialImmutableReused=" + (subList == subCopy));
    }

    @Test void modernJdkCopyOfIndependentComparison() throws Exception {
        Method copyOf;
        try {
            copyOf = List.class.getMethod("copyOf", Collection.class);
        } catch (NoSuchMethodException absentOnJava8) {
            System.out.println("CH02 modernListCopyOf=NOT_APPLICABLE API requires Java 10+");
            return;
        }
        Item item = new Item("before");
        List<Item> source = new ArrayList<>(Arrays.asList(item));
        @SuppressWarnings("unchecked")
        List<Item> modern = (List<Item>) copyOf.invoke(null, source);
        source.clear();
        assertEquals(1, modern.size());
        assertSame(item, modern.get(0));
        item.name = "after";
        assertEquals("after", modern.get(0).name);
        assertThrows(UnsupportedOperationException.class,
                () -> modern.add(new Item("B")));
        InvocationTargetException thrown = assertThrows(InvocationTargetException.class,
                () -> copyOf.invoke(null, Arrays.asList(item, null)));
        assertInstanceOf(NullPointerException.class, thrown.getCause());
        System.out.println("CH02 modernListCopyOf=PASS isolatedContainer/sharedElement/rejectWrite/rejectNull");
    }

}
