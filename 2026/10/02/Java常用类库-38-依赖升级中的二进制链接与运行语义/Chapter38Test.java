package blog.libraries;

import com.google.common.collect.ImmutableMap;
import org.junit.jupiter.api.Test;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.TimeUnit;
import static org.junit.jupiter.api.Assertions.*;

public class Chapter38Test {
    public static final class BinaryCompatibilityProbe {
        public static void main(String[] args) {
            System.out.println("loadedFrom=" + ImmutableMap.class.getProtectionDomain().getCodeSource().getLocation());
            System.out.println("value=" + ImmutableMap.<String, Integer>builder()
                    .put("A", 1).put("A", 2).buildKeepingLast().get("A"));
        }
    }
    private Path newJar() throws Exception {
        return Paths.get(ImmutableMap.class.getProtectionDomain().getCodeSource().getLocation().toURI());
    }
    private Path oldJar() {
        String path = System.getProperty("oldGuavaJar");
        assertNotNull(path, "Set -DoldGuavaJar=/absolute/path/guava-30.1.1-jre.jar; see Chapter38 RUN.md");
        Path jar = Paths.get(path).toAbsolutePath();
        assertTrue(Files.isRegularFile(jar), "old jar must exist");
        return jar;
    }
    private static String sha256(Path path) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path));
        StringBuilder text = new StringBuilder();
        for (byte b : digest) text.append(String.format("%02x", b & 255));
        return text.toString();
    }
    private String[] run(String name, Path jar, int expectedExit) throws Exception {
        Path dir = Paths.get("target", "chapter38-forks"); Files.createDirectories(dir);
        Path classes = Paths.get(BinaryCompatibilityProbe.class.getProtectionDomain().getCodeSource().getLocation().toURI());
        List<String> command = Arrays.asList(Paths.get(System.getProperty("java.home"), "bin", "java").toString(),
                "-cp", classes + File.pathSeparator + jar, BinaryCompatibilityProbe.class.getName());
        Files.write(dir.resolve(name + ".command.txt"), command, StandardCharsets.UTF_8);
        Files.write(dir.resolve(name + ".sha256.txt"), Arrays.asList(sha256(jar) + "  " + jar), StandardCharsets.UTF_8);
        Path out = dir.resolve(name + ".stdout.txt"), err = dir.resolve(name + ".stderr.txt");
        Process process = new ProcessBuilder(command).redirectOutput(out.toFile()).redirectError(err.toFile()).start();
        try {
            assertTrue(process.waitFor(20, TimeUnit.SECONDS), "fork deadline");
            assertEquals(expectedExit, process.exitValue());
            Files.write(dir.resolve(name + ".exit.txt"), Arrays.asList(Integer.toString(process.exitValue())), StandardCharsets.UTF_8);
        } finally { if (process.isAlive()) process.destroyForcibly(); }
        return new String[] {new String(Files.readAllBytes(out), StandardCharsets.UTF_8),
                new String(Files.readAllBytes(err), StandardCharsets.UTF_8)};
    }
    @Test void currentRuntimeResolvesNewMethod() throws Exception {
        Path jar = newJar();
        assertTrue(jar.getFileName().toString().contains("33.5.0-jre"));
        String[] result = run("new", jar, 0);
        assertTrue(result[0].contains(jar.toRealPath().toUri().toURL().toString()), result[0]);
        assertTrue(result[0].contains("value=2")); assertEquals("", result[1]);
    }
    @Test void oldRuntimeFailsAtRealMethodResolution() throws Exception {
        Path jar = oldJar();
        assertTrue(jar.getFileName().toString().contains("30.1.1-jre"));
        String[] result = run("old", jar, 1);
        assertTrue(result[0].contains(jar.toRealPath().toUri().toURL().toString()), result[0]);
        assertFalse(result[0].contains("value=2"));
        assertTrue(result[1].contains("java.lang.NoSuchMethodError"));
        assertTrue(result[1].contains("buildKeepingLast"));
        assertFalse(result[1].contains("ClassNotFoundException"));
    }
}
