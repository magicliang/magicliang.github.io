package blog.libraries;
import org.apache.commons.lang3.tuple.ImmutablePair;
import org.apache.commons.lang3.tuple.MutablePair;
import org.apache.commons.lang3.tuple.Pair;
import org.apache.commons.lang3.tuple.Triple;
import org.apache.commons.lang3.mutable.MutableInt;
import org.apache.commons.lang3.builder.EqualsBuilder;
import org.apache.commons.lang3.builder.HashCodeBuilder;
import org.apache.commons.lang3.builder.ToStringBuilder;
import org.apache.commons.lang3.builder.ToStringStyle;
import org.junit.jupiter.api.Test;
import java.util.AbstractMap;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
public class Chapter22Test {
    static final class ProductKey {
        private final String merchantId;
        private final String productId;
        ProductKey(String merchantId, String productId) {
            this.merchantId = java.util.Objects.requireNonNull(merchantId);
            this.productId = java.util.Objects.requireNonNull(productId);
        }
        @Override public boolean equals(Object other) {
            if (!(other instanceof ProductKey)) { return false; }
            ProductKey that = (ProductKey) other;
            return merchantId.equals(that.merchantId) && productId.equals(that.productId);
        }
        @Override public int hashCode() { return java.util.Objects.hash(merchantId, productId); }
    }
    static final class Credentials {
        private final String user;
        private final String token;
        Credentials(String user, String token) { this.user = user; this.token = token; }
        String safeText() { return new ToStringBuilder(this, ToStringStyle.SHORT_PREFIX_STYLE).append("user", user).append("token", "[REDACTED]").toString(); }
    }
    @Test void pairMutabilityAndEntryEquality() {
        Pair<String, Integer> immutable = ImmutablePair.of("A", 1);
        assertThrows(UnsupportedOperationException.class, () -> immutable.setValue(2));
        MutablePair<String, Integer> mutable = MutablePair.of("A", 1);
        int oldHash = mutable.hashCode();
        assertEquals(Integer.valueOf(1), mutable.setValue(2));
        assertNotEquals(oldHash, mutable.hashCode());
        assertEquals(new AbstractMap.SimpleEntry<>("A", 2), mutable);
        assertEquals(mutable, new AbstractMap.SimpleEntry<>("A", 2));
        assertEquals(Triple.of("A", "B", "C"), Triple.of("A", "B", "C"));
        ProductKey key = new ProductKey("shop", "sku");
        assertEquals(key, new ProductKey("shop", "sku"));
        assertEquals(key.hashCode(), new ProductKey("shop", "sku").hashCode());
        assertNotEquals(key, Pair.of("shop", "sku"));
        assertThrows(NullPointerException.class, () -> new ProductKey(null, "sku"));
    }
    @Test void immutablePairDoesNotFreezeNestedList() {
        List<String> values = new ArrayList<>(Arrays.asList("A"));
        Pair<String, List<String>> pair = ImmutablePair.of("shop", values);
        values.add("B");
        assertEquals(Arrays.asList("A", "B"), pair.getRight());
        assertNull(Pair.of(null, null).getLeft());
    }
    @Test void reflectionIncludesPrivateSensitiveFieldsUnlessExcluded() {
        Credentials credentials = new Credentials("alice", "synthetic-secret");
        assertTrue(ToStringBuilder.reflectionToString(credentials, ToStringStyle.SHORT_PREFIX_STYLE).contains("synthetic-secret"));
        assertFalse(credentials.safeText().contains("synthetic-secret"));
        assertTrue(credentials.safeText().contains("[REDACTED]"));
        assertTrue(EqualsBuilder.reflectionEquals(credentials, new Credentials("alice", "synthetic-secret")));
        assertFalse(EqualsBuilder.reflectionEquals(credentials, new Credentials("alice", "other")));
        assertEquals(HashCodeBuilder.reflectionHashCode(credentials), HashCodeBuilder.reflectionHashCode(new Credentials("alice", "synthetic-secret")));
    }
    @Test void mutableWrapperIsAStatefulObject() {
        MutableInt count = new MutableInt(2);
        MutableInt alias = count;
        count.increment();
        assertEquals(3, alias.intValue());
        assertNotEquals(Integer.valueOf(3), count);
    }
}
