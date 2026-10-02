package blog.libraries;

import com.google.common.graph.ElementOrder;
import com.google.common.graph.GraphBuilder;
import com.google.common.graph.Graphs;
import com.google.common.graph.ImmutableGraph;
import com.google.common.graph.MutableGraph;
import com.google.common.graph.MutableNetwork;
import com.google.common.graph.MutableValueGraph;
import com.google.common.graph.NetworkBuilder;
import com.google.common.graph.ValueGraphBuilder;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Extension01Test {
    @Test void oneDatasetHasThreeDifferentEdgeModels() {
        MutableGraph<String> graph = GraphBuilder.directed().allowsSelfLoops(false)
                .nodeOrder(ElementOrder.insertion()).build();
        MutableValueGraph<String, Integer> values = ValueGraphBuilder.directed().build();
        MutableNetwork<String, String> network = NetworkBuilder.directed()
                .allowsParallelEdges(true).allowsSelfLoops(false).build();
        for (String n : Arrays.asList("sku", "price", "stock", "orphan")) {
            graph.addNode(n); values.addNode(n); network.addNode(n);
        }
        assertTrue(graph.putEdge("sku", "price"));
        assertFalse(graph.putEdge("sku", "price"));
        graph.putEdge("sku", "stock");
        assertNull(values.putEdgeValue("sku", "price", 10));
        assertEquals(Integer.valueOf(10), values.putEdgeValue("sku", "price", 20));
        values.putEdgeValue("sku", "stock", 30);
        network.addEdge("sku", "price", "source-a");
        network.addEdge("sku", "price", "source-b");
        network.addEdge("sku", "stock", "source-c");
        assertEquals(2, graph.edges().size());
        assertEquals(2, values.edges().size());
        assertEquals(3, network.edges().size());
        assertEquals(2, network.edgesConnecting("sku", "price").size());
        assertEquals(2, network.asGraph().edges().size());
        assertFalse(graph.hasEdgeConnecting("price", "sku"));
        assertThrows(IllegalArgumentException.class, () -> graph.putEdge("sku", "sku"));
        assertThrows(IllegalArgumentException.class,
                () -> network.addEdge("stock", "price", "source-a"));
        assertEquals(Arrays.asList("sku", "price", "stock", "orphan"),
                new ArrayList<>(graph.nodes()));
        MutableGraph<String> loops = GraphBuilder.undirected().allowsSelfLoops(true).build();
        loops.putEdge("sku", "sku");
        assertEquals(2, loops.degree("sku"));
        System.out.println("E01 edge counts graph=2,value=2,network=3; undirected loop degree=2");
    }

    @Test void liveViewSnapshotAndAdjacencyProtocol() {
        MutableGraph<String> graph = GraphBuilder.directed().build();
        graph.putEdge("sku", "price"); graph.addNode("orphan");
        Set<String> successors = graph.successors("sku");
        ImmutableGraph<String> snapshot = ImmutableGraph.copyOf(graph);
        graph.putEdge("sku", "stock");
        assertTrue(successors.contains("stock"));
        assertFalse(snapshot.nodes().contains("stock"));
        assertThrows(UnsupportedOperationException.class, () -> successors.add("bad"));
        assertFalse(Graphs.hasCycle(graph));
        graph.putEdge("price", "sku");
        assertTrue(Graphs.hasCycle(graph));
        assertFalse(Graphs.hasCycle(snapshot));
        Map<String, Set<String>> adjacency = new LinkedHashMap<>();
        for (String node : graph.nodes()) adjacency.put(node, new LinkedHashSet<>());
        for (String node : graph.nodes()) adjacency.get(node).addAll(graph.successors(node));
        assertEquals(graph.nodes(), adjacency.keySet());
        assertTrue(adjacency.get("orphan").isEmpty());
        assertTrue(adjacency.get("price").contains("sku"));
        assertFalse(adjacency.get("stock").contains("sku"));
        System.out.println("E01 liveView=" + successors + ", snapshot=" + snapshot + ", adjacency=" + adjacency);
    }
}
