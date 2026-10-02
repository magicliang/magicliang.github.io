package blog.libraries;

import org.junit.jupiter.api.Test;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.slf4j.spi.SLF4JServiceProvider;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.ServiceLoader;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import static org.junit.jupiter.api.Assertions.*;

public class Chapter33Test {
    public static final class Probe {
        public static void main(String[] args) {
            int count = 0;
            for (SLF4JServiceProvider provider : ServiceLoader.load(SLF4JServiceProvider.class)) {
                System.out.println("provider=" + provider.getClass().getName()); count++;
            }
            System.out.println("providers=" + count);
            Logger logger = LoggerFactory.getLogger("catalog");
            System.out.println("factory=" + LoggerFactory.getILoggerFactory().getClass().getName());
            if (logger.isDebugEnabled()) throw new AssertionError("debug must be disabled");
            AtomicInteger calls = new AtomicInteger();
            logger.debug("eager {}", calls.incrementAndGet());
            logger.atDebug().addArgument(() -> calls.incrementAndGet()).log("lazy {}");
            System.out.println("argumentCalls=" + calls.get());
            if (calls.get() != 1) throw new AssertionError("unexpected evaluation");
            logger.info("product={} token={}", "A", "[REDACTED]");
            if ("bridge".equals(args[0])) {
                org.slf4j.bridge.SLF4JBridgeHandler.removeHandlersForRootLogger();
                org.slf4j.bridge.SLF4JBridgeHandler.install();
                try { java.util.logging.Logger.getLogger("legacy-catalog").info("bridged-product=A"); }
                finally { org.slf4j.bridge.SLF4JBridgeHandler.uninstall(); }
                System.out.println("bridgeInstalled=" + org.slf4j.bridge.SLF4JBridgeHandler.isInstalled());
            }
            if ("jdk14".equals(args[0])) {
                try {
                    MDC.put("requestId", "req-A");
                    if (!"req-A".equals(MDC.get("requestId"))) throw new AssertionError("MDC adapter missing");
                    throw new IllegalStateException("simulated request failure");
                } catch (IllegalStateException expected) {
                    System.out.println("failedRequest=true");
                } finally {
                    MDC.remove("requestId");
                }
                System.out.println("nextRequestMdc=" + MDC.get("requestId"));
                if (MDC.get("requestId") != null) throw new AssertionError("MDC leaked");
            }
        }
    }
    private String[] fork(String mode) throws Exception {
        String cp = System.getProperty("surefire.test.class.path", System.getProperty("java.class.path"));
        List<String> entries = new ArrayList<>();
        entries.add(new File(Probe.class.getProtectionDomain().getCodeSource().getLocation().toURI()).getPath());
        for (String entry : cp.split(java.util.regex.Pattern.quote(File.pathSeparator))) {
            String name = new File(entry).getName();
            if (name.startsWith("slf4j-api-")
                    || (("simple".equals(mode) || "multiple".equals(mode) || "bridge".equals(mode)) && name.startsWith("slf4j-simple-"))
                    || ("bridge".equals(mode) && name.startsWith("jul-to-slf4j-"))
                    || (("jdk14".equals(mode) || "multiple".equals(mode)) && name.startsWith("slf4j-jdk14-"))) {
                entries.add(entry);
            }
        }
        Path dir = Paths.get("target", "chapter33-forks"); Files.createDirectories(dir);
        Path stdout = dir.resolve(mode + ".stdout.txt"), stderr = dir.resolve(mode + ".stderr.txt");
        List<String> command = new ArrayList<>();
        command.add(Paths.get(System.getProperty("java.home"), "bin", "java").toString());
        command.add("-Dorg.slf4j.simpleLogger.defaultLogLevel=info");
        command.add("-cp"); command.add(String.join(File.pathSeparator, entries));
        command.add(Probe.class.getName()); command.add(mode);
        Files.write(dir.resolve(mode + ".command.txt"), command, StandardCharsets.UTF_8);
        Process process = new ProcessBuilder(command).redirectOutput(stdout.toFile()).redirectError(stderr.toFile()).start();
        try {
            assertTrue(process.waitFor(20, TimeUnit.SECONDS), "fork deadline");
            assertEquals(0, process.exitValue());
        } finally { if (process.isAlive()) process.destroyForcibly(); }
        return new String[] {new String(Files.readAllBytes(stdout), StandardCharsets.UTF_8),
                new String(Files.readAllBytes(stderr), StandardCharsets.UTF_8)};
    }
    @Test void noProviderFallsBackWithDiagnostic() throws Exception {
        String[] out = fork("none");
        assertTrue(out[0].contains("providers=0")); assertTrue(out[0].contains("NOPLoggerFactory"));
        assertTrue(out[1].contains("No SLF4J providers were found"));
        assertTrue(out[0].contains("argumentCalls=1"));
    }
    @Test void singleProviderLogsOnlySanitizedFields() throws Exception {
        String[] out = fork("simple");
        assertTrue(out[0].contains("providers=1")); assertTrue(out[0].contains("SimpleLoggerFactory"));
        assertTrue(out[1].contains("product=A token=[REDACTED]"));
        assertFalse(out[1].contains("synthetic-secret"));
        assertFalse(out[1].contains("multiple SLF4J providers"));
    }
    @Test void multipleProvidersAreDetectedWithoutAssumingWinner() throws Exception {
        String[] out = fork("multiple");
        assertTrue(out[0].contains("providers=2"));
        assertTrue(out[1].contains("multiple SLF4J providers"));
        assertTrue(out[0].contains("factory="));
    }
    @Test void mdcIsRemovedAfterFailedRequest() throws Exception {
        String[] out = fork("jdk14");
        assertTrue(out[0].contains("providers=1")); assertTrue(out[0].contains("JDK14LoggerFactory"));
        assertTrue(out[0].contains("failedRequest=true")); assertTrue(out[0].contains("nextRequestMdc=null"));
    }
    @Test void julBridgeHasOneDirectionAndIsRemoved() throws Exception {
        String[] out = fork("bridge");
        assertTrue(out[0].contains("providers=1"));
        assertTrue(out[1].contains("INFO legacy-catalog - bridged-product=A"));
        assertEquals(1, out[1].split("bridged-product=A", -1).length - 1);
        assertTrue(out[0].contains("bridgeInstalled=false"));
    }
}
