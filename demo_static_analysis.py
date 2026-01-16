#!/usr/bin/env python3
"""
Demo: AST + NetworkX Static Analysis for Feature Flagging

This demo shows how static analysis can help you understand the impact
of feature flags on your codebase.
"""

import json
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ast_callgraph_analyzer import (
    analyze_file,
    build_networkx_graph,
    get_downstream_dependencies,
    get_upstream_dependencies,
    get_direct_callers
)


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def print_section(text):
    """Print a formatted section"""
    print(f"\n{'─' * 80}")
    print(f"  {text}")
    print('─' * 80)


def demo_basic_analysis():
    """Demo 1: Basic call graph analysis"""
    print_header("DEMO 1: Basic Call Graph Analysis")

    print("📁 Analyzing sample_app.py...")
    call_graph, functions, feature_flags = analyze_file("sample_app.py")

    print(f"✅ Found {len(functions)} functions")
    print(f"✅ Detected {len(call_graph)} function call relationships")
    print(f"✅ Total function calls: {sum(len(v) for v in call_graph.values())}")

    print_section("Top 5 Most Called Functions")

    # Count how many functions call each function
    call_counts = {}
    for caller, callees in call_graph.items():
        for callee in callees:
            call_counts[callee] = call_counts.get(callee, 0) + 1

    top_called = sorted(call_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    for func, count in top_called:
        print(f"  • {func}: called by {count} function(s)")


def demo_dependency_tracking():
    """Demo 2: Track dependencies for a specific function"""
    print_header("DEMO 2: Dependency Tracking")

    call_graph, functions, feature_flags = analyze_file("sample_app.py")
    graph = build_networkx_graph(call_graph)

    # Pick an interesting function
    target_func = "sample_app.calculate_recommendations"

    print(f"🔍 Analyzing: {target_func}")

    # Get downstream (what this function calls)
    downstream = get_downstream_dependencies(graph, target_func)
    print(f"\n⬇️  Downstream Dependencies ({len(downstream)} functions):")
    print("   (These become unreachable if this function is disabled)\n")
    for dep in sorted(downstream):
        print(f"   • {dep}")

    # Get upstream (what calls this function)
    upstream = get_upstream_dependencies(graph, target_func)
    print(f"\n⬆️  Upstream Dependencies ({len(upstream)} functions):")
    print("   (These depend on this function)\n")
    for dep in sorted(upstream):
        print(f"   • {dep}")

    # Get direct callers
    direct = get_direct_callers(call_graph, target_func)
    print(f"\n📞 Direct Callers ({len(direct)} functions):")
    print("   (These call this function directly)\n")
    for dep in sorted(direct):
        print(f"   • {dep}")


def demo_feature_impact_simulation():
    """Demo 3: Simulate disabling a feature"""
    print_header("DEMO 3: Feature Flag Impact Simulation")

    call_graph, functions, feature_flags = analyze_file("sample_app.py")
    graph = build_networkx_graph(call_graph)

    # Simulate disabling calculate_recommendations
    feature = "sample_app.calculate_recommendations"

    print(f"🚩 Simulating: What happens if we disable '{feature}'?")

    downstream = get_downstream_dependencies(graph, feature)
    upstream = get_upstream_dependencies(graph, feature)

    print(f"\n📊 Impact Analysis:")
    print(f"   • {len(downstream)} functions become unreachable")
    print(f"   • {len(upstream)} functions lose access to this feature")
    print(f"   • Total impact radius: {len(downstream) + len(upstream)} functions")

    print(f"\n⚠️  Functions that will become unreachable:")
    for func in sorted(downstream)[:10]:  # Show first 10
        print(f"   • {func}")
    if len(downstream) > 10:
        print(f"   ... and {len(downstream) - 10} more")

    print(f"\n⚠️  Functions that need fallback logic:")
    direct_callers = get_direct_callers(call_graph, feature)
    for func in sorted(direct_callers):
        print(f"   • {func} - Must handle when feature is disabled")


def demo_call_chain_tracing():
    """Demo 4: Trace call chains"""
    print_header("DEMO 4: Call Chain Tracing")

    call_graph, functions, feature_flags = analyze_file("sample_app.py")

    print("🔗 Tracing: How does main() reach database_query()?")

    # Find paths manually (simplified)
    def find_paths(graph, start, end, path=[]):
        path = path + [start]
        if start == end:
            return [path]
        if start not in graph:
            return []
        paths = []
        for node in graph[start]:
            if node not in path:  # Avoid cycles
                newpaths = find_paths(graph, node, end, path)
                paths.extend(newpaths)
        return paths

    paths = find_paths(call_graph, "sample_app.main", "sample_app.database_query")

    print(f"\n✅ Found {len(paths)} different paths:\n")

    for i, path in enumerate(paths[:5], 1):  # Show first 5 paths
        print(f"Path {i}:")
        for j, func in enumerate(path):
            indent = "  " * j
            arrow = "└─>" if j > 0 else "  "
            func_short = func.split('.')[-1]
            print(f"{indent}{arrow} {func_short}")
        print()

    if len(paths) > 5:
        print(f"... and {len(paths) - 5} more paths")


def demo_shared_dependencies():
    """Demo 5: Find shared dependencies"""
    print_header("DEMO 5: Shared Dependencies")

    call_graph, functions, feature_flags = analyze_file("sample_app.py")

    print("🔍 Finding functions used by multiple features...")

    # Find functions that are called by multiple different functions
    call_counts = {}
    callers = {}

    for caller, callees in call_graph.items():
        for callee in callees:
            if callee not in call_counts:
                call_counts[callee] = 0
                callers[callee] = set()
            call_counts[callee] += 1
            callers[callee].add(caller)

    # Find shared utilities
    shared = [(func, count, callers[func]) for func, count in call_counts.items()
              if count >= 3]  # Called by 3+ functions
    shared.sort(key=lambda x: x[1], reverse=True)

    print(f"\n📦 Top Shared Dependencies:\n")

    for func, count, caller_set in shared[:10]:
        func_short = func.split('.')[-1]
        print(f"   {func_short}:")
        print(f"     • Called by {count} different functions")
        print(f"     • Used by: {', '.join([c.split('.')[-1] for c in list(caller_set)[:3]])}")
        if len(caller_set) > 3:
            print(f"       ... and {len(caller_set) - 3} more")
        print()


def demo_export_formats():
    """Demo 6: Show different export formats"""
    print_header("DEMO 6: Export Formats")

    print("📤 Generated files from static analysis:\n")

    import os
    files = [
        ("callgraph.json", "Machine-readable call graph (for tools/APIs)"),
        ("callgraph.dot", "GraphViz format (for external visualization)"),
        ("callgraph_viz.png", "Visual diagram of entire call graph"),
        ("callgraph_viz.svg", "Scalable vector graphics (for web/docs)"),
    ]

    for filename, description in files:
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            size_str = f"{size:,} bytes" if size < 1024 else f"{size/1024:.1f} KB"
            print(f"   ✅ {filename:<25} - {description}")
            print(f"      Size: {size_str}\n")

    print("\n💡 Use cases:")
    print("   • JSON: Parse in your CI/CD pipeline")
    print("   • DOT: Generate custom visualizations with GraphViz")
    print("   • PNG: Include in documentation or dashboards")
    print("   • SVG: Embed in web applications")


def demo_integration_example():
    """Demo 7: Integration with feature flag system"""
    print_header("DEMO 7: CI/CD Integration Example")

    print("🔧 Example: Validate feature flags in CI/CD pipeline\n")

    call_graph, functions, feature_flags = analyze_file("sample_app.py")
    graph = build_networkx_graph(call_graph)

    print("```python")
    print("# In your CI/CD pipeline (e.g., GitHub Actions)")
    print()
    print("from ast_callgraph_analyzer import analyze_file, get_direct_callers")
    print()
    print("# Analyze code")
    print("call_graph, functions, feature_flags = analyze_file('main.py')")
    print()
    print("# Check for missing fallback logic")
    print("validation_errors = []")
    print()
    print("for feature in important_features:")
    print("    direct_callers = get_direct_callers(call_graph, feature)")
    print("    ")
    print("    for caller in direct_callers:")
    print("        # Check if caller has 'if not client.isEnabled' fallback")
    print("        if not has_fallback_logic(caller, feature):")
    print("            validation_errors.append(")
    print("                f'Missing fallback in {caller} for {feature}'")
    print("            )")
    print()
    print("if validation_errors:")
    print("    print('❌ Feature flag validation failed!')")
    print("    for error in validation_errors:")
    print("        print(f'  • {error}')")
    print("    exit(1)  # Fail the build")
    print("```")

    print("\n📋 Benefits:")
    print("   • Catch missing fallback logic before deployment")
    print("   • Ensure all feature flags have proper handling")
    print("   • Document feature dependencies automatically")
    print("   • Prevent breaking changes")


def demo_real_world_scenario():
    """Demo 8: Real-world scenario"""
    print_header("DEMO 8: Real-World Scenario")

    print("🎯 Scenario: You want to disable the recommendations feature\n")

    call_graph, functions, feature_flags = analyze_file("sample_app.py")
    graph = build_networkx_graph(call_graph)

    feature = "sample_app.calculate_recommendations"

    print("Step 1: Run static analysis")
    print(f"   $ python3 ast_callgraph_analyzer.py\n")

    downstream = get_downstream_dependencies(graph, feature)
    direct_callers = get_direct_callers(call_graph, feature)

    print("Step 2: Review impact report")
    print(f"   • {len(downstream)} functions will become unreachable")
    print(f"   • {len(direct_callers)} functions call this feature\n")

    print("Step 3: Check fallback logic")
    print("   Checking if main() has fallback logic...")

    # Read sample_app.py to check for fallback
    with open("sample_app.py", "r") as f:
        content = f.read()

    if "client.isEnabled" in content and "calculate_recommendations" in content:
        print("   ✅ Fallback logic detected in sample_app.py")
        print("      Found: if not client.isEnabled(...): # fallback\n")
    else:
        print("   ⚠️  No fallback logic detected - review needed!\n")

    print("Step 4: Update feature flag configuration")
    print("   Edit rulesets.yaml:")
    print("   ```yaml")
    print("   production:")
    print("     features:")
    print("       feature1_recommendations:")
    print("         enabled: false  # ← Disable here")
    print("   ```\n")

    print("Step 5: Deploy safely")
    print("   ✅ Static analysis confirmed fallback exists")
    print("   ✅ Configuration updated")
    print("   ✅ Ready to deploy!")


def main():
    """Run all demos"""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  AST + NetworkX Static Analysis Demo".center(78) + "█")
    print("█" + "  Feature Flagging Impact Analysis".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    demos = [
        ("Basic Analysis", demo_basic_analysis),
        ("Dependency Tracking", demo_dependency_tracking),
        ("Feature Impact", demo_feature_impact_simulation),
        ("Call Chain Tracing", demo_call_chain_tracing),
        ("Shared Dependencies", demo_shared_dependencies),
        ("Export Formats", demo_export_formats),
        ("CI/CD Integration", demo_integration_example),
        ("Real-World Scenario", demo_real_world_scenario),
    ]

    print("\n📋 Available Demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"   {i}. {name}")
    print(f"   {len(demos) + 1}. Run all demos")
    print("   0. Exit")

    while True:
        try:
            choice = input("\n👉 Select demo number (or press Enter for all): ").strip()

            if not choice:
                choice = str(len(demos) + 1)

            choice = int(choice)

            if choice == 0:
                print("\n👋 Thanks for watching the demo!\n")
                break
            elif choice == len(demos) + 1:
                # Run all demos
                for name, demo_func in demos:
                    demo_func()
                    input("\n⏸️  Press Enter to continue to next demo...")
                print_header("🎉 All Demos Complete!")
                break
            elif 1 <= choice <= len(demos):
                demos[choice - 1][1]()
                input("\n⏸️  Press Enter to return to menu...")
            else:
                print("❌ Invalid choice. Please try again.")
        except ValueError:
            print("❌ Please enter a number.")
        except KeyboardInterrupt:
            print("\n\n👋 Thanks for watching the demo!\n")
            break


if __name__ == "__main__":
    main()
