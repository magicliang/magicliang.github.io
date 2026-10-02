package blog.libraries;

import io.vavr.Lazy;
import io.vavr.collection.List;
import io.vavr.control.Option;
import io.vavr.control.Try;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Extension06Test {
    @Test void nullableMappingAndAdaptersChangeRepresentation() {
        Option<String> value = Option.of("sku").map(s -> (String) null);
        assertTrue(value.isDefined()); assertNull(value.get());
        assertFalse(Optional.of("sku").map(s -> (String) null).isPresent());
        assertTrue(value.toJavaOptional().equals(Optional.empty()));
        assertTrue(Option.of(null).isEmpty());
        assertTrue(value.flatMap(Option::of).isEmpty());
        com.google.common.base.Optional<String> guava =
                com.google.common.base.Optional.fromJavaUtil(value.toJavaOptional());
        assertFalse(guava.isPresent());
        System.out.println("E06 Some(null) defined=true -> JDK empty -> Guava absent");
    }

    @Test void tryCapturesOrdinaryFailureButRethrowsFatalClasses() {
        Try<Integer> bad = Try.of(() -> Integer.parseInt("bad"));
        assertTrue(bad.isFailure()); assertTrue(bad.getCause() instanceof NumberFormatException);
        assertEquals(Integer.valueOf(0), bad.recover(NumberFormatException.class, e -> 0).get());
        assertTrue(bad.toOption().isEmpty());
        AssertionError assertion = new AssertionError("assertion");
        assertSame(assertion, Try.of(() -> { throw assertion; }).getCause());
        LinkageError linkage = new LinkageError("synthetic linkage");
        assertSame(linkage, assertThrows(LinkageError.class, () -> Try.of(() -> { throw linkage; })));
        InterruptedException interrupted = new InterruptedException("synthetic interrupt");
        assertSame(interrupted, assertThrows(InterruptedException.class,
                () -> Try.of(() -> { throw interrupted; })));
        System.out.println("E06 Try captured NumberFormatException/AssertionError; rethrew LinkageError/InterruptedException");
    }

    @Test void persistentStructureSharesTailButNotDeepImmutability() {
        StringBuilder mutable = new StringBuilder("old");
        List<StringBuilder> old = List.of(mutable);
        List<StringBuilder> next = old.prepend(new StringBuilder("new"));
        assertSame(old, next.tail()); assertEquals(1, old.size()); assertEquals(2, next.size());
        mutable.append("!");
        assertEquals("old!", old.head().toString());
        assertEquals("old!", next.tail().head().toString());
        AtomicInteger calls = new AtomicInteger();
        Lazy<Integer> lazy = Lazy.of(calls::incrementAndGet);
        assertEquals(0, calls.get()); assertEquals(Integer.valueOf(1), lazy.get());
        assertEquals(Integer.valueOf(1), lazy.get()); assertEquals(1, calls.get());
        System.out.println("E06 prepend tail identity=true, shared mutable element=old!, Lazy successful supplier calls=1");
    }
}
