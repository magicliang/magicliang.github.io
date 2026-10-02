package blog.libraries;

import com.google.common.base.Preconditions;
import com.google.common.base.Verify;
import com.google.common.base.VerifyException;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter05Test {
    @Test void failuresIdentifyDifferentContracts() {
        assertEquals("quantity=-1", assertThrows(IllegalArgumentException.class,
                () -> Preconditions.checkArgument(false, "quantity=%s", -1)).getMessage());
        assertEquals("catalog closed", assertThrows(IllegalStateException.class,
                () -> Preconditions.checkState(false, "catalog closed")).getMessage());
        assertEquals("index mismatch: A", assertThrows(VerifyException.class,
                () -> Verify.verify(false, "index mismatch: %s", "A")).getMessage());
        assertEquals("merchant", assertThrows(NullPointerException.class,
                () -> Preconditions.checkNotNull(null, "merchant")).getMessage());
        assertEquals("merchant", assertThrows(NullPointerException.class,
                () -> Objects.requireNonNull(null, "merchant")).getMessage());
        assertThrows(VerifyException.class, () -> Verify.verifyNotNull(null, "index"));
        Object value = new Object();
        assertSame(value, Preconditions.checkNotNull(value));
        assertSame(value, Objects.requireNonNull(value));
        System.out.println("05 failures: argument=IAE state=ISE assumption=VerifyException null=NPE");
    }
    @Test void argumentsAreEagerButSupplierBodiesCanBeLazy() {
        AtomicInteger count = new AtomicInteger();
        Preconditions.checkArgument(true, "cost=%s", count.incrementAndGet());
        assertEquals(1, count.get());
        Object value = new Object();
        Objects.requireNonNull(value, () -> "cost=" + count.incrementAndGet());
        assertEquals(1, count.get());
        assertEquals("cost=2", assertThrows(NullPointerException.class,
                () -> Objects.requireNonNull(null, () -> "cost=" + count.incrementAndGet())).getMessage());
        assertEquals(2, count.get());
        assertThrows(IllegalStateException.class,
                () -> Preconditions.checkArgument(true, "cost=%s", failingMessage()));
        System.out.println("05 evaluation: successful Guava check evaluates argument; JDK message supplier delayed");
    }
    static String failingMessage() { throw new IllegalStateException("message failure"); }
    @Test void messageFormattingIsNotPrintf() {
        assertEquals("bad %d: A [7]", assertThrows(IllegalArgumentException.class,
                () -> Preconditions.checkArgument(false, "bad %d: %s", "A", 7)).getMessage());
        Preconditions.checkArgument(true, "valid");
        Verify.verify(true, "valid");
        System.out.println("05 formatting: %s substituted; %d literal; surplus appended");
    }
}
