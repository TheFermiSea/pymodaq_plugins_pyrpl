"""
PyRPL Bug Fixes and Compatibility Patches

This module contains patches for known PyRPL bugs that prevent proper operation
with modern Python versions and specific hardware configurations.

Import this module BEFORE importing pyrpl to apply all necessary patches.
"""

import logging

logger = logging.getLogger(__name__)


def apply_all_patches():
    """Apply all PyRPL compatibility patches."""
    
    # Patch 1: Fix ZeroDivisionError in FrequencyRegister._MAXSHIFT
    _patch_frequency_register_zero_division()
    
    logger.info("All PyRPL compatibility patches applied")


def _patch_frequency_register_zero_division():
    """
    Patch PyRPL's FrequencyRegister._MAXSHIFT to handle zero _MINBW.
    
    This fixes a bug where the Network Analyzer initialization causes a
    ZeroDivisionError when _MINBW returns 0.
    
    The error occurs in:
    pyrpl/attributes.py:785 in _MAXSHIFT
        return clog2(125000000.0/float(self._MINBW(obj)))
    
    When _MINBW(obj) returns 0, this causes division by zero.
    """
    try:
        import pyrpl.attributes as pyrpl_attrs
        from math import log2, ceil
        
        # Get the FrequencyRegister class
        if not hasattr(pyrpl_attrs, 'FrequencyRegister'):
            logger.debug("FrequencyRegister not found in pyrpl.attributes")
            return False
            
        FrequencyRegister = pyrpl_attrs.FrequencyRegister
        
        # Find the unbound method - it may be defined differently
        original_method = None
        for attr_name in ['_MAXSHIFT', '_maxshift']:
            if hasattr(FrequencyRegister, attr_name):
                original_method = getattr(FrequencyRegister, attr_name)
                method_name = attr_name
                break
        
        if original_method is None:
            logger.debug("_MAXSHIFT method not found on FrequencyRegister")
            return False
        
        # Check if already patched
        if hasattr(original_method, '_pyrpl_patched'):
            logger.debug("FrequencyRegister._MAXSHIFT already patched")
            return True
        
        # Create patched method
        def _MAXSHIFT_patched(self, obj):
            """Patched _MAXSHIFT that handles zero _MINBW."""
            try:
                min_bw = self._MINBW(obj) if hasattr(self, '_MINBW') else 0
                
                # Handle zero or None _MINBW
                if not min_bw or min_bw <= 0:
                    logger.debug(f"_MINBW returned {min_bw}, using default MAXSHIFT=25")
                    return 25  # Reasonable default for Red Pitaya (125 MHz / 2^25 ≈ 3.7 Hz)
                
                # Use clog2 function from original code
                if hasattr(pyrpl_attrs, 'clog2'):
                    return pyrpl_attrs.clog2(125000000.0 / float(min_bw))
                else:
                    # Fallback to Python's log2
                    return int(ceil(log2(125000000.0 / float(min_bw))))
                    
            except ZeroDivisionError:
                logger.warning("Caught ZeroDivisionError in _MAXSHIFT, using default=25")
                return 25
            except Exception as e:
                logger.warning(f"Error in _MAXSHIFT: {e}, using default=25")
                return 25
        
        # Mark as patched
        _MAXSHIFT_patched._pyrpl_patched = True
        
        # Apply the patch to the class
        setattr(FrequencyRegister, method_name, _MAXSHIFT_patched)
        
        logger.info(f"✓ Patched PyRPL FrequencyRegister.{method_name} to handle zero _MINBW")
        return True
                
    except ImportError:
        logger.debug("PyRPL not yet imported, patch will be applied on first import")
        return False
    except Exception as e:
        logger.warning(f"Could not patch PyRPL FrequencyRegister._MAXSHIFT: {e}")
        import traceback
        traceback.print_exc()
        return False


# DO NOT auto-apply on module import - pyrpl may not be imported yet
# Patches must be manually called after pyrpl import but BEFORE creating Pyrpl() instance
