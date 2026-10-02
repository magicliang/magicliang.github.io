package blog.libraries.io;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.Enumeration;
import java.util.HashSet;
import java.util.Set;
import java.util.zip.CRC32;
import java.util.zip.CheckedOutputStream;
import org.apache.commons.compress.archivers.tar.TarArchiveEntry;
import org.apache.commons.compress.archivers.tar.TarArchiveInputStream;
import org.apache.commons.compress.archivers.tar.TarConstants;
import org.apache.commons.compress.archivers.zip.ZipArchiveEntry;
import org.apache.commons.compress.archivers.zip.ZipFile;

public final class PrivateArchive {
    private PrivateArchive() { }

    public static final class Limits {
        final int entries;
        final long entryBytes;
        final long totalBytes;
        final long archiveBytes;
        final long nanos;

        public Limits(int entries, long entryBytes, long totalBytes, long archiveBytes, long nanos) {
            if (entries <= 0 || entryBytes < 0 || totalBytes < 0 || archiveBytes <= 0 || nanos <= 0) {
                throw new IllegalArgumentException("invalid archive limits");
            }
            this.entries = entries;
            this.entryBytes = entryBytes;
            this.totalBytes = totalBytes;
            this.archiveBytes = archiveBytes;
            this.nanos = nanos;
        }
    }

    public static Path extractZip(Path archive, Path trustedParent, Limits limits) throws IOException {
        return extract(archive, trustedParent, limits, true);
    }

    public static Path extractTar(Path archive, Path trustedParent, Limits limits) throws IOException {
        return extract(archive, trustedParent, limits, false);
    }

    private static Path extract(Path archive, Path trustedParent, Limits limits, boolean zip) throws IOException {
        if (Files.size(archive) > limits.archiveBytes) {
            throw new IOException("archive byte budget exceeded");
        }
        Path root = Files.createTempDirectory(trustedParent.toRealPath(), "unpack-");
        long start = System.nanoTime();
        try {
            State state = new State(root, limits, start);
            if (zip) {
                try (ZipFile input = ZipFile.builder().setPath(archive).get()) {
                    Enumeration<ZipArchiveEntry> entries = input.getEntries();
                    while (entries.hasMoreElements()) {
                        ZipArchiveEntry entry = entries.nextElement();
                        int type = entry.getUnixMode() & 0170000;
                        if (entry.isUnixSymlink() || (type != 0 && type != 0100000 && type != 0040000)
                                || (type == 0040000 && !entry.isDirectory()) || !input.canReadEntryData(entry)) {
                            throw new IOException("unsupported ZIP entry");
                        }
                        try (InputStream data = input.getInputStream(entry)) {
                            state.write(entry.getName(), entry.isDirectory(), entry.getSize(), entry.getCrc(), data);
                        }
                    }
                }
            } else {
                try (InputStream raw = Files.newInputStream(archive);
                     TarArchiveInputStream input = new TarArchiveInputStream(raw)) {
                    TarArchiveEntry entry;
                    while ((entry = input.getNextEntry()) != null) {
                        byte type = entry.getLinkFlag();
                        if ((type != TarConstants.LF_NORMAL && type != TarConstants.LF_OLDNORM && type != TarConstants.LF_DIR) || entry.isLink()
                                || entry.isSymbolicLink() || entry.isSparse() || !input.canReadEntryData(entry)) {
                            throw new IOException("unsupported TAR entry");
                        }
                        state.write(entry.getName(), entry.isDirectory(), entry.getSize(), -1, input);
                    }
                }
            }
            BoundedIo.checkTime(start, limits.nanos);
            return root;
        } catch (IOException | RuntimeException | Error failure) {
            try {
                deleteTree(root);
            } catch (IOException cleanupFailure) {
                failure.addSuppressed(cleanupFailure);
            }
            throw failure;
        }
    }

    private static final class State {
        final Path root;
        final Limits limits;
        final long start;
        final Set<Path> seen = new HashSet<>();
        int entries;
        long total;

        State(Path root, Limits limits, long start) {
            this.root = root;
            this.limits = limits;
            this.start = start;
        }

        void write(String name, boolean directory, long size, long expectedCrc, InputStream input) throws IOException {
            BoundedIo.checkTime(start, limits.nanos);
            if (++entries > limits.entries) {
                throw new IOException("entry budget exceeded");
            }
            Path target = SafePaths.resolveNewFile(root, name);
            if (!seen.add(target)) {
                throw new IOException("duplicate entry");
            }
            if (directory) {
                if (size != 0) {
                    throw new IOException("directory with data");
                }
                Files.createDirectory(target);
                return;
            }
            CRC32 crc = new CRC32();
            long count;
            try (OutputStream file = Files.newOutputStream(target, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
                 CheckedOutputStream checked = new CheckedOutputStream(file, crc)) {
                count = BoundedIo.copy(input, checked, Math.min(limits.entryBytes, limits.totalBytes - total), start, limits.nanos);
            }
            if (count != size || (expectedCrc != -1 && crc.getValue() != expectedCrc)) {
                throw new IOException("entry size or CRC mismatch");
            }
            total += count;
        }
    }

    public static void deleteTree(Path root) throws IOException {
        Files.walkFileTree(root, new SimpleFileVisitor<Path>() {
            @Override
            public FileVisitResult visitFile(Path file, BasicFileAttributes attributes) throws IOException {
                Files.delete(file);
                return FileVisitResult.CONTINUE;
            }

            @Override
            public FileVisitResult postVisitDirectory(Path directory, IOException failure) throws IOException {
                if (failure != null) {
                    throw failure;
                }
                Files.delete(directory);
                return FileVisitResult.CONTINUE;
            }
        });
    }
}
