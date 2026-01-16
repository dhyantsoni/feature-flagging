# POC: Static Analysis with Pyan3

## Overview

This POC attempts to use **Pyan3** for static call graph analysis to support feature flagging systems.

## Status: ❌ NOT VIABLE

### Issues Encountered

1. **CLI bugs**: `pyan3` command-line tool has TypeError in `CallGraphVisitor.__init__()`
   ```
   TypeError: CallGraphVisitor.__init__() got multiple values for argument 'root'
   ```

2. **Programmatic API bugs**: When using Pyan3 as a library:
   ```
   FileNotFoundError: [Errno 2] No such file or directory: ''
   ```
   - `get_module_name()` function fails with empty string path
   - Unable to analyze files outside of a proper Python package structure

3. **Maintenance concerns**:
   - Version 1.2.0 still has critical bugs
   - Not production-ready for automated analysis

## Attempted Solutions

### 1. CLI Approach
```bash
pyan3 sample_app.py --dot --colored --grouped --annotated
```
**Result**: TypeError in `__init__()`

### 2. Programmatic API
```python
from pyan.analyzer import CallGraphVisitor
visitor = CallGraphVisitor([source_file], logger=logger)
```
**Result**: FileNotFoundError in `get_module_name()`

### 3. Workarounds Explored
- Creating `__init__.py` files
- Using absolute paths
- Modifying root parameter

**Result**: None successful

## Comparison vs PyCG

| Feature | PyCG | Pyan3 |
|---------|------|-------|
| Installation | ✅ Works | ✅ Works |
| CLI Usage | ✅ Works | ❌ Broken |
| Programmatic API | ✅ Works | ❌ Broken |
| Precision | 99.2% | Unable to test |
| Maintenance | Archived but functional | Broken |
| Production Ready | ✅ Yes | ❌ No |

## Conclusion

**Pyan3 is NOT recommended** for feature flag static analysis due to:
- Critical bugs in both CLI and programmatic interfaces
- Unreliable for automated CI/CD pipelines
- Lack of stable API for integration

**Recommendation**: Use PyCG or custom AST+NetworkX solution instead.

## Files

- `requirements.txt`: Pyan3 dependency
- `generate_callgraph_pyan.py`: Attempted implementation (non-functional)
- `sample_app.py`: Test application
- `POC_README.md`: This documentation

## Next Steps

Move to **poc/ast-networkx-static-analysis** branch for a more reliable custom solution.
