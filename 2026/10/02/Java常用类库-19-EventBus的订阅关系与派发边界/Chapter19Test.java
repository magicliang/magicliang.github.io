package blog.libraries;

import com.google.common.eventbus.DeadEvent;
import com.google.common.eventbus.EventBus;
import com.google.common.eventbus.Subscribe;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter19Test {
    public static final class Nested {
        final EventBus bus;
        final List<String> trace = new ArrayList<>();
        Nested(EventBus bus) { this.bus = bus; }
        @Subscribe public void parent(String event) { trace.add("parent-start"); bus.post(1); trace.add("parent-end"); }
        @Subscribe public void child(Integer event) { trace.add("child@" + Thread.currentThread().getName()); }
    }
    public static final class Broken {
        @Subscribe public void accept(String value) { throw new IllegalArgumentException("bad event"); }
    }
    public static final class Counter {
        int calls;
        @Subscribe public void accept(String value) { calls++; }
    }
    public static final class DeadRecorder {
        final List<Object> events = new ArrayList<>();
        @Subscribe public void dead(DeadEvent event) { events.add(event.getEvent()); }
    }
    @Test void reentrantPostQueuesUntilCurrentSubscriberReturns() {
        EventBus bus = new EventBus(); Nested nested = new Nested(bus); bus.register(nested);
        bus.post("SKU-1");
        assertEquals(Arrays.asList("parent-start", "parent-end", "child@" + Thread.currentThread().getName()), nested.trace);
        bus.unregister(nested);
        System.out.println("19 synchronous nested trace=" + nested.trace);
    }
    @Test void subscriberExceptionGoesToHandlerNotPublisher() {
        AtomicReference<Throwable> failure = new AtomicReference<>(); AtomicInteger calls = new AtomicInteger();
        EventBus bus = new EventBus((error, context) -> { failure.set(error); calls.incrementAndGet(); });
        Broken broken = new Broken(); Counter counter = new Counter(); bus.register(broken); bus.register(counter);
        assertDoesNotThrow(() -> bus.post("SKU-1"));
        assertInstanceOf(IllegalArgumentException.class, failure.get()); assertEquals("bad event", failure.get().getMessage());
        assertEquals(1, calls.get()); assertEquals(1, counter.calls);
        bus.unregister(broken); bus.unregister(counter);
        System.out.println("19 publisher returned normally; exceptionHandler=bad event; other subscriber called once");
    }
    @Test void registrationAndDeadEventsExposeDeliveryGaps() {
        EventBus bus = new EventBus(); DeadRecorder dead = new DeadRecorder(); Counter counter = new Counter(); bus.register(dead);
        bus.post("before"); bus.register(counter); bus.register(counter); bus.post("during");
        assertEquals(1, counter.calls); bus.unregister(counter); bus.post("after");
        assertEquals(Arrays.asList("before", "after"), dead.events);
        assertThrows(IllegalArgumentException.class, () -> bus.unregister(counter));
        bus.unregister(dead);
        System.out.println("19 deadEvents=" + dead.events + "; duplicate registration delivered once; unregistered events not replayed");
    }
}
