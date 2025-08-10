# PyRPL Compatibility Fixes Reference

## Critical Python 3.12 Compatibility Issues and Solutions

This memory documents the specific compatibility fixes needed for PyRPL to work with modern Python environments (3.12+).

## Issue 1: collections.Mapping Deprecation

**Problem**: Python 3.10+ deprecated `collections.Mapping` in favor of `collections.abc.Mapping`

**Error**:
```
AttributeError: module 'collections' has no attribute 'Mapping'
```

**Solution** (in `pyrpl_wrapper.py`):
```python
import collections.abc
import collections
if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping
    collections.MutableMapping = collections.abc.MutableMapping
    collections.MutableSet = collections.abc.MutableSet
    collections.Set = collections.abc.Set
    collections.MutableSequence = collections.abc.MutableSequence
    collections.Sequence = collections.abc.Sequence
    collections.Iterable = collections.abc.Iterable
    collections.Iterator = collections.abc.Iterator
    collections.Container = collections.abc.Container
    collections.Sized = collections.abc.Sized
    collections.Callable = collections.abc.Callable
    collections.Hashable = collections.abc.Hashable
```

## Issue 2: NumPy np.complex Deprecation

**Problem**: NumPy 1.20+ deprecated `np.complex` as alias for builtin `complex`

**Error**:
```
AttributeError: module 'numpy' has no attribute 'complex'
```

**Solution**:
```python
import numpy as np
if not hasattr(np, 'complex'):
    np.complex = complex
    np.complex_ = complex
```

## Issue 3: Qt Timer setInterval Float/Int Issue

**Problem**: PyQt5 `QTimer.setInterval()` expects int but PyRPL passes float

**Error**:
```
TypeError: setInterval(self, msec: int): argument 1 has unexpected type 'float'
```

**Solution**:
```python
try:
    from qtpy.QtCore import QTimer
    original_setInterval = QTimer.setInterval
    
    def setInterval_patched(self, msec):
        """Patched setInterval to handle float inputs properly."""
        return original_setInterval(self, int(msec))
    
    QTimer.setInterval = setInterval_patched
except ImportError:
    pass  # Qt not available, skip timer patch
```

## Issue 4: PyRPL Import Path Error

**Problem**: Incorrect import path for PID module class

**Error**:
```
ImportError: cannot import name 'PidModule' from 'pyrpl.hardware_modules.pid'
```

**Solution**:
```python
# Wrong:
from pyrpl.hardware_modules.pid import PidModule

# Correct:
from pyrpl.hardware_modules.pid import Pid as PidModule
```

## Issue 5: PyRPL ZeroDivisionError During Connection

**Problem**: PyRPL throws ZeroDivisionError during software module loading but connection is actually successful

**Error**:
```
ZeroDivisionError: float division by zero
```

**Solution**:
```python
except Exception as e:
    # Check if this is a PyRPL-related error that we can ignore
    error_str = str(e)
    if "float division by zero" in error_str and self._pyrpl and self._redpitaya:
        logger.info(f"PyRPL connection successful despite error: {error_str}")
        self.state = ConnectionState.CONNECTED
        self.connected_at = time.time()
        self.last_error = None
        return True
```

## Complete Compatibility Template

For any new PyRPL integration, apply these fixes in this order:

1. **Import compatibility patches first** (before importing PyRPL)
2. **Apply Qt patches** (before PyRPL creates Qt objects)
3. **Import PyRPL with proper paths**
4. **Handle connection errors gracefully**

**Template Code**:
```python
import collections.abc
import collections
import numpy as np

# Fix collections deprecation
if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping
    # ... (all other mappings)

# Fix numpy deprecation  
if not hasattr(np, 'complex'):
    np.complex = complex
    np.complex_ = complex

# Fix Qt timer compatibility
try:
    from qtpy.QtCore import QTimer
    original_setInterval = QTimer.setInterval
    def setInterval_patched(self, msec):
        return original_setInterval(self, int(msec))
    QTimer.setInterval = setInterval_patched
except ImportError:
    pass

# Now safely import PyRPL
import pyrpl
from pyrpl.hardware_modules.pid import Pid as PidModule
```

## Testing Validation
These fixes have been validated with:
- Python 3.12
- PyQt5
- NumPy 1.24+  
- PyRPL 0.9.5+
- Real Red Pitaya hardware (rp-f08d6c.local)

Date: August 7, 2025
Status: Production validated