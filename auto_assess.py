"""
Auto-assessment script for AST analysis results.
Generates actionable recommendations from codebase analysis.
"""

import json
import sys
from typing import Dict, List, Tuple
from collections import defaultdict


def load_analysis(filepath: str) -> Dict:
    """Load analysis JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def assess_complexity(analysis: Dict, threshold: int = 15) -> List[Dict]:
    """
    Assess functions by cyclomatic complexity.
    Returns list of high-complexity functions with recommendations.
    """
    high_complexity = analysis.get('high_complexity', {})
    if not high_complexity:
        high_complexity = {
            k: v for k, v in analysis.get('function_complexity', {}).items()
            if v > threshold
        }

    recommendations = []
    for func, complexity in sorted(high_complexity.items(), key=lambda x: -x[1]):
        severity = "CRITICAL" if complexity > 40 else "HIGH" if complexity > 25 else "MEDIUM"
        rec = {
            "function": func,
            "complexity": complexity,
            "severity": severity,
            "recommendation": f"Refactor into smaller functions. Consider extracting {complexity // 10} helper functions.",
            "estimated_helpers": max(2, complexity // 10)
        }
        recommendations.append(rec)

    return recommendations


def assess_feature_flags(analysis: Dict) -> Dict:
    """
    Assess feature flag coverage and risk.
    """
    feature_flags = analysis.get('feature_flags', {})
    feature_impact = analysis.get('feature_impact', {})

    # Group by feature
    features = defaultdict(list)
    for func, flag in feature_flags.items():
        features[flag].append(func)

    assessment = {
        "total_features": len(features),
        "total_flagged_functions": len(feature_flags),
        "features": {}
    }

    for feature, funcs in features.items():
        impact_data = feature_impact.get(feature, {})
        total_downstream = 0
        total_must_keep = 0

        for func in funcs:
            if func in impact_data:
                summary = impact_data[func].get('impact_summary', {})
                total_downstream += summary.get('can_disable_count', 0)
                total_must_keep += summary.get('must_keep_count', 0)

        risk_level = "HIGH" if total_must_keep > 5 else "MEDIUM" if total_downstream > 10 else "LOW"

        assessment["features"][feature] = {
            "entry_points": funcs,
            "entry_point_count": len(funcs),
            "downstream_functions": total_downstream,
            "shared_dependencies": total_must_keep,
            "risk_level": risk_level,
            "recommendation": (
                f"Feature '{feature}' has {len(funcs)} entry points. "
                f"Disabling would affect ~{total_downstream} functions. "
                f"{total_must_keep} shared helpers must remain active."
            )
        }

    return assessment


def assess_dead_code(analysis: Dict) -> List[str]:
    """
    Find potentially dead code (functions never called).
    """
    functions = set(analysis.get('functions', []))
    call_graph = analysis.get('call_graph', {})

    # Find all called functions
    called_functions = set()
    for caller, callees in call_graph.items():
        for callee in callees:
            called_functions.add(callee)

    # Functions that are never called (potential dead code)
    # Exclude entry points (routes, main, etc.)
    never_called = []
    for func in functions:
        if func not in called_functions:
            # Skip likely entry points
            if any(x in func.lower() for x in ['route', 'main', 'handler', 'callback', 'test']):
                continue
            never_called.append(func)

    return never_called


def assess_helper_dependencies(analysis: Dict) -> Dict:
    """
    Assess helper function dependencies and shared helpers.
    """
    helper_functions = analysis.get('helper_functions', {})
    shared_helpers = analysis.get('shared_helpers', [])

    return {
        "total_helpers": len(helper_functions),
        "shared_helpers_count": len(shared_helpers),
        "shared_helpers": shared_helpers,
        "risk_assessment": (
            "HIGH" if len(shared_helpers) > 10 else
            "MEDIUM" if len(shared_helpers) > 3 else
            "LOW"
        ),
        "recommendation": (
            f"{len(shared_helpers)} shared helpers are used by multiple features. "
            f"Changes to these require careful testing across all dependent features."
        )
    }


def generate_report(analysis: Dict) -> Dict:
    """
    Generate comprehensive assessment report.
    """
    report = {
        "summary": {
            "files_analyzed": analysis.get('files_analyzed', 1),
            "total_functions": analysis.get('total_functions', len(analysis.get('functions', []))),
            "feature_flagged": len(analysis.get('feature_flags', {})),
        },
        "complexity_assessment": assess_complexity(analysis),
        "feature_flag_assessment": assess_feature_flags(analysis),
        "helper_assessment": assess_helper_dependencies(analysis),
        "potential_dead_code": assess_dead_code(analysis),
        "actionable_items": []
    }

    # Generate actionable items
    actions = []

    # High complexity items
    critical = [r for r in report["complexity_assessment"] if r["severity"] == "CRITICAL"]
    if critical:
        actions.append({
            "priority": "HIGH",
            "category": "Refactoring",
            "action": f"Refactor {len(critical)} critical complexity functions",
            "details": [f["function"] for f in critical[:5]]
        })

    # Feature flag items
    for feature, data in report["feature_flag_assessment"].get("features", {}).items():
        if data["risk_level"] == "HIGH":
            actions.append({
                "priority": "MEDIUM",
                "category": "Feature Flags",
                "action": f"Review high-risk feature '{feature}'",
                "details": data["recommendation"]
            })

    # Dead code items
    dead_code = report["potential_dead_code"]
    if len(dead_code) > 5:
        actions.append({
            "priority": "LOW",
            "category": "Cleanup",
            "action": f"Review {len(dead_code)} potentially unused functions",
            "details": dead_code[:10]
        })

    report["actionable_items"] = actions
    return report


def print_report(report: Dict):
    """Pretty print the assessment report."""
    print("=" * 80)
    print("CODEBASE ASSESSMENT REPORT")
    print("=" * 80)

    # Summary
    summary = report["summary"]
    print(f"\n📊 Summary:")
    print(f"   Files analyzed: {summary['files_analyzed']}")
    print(f"   Total functions: {summary['total_functions']}")
    print(f"   Feature-flagged: {summary['feature_flagged']}")

    # Complexity
    print(f"\n🔴 Complexity Issues:")
    complexity = report["complexity_assessment"]
    for item in complexity[:10]:
        icon = "🔴" if item["severity"] == "CRITICAL" else "🟠" if item["severity"] == "HIGH" else "🟡"
        print(f"   {icon} [{item['severity']}] {item['function']} (complexity: {item['complexity']})")

    # Feature flags
    print(f"\n🚩 Feature Flag Assessment:")
    ff_assessment = report["feature_flag_assessment"]
    print(f"   Total features: {ff_assessment['total_features']}")
    for feature, data in ff_assessment.get("features", {}).items():
        risk_icon = "🔴" if data["risk_level"] == "HIGH" else "🟠" if data["risk_level"] == "MEDIUM" else "🟢"
        print(f"   {risk_icon} {feature}: {data['entry_point_count']} entry points, {data['downstream_functions']} downstream")

    # Helpers
    print(f"\n🔧 Helper Dependencies:")
    helpers = report["helper_assessment"]
    print(f"   Total helpers: {helpers['total_helpers']}")
    print(f"   Shared helpers: {helpers['shared_helpers_count']}")
    if helpers['shared_helpers']:
        for h in helpers['shared_helpers'][:5]:
            print(f"     • {h}")

    # Dead code
    dead = report["potential_dead_code"]
    if dead:
        print(f"\n🗑️  Potential Dead Code ({len(dead)} functions):")
        for func in dead[:10]:
            print(f"     • {func}")

    # Actions
    print(f"\n✅ Actionable Items:")
    for action in report["actionable_items"]:
        icon = "🔴" if action["priority"] == "HIGH" else "🟠" if action["priority"] == "MEDIUM" else "🟢"
        print(f"   {icon} [{action['priority']}] {action['action']}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python auto_assess.py <analysis.json>")
        print("Example: python auto_assess.py nixo_full_analysis.json")
        sys.exit(1)

    filepath = sys.argv[1]
    print(f"Loading analysis from {filepath}...")

    analysis = load_analysis(filepath)
    report = generate_report(analysis)
    print_report(report)

    # Save report
    output_file = filepath.replace('.json', '_assessment.json')
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nDetailed report saved to: {output_file}")
