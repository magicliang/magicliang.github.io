import com.google.common.primitives.Ints;
import java.util.Arrays;
import java.util.List;

public final class QuantityView {
    public static void main(String[] args) {
        int[] quantities = {1, 2, 3};
        List<Integer> view = Ints.asList(quantities);
        view.set(1, 20);
        int[] detached = Ints.toArray(view);
        detached[1] = 99;
        if (quantities[1] != 20) { throw new AssertionError(); }
        System.out.println(Arrays.toString(quantities));
    }
}
