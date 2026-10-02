package blog.libraries;

import com.google.common.collect.Lists;
import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.github.benmanes.caffeine.cache.Caffeine;
import it.unimi.dsi.fastutil.ints.Int2ObjectOpenHashMap;
import org.eclipse.collections.impl.map.mutable.primitive.IntObjectHashMap;
import org.openjdk.jmh.annotations.*;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.NANOSECONDS)
@Warmup(iterations = 2, time = 1)
@Measurement(iterations = 3, time = 1)
@Fork(value = 2, jvmArgsAppend = {"-Xms256m", "-Xmx256m"})
@State(Scope.Thread)
public class LibraryBenchmarks {
    @Param({"1024"})
    public int size;
    private List<Integer> input;
    private Map<Integer, Integer> boxed;
    private Int2ObjectOpenHashMap<Integer> fast;
    private IntObjectHashMap<Integer> eclipse;
    private com.google.common.cache.LoadingCache<Integer, Integer> guavaHit;
    private com.github.benmanes.caffeine.cache.LoadingCache<Integer, Integer> caffeineHit;
    private com.google.common.cache.LoadingCache<Integer, Integer> guavaMiss;
    private com.github.benmanes.caffeine.cache.LoadingCache<Integer, Integer> caffeineMiss;
    private int cursor;

    @Setup(Level.Trial)
    public void setupAndCheckEquivalentResults() throws Exception {
        input = new ArrayList<>(size);
        boxed = new HashMap<>(size * 2);
        fast = new Int2ObjectOpenHashMap<>(size);
        eclipse = new IntObjectHashMap<>(size);
        guavaHit = newGuava(size * 2);
        caffeineHit = Caffeine.newBuilder().maximumSize(size * 2).build(key -> key * 3);
        guavaMiss = newGuava(256);
        caffeineMiss = Caffeine.newBuilder().maximumSize(256).executor(Runnable::run).build(key -> key * 3);
        for (int i = 0; i < size; i++) {
            int key = 1000 + i;
            input.add(key);
            Integer value = key * 3;
            boxed.put(key, value);
            fast.put(key, value);
            eclipse.put(key, value);
            guavaHit.put(key, value);
            caffeineHit.put(key, value);
        }
        guavaHit.cleanUp();
        caffeineHit.cleanUp();
        if (!eagerTransform().equals(lazyTransformThenMaterialize())) throw new AssertionError("transform mismatch");
        for (int key = 1000; key < 1000 + size; key++) {
            Integer expected = boxed.get(key);
            if (!expected.equals(fast.get(key)) || !expected.equals(eclipse.get(key))
                    || !expected.equals(guavaHit.get(key)) || !expected.equals(caffeineHit.get(key))) {
                throw new AssertionError("lookup mismatch");
            }
        }
        if (guavaMiss.get(99) != 297 || caffeineMiss.get(99) != 297) throw new AssertionError("load mismatch");
        guavaMiss.invalidateAll();
        caffeineMiss.invalidateAll();
        cursor = 0;
    }

    private static com.google.common.cache.LoadingCache<Integer, Integer> newGuava(int max) {
        return CacheBuilder.newBuilder().maximumSize(max).build(new CacheLoader<Integer, Integer>() {
            @Override public Integer load(Integer key) { return key * 3; }
        });
    }

    @Benchmark
    public List<Integer> eagerTransform() {
        List<Integer> output = new ArrayList<>(input.size());
        for (Integer value : input) output.add(value * 3);
        return output;
    }

    @Benchmark
    public List<Integer> lazyTransformThenMaterialize() {
        return new ArrayList<>(Lists.transform(input, value -> value * 3));
    }

    private int hitKey() { return 1000 + ((cursor++ & Integer.MAX_VALUE) % size); }
    private int missKey() { return 100000 + (cursor++ & 0x3fffffff); }

    @Benchmark public Integer boxedLookup() { return boxed.get(hitKey()); }
    @Benchmark public Integer fastutilLookup() { return fast.get(hitKey()); }
    @Benchmark public Integer eclipseLookup() { return eclipse.get(hitKey()); }
    @Benchmark public Integer guavaHit() { return guavaHit.getUnchecked(hitKey()); }
    @Benchmark public Integer caffeineHit() { return caffeineHit.get(hitKey()); }
    @Benchmark public Integer guavaMiss() { return guavaMiss.getUnchecked(missKey()); }
    @Benchmark public Integer caffeineMiss() { return caffeineMiss.get(missKey()); }
}
