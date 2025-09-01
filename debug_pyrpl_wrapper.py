#!/usr/bin/env python3
"""
Debug PyRPL wrapper import issues
"""
import sys
import collections.abc
import collections

# Apply Python 3.10+ compatibility fix
if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping
    collections.MutableMapping = collections.abc.MutableMapping

def test_pyrpl_wrapper_debug():
    """Debug the PyRPL wrapper import"""
    print("="*60)
    print("Debugging PyRPL Wrapper Import")
    print("="*60)
    
    try:
        # Test direct PyRPL import first
        import pyrpl
        print(f"✅ Direct pyrpl import successful")
        print(f"✅ PyRPL version: {pyrpl.__version__}")
        
        # Now test the wrapper
        sys.path.insert(0, 'src')
        
        print(f"\n🔍 Testing wrapper import...")
        
        # Import the wrapper with debugging
        import logging
        logging.basicConfig(level=logging.DEBUG)
        
        from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PYRPL_AVAILABLE
        print(f"Wrapper reports PYRPL_AVAILABLE: {PYRPL_AVAILABLE}")
        
        if PYRPL_AVAILABLE:
            print("✅ Wrapper successfully detected PyRPL")
            from pymodaq_plugins_pyrpl.utils.pyrpl_wrapper import PyRPLManager
            manager = PyRPLManager.get_instance()
            print("✅ PyRPL manager created")
        else:
            print("❌ Wrapper failed to detect PyRPL")
            
    except Exception as e:
        print(f"❌ Debug test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_pyrpl_wrapper_debug()