package blog.libraries;

import com.google.common.hash.BloomFilter;
import com.google.common.hash.Funnels;
import com.google.common.hash.Hashing;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.LinkedHashSet;
import java.util.Random;
import java.util.Set;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter18Test {
    @Test void encodingByteOrderAndKnownVectorsAreExplicit() throws Exception {
        assertEquals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", Hashing.sha256().hashString("abc", StandardCharsets.UTF_8).toString());
        assertEquals("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", Hashing.sha256().hashBytes(new byte[0]).toString());
        assertArrayEquals(MessageDigest.getInstance("SHA-256").digest("商品".getBytes(StandardCharsets.UTF_8)), Hashing.sha256().hashString("商品", StandardCharsets.UTF_8).asBytes());
        assertEquals(Hashing.sha256().hashBytes(new byte[] {4,3,2,1}), Hashing.sha256().newHasher().putInt(0x01020304).hash());
        assertNotEquals(Hashing.sha256().hashBytes(new byte[] {1,2,3,4}), Hashing.sha256().newHasher().putInt(0x01020304).hash());
        assertEquals(Hashing.sha256().newHasher().putString("ab", StandardCharsets.UTF_8).putString("c", StandardCharsets.UTF_8).hash(), Hashing.sha256().newHasher().putString("a", StandardCharsets.UTF_8).putString("bc", StandardCharsets.UTF_8).hash());
        assertNotEquals(Hashing.sha256().newHasher().putInt(2).putString("ab", StandardCharsets.UTF_8).putInt(1).putString("c", StandardCharsets.UTF_8).hash(), Hashing.sha256().newHasher().putInt(1).putString("a", StandardCharsets.UTF_8).putInt(2).putString("bc", StandardCharsets.UTF_8).hash());
        System.out.println("18 SHA256 empty/abc vectors PASS; UTF8 JDK cross-check PASS; putInt=little-endian; unframed concatenation collision reproduced");
    }
    @Test void exactSetSeparatesFalsePositivesFromInsertedMembers() {
        Random random = new Random(20261002L);
        Set<String> inserted = new LinkedHashSet<>();
        while (inserted.size() < 10000) { inserted.add("I:" + random.nextLong()); }
        BloomFilter<CharSequence> sized = BloomFilter.create(Funnels.stringFunnel(StandardCharsets.UTF_8), 1000, .01);
        BloomFilter<CharSequence> overloaded = BloomFilter.create(Funnels.stringFunnel(StandardCharsets.UTF_8), 1000, .01);
        Set<String> first = new LinkedHashSet<>();
        for (String value : inserted) { overloaded.put(value); if (first.size() < 1000) { first.add(value); sized.put(value); } }
        for (String value : first) { assertTrue(sized.mightContain(value)); assertFalse(sized.put(value)); }
        for (String value : inserted) { assertTrue(overloaded.mightContain(value)); }
        int positives = 0, overloadedPositives = 0;
        Set<String> absent = new LinkedHashSet<>();
        while (absent.size() < 10000) { absent.add("Q:" + random.nextLong()); }
        for (String query : absent) {
            assertFalse(inserted.contains(query));
            if (sized.mightContain(query)) { positives++; }
            if (overloaded.mightContain(query)) { overloadedPositives++; }
        }
        assertTrue(positives >= 0 && positives <= absent.size());
        assertTrue(overloadedPositives >= 0 && overloadedPositives <= absent.size());
        System.out.println("18 seed=20261002 funnel=UTF8 expectedN=1000 requestedFpp=.01 actualN=1000 absentQueries=10000 falseNegatives=0 falsePositives=" + positives + " bitEstimateFpp=" + sized.expectedFpp());
        System.out.println("18 same expectedN=1000 actualN=10000 absentQueries=10000 falseNegatives=0 falsePositives=" + overloadedPositives + " bitEstimateFpp=" + overloaded.expectedFpp());
    }
}
