import com.google.common.hash.BloomFilter;
import com.google.common.hash.Funnels;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Set;

public final class FilteredCatalog {
    public static void main(String[] args) {
        Set<String> exact = new HashSet<>();
        BloomFilter<CharSequence> filter = BloomFilter.create(
                Funnels.stringFunnel(StandardCharsets.UTF_8), 1000, 0.01);
        exact.add("A:SKU-1");
        filter.put("A:SKU-1");
        String query = "A:SKU-1";
        boolean exists = filter.mightContain(query) && exact.contains(query);
        if (!exists) { throw new AssertionError(); }
        System.out.println("exact member=" + exists);
    }
}
