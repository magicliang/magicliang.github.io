package blog.libraries;

import com.google.common.collect.ContiguousSet;
import com.google.common.collect.DiscreteDomain;
import com.google.common.collect.Range;
import com.google.common.collect.RangeMap;
import com.google.common.collect.RangeSet;
import com.google.common.collect.TreeRangeMap;
import com.google.common.collect.TreeRangeSet;
import java.util.Arrays;
import java.util.LinkedHashSet;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Chapter14Test {
    @Test
    void endpointsAndDiscreteEmptinessAreDifferentQuestions() {
        Range<Integer> price = Range.closedOpen(100, 200);
        assertTrue(price.contains(100));
        assertTrue(price.contains(199));
        assertFalse(price.contains(200));
        assertTrue(Range.closedOpen(100, 100).isEmpty());
        assertThrows(IllegalArgumentException.class, () -> Range.open(100, 100));
        Range<Integer> gap = Range.open(3, 4);
        assertFalse(gap.isEmpty());
        assertTrue(ContiguousSet.create(gap, DiscreteDomain.integers()).isEmpty());
        assertEquals(Range.closedOpen(4, 4), gap.canonical(DiscreteDomain.integers()));
        assertThrows(NullPointerException.class, () -> price.contains(null));
        System.out.println("14 discrete: Range.open(3,4).isEmpty=false; integerContiguousSet.isEmpty=true");
    }

    @Test
    void connectedDoesNotMeanNonEmptyIntersection() {
        Range<Integer> first = Range.closedOpen(0, 10);
        Range<Integer> next = Range.closedOpen(10, 20);
        assertTrue(first.isConnected(next));
        assertTrue(first.intersection(next).isEmpty());
        assertFalse(Range.open(0, 10).isConnected(Range.open(10, 20)));
        assertThrows(IllegalArgumentException.class,
                () -> first.intersection(Range.closedOpen(20, 30)));
    }

    @Test
    void rangeSetCoalescesAndRemovalSplitsWithExactEndpoints() {
        RangeSet<Integer> eligible = TreeRangeSet.create();
        eligible.add(Range.closedOpen(0, 10));
        eligible.add(Range.closedOpen(10, 20));
        assertEquals(new LinkedHashSet<>(Arrays.asList(Range.closedOpen(0, 20))), eligible.asRanges());
        eligible.remove(Range.closed(5, 15));
        assertEquals(new LinkedHashSet<>(Arrays.asList(Range.closedOpen(0, 5), Range.open(15, 20))),
                eligible.asRanges());
        assertFalse(eligible.contains(5));
        assertFalse(eligible.contains(15));
        assertTrue(eligible.contains(16));
        assertTrue(eligible.complement().contains(5));
        System.out.println("14 set: [0,10)+[10,20) -> [0,20); remove[5,15] -> [0,5),(15,20)");
    }

    @Test
    void rangeMapOverwriteKeepsOuterFragmentsAndRemoveCreatesHole() {
        RangeMap<Integer, String> tiers = TreeRangeMap.create();
        tiers.put(Range.closedOpen(0, 100), "base");
        tiers.put(Range.closedOpen(20, 40), "promo");
        assertEquals(3, tiers.asMapOfRanges().size());
        assertEquals("base", tiers.get(19));
        assertEquals("promo", tiers.get(20));
        assertEquals("promo", tiers.get(39));
        assertEquals("base", tiers.get(40));
        tiers.remove(Range.closedOpen(30, 50));
        assertEquals("promo", tiers.get(29));
        assertNull(tiers.get(30));
        assertNull(tiers.get(49));
        assertEquals("base", tiers.get(50));
        assertEquals(new LinkedHashSet<>(Arrays.asList(Range.closedOpen(0, 20),
                Range.closedOpen(20, 30), Range.closedOpen(50, 100))), tiers.asMapOfRanges().keySet());
        System.out.println("14 map: overwrite -> [0,20)=base,[20,40)=promo,[40,100)=base; remove[30,50) creates hole");
    }

    @Test
    void sameValueNeedsExplicitCoalescingAndViewsAreLive() {
        TreeRangeMap<Integer, String> tiers = TreeRangeMap.create();
        tiers.put(Range.closedOpen(0, 10), "base");
        tiers.put(Range.closedOpen(10, 20), "base");
        assertEquals(2, tiers.asMapOfRanges().size());
        RangeMap<Integer, String> window = tiers.subRangeMap(Range.closedOpen(5, 15));
        assertEquals("base", window.get(5));
        tiers.putCoalescing(Range.closedOpen(10, 20), "base");
        assertEquals(1, tiers.asMapOfRanges().size());
        window.remove(Range.closedOpen(5, 10));
        assertNull(tiers.get(5));
        assertEquals("base", tiers.get(10));
        assertThrows(IllegalArgumentException.class, () -> window.put(Range.closedOpen(0, 6), "x"));
        assertThrows(NullPointerException.class, () -> tiers.put(Range.closedOpen(1, 2), null));
    }
}
