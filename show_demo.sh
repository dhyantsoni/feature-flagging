#!/bin/bash

# Simple demo script - Run everything and show results

echo "════════════════════════════════════════════════════════════════"
echo "  AST + NetworkX Static Analysis Demo"
echo "  Feature Flagging System"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Step 1: Analyze
echo "Step 1: Analyzing sample_app.py..."
python3 ast_callgraph_analyzer.py | grep -E "(✅|📍|🚩|📊|Total|Feature)" | head -20
echo ""

# Step 2: Visualize
echo "Step 2: Generating visualizations..."
python3 visualize_graph.py 2>&1 | grep "✅"
echo ""

# Step 3: Show files
echo "Step 3: Generated files:"
ls -lh callgraph.json callgraph.dot *.png 2>/dev/null | awk '{if (NR>1) print "  •", $9, "("$5")"}'
echo ""

# Step 4: Show sample
echo "Step 4: Sample call graph (first 10 functions):"
cat callgraph.json | python3 -m json.tool | head -25
echo "  ... (see callgraph.json for full output)"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "✅ Demo complete!"
echo ""
echo "Next steps:"
echo "  • View callgraph_viz.png for visual diagram"
echo "  • Run 'python3 demo_static_analysis.py' for interactive demo"
echo "  • Check DEMO_HOWTO.md for more options"
echo "════════════════════════════════════════════════════════════════"
