package blog.libraries;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

public final class LibraryDecisionDemo {
    public static void main(String[] args) {
        List<Product> input = new ArrayList<>(Arrays.asList(
                new Product("merchant-a", "sku", new BigDecimal("10.00")),
                new Product("merchant-a", "sku-2", new BigDecimal("20.00")),
                new Product("merchant-b", "sku", new BigDecimal("30.00"))));
        Map<String, List<Product>> catalog = Catalog.groupByMerchant(input);
        input.clear();
        if (catalog.size() != 2 || catalog.get("merchant-a").size() != 2
                || catalog.get("merchant-b").size() != 1) {
            throw new AssertionError("merchant scope or snapshot changed");
        }
        boolean rejected = false;
        try {
            Catalog.groupByMerchant(Arrays.asList(
                    new Product("merchant-a", "sku", BigDecimal.ONE),
                    new Product("merchant-a", "sku", BigDecimal.TEN)));
        } catch (IllegalArgumentException expected) {
            rejected = true;
        }
        if (!rejected) throw new AssertionError("duplicate product was accepted");
        boolean immutable = false;
        try {
            catalog.get("merchant-a").clear();
        } catch (UnsupportedOperationException expected) {
            immutable = true;
        }
        if (!immutable) throw new AssertionError("published list was mutable");
        System.out.println("catalog=3; merchants=2; sku-reuse=allowed; duplicate=rejected; snapshot=isolated");
    }
}
