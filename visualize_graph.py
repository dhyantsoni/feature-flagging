"""
Visualize call graph using matplotlib and networkx
"""

import json
import networkx as nx
import matplotlib.pyplot as plt
from ast_callgraph_analyzer import build_networkx_graph, analyze_file


def visualize_call_graph(json_file: str, feature_flags: dict, output_file: str = "callgraph_viz.png"):
    """Create a visual representation of the call graph"""

    # Load call graph
    with open(json_file, 'r') as f:
        call_graph = json.load(f)

    # Build NetworkX graph
    G = build_networkx_graph(call_graph)

    # Set up the plot
    plt.figure(figsize=(20, 16))

    # Use hierarchical layout
    pos = nx.spring_layout(G, k=2, iterations=50)

    # Separate nodes by type
    feature_nodes = [n for n in G.nodes() if n in feature_flags]
    regular_nodes = [n for n in G.nodes() if n not in feature_flags and not n.startswith("sample_app.print")]
    utility_nodes = [n for n in G.nodes() if n.startswith("sample_app.print") or "." in n and n.split(".")[0] != "sample_app"]

    # Draw nodes with different colors
    nx.draw_networkx_nodes(G, pos,
                          nodelist=feature_nodes,
                          node_color='lightblue',
                          node_size=3000,
                          node_shape='s',
                          label='Feature-Flagged')

    nx.draw_networkx_nodes(G, pos,
                          nodelist=regular_nodes,
                          node_color='lightgreen',
                          node_size=2000,
                          node_shape='o',
                          label='Regular Functions')

    nx.draw_networkx_nodes(G, pos,
                          nodelist=utility_nodes,
                          node_color='lightgray',
                          node_size=1500,
                          node_shape='o',
                          label='Utility/External')

    # Draw edges
    nx.draw_networkx_edges(G, pos,
                          edge_color='gray',
                          arrows=True,
                          arrowsize=20,
                          arrowstyle='->',
                          width=1.5,
                          alpha=0.6)

    # Draw labels
    labels = {}
    for node in G.nodes():
        # Simplify labels
        short_name = node.split('.')[-1]
        if node in feature_flags:
            labels[node] = f"{short_name}\n@{feature_flags[node]}"
        else:
            labels[node] = short_name

    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight='bold')

    plt.title("Feature Flag Call Graph Visualization\n(AST + NetworkX)", fontsize=16, fontweight='bold')
    plt.legend(loc='upper left', fontsize=12)
    plt.axis('off')
    plt.tight_layout()

    # Save
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Visualization saved to: {output_file}")

    # Also save as SVG for better quality
    svg_file = output_file.replace('.png', '.svg')
    plt.savefig(svg_file, format='svg', bbox_inches='tight')
    print(f"✅ SVG visualization saved to: {svg_file}")

    # plt.show()  # Uncomment to display interactively


def create_feature_impact_diagram(feature_name: str, impact_data: dict, output_file: str):
    """Create a focused diagram showing impact of one feature"""

    func_data = list(impact_data.values())[0]

    # Create subgraph
    G = nx.DiGraph()

    # Add the feature function
    feature_func = list(impact_data.keys())[0]
    G.add_node(feature_func, node_type='feature')

    # Add downstream dependencies
    for dep in func_data['downstream_dependencies']:
        G.add_node(dep, node_type='downstream')
        # Try to infer edge (this is simplified)
        G.add_edge(feature_func, dep)

    # Add upstream dependencies
    for dep in func_data['direct_callers']:
        G.add_node(dep, node_type='upstream')
        G.add_edge(dep, feature_func)

    # Layout
    plt.figure(figsize=(14, 10))
    pos = nx.spring_layout(G, k=3, iterations=50)

    # Draw nodes by type
    feature_nodes = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'feature']
    upstream_nodes = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'upstream']
    downstream_nodes = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'downstream']

    nx.draw_networkx_nodes(G, pos, nodelist=feature_nodes, node_color='#FF6B6B', node_size=4000, node_shape='s')
    nx.draw_networkx_nodes(G, pos, nodelist=upstream_nodes, node_color='#4ECDC4', node_size=3000)
    nx.draw_networkx_nodes(G, pos, nodelist=downstream_nodes, node_color='#FFE66D', node_size=2500)

    # Draw edges
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20, width=2, alpha=0.7)

    # Labels
    labels = {n: n.split('.')[-1] for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=9, font_weight='bold')

    plt.title(f"Feature Impact: {feature_name}\n{func_data['impact_summary']['total_affected_functions']} functions affected",
             fontsize=14, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()

    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Feature impact diagram saved to: {output_file}")


if __name__ == "__main__":
    # Analyze and visualize
    call_graph, functions, feature_flags = analyze_file("sample_app.py")

    print("Creating visualizations...")
    print()

    # Main call graph
    visualize_call_graph("callgraph.json", feature_flags, "callgraph_viz.png")

    # Individual feature diagrams
    with open("feature_impact_analysis.json", "r") as f:
        all_impact = json.load(f)

    for feature_name, impact_data in all_impact.items():
        output_file = f"feature_impact_{feature_name}.png"
        create_feature_impact_diagram(feature_name, impact_data, output_file)

    print()
    print("=" * 80)
    print("All visualizations created successfully!")
    print("=" * 80)
