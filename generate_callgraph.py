"""
Generate call graph using PyCG programmatically.
This script analyzes sample_app.py and creates a call graph.
"""

import json
import sys
import importlib.abc

# Monkey patch for PyCG compatibility issue
if not hasattr(importlib, 'abc'):
    importlib.abc = importlib.abc

from pycg.pycg import CallGraphGenerator
from pycg import formats

def generate_call_graph(entry_point, package_name="."):
    """Generate call graph for the given entry point"""

    # Initialize call graph generator
    cg_generator = CallGraphGenerator(
        [entry_point],
        package_name,
        max_iter=3,
        operation="call-graph"
    )

    # Generate the call graph
    cg_generator.analyze()

    # Get the call graph
    formatter = formats.Simple(cg_generator)

    return formatter.generate()


if __name__ == "__main__":
    entry_point = "sample_app.py"

    print("Generating call graph...")
    try:
        call_graph = generate_call_graph(entry_point)

        # Save to JSON file
        with open("callgraph.json", "w") as f:
            json.dump(call_graph, f, indent=2)

        print(f"Call graph generated successfully!")
        print(f"Total functions found: {len(call_graph)}")
        print(f"Output saved to: callgraph.json")

    except Exception as e:
        print(f"Error generating call graph: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
