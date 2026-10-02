package blog.libraries;

import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.util.Objects;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

public class Chapter35ModernTest {
    interface Transport { String send(String productId) throws IOException; }
    static final class CatalogGateway {
        private final Transport transport;
        CatalogGateway(Transport transport) { this.transport = Objects.requireNonNull(transport); }
        String fetch(String id) throws IOException {
            if (id == null || id.trim().isEmpty()) throw new IllegalArgumentException("productId required");
            return transport.send(id);
        }
    }
    @Test void invalidInputNeverReachesExternalBoundary() {
        Transport transport = mock(Transport.class);
        CatalogGateway gateway = new CatalogGateway(transport);
        assertThatIllegalArgumentException().isThrownBy(() -> gateway.fetch(" "));
        verifyNoInteractions(transport);
    }
    @Test void failureIsPropagatedWithoutInventingARetryPolicy() throws Exception {
        Transport transport = mock(Transport.class);
        IOException unavailable = new IOException("transport unavailable");
        when(transport.send("A")).thenThrow(unavailable);
        assertThatThrownBy(() -> new CatalogGateway(transport).fetch("A")).isSameAs(unavailable);
        verify(transport, times(1)).send("A"); verifyNoMoreInteractions(transport);
    }
    @Test void validRequestKeepsExactIdentifier() throws Exception {
        Transport transport = mock(Transport.class);
        when(transport.send("shop:A")).thenReturn("payload");
        assertThat(new CatalogGateway(transport).fetch("shop:A")).isEqualTo("payload");
        verify(transport).send("shop:A");
    }
}
