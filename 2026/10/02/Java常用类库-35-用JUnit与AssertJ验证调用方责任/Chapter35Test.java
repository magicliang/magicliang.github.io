package blog.libraries;

import com.google.common.collect.ImmutableList;
import org.apache.commons.lang3.StringUtils;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import static org.assertj.core.api.Assertions.*;

public class Chapter35Test {
    static List<String> snapshot(List<String> input) {
        return Boolean.getBoolean("chapter35.mutant") ? input : ImmutableList.copyOf(input);
    }
    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {" ", "\t"})
    void blankInputContract(String input) { assertThat(StringUtils.isBlank(input)).isTrue(); }

    @Test void snapshotDoesNotFollowSourceChanges() {
        List<String> source = new ArrayList<>(Arrays.asList("A"));
        List<String> result = snapshot(source);
        source.add("B");
        assertThat(result).containsExactly("A");
    }
    @Test void realLibraryRejectsNullRatherThanMockedExpectation() {
        assertThatNullPointerException().isThrownBy(() -> ImmutableList.copyOf(Arrays.asList("A", null)));
        assertThatThrownBy(() -> ImmutableList.of("A").add("B")).isInstanceOf(UnsupportedOperationException.class);
    }
    static final class TrackedInput extends ByteArrayInputStream {
        boolean closed;
        TrackedInput() { super(new byte[] {1}); }
        @Override public void close() throws IOException { closed = true; super.close(); }
    }
    static void parseAndClose(InputStream input) throws IOException {
        try (InputStream owned = input) {
            if (owned.read() == 1) throw new IOException("bad record");
        }
    }
    @Test void resourceClosesOnFailure() {
        TrackedInput input = new TrackedInput();
        assertThatIOException().isThrownBy(() -> parseAndClose(input)).withMessage("bad record");
        assertThat(input.closed).isTrue();
    }
}
