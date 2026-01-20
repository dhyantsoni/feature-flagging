# How to Demo AST + NetworkX Static Analysis

## Quick Demo (Recommended)

### Option 1: Run the Interactive Demo Script

```bash
python3 demo_static_analysis.py
```

Then select from the menu:
1. **Basic Analysis** - See call graph statistics
2. **Dependency Tracking** - Track function dependencies
3. **Feature Impact** - Simulate disabling a feature
4. **Call Chain Tracing** - Find paths between functions
5. **Shared Dependencies** - Find commonly used functions
6. **Export Formats** - See generated files
7. **CI/CD Integration** - Example pipeline code
8. **Real-World Scenario** - Complete workflow
9. **Run All Demos** - See everything

Press **Enter** at the prompt to run all demos.

---

## Option 2: Run Individual Components

### Step 1: Analyze the Code
```bash
python3 ast_callgraph_analyzer.py
```

**Output:**
- ✅ Analyzes `sample_app.py`
- ✅ Generates `callgraph.json` (machine-readable)
- ✅ Generates `callgraph.dot` (GraphViz format)
- ✅ Shows feature flag impact analysis

### Step 2: Create Visualizations
```bash
python3 visualize_graph.py
```

**Output:**
- ✅ `callgraph_viz.png` - Full call graph diagram
- ✅ `callgraph_viz.svg` - Scalable vector version
- ✅ `feature_impact_*.png` - Per-feature diagrams

### Step 3: View Generated Files
```bash
ls -lh callgraph* feature_impact*
```

### Step 4: Open Visualization
```bash
# On Linux with display
xdg-open callgraph_viz.png

# Or copy to view elsewhere
cp callgraph_viz.png /path/to/view/
```

---

## Option 3: One-Line Commands

### See Everything At Once
```bash
python3 ast_callgraph_analyzer.py && python3 visualize_graph.py && ls -lh *.png *.json
```

### Just Show Analysis
```bash
python3 ast_callgraph_analyzer.py 2>&1 | grep -E "(✅|📍|🚩|📊|⬇️|⬆️|⚠️)"
```

### Generate and View Visualization
```bash
python3 visualize_graph.py && xdg-open callgraph_viz.png 2>/dev/null
```

---

## Option 4: Show Specific Feature Impact

```python
# Create quick_demo.py
from ast_callgraph_analyzer import analyze_file, build_networkx_graph, get_downstream_dependencies

call_graph, functions, feature_flags = analyze_file("sample_app.py")
graph = build_networkx_graph(call_graph)

feature = "sample_app.calculate_recommendations"
downstream = get_downstream_dependencies(graph, feature)

print(f"🚩 Disabling {feature} affects {len(downstream)} functions:")
for func in sorted(downstream):
    print(f"   • {func}")
```

Then run:
```bash
python3 quick_demo.py
```

---

## What You'll See

### 1. Call Graph JSON
```json
{
  "sample_app.calculate_recommendations": [
    "client.isEnabled",
    "sample_app.fetch_user_preferences",
    "sample_app.generate_recommendations",
    "sample_app.cache_recommendations"
  ],
  ...
}
```

### 2. Impact Analysis Report
```
📍 Function: sample_app.calculate_recommendations
🚩 Feature Flag: feature1_recommendations

📊 Impact Summary:
  • Total affected functions: 8
  • Functions that become unreachable: 7
  • Functions that depend on this: 1
  • Functions needing fallback logic: 1

⬇️  Downstream Dependencies (will become unreachable):
  • sample_app.fetch_user_preferences
  • sample_app.database_query
  • sample_app.generate_recommendations
  ...
```

### 3. Visual Call Graph
A PNG diagram showing:
- Green circles = Regular functions
- Gray circles = Utility functions
- Arrows = Function calls
- Clear function names

---

## Integration Examples

### In CI/CD Pipeline

```bash
# .github/workflows/feature-flags.yml
- name: Validate Feature Flags
  run: |
    python3 ast_callgraph_analyzer.py
    python3 validate_fallbacks.py  # Your custom script
    # Fail build if missing fallbacks
```

### In Pre-Commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
python3 ast_callgraph_analyzer.py > /dev/null
if [ $? -ne 0 ]; then
    echo "❌ Call graph analysis failed!"
    exit 1
fi
echo "✅ Call graph analysis passed"
```

### As API Endpoint

```python
# app.py
from flask import Flask, jsonify
from ast_callgraph_analyzer import analyze_file

app = Flask(__name__)

@app.route('/api/analyze/<feature>')
def analyze_feature(feature):
    call_graph, _, _ = analyze_file("main.py")
    # ... analyze feature ...
    return jsonify({"impact": impact_data})
```

---

## Tips for Presenting

### 1. **Start with the visualization**
   - Show `callgraph_viz.png` first
   - Explain the green nodes (functions) and arrows (calls)
   - Point out the `main` function at the center

### 2. **Run the demo script**
   - `python3 demo_static_analysis.py`
   - Choose "Real-World Scenario" (option 8)
   - Shows complete workflow

### 3. **Show the generated JSON**
   - `cat callgraph.json | jq '.' | head -30`
   - Demonstrate machine-readable format
   - Perfect for automation

### 4. **Explain the value**
   - "Before deploying, we know exactly what breaks"
   - "No surprises - we see all dependencies"
   - "Automated validation in CI/CD"

---

## Files Generated

| File | Size | Purpose |
|------|------|---------|
| `callgraph.json` | ~2.4KB | Machine-readable call graph |
| `callgraph.dot` | ~6KB | GraphViz source |
| `callgraph_viz.png` | ~738KB | Visual diagram |
| `callgraph_viz.svg` | ~102KB | Scalable vector |
| `feature_impact_analysis.json` | ~2KB | Impact analysis data |
| `feature_impact_*.png` | ~150KB each | Per-feature diagrams |

---

## Troubleshooting

### "Module not found" error
```bash
# Make sure you're in the right directory
cd /path/to/feature-flagging
git checkout poc/ast-networkx-static-analysis
python3 ast_callgraph_analyzer.py
```

### "No display" for visualization
```bash
# Generate without display, then view elsewhere
python3 visualize_graph.py
cp *.png /path/to/view/
```

### Want faster demo?
```bash
# Skip menu, run specific demo
echo "8" | python3 demo_static_analysis.py | head -50
```

---

## Summary

**Simplest way to demo:**

```bash
python3 demo_static_analysis.py
# Press Enter to run all demos
```

**OR:**

```bash
# Generate everything
python3 ast_callgraph_analyzer.py && python3 visualize_graph.py

# Show the visualization
xdg-open callgraph_viz.png
```

**That's it!** 🎉
