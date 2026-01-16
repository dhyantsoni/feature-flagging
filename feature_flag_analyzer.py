"""
Feature Flag Impact Analyzer using PyCG call graph.

This tool analyzes the impact of disabling a feature-flagged function by:
1. Identifying all functions called by the flagged function (downstream dependencies)
2. Identifying all functions that call the flagged function (upstream dependencies)
3. Determining which functions might need fallback handling
"""

import json
import ast
from typing import Set, Dict, List, Tuple


class FeatureFlagAnalyzer:
    def __init__(self, callgraph_file: str, source_file: str):
        """Initialize analyzer with call graph and source file"""
        with open(callgraph_file, 'r') as f:
            self.callgraph = json.load(f)

        self.source_file = source_file
        self.feature_flags = self._extract_feature_flags()

    def _extract_feature_flags(self) -> Dict[str, str]:
        """Extract feature flag mappings from source code"""
        feature_flags = {}

        with open(self.source_file, 'r') as f:
            tree = ast.parse(f.read(), filename=self.source_file)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if hasattr(decorator.func, 'id') and decorator.func.id == 'feature_flag':
                            if decorator.args:
                                flag_name = ast.literal_eval(decorator.args[0])
                                func_name = f"sample_app.{node.name}"
                                feature_flags[func_name] = flag_name

        return feature_flags

    def get_downstream_dependencies(self, function_name: str, visited: Set[str] = None) -> Set[str]:
        """
        Get all functions called by the given function (downstream).
        This represents functions that won't be reached if the feature is disabled.
        """
        if visited is None:
            visited = set()

        if function_name in visited or function_name not in self.callgraph:
            return visited

        visited.add(function_name)

        # Get direct callees
        callees = self.callgraph.get(function_name, [])

        for callee in callees:
            # Skip builtins
            if not callee.startswith("<builtin>"):
                self.get_downstream_dependencies(callee, visited)

        return visited

    def get_upstream_dependencies(self, function_name: str) -> Set[str]:
        """
        Get all functions that call the given function (upstream).
        This represents functions that depend on the flagged feature.
        """
        callers = set()

        for func, callees in self.callgraph.items():
            if function_name in callees:
                # Skip builtins
                if not func.startswith("<builtin>"):
                    callers.add(func)

        return callers

    def analyze_feature_impact(self, feature_flag_name: str) -> Dict:
        """
        Analyze the full impact of disabling a feature flag.
        Returns both upstream and downstream dependencies.
        """
        # Find the function(s) with this feature flag
        flagged_functions = [
            func for func, flag in self.feature_flags.items()
            if flag == feature_flag_name
        ]

        if not flagged_functions:
            return {
                "error": f"No functions found with feature flag: {feature_flag_name}",
                "available_flags": list(set(self.feature_flags.values()))
            }

        results = {}

        for func in flagged_functions:
            downstream = self.get_downstream_dependencies(func)
            downstream.discard(func)  # Remove the function itself

            upstream = self.get_upstream_dependencies(func)

            # Find upstream functions that might need fallback logic
            needs_fallback = set()
            for caller in upstream:
                # If caller is not feature-flagged, it needs fallback handling
                if caller not in self.feature_flags:
                    needs_fallback.add(caller)

            results[func] = {
                "feature_flag": feature_flag_name,
                "downstream_dependencies": sorted(list(downstream)),
                "upstream_dependencies": sorted(list(upstream)),
                "requires_fallback_in": sorted(list(needs_fallback)),
                "impact_summary": {
                    "total_affected_functions": len(downstream) + len(upstream),
                    "functions_that_become_unreachable": len(downstream),
                    "functions_that_depend_on_this": len(upstream),
                    "functions_needing_fallback_logic": len(needs_fallback)
                }
            }

        return results

    def analyze_all_features(self) -> Dict:
        """Analyze impact of all feature flags"""
        all_results = {}
        unique_flags = set(self.feature_flags.values())

        for flag in unique_flags:
            all_results[flag] = self.analyze_feature_impact(flag)

        return all_results

    def get_dependency_chain(self, function_name: str, target: str,
                            visited: Set[str] = None, path: List[str] = None) -> List[List[str]]:
        """
        Find all paths from function_name to target function.
        Useful for understanding dependency chains.
        """
        if visited is None:
            visited = set()
        if path is None:
            path = []

        path = path + [function_name]
        visited.add(function_name)

        if function_name == target:
            return [path]

        if function_name not in self.callgraph:
            return []

        paths = []
        for callee in self.callgraph[function_name]:
            if callee not in visited and not callee.startswith("<builtin>"):
                new_paths = self.get_dependency_chain(callee, target, visited.copy(), path)
                paths.extend(new_paths)

        return paths


def print_analysis_report(analysis_results: Dict):
    """Pretty print the analysis results"""
    print("=" * 80)
    print("FEATURE FLAG IMPACT ANALYSIS REPORT")
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
        print(f"  • Functions needing fallback logic: {summary['functions_needing_fallback_logic']}")

        if data['downstream_dependencies']:
            print(f"\n⬇️  Downstream Dependencies (will become unreachable):")
            for dep in data['downstream_dependencies']:
                print(f"  • {dep}")

        if data['upstream_dependencies']:
            print(f"\n⬆️  Upstream Dependencies (depend on this feature):")
            for dep in data['upstream_dependencies']:
                print(f"  • {dep}")

        if data['requires_fallback_in']:
            print(f"\n⚠️  Functions Requiring Fallback Logic:")
            for dep in data['requires_fallback_in']:
                print(f"  • {dep}")

        print("\n" + "-" * 80)


if __name__ == "__main__":
    # Initialize analyzer
    analyzer = FeatureFlagAnalyzer("callgraph.json", "sample_app.py")

    print("Discovered feature flags:")
    for func, flag in analyzer.feature_flags.items():
        print(f"  • {flag}: {func}")
    print()

    # Analyze all features
    all_results = analyzer.analyze_all_features()

    for flag_name, results in all_results.items():
        print_analysis_report(results)

    # Save detailed results to JSON
    with open("feature_impact_analysis.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("\n✅ Detailed analysis saved to: feature_impact_analysis.json")
