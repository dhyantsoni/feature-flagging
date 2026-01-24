"""
Custom static call graph analyzer using Python's AST module and NetworkX.

This provides full control over the analysis and avoids third-party bugs.
"""

import ast
import json
import networkx as nx
from typing import Dict, Set, List, Tuple
from pathlib import Path


class CallGraphAnalyzer(ast.NodeVisitor):
    """AST visitor that builds a call graph"""

    def __init__(self, module_name: str = ""):
        self.module_name = module_name
        self.current_function = None
        self.current_class = None
        self.call_graph = {}
        self.functions = set()
        self.feature_flags = {}

    def visit_ClassDef(self, node):
        """Visit class definition"""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        """Visit function definition"""
        # Build fully qualified function name
        if self.current_class:
            func_name = f"{self.module_name}.{self.current_class}.{node.name}"
        else:
            func_name = f"{self.module_name}.{node.name}"

        self.functions.add(func_name)

        # Check for feature flag decorator
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if hasattr(decorator.func, 'id') and decorator.func.id == 'feature_flag':
                    if decorator.args:
                        flag_name = ast.literal_eval(decorator.args[0])
                        self.feature_flags[func_name] = flag_name

        # Initialize call list for this function
        if func_name not in self.call_graph:
            self.call_graph[func_name] = []

        # Visit function body
        old_function = self.current_function
        self.current_function = func_name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_AsyncFunctionDef(self, node):
        """Visit async function definition (treat same as regular function)"""
        self.visit_FunctionDef(node)

    def visit_Call(self, node):
        """Visit function call"""
        if self.current_function:
            # Extract called function name
            called_func = self._extract_call_name(node)

            if called_func:
                # Add to call graph
                if called_func not in self.call_graph[self.current_function]:
                    self.call_graph[self.current_function].append(called_func)

        self.generic_visit(node)

    def _extract_call_name(self, node):
        """Extract function name from Call node"""
        if isinstance(node.func, ast.Name):
            # Simple function call: func()
            return f"{self.module_name}.{node.func.id}"
        elif isinstance(node.func, ast.Attribute):
            # Method call or module.func()
            if isinstance(node.func.value, ast.Name):
                # obj.method() or module.func()
                return f"{node.func.value.id}.{node.func.attr}"
            else:
                # Complex attribute access
                return f"<dynamic>.{node.func.attr}"
        else:
            # Complex call expression
            return None


def analyze_file(file_path: str) -> Tuple[Dict, Set, Dict]:
    """
    Analyze a Python file and extract call graph.

    Returns:
        Tuple of (call_graph, functions, feature_flags)
    """
    with open(file_path, 'r') as f:
        source = f.read()

    tree = ast.parse(source, filename=file_path)

    # Extract module name from file path
    module_name = Path(file_path).stem

    analyzer = CallGraphAnalyzer(module_name)
    analyzer.visit(tree)

    return analyzer.call_graph, analyzer.functions, analyzer.feature_flags


def build_networkx_graph(call_graph: Dict) -> nx.DiGraph:
    """Build a NetworkX directed graph from call graph"""
    G = nx.DiGraph()

    # Add all nodes
    for func in call_graph.keys():
        G.add_node(func)

    # Add edges (calls)
    for caller, callees in call_graph.items():
        for callee in callees:
            G.add_edge(caller, callee)

    return G


def get_downstream_dependencies(graph: nx.DiGraph, function: str) -> Set[str]:
    """
    Get all functions called by the given function (transitive closure).
    Uses DFS to find all reachable nodes.
    """
    if function not in graph:
        return set()

    # Get all descendants (functions called directly or indirectly)
    descendants = nx.descendants(graph, function)
    return descendants


def get_upstream_dependencies(graph: nx.DiGraph, function: str) -> Set[str]:
    """
    Get all functions that call the given function (transitive closure).
    Uses reverse DFS to find all nodes that can reach this function.
    """
    if function not in graph:
        return set()

    # Get all ancestors (functions that call this directly or indirectly)
    ancestors = nx.ancestors(graph, function)
    return ancestors


def get_direct_callers(call_graph: Dict, function: str) -> Set[str]:
    """Get functions that directly call the given function"""
    callers = set()
    for caller, callees in call_graph.items():
        if function in callees:
            callers.add(caller)
    return callers


