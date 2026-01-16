"""
Generate call graph using Pyan3.
This script analyzes sample_app.py and creates a call graph.
"""

import subprocess
import sys
import os
import json
import re

def generate_call_graph_programmatic(source_file):
    """
    Generate call graph using Pyan3 programmatically to avoid CLI bugs
    """
    try:
        from pyan.analyzer import CallGraphVisitor
        from pyan.visgraph import VisualGraph
        from pyan.writers import DotWriter
        import logging

        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        print(f"Analyzing {source_file}...")

        # Create visitor
        visitor = CallGraphVisitor([source_file], logger=logger)

        # Visit the file
        visitor.analyze()

        # Create visual graph
        graph = VisualGraph.from_visitor(
            visitor,
            options={
                'draw_defines': True,
                'draw_uses': True,
                'colored': True,
                'grouped': True,
                'annotated': True
            },
            logger=logger
        )

        # Generate DOT output
        writer = DotWriter(
            graph,
            options=['draw_defines', 'draw_uses', 'colored', 'grouped', 'annotated'],
            output='callgraph.dot',
            logger=logger
        )

        dot_output = writer.run()

        # Save DOT file
        with open("callgraph.dot", "w") as f:
            f.write(dot_output)

        print(f"✅ Call graph generated successfully!")
        print(f"   Output saved to: callgraph.dot")

        # Also extract JSON representation for easier parsing
        callgraph_json = extract_graph_to_json(visitor)
        with open("callgraph.json", "w") as f:
            json.dump(callgraph_json, f, indent=2)

        print(f"✅ JSON format saved to: callgraph.json")
        print(f"   Total nodes: {len(callgraph_json)}")

        # Generate PNG if GraphViz is available
        try:
            subprocess.run(
                ["dot", "-Tpng", "callgraph.dot", "-o", "callgraph.png"],
                capture_output=True,
                check=True
            )
            print(f"✅ GraphViz visualization created: callgraph.png")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("ℹ️  GraphViz not installed - skipping PNG generation")

        return True

    except Exception as e:
        print(f"❌ Error generating call graph: {e}")
        import traceback
        traceback.print_exc()
        return False


def extract_graph_to_json(visitor):
    """
    Extract call graph from visitor into JSON format similar to PyCG
    """
    callgraph = {}

    # Extract all nodes and their relationships
    for node in visitor.nodes:
        node_name = str(node.get_short_name())
        callees = []

        # Get all targets this node calls
        for edge in visitor.uses_edges:
            if str(edge.source.get_short_name()) == node_name:
                target = str(edge.target.get_short_name())
                callees.append(target)

        # Also check defines edges (for definitions)
        for edge in visitor.defines_edges:
            if str(edge.source.get_short_name()) == node_name:
                target = str(edge.target.get_short_name())
                if target not in callees:
                    callees.append(target)

        callgraph[node_name] = callees

    return callgraph


def generate_call_graph(source_file, output_format="dot"):
    """
    Generate call graph using Pyan3

    Args:
        source_file: Python file to analyze
        output_format: Output format (dot, tgf, yed)
    """
    # Use programmatic approach due to CLI bugs
    return generate_call_graph_programmatic(source_file)


if __name__ == "__main__":
    source_file = "sample_app.py"

    if not os.path.exists(source_file):
        print(f"❌ Error: {source_file} not found")
        sys.exit(1)

    # Generate in DOT format (GraphViz)
    success = generate_call_graph(source_file, "dot")

    if success:
        print("\n" + "=" * 80)
        print("Next steps:")
        print("  1. View callgraph.dot in a text editor")
        print("  2. View callgraph.png if GraphViz is installed")
        print("  3. Run feature_flag_analyzer_pyan.py for impact analysis")
        print("=" * 80)

    sys.exit(0 if success else 1)
