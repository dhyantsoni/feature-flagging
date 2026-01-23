"""
Enhanced AST analyzer with smart helper function detection and Supabase integration.
Detects shared helpers that are used by multiple features vs feature-specific helpers.
"""

import ast
import json
import networkx as nx
from typing import Dict, Set, List, Tuple, Optional
from pathlib import Path
from collections import defaultdict

from ast_callgraph_analyzer import (
    CallGraphAnalyzer,
    analyze_file,
    build_networkx_graph,
    get_downstream_dependencies,
    get_upstream_dependencies
)


class EnhancedCallGraphAnalyzer(CallGraphAnalyzer):
    """Extended analyzer with helper detection and complexity metrics"""

    def __init__(self, module_name: str = ""):
        super().__init__(module_name)
        self.function_complexity = {}  # Track cyclomatic complexity
        self.function_lines = {}  # Track line numbers

    def visit_FunctionDef(self, node):
        """Extended function visitor that tracks additional metrics"""
        # Call parent implementation
        super().visit_FunctionDef(node)

        # Build function name
        if self.current_class:
            func_name = f"{self.module_name}.{self.current_class}.{node.name}"
        else:
            func_name = f"{self.module_name}.{node.name}"

        # Track line number
        self.function_lines[func_name] = node.lineno

        # Calculate basic complexity (count decision points)
        complexity = self._calculate_complexity(node)
        self.function_complexity[func_name] = complexity

    def _calculate_complexity(self, node) -> int:
        """Calculate cyclomatic complexity (simplified)"""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Count decision points
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity


def detect_helper_functions(call_graph: Dict, feature_flags: Dict,
                            graph: nx.DiGraph) -> Tuple[Dict[str, dict], Set[str]]:
    """
    Detect helper functions and classify them as feature-specific or shared.

    Returns:
        Tuple of (helper_info, shared_helpers)
        - helper_info: Dict mapping function names to helper metadata
        - shared_helpers: Set of functions used by multiple features
    """
    helper_info = {}
    feature_to_helpers = defaultdict(set)

    # For each feature-flagged function, find its downstream dependencies
    for flagged_func, flag_name in feature_flags.items():
        if flagged_func not in graph:
            continue

        # Get all downstream functions (helpers used by this feature)
        downstream = get_downstream_dependencies(graph, flagged_func)

        for helper_func in downstream:
            # Skip if it's also a feature-flagged function
            if helper_func not in feature_flags:
                feature_to_helpers[flag_name].add(helper_func)

                if helper_func not in helper_info:
                    helper_info[helper_func] = {
                        "used_by_features": set(),
                        "is_shared": False,
                        "is_leaf": len(call_graph.get(helper_func, [])) == 0
                    }

                helper_info[helper_func]["used_by_features"].add(flag_name)

    # Identify shared helpers (used by multiple features)
    shared_helpers = set()
    for helper_func, info in helper_info.items():
        if len(info["used_by_features"]) > 1:
            info["is_shared"] = True
            shared_helpers.add(helper_func)

    # Convert sets to lists for JSON serialization
    for helper_func in helper_info:
        helper_info[helper_func]["used_by_features"] = list(
            helper_info[helper_func]["used_by_features"]
        )

    return helper_info, shared_helpers


def calculate_feature_disable_impact(call_graph: Dict, feature_flags: Dict,
                                     graph: nx.DiGraph, flag_name: str,
                                     helper_info: Dict[str, dict]) -> Dict:
    """
    Calculate what happens when a feature is disabled, considering shared helpers.

    Returns detailed impact including:
    - Functions that can be safely disabled (feature-specific)
    - Functions that must remain (shared helpers)
    - Fallback requirements
    """
    # Find functions with this feature flag
    flagged_functions = [
        func for func, flag in feature_flags.items()
        if flag == flag_name
    ]

    if not flagged_functions:
        return {"error": f"No functions found with feature flag: {flag_name}"}

    results = {}

    for func in flagged_functions:
        if func not in graph:
            continue

        # Get downstream dependencies
        downstream = get_downstream_dependencies(graph, func)

        # Classify downstream functions
        can_disable = set()  # Feature-specific, can be disabled
        must_keep = set()    # Shared helpers, must keep active

        for dep_func in downstream:
            if dep_func in helper_info:
                if helper_info[dep_func]["is_shared"]:
                    must_keep.add(dep_func)
                else:
                    can_disable.add(dep_func)
            else:
                # Not a helper, probably can disable if it's feature-specific
                can_disable.add(dep_func)

        # Get upstream dependencies (who calls this feature)
        upstream = get_upstream_dependencies(graph, func)

        # Find direct callers needing fallback
        direct_callers = set()
        for caller, callees in call_graph.items():
            if func in callees:
                direct_callers.add(caller)

        needs_fallback = set()
        for caller in direct_callers:
            if caller not in feature_flags:
                needs_fallback.add(caller)

        results[func] = {
            "feature_flag": flag_name,
            "can_safely_disable": sorted(list(can_disable)),
            "must_keep_active": sorted(list(must_keep)),
            "must_keep_reasons": {
                fn: f"Shared by features: {', '.join(helper_info[fn]['used_by_features'])}"
                for fn in must_keep if fn in helper_info
            },
            "upstream_dependencies": sorted(list(upstream)),
            "direct_callers": sorted(list(direct_callers)),
            "requires_fallback_in": sorted(list(needs_fallback)),
            "impact_summary": {
                "total_downstream": len(downstream),
                "can_disable_count": len(can_disable),
                "must_keep_count": len(must_keep),
                "functions_need_fallback": len(needs_fallback)
            }
        }

    return results