def analyze_feature_impact(call_graph: Dict, feature_flags: Dict, flag_name: str) -> Dict:
    """
    Analyze the impact of disabling a feature flag.

    Returns detailed impact report.
    """
    # Find functions with this feature flag
    flagged_functions = [
        func for func, flag in feature_flags.items()
        if flag == flag_name
    ]

    if not flagged_functions:
        return {
            "error": f"No functions found with feature flag: {flag_name}",
            "available_flags": list(set(feature_flags.values()))
        }

    # Build NetworkX graph for analysis
    graph = build_networkx_graph(call_graph)

    results = {}

    for func in flagged_functions:
        # Get downstream dependencies (functions that become unreachable)
        downstream = get_downstream_dependencies(graph, func)

        # Get upstream dependencies (functions that call this)
        upstream = get_upstream_dependencies(graph, func)

        # Get direct callers (immediate upstream)
        direct_callers = get_direct_callers(call_graph, func)

        # Find functions needing fallback (non-flagged direct callers)
        needs_fallback = set()
        for caller in direct_callers:
            if caller not in feature_flags:
                needs_fallback.add(caller)

        results[func] = {
            "feature_flag": flag_name,
            "downstream_dependencies": sorted(list(downstream)),
            "upstream_dependencies": sorted(list(upstream)),
            "direct_callers": sorted(list(direct_callers)),
            "requires_fallback_in": sorted(list(needs_fallback)),
            "impact_summary": {
                "total_affected_functions": len(downstream) + len(upstream),
                "functions_that_become_unreachable": len(downstream),
                "functions_that_depend_on_this": len(upstream),
                "direct_call_sites": len(direct_callers),
                "functions_needing_fallback_logic": len(needs_fallback)
            }
        }

    return results


def export_to_json(call_graph: Dict, output_file: str):
    """Export call graph to JSON format"""
    with open(output_file, 'w') as f:
        json.dump(call_graph, f, indent=2)


def export_to_graphviz(graph: nx.DiGraph, feature_flags: Dict, output_file: str):
    """Export graph to GraphViz DOT format"""
    with open(output_file, 'w') as f:
        f.write("digraph CallGraph {\n")
        f.write("  rankdir=LR;\n")
        f.write("  node [shape=box];\n\n")

        # Add nodes with colors for feature-flagged functions
        for node in graph.nodes():
            if node in feature_flags:
                color = "lightblue"
                label = f"{node}\\n[@{feature_flags[node]}]"
            else:
                color = "white"
                label = node

            f.write(f'  "{node}" [label="{label}", style=filled, fillcolor={color}];\n')

        f.write("\n")

        # Add edges
        for source, target in graph.edges():
            f.write(f'  "{source}" -> "{target}";\n')

        f.write("}\n")


def print_analysis_report(analysis_results: Dict):
    """Pretty print the analysis results"""
    print("=" * 80)
    print("FEATURE FLAG IMPACT ANALYSIS REPORT (AST + NetworkX)")
    print("=" * 80)

    for func_name, data in analysis_results.items():
        if "error" in data:
            print(f"\n❌ Error: {data['error']}")
            print(f"Available flags: {', '.join(data['available_flags'])}")
            continue

        print(f"\n📍 Function: {func_name}")
        print(f"🚩 Feature Flag: {data['feature_flag']}")
        print(f"\n📊 Impact Summary:")
        summary = data['impact_summary']
        print(f"  • Total affected functions: {summary['total_affected_functions']}")
        print(f"  • Functions that become unreachable: {summary['functions_that_become_unreachable']}")
        print(f"  • Functions that depend on this: {summary['functions_that_depend_on_this']}")
        print(f"  • Direct call sites: {summary['direct_call_sites']}")
        print(f"  • Functions needing fallback logic: {summary['functions_needing_fallback_logic']}")

        if data['downstream_dependencies']:
            print(f"\n⬇️  Downstream Dependencies (will become unreachable):")
            for dep in data['downstream_dependencies']:
                print(f"  • {dep}")

        if data['direct_callers']:
            print(f"\n📞 Direct Callers:")
            for dep in data['direct_callers']:
                print(f"  • {dep}")

        if data['requires_fallback_in']:
            print(f"\n⚠️  Functions Requiring Fallback Logic:")
            for dep in data['requires_fallback_in']:
                print(f"  • {dep}")

        print("\n" + "-" * 80)


if __name__ == "__main__":
    import sys

    # Analyze sample_app.py
    source_file = "sample_app.py"

    print(f"Analyzing {source_file} using AST + NetworkX...")
    print()

    # Parse and analyze
    call_graph, functions, feature_flags = analyze_file(source_file)

    print(f"✅ Analysis complete!")
    print(f"   Total functions found: {len(functions)}")
    print(f"   Total function calls: {sum(len(v) for v in call_graph.values())}")
    print(f"   Feature-flagged functions: {len(feature_flags)}")
    print()

    # Export call graph
    export_to_json(call_graph, "callgraph.json")
    print(f"✅ Call graph saved to: callgraph.json")

    # Build NetworkX graph
    graph = build_networkx_graph(call_graph)

    # Export to GraphViz
    export_to_graphviz(graph, feature_flags, "callgraph.dot")
    print(f"✅ GraphViz export saved to: callgraph.dot")

    # Analyze all feature flags
    print(f"\n{'=' * 80}")
    print("Discovered feature flags:")
    for func, flag in feature_flags.items():
        print(f"  • {flag}: {func}")
    print()

    all_results = {}
    for flag_name in set(feature_flags.values()):
        results = analyze_feature_impact(call_graph, feature_flags, flag_name)
        all_results[flag_name] = results
        print_analysis_report(results)

    # Save detailed results
    with open("feature_impact_analysis.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("\n✅ Detailed analysis saved to: feature_impact_analysis.json")
