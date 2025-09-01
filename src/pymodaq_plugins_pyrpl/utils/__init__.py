# -*- coding: utf-8 -*-
"""
PyMoDAQ PyRPL Plugin Utilities

This module provides utilities for the PyMoDAQ PyRPL plugin, including
centralized connection management and configuration handling.
"""

# Import Config from the parent package's utils.py file
import sys
from pathlib import Path

# The Config class is defined in the parent directory's utils.py, not in this utils/ subdirectory
# We need to import it from the parent package level
parent_path = Path(__file__).parent.parent
utils_path = parent_path / 'utils.py'

if utils_path.exists():
    # Import the Config class from utils.py in parent directory
    spec = None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("parent_utils", utils_path)
        parent_utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parent_utils)
        Config = parent_utils.Config
    except Exception:
        # Fallback if import fails
        from pymodaq_utils.config import BaseConfig
        
        class Config(BaseConfig):
            """Fallback Config class for PyRPL plugin"""
            config_name = "config_pyrpl"
else:
    # Fallback: define a minimal Config class
    from pymodaq_utils.config import BaseConfig
    
    class Config(BaseConfig):
        """Fallback Config class for PyRPL plugin"""
        config_name = "config_pyrpl"

try:
    from .pyrpl_wrapper import PyRPLConnection, PyRPLManager
except ImportError:
    # Handle cases where PyRPL is not available
    PyRPLConnection = None
    PyRPLManager = None

__all__ = ['Config', 'PyRPLConnection', 'PyRPLManager']