def analyze_codebase_with_helpers(file_path: str) -> Dict:
    """
    Comprehensive analysis including helper detection.

    Returns complete analysis with:
    - Call graph
    - Function list
    - Feature flags
    - Helper classification
    - Shared helper detection
    - Feature disable impact
    """
    # Basic analysis
    call_graph, functions, feature_flags = analyze_file(file_path)

    # Build graph
    graph = build_networkx_graph(call_graph)

    # Analyze with enhanced analyzer for complexity metrics
    with open(file_path, 'r') as f:
        source = f.read()
    tree = ast.parse(source, filename=file_path)
    module_name = Path(file_path).stem
    enhanced_analyzer = EnhancedCallGraphAnalyzer(module_name)
    enhanced_analyzer.visit(tree)

    # Detect helpers
    helper_info, shared_helpers = detect_helper_functions(call_graph, feature_flags, graph)

    # Calculate impact for each feature
    feature_impact = {}
    for flag_name in set(feature_flags.values()):
        impact = calculate_feature_disable_impact(
            call_graph, feature_flags, graph, flag_name, helper_info
        )
        feature_impact[flag_name] = impact

    return {
        "file_path": file_path,
        "call_graph": call_graph,
        "functions": list(functions),
        "feature_flags": feature_flags,
        "helper_functions": helper_info,
        "shared_helpers": list(shared_helpers),
        "function_complexity": enhanced_analyzer.function_complexity,
        "function_lines": enhanced_analyzer.function_lines,
        "feature_impact": feature_impact,
        "statistics": {
            "total_functions": len(functions),
            "total_calls": sum(len(v) for v in call_graph.values()),
            "feature_flagged_functions": len(feature_flags),
            "helper_functions": len(helper_info),
            "shared_helpers": len(shared_helpers),
            "features": len(set(feature_flags.values()))
        }
    }


def get_functions_for_feature(analysis: Dict, feature_name: str) -> Dict[str, List[str]]:
    """
    Get all functions associated with a feature, organized by type.

    Returns:
        Dict with categories: entry_point, can_disable, must_keep
    """
    feature_flags = analysis["feature_flags"]
    feature_impact = analysis["feature_impact"]

    # Find entry point (main feature-flagged function)
    entry_points = [
        func for func, flag in feature_flags.items()
        if flag == feature_name
    ]

    if feature_name not in feature_impact:
        return {
            "entry_points": entry_points,
            "can_disable": [],
            "must_keep": []
        }

    # Get impact data
    can_disable = set()
    must_keep = set()

    for func_impact in feature_impact[feature_name].values():
        if isinstance(func_impact, dict):
            can_disable.update(func_impact.get("can_safely_disable", []))
            must_keep.update(func_impact.get("must_keep_active", []))

    return {
        "entry_points": entry_points,
        "can_disable": sorted(list(can_disable)),
        "must_keep": sorted(list(must_keep))
    }


def print_helper_analysis(analysis: Dict):
    """Pretty print helper function analysis"""
    print("=" * 80)
    print("ENHANCED FUNCTION GRAPH ANALYSIS WITH HELPER DETECTION")
    print("=" * 80)

    stats = analysis["statistics"]
    print(f"\n📊 Statistics:")
    print(f"   Total functions: {stats['total_functions']}")
    print(f"   Feature-flagged functions: {stats['feature_flagged_functions']}")
    print(f"   Helper functions: {stats['helper_functions']}")
    print(f"   Shared helpers: {stats['shared_helpers']}")
    print(f"   Total features: {stats['features']}")

    print(f"\n🔍 Shared Helpers (used by multiple features):")
    for helper in analysis["shared_helpers"]:
        info = analysis["helper_functions"][helper]
        print(f"   • {helper}")
        print(f"     Used by: {', '.join(info['used_by_features'])}")

    print(f"\n🚩 Feature Impact Analysis:")
    for feature_name, impact_data in analysis["feature_impact"].items():
        print(f"\n   Feature: {feature_name}")
        for func, impact in impact_data.items():
            if isinstance(impact, dict) and "impact_summary" in impact:
                summary = impact["impact_summary"]
                print(f"      Entry point: {func}")
                print(f"      Can safely disable: {summary['can_disable_count']} functions")
                print(f"      Must keep active: {summary['must_keep_count']} shared helpers")
                print(f"      Need fallback logic: {summary['functions_need_fallback']} functions")


if __name__ == "__main__":
    import sys

    source_file = sys.argv[1] if len(sys.argv) > 1 else "sample_app.py"

    print(f"Analyzing {source_file} with enhanced helper detection...")
    print()

    analysis = analyze_codebase_with_helpers(source_file)

    print_helper_analysis(analysis)

    # Save detailed results
    output_file = "enhanced_analysis.json"
    with open(output_file, "w") as f:
        json.dump(analysis, f, indent=2)

    print(f"\n✅ Detailed analysis saved to: {output_file}")
