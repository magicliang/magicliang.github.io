import java.util.Arrays;
import java.util.List;

public final class ExplicitCatalogListeners {
    interface Listener {
        void changed(String sku);
    }

    static final class Catalog {
        private final List<Listener> listeners;

        Catalog(List<Listener> listeners) {
            this.listeners = listeners;
        }

        void notifyChanged(String sku) {
            for (Listener listener : listeners) {
                listener.changed(sku);
            }
        }
    }

    public static void main(String[] args) {
        Listener first = sku -> System.out.println("count:" + sku);
        Listener second = sku -> System.out.println("view:" + sku);
        new Catalog(Arrays.asList(first, second)).notifyChanged("SKU-1");
    }
}
