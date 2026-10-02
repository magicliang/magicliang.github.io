package blog.libraries;

import blog.libraries.io.SafePaths;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import org.apache.commons.io.FilenameUtils;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class Chapter26Test {
    @TempDir Path temp;

    @Test
    void lexicalNormalizationCanHideTraversalIntent() {
        assertEquals("report.csv", FilenameUtils.normalize("safe/../report.csv", true));
        assertNull(FilenameUtils.normalize("../report.csv", true));
        assertEquals("safe/report.csv", FilenameUtils.normalize("safe\\report.csv", true));
    }

    @Test
    void allUntrustedPathFormsAreRejected() throws Exception {
        Path root = Files.createDirectory(temp.resolve("root"));
        for (String name : new String[] {"../escape", "a/../../escape", "/tmp/escape", "C:/escape", "a\\..\\escape", "a/../x", ".", ""}) {
            assertThrows(IOException.class, () -> SafePaths.resolveNewFile(root, name), name);
        }
        assertFalse(Files.exists(temp.resolve("escape")));
    }

    @Test
    void existingAndSymlinkParentsCannotBeOverwritten() throws Exception {
        Path root = Files.createDirectory(temp.resolve("root"));
        Path outside = Files.createDirectory(temp.resolve("outside"));
        Path existing = root.resolve("old.csv");
        Files.write(existing, new byte[] {7});
        assertThrows(IOException.class, () -> SafePaths.resolveNewFile(root, "old.csv"));
        Files.createSymbolicLink(root.resolve("link"), outside);
        assertThrows(IOException.class, () -> SafePaths.resolveNewFile(root, "link/escape.csv"));
        assertFalse(Files.exists(outside.resolve("escape.csv")));
        assertArrayEquals(new byte[] {7}, Files.readAllBytes(existing));
        Path fresh = SafePaths.resolveNewFile(root, "new/report.csv");
        Files.write(fresh, new byte[] {1}, StandardOpenOption.CREATE_NEW);
        assertTrue(fresh.toRealPath().startsWith(root.toRealPath()));
        System.out.println("26 path policy: traversal/absolute/backslash/existing/symlink rejected; nested create accepted");
    }
}
