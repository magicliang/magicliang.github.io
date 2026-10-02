package blog.libraries;

import blog.libraries.io.PrivateArchive;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.stream.Stream;
import org.apache.commons.compress.archivers.tar.TarArchiveEntry;
import org.apache.commons.compress.archivers.tar.TarArchiveOutputStream;
import org.apache.commons.compress.archivers.tar.TarConstants;
import org.apache.commons.compress.archivers.zip.ZipArchiveEntry;
import org.apache.commons.compress.archivers.zip.ZipArchiveOutputStream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class Chapter30Test {
    @TempDir Path temp;

    private PrivateArchive.Limits normal() {
        return new PrivateArchive.Limits(10, 1024, 4096, 1_000_000, 5_000_000_000L);
    }

    private Path zip(String[] names, byte[] content, boolean symlink) throws Exception {
        Path file = Files.createTempFile(temp, "input-", ".zip");
        try (ZipArchiveOutputStream output = new ZipArchiveOutputStream(file)) {
            for (String name : names) {
                ZipArchiveEntry entry = new ZipArchiveEntry(name);
                if (symlink) { entry.setUnixMode(0120777); }
                output.putArchiveEntry(entry);
                output.write(content);
                output.closeArchiveEntry();
            }
        }
        return file;
    }

    private Path tar(String name, byte type, byte[] content) throws Exception {
        Path file = Files.createTempFile(temp, "input-", ".tar");
        try (OutputStream raw = Files.newOutputStream(file);
             TarArchiveOutputStream output = new TarArchiveOutputStream(raw)) {
            TarArchiveEntry entry = new TarArchiveEntry(name, type, true);
            if (type == TarConstants.LF_NORMAL) { entry.setSize(content.length); }
            else { entry.setLinkName("../outside"); }
            output.putArchiveEntry(entry);
            if (type == TarConstants.LF_NORMAL) { output.write(content); }
            output.closeArchiveEntry();
        }
        return file;
    }

    private void assertEmpty(Path parent) throws Exception {
        try (Stream<Path> files = Files.list(parent)) { assertEquals(0, files.count()); }
    }

    @Test
    void zipAndTarExtractRegularFilesUnderPrivateRoot() throws Exception {
        Path parent = Files.createDirectory(temp.resolve("output"));
        byte[] data = "sku,price\nA,100\n".getBytes(StandardCharsets.UTF_8);
        Path zipped = PrivateArchive.extractZip(zip(new String[] {"nested/catalog.csv"}, data, false), parent, normal());
        assertArrayEquals(data, Files.readAllBytes(zipped.resolve("nested/catalog.csv")));
        Path tarred = PrivateArchive.extractTar(tar("catalog.csv", TarConstants.LF_NORMAL, data), parent, normal());
        assertArrayEquals(data, Files.readAllBytes(tarred.resolve("catalog.csv")));
        Path directory = PrivateArchive.extractZip(zip(new String[] {"empty/"}, new byte[0], false), parent, normal());
        assertTrue(Files.isDirectory(directory.resolve("empty")));
        PrivateArchive.deleteTree(directory);
        PrivateArchive.deleteTree(zipped);
        PrivateArchive.deleteTree(tarred);
        assertEmpty(parent);
    }

    @Test
    void traversalAbsoluteMixedPathsAndDuplicateAreRejectedWithCleanup() throws Exception {
        Path parent = Files.createDirectory(temp.resolve("output"));
        for (String name : new String[] {"../escaped", "/escaped", "C:/escaped", "a\\..\\escaped"}) {
            Path input = zip(new String[] {"accepted-first", name}, new byte[] {1}, false);
            assertThrows(IOException.class, () -> PrivateArchive.extractZip(input, parent, normal()), name);
            assertEmpty(parent);
            Path tarInput = tar(name, TarConstants.LF_NORMAL, new byte[] {1});
            assertThrows(IOException.class, () -> PrivateArchive.extractTar(tarInput, parent, normal()), name);
            assertEmpty(parent);
        }
        Path duplicate = zip(new String[] {"same", "same"}, new byte[] {1}, false);
        assertThrows(IOException.class, () -> PrivateArchive.extractZip(duplicate, parent, normal()));
        assertEmpty(parent);
        Path existing = zip(new String[] {"nested/file", "nested/"}, new byte[0], false);
        assertThrows(IOException.class, () -> PrivateArchive.extractZip(existing, parent, normal()));
        assertEmpty(parent);
        assertFalse(Files.exists(temp.resolve("escaped")));
        Path tarTraversal = tar("../escaped", TarConstants.LF_NORMAL, new byte[] {1});
        assertThrows(IOException.class, () -> PrivateArchive.extractTar(tarTraversal, parent, normal()));
        assertEmpty(parent);
    }

    @Test
    void archiveLinksAndSpecialEntriesAreRejected() throws Exception {
        Path parent = Files.createDirectory(temp.resolve("output"));
        Path linkedZip = zip(new String[] {"link"}, "../outside".getBytes(StandardCharsets.UTF_8), true);
        assertThrows(IOException.class, () -> PrivateArchive.extractZip(linkedZip, parent, normal()));
        for (byte type : new byte[] {TarConstants.LF_SYMLINK, TarConstants.LF_LINK, TarConstants.LF_FIFO}) {
            Path input = tar("link", type, new byte[0]);
            assertThrows(IOException.class, () -> PrivateArchive.extractTar(input, parent, normal()));
            assertEmpty(parent);
        }
    }

    @Test
    void actualDecompressedBytesEntryCountAndTimeAreBudgeted() throws Exception {
        Path parent = Files.createDirectory(temp.resolve("output"));
        Path input = zip(new String[] {"a", "b"}, new byte[6], false);
        PrivateArchive.Limits[] limits = {
            new PrivateArchive.Limits(1, 100, 100, 1_000_000, 5_000_000_000L),
            new PrivateArchive.Limits(10, 5, 100, 1_000_000, 5_000_000_000L),
            new PrivateArchive.Limits(10, 10, 10, 1_000_000, 5_000_000_000L),
            new PrivateArchive.Limits(10, 100, 100, 1_000_000, 1),
            new PrivateArchive.Limits(10, 100, 100, 1, 5_000_000_000L)
        };
        for (PrivateArchive.Limits limit : limits) {
            assertThrows(IOException.class, () -> PrivateArchive.extractZip(input, parent, limit));
            assertEmpty(parent);
        }
        Path highRatio = zip(new String[] {"zeros"}, new byte[100_000], false);
        assertTrue(Files.size(highRatio) < 2000);
        assertThrows(IOException.class, () -> PrivateArchive.extractZip(highRatio, parent, normal()));
        assertEmpty(parent);
        System.out.println("30 budgets: entries/item/total/archive/time/high-ratio rejected; failed roots removed");
    }

    @Test
    void damagedArchiveAndTruncatedTarFailWithoutPublishingPartialFiles() throws Exception {
        Path parent = Files.createDirectory(temp.resolve("output"));
        Path valid = zip(new String[] {"a"}, new byte[] {1}, false);
        byte[] zipBytes = Files.readAllBytes(valid);
        Files.write(valid, Arrays.copyOf(zipBytes, zipBytes.length / 2));
        assertThrows(IOException.class, () -> PrivateArchive.extractZip(valid, parent, normal()));
        assertEmpty(parent);
        Path validTar = tar("a", TarConstants.LF_NORMAL, new byte[600]);
        Files.write(validTar, Arrays.copyOf(Files.readAllBytes(validTar), 520));
        assertThrows(IOException.class, () -> PrivateArchive.extractTar(validTar, parent, normal()));
        assertEmpty(parent);
    }
}
