package blog.libraries;

import com.google.common.base.Optional;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.NotSerializableException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter06Test {
    @Test void presenceAndNullMappingDoNotHaveTheSameContract() {
        assertFalse(Optional.fromNullable(null).isPresent());
        assertFalse(java.util.Optional.ofNullable(null).isPresent());
        assertThrows(IllegalStateException.class, () -> Optional.absent().get());
        assertThrows(java.util.NoSuchElementException.class, () -> java.util.Optional.empty().get());
        assertThrows(NullPointerException.class, () -> Optional.of("SKU-1").transform(x -> null));
        assertFalse(java.util.Optional.of("SKU-1").map(x -> null).isPresent());
        AtomicInteger calls = new AtomicInteger();
        assertFalse(Optional.<String>absent().transform(x -> calls.incrementAndGet()).isPresent());
        assertFalse(java.util.Optional.<String>empty().map(x -> calls.incrementAndGet()).isPresent());
        assertEquals(0, calls.get());
        System.out.println("06 mapping: Guava null-result=NPE JDK=null-to-empty; absent mappers not called");
    }
    @Test void defaultsAndConversionsNeedExplicitNullPolicy() {
        AtomicInteger calls = new AtomicInteger();
        assertEquals("present", Optional.of("present").or("fallback" + calls.incrementAndGet()));
        assertEquals("present", java.util.Optional.of("present").orElse("fallback" + calls.incrementAndGet()));
        assertEquals(2, calls.get());
        assertEquals("present", Optional.of("present").or(() -> "fallback" + calls.incrementAndGet()));
        assertEquals("present", java.util.Optional.of("present").orElseGet(() -> "fallback" + calls.incrementAndGet()));
        assertEquals(2, calls.get());
        assertThrows(NullPointerException.class, () -> Optional.of("present").or((String) null));
        assertEquals("present", java.util.Optional.of("present").orElse(null));
        assertThrows(NullPointerException.class, () -> Optional.<String>absent().or(() -> null));
        assertNull(java.util.Optional.<String>empty().orElseGet(() -> null));
        assertEquals(java.util.Optional.of("SKU-1"), Optional.of("SKU-1").toJavaUtil());
        assertEquals(Optional.absent(), Optional.fromJavaUtil(java.util.Optional.empty()));
        assertNull(Optional.fromJavaUtil(null));
        assertNull(Optional.toJavaUtil(null));
        System.out.println("06 fallback: eager=2 supplier-present=0; static conversions preserve null reference");
    }
    @Test void oldFunctionInterfacesAdaptInOneDirection() {
        com.google.common.base.Function<String, Integer> oldFunction = String::length;
        java.util.function.Function<String, Integer> modernFunction = oldFunction;
        assertEquals(5, modernFunction.apply("SKU-1"));
        java.util.function.Function<String, Integer> modernOnly = String::length;
        com.google.common.base.Function<String, Integer> adapted = modernOnly::apply;
        assertEquals(5, adapted.apply("SKU-1"));
        com.google.common.base.Predicate<String> oldPredicate = s -> s.startsWith("SKU-");
        java.util.function.Predicate<String> modernPredicate = oldPredicate;
        assertTrue(modernPredicate.test("SKU-1"));
        assertFalse(Optional.class.equals(java.util.Optional.class));
        System.out.println("06 interfaces: Guava Function/Predicate extend JDK interfaces; reverse adapter explicit");
    }
    @Test void serializationIsAnObjectGraphContract() throws Exception {
        assertEquals(Optional.of("SKU-1"), roundTrip(Optional.of("SKU-1")));
        assertEquals(Optional.absent(), roundTrip(Optional.absent()));
        assertThrows(NotSerializableException.class, () -> roundTrip(java.util.Optional.of("SKU-1")));
        assertThrows(NotSerializableException.class, () -> roundTrip(Optional.of(new Object())));
        System.out.println("06 serialization: Guava<String>/absent PASS; JDK Optional and nonserializable payload fail");
    }
    static Object roundTrip(Object value) throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (ObjectOutputStream output = new ObjectOutputStream(bytes)) { output.writeObject(value); }
        try (ObjectInputStream input = new ObjectInputStream(new ByteArrayInputStream(bytes.toByteArray()))) {
            return input.readObject();
        }
    }
}
