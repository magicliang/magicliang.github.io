package blog.libraries;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

public final class Catalog {
    private Catalog() {
    }

    public static Map<String, List<Product>> groupByMerchant(List<Product> products) {
        Objects.requireNonNull(products, "products");
        Map<String, Map<String, Product>> index = new LinkedHashMap<>();
        for (Product product : products) {
            Objects.requireNonNull(product, "product");
            Map<String, Product> group = index.get(product.getMerchantId());
            if (group == null) {
                group = new LinkedHashMap<>();
                index.put(product.getMerchantId(), group);
            }
            if (group.containsKey(product.getProductId())) {
                throw new IllegalArgumentException("duplicate product in merchant: "
                        + product.getMerchantId() + "/" + product.getProductId());
            }
            group.put(product.getProductId(), product);
        }
        Map<String, List<Product>> result = new LinkedHashMap<>();
        for (Map.Entry<String, Map<String, Product>> entry : index.entrySet()) {
            result.put(entry.getKey(), Collections.unmodifiableList(
                    new ArrayList<>(entry.getValue().values())));
        }
        return Collections.unmodifiableMap(result);
    }
}
