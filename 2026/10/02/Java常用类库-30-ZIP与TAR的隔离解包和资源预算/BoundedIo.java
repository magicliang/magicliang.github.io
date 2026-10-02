package blog.libraries.io;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Objects;

public final class BoundedIo {
    private BoundedIo() { }

    public static long copy(InputStream input, OutputStream output, long maxBytes) throws IOException {
        return copy(input, output, maxBytes, System.nanoTime(), Long.MAX_VALUE);
    }

    public static long copy(InputStream input, OutputStream output, long maxBytes,
                            long startedNanos, long maxNanos) throws IOException {
        Objects.requireNonNull(input, "input");
        Objects.requireNonNull(output, "output");
        if (maxBytes < 0 || maxNanos <= 0) {
            throw new IllegalArgumentException("invalid budget");
        }
        byte[] buffer = new byte[8192];
        long copied = 0;
        while (true) {
            checkTime(startedNanos, maxNanos);
            int requested = (int) Math.min(buffer.length, maxBytes - copied + (maxBytes == Long.MAX_VALUE ? 0 : 1));
            int count = input.read(buffer, 0, Math.max(1, requested));
            checkTime(startedNanos, maxNanos);
            if (count == -1) {
                return copied;
            }
            if (count == 0) {
                int value = input.read();
                checkTime(startedNanos, maxNanos);
                if (value == -1) {
                    return copied;
                }
                buffer[0] = (byte) value;
                count = 1;
            }
            if (count > maxBytes - copied) {
                throw new IOException("byte budget exceeded");
            }
            output.write(buffer, 0, count);
            copied += count;
        }
    }

    static void checkTime(long startedNanos, long maxNanos) throws IOException {
        if (System.nanoTime() - startedNanos >= maxNanos) {
            throw new IOException("time budget exceeded");
        }
    }
}
