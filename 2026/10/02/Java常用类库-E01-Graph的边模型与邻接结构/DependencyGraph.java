import com.google.common.graph.GraphBuilder;
import com.google.common.graph.Graphs;
import com.google.common.graph.MutableGraph;

public final class DependencyGraph {
    public static void main(String[] args) {
        MutableGraph<String> graph = GraphBuilder.directed().allowsSelfLoops(false).build();
        graph.putEdge("sku", "price");
        if (Graphs.hasCycle(graph)) { throw new AssertionError(); }
        graph.putEdge("price", "sku");
        if (!Graphs.hasCycle(graph)) { throw new AssertionError(); }
        System.out.println("cycle detected after reverse dependency");
    }
}
