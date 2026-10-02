package blog.libraries;

import com.google.common.io.ByteSource;
import com.google.common.io.ByteStreams;
import com.google.common.io.CharSource;
import com.google.common.math.IntMath;
import com.google.common.primitives.Ints;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.Reader;
import java.io.StringReader;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Extension02Test {
    @Test void arrayViewAndNumericPolicy() {
        int[] raw = {1, 2, 3};
        List<Integer> view = Ints.asList(raw);
        raw[0] = 10; assertEquals(Integer.valueOf(10), view.get(0));
        view.set(1, 20); assertEquals(20, raw[1]);
        assertThrows(UnsupportedOperationException.class, () -> view.add(4));
        int[] copy = Ints.toArray(view); copy[0] = 99; assertEquals(10, raw[0]);
        assertThrows(IllegalArgumentException.class, () -> Ints.checkedCast(2147483648L));
        assertEquals(Integer.MAX_VALUE, Ints.saturatedCast(2147483648L));
        assertThrows(ArithmeticException.class, () -> IntMath.checkedAdd(Integer.MAX_VALUE, 1));
        assertThrows(ArithmeticException.class, () -> Math.addExact(Integer.MAX_VALUE, 1));
        assertEquals(-2, IntMath.divide(-7, 3, RoundingMode.DOWN));
        assertEquals(-3, IntMath.divide(-7, 3, RoundingMode.FLOOR));
        assertEquals(2, IntMath.divide(5, 2, RoundingMode.HALF_EVEN));
        assertEquals(4, IntMath.divide(7, 2, RoundingMode.HALF_EVEN));
        assertThrows(ArithmeticException.class, () -> IntMath.divide(7, 3, RoundingMode.UNNECESSARY));
        System.out.println("E02 view bidirectional; overflow rejected; -7/3 DOWN=-2 FLOOR=-3 HALF_EVEN 5/2=2 7/2=4");
    }

    static final class ShortInput extends ByteArrayInputStream {
        boolean closed;
        ShortInput(byte[] bytes) { super(bytes); }
        @Override public synchronized int read(byte[] b, int off, int len) {
            return super.read(b, off, Math.min(1, len));
        }
        @Override public void close() throws IOException { closed = true; super.close(); }
    }

    @Test void byteSourceOwnsOpenedStreamButByteStreamsDoesNot() throws Exception {
        byte[] bytes = "商品".getBytes(StandardCharsets.UTF_8);
        ShortInput borrowed = new ShortInput(bytes);
        assertArrayEquals(bytes, ByteStreams.toByteArray(borrowed));
        assertFalse(borrowed.closed); borrowed.close();
        AtomicInteger opens = new AtomicInteger();
        ShortInput[] latest = new ShortInput[1];
        ByteSource source = new ByteSource() {
            @Override public InputStream openStream() {
                opens.incrementAndGet(); latest[0] = new ShortInput(bytes); return latest[0];
            }
        };
        assertArrayEquals(bytes, source.read()); assertTrue(latest[0].closed);
        assertEquals("商品", source.asCharSource(StandardCharsets.UTF_8).read());
        assertTrue(latest[0].closed); assertEquals(2, opens.get());
        InputStream openedByCaller = source.openStream();
        assertFalse(latest[0].closed); openedByCaller.close(); assertTrue(latest[0].closed);
        System.out.println("E02 short reads reconstructed UTF8; source closes internal streams, caller closes explicit openStream");
    }

    @Test void charSourceClosesOnSuccessAndReadFailure() throws Exception {
        AtomicInteger closes = new AtomicInteger();
        CharSource source = new CharSource() {
            @Override public Reader openStream() {
                return new StringReader("商品\n价格") {
                    @Override public int read(char[] b, int off, int len) throws IOException {
                        return super.read(b, off, Math.min(1, len));
                    }
                    @Override public void close() { closes.incrementAndGet(); super.close(); }
                };
            }
        };
        assertEquals("商品\n价格", source.read()); assertEquals(1, closes.get());
        CharSource failing = new CharSource() {
            @Override public Reader openStream() {
                return new Reader() {
                    @Override public int read(char[] b, int o, int l) throws IOException {
                        throw new IOException("injected read failure");
                    }
                    @Override public void close() { closes.incrementAndGet(); }
                };
            }
        };
        IOException failure = assertThrows(IOException.class, failing::read);
        assertEquals("injected read failure", failure.getMessage());
        assertEquals(2, closes.get());
        System.out.println("E02 CharSource closes=2 across success and failure");
    }
}
