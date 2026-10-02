package blog.libraries;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import org.apache.commons.codec.CodecPolicy;
import org.apache.commons.codec.binary.Base64;
import org.apache.commons.codec.binary.Hex;
import org.apache.commons.codec.digest.DigestUtils;
import org.apache.commons.codec.digest.HmacUtils;
import org.apache.commons.codec.digest.HmacAlgorithms;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter28Test {
    @Test
    void urlAlphabetPaddingAndCharsetAreSeparateChoices() {
        byte[] value = {(byte) 0xfb, (byte) 0xff};
        assertEquals("+/8=", Base64.encodeBase64String(value));
        assertEquals("-_8", Base64.encodeBase64URLSafeString(value));
        assertArrayEquals(value, java.util.Base64.getUrlDecoder().decode("-_8"));
        byte[] utf8 = "商品".getBytes(StandardCharsets.UTF_8);
        assertArrayEquals(utf8, Base64.decodeBase64(Base64.encodeBase64String(utf8)));
    }

    @Test
    void strictTrailingBitsDoesNotMeanStrictAlphabet() {
        Base64 strict = Base64.builder().setDecodingPolicy(CodecPolicy.STRICT).get();
        Base64 lenient = Base64.builder().setDecodingPolicy(CodecPolicy.LENIENT).get();
        assertArrayEquals(new byte[] {'M'}, lenient.decode("TR=="));
        assertThrows(IllegalArgumentException.class, () -> strict.decode("TR=="));
        assertArrayEquals(new byte[] {'M'}, strict.decode("T!Q=="));
        assertThrows(IllegalArgumentException.class, () -> java.util.Base64.getDecoder().decode("T!Q=="));
        assertArrayEquals(new byte[] {'M'}, Base64.decodeBase64Standard("T!Q=="));
        System.out.println("28 strict policy rejects nonzero tail bits; JDK basic decoder rejects nonalphabet input");
    }

    @Test
    void digestAndHmacMatchPublishedVectors() throws Exception {
        assertEquals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                DigestUtils.sha256Hex("abc".getBytes(StandardCharsets.US_ASCII)));
        byte[] key = new byte[20];
        Arrays.fill(key, (byte) 0x0b);
        String hmac = new HmacUtils(HmacAlgorithms.HMAC_SHA_256, key).hmacHex("Hi There".getBytes(StandardCharsets.US_ASCII));
        assertEquals("b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7", hmac);
        assertArrayEquals(new byte[] {0, 15, (byte) 255}, Hex.decodeHex("000fff"));
        assertThrows(org.apache.commons.codec.DecoderException.class, () -> Hex.decodeHex("0"));
    }
}
