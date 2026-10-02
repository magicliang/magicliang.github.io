package blog.libraries;

import blog.libraries.io.BoundedIo;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.ByteBuffer;
import org.apache.commons.io.IOUtils;
import org.apache.commons.io.FileUtils;
import org.apache.commons.io.input.BOMInputStream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class Chapter25Test {
    @TempDir java.nio.file.Path temp;
    static final class ShortInput extends ByteArrayInputStream {
        boolean closed;
        ShortInput(byte[] data) { super(data); }
        @Override
        public synchronized int read(byte[] bytes, int offset, int length) {
            return super.read(bytes, offset, Math.min(length, 1));
        }
        @Override
        public void close() throws IOException { closed = true; super.close(); }
    }

    @Test
    void shortReadIsNotEndOfInputAndCopyDoesNotOwnStreams() throws Exception {
        ShortInput input = new ShortInput("商品".getBytes(StandardCharsets.UTF_8));
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        assertEquals(6, IOUtils.copy(input, output));
        assertEquals("商品", output.toString("UTF-8"));
        assertFalse(input.closed);
        input.close();
        assertTrue(input.closed);
    }

    @Test
    void bomIsRemovedBeforeExplicitUtf8Decoding() throws Exception {
        byte[] bytes = {(byte) 0xef, (byte) 0xbb, (byte) 0xbf, 's', 'k', 'u'};
        assertTrue(new String(bytes, StandardCharsets.UTF_8).startsWith("\ufeff"));
        ShortInput source = new ShortInput(bytes);
        try (BOMInputStream input = BOMInputStream.builder().setInputStream(source).get()) {
            assertTrue(input.hasBOM());
            assertEquals("sku", IOUtils.toString(input, StandardCharsets.UTF_8));
        }
        assertTrue(source.closed);
        assertThrows(CharacterCodingException.class, () -> StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(new byte[] {(byte) 0xc3, 0x28})));
    }

    @Test
    void budgetUsesActualReadsAndKeepsOutputWithinLimit() throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        assertThrows(IOException.class, () -> BoundedIo.copy(new ShortInput(new byte[6]), output, 5));
        assertEquals(5, output.size());
        assertEquals(5, BoundedIo.copy(new ShortInput(new byte[5]), new ByteArrayOutputStream(), 5));
        assertEquals(0, BoundedIo.copy(new ByteArrayInputStream(new byte[0]), new ByteArrayOutputStream(), 0));
        assertThrows(IOException.class, () -> BoundedIo.copy(new ByteArrayInputStream(new byte[1]),
                new ByteArrayOutputStream(), 10, System.nanoTime() - 100, 1));
        System.out.println("25 bounded copy: six bytes at budget five -> reject, written=5");
    }

    @Test
    void fileUtilityOwnsInputWhileStreamCopyDoesNot() throws Exception {
        ShortInput owned = new ShortInput(new byte[] {1, 2});
        java.nio.file.Path file = temp.resolve("copied.bin");
        FileUtils.copyInputStreamToFile(owned, file.toFile());
        assertTrue(owned.closed);
        assertArrayEquals(new byte[] {1, 2}, java.nio.file.Files.readAllBytes(file));
        ShortInput borrowed = new ShortInput(new byte[] {3});
        FileUtils.copyToFile(borrowed, temp.resolve("borrowed.bin").toFile());
        assertFalse(borrowed.closed);
        borrowed.close();
    }

    @Test
    void readFailureIsNotReportedAsSuccessfulPartialCopy() throws Exception {
        final boolean[] closed = {false};
        InputStream broken = new InputStream() {
            int reads;
            @Override public int read() throws IOException {
                if (reads++ == 2) { throw new IOException("synthetic read failure"); }
                return 65;
            }
            @Override public void close() { closed[0] = true; }
        };
        try (InputStream owned = broken) {
            assertThrows(IOException.class, () -> BoundedIo.copy(owned, new ByteArrayOutputStream(), 10));
        }
        assertTrue(closed[0]);
    }
}
