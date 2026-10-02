package blog.libraries;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Objects;

public final class Product {
    private final String merchantId;
    private final String productId;
    private final BigDecimal price;

    public Product(String merchantId, String productId, BigDecimal price) {
        this.merchantId = requireIdentifier(merchantId, "merchantId");
        this.productId = requireIdentifier(productId, "productId");
        BigDecimal normalized = Objects.requireNonNull(price, "price")
                .setScale(2, RoundingMode.UNNECESSARY);
        if (normalized.signum() < 0) {
            throw new IllegalArgumentException("price must be non-negative");
        }
        this.price = normalized;
    }

    private static String requireIdentifier(String identifier, String field) {
        Objects.requireNonNull(identifier, field);
        if (identifier.isEmpty()) {
            throw new IllegalArgumentException(field + " must not be empty");
        }
        return identifier;
    }

    public String getMerchantId() {
        return merchantId;
    }

    public String getProductId() {
        return productId;
    }

    public BigDecimal getPrice() {
        return price;
    }
}
