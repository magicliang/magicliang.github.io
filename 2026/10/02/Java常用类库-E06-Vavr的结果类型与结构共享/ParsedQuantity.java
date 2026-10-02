import io.vavr.control.Try;

public final class ParsedQuantity {
    public static void main(String[] args) {
        Try<Integer> parsed = Try.of(() -> Integer.parseInt("bad"));
        if (!parsed.isFailure()) { throw new AssertionError(); }
        String reason = parsed.getCause().getClass().getSimpleName();
        int fallback = parsed.recover(NumberFormatException.class, ex -> 0).get();
        System.out.println("reason=" + reason + ", explicitFallback=" + fallback);
    }
}
