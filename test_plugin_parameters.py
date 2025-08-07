#!/usr/bin/env python3
"""
Test script to check PyRPL plugin parameter structures
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def check_plugin_parameters():
    """Check parameter structures for all PyRPL plugins."""
    
    plugins = [
        ('PID Plugin', 'pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_PID', 'DAQ_Move_PyRPL_PID'),
        ('ASG Plugin', 'pymodaq_plugins_pyrpl.daq_move_plugins.daq_move_PyRPL_ASG', 'DAQ_Move_PyRPL_ASG'),
        ('Voltage Monitor', 'pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL', 'DAQ_0DViewer_PyRPL'),
        ('Scope Plugin', 'pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_1D.daq_1Dviewer_PyRPL_Scope', 'DAQ_1DViewer_PyRPL_Scope'),
        ('IQ Plugin', 'pymodaq_plugins_pyrpl.daq_viewer_plugins.plugins_0D.daq_0Dviewer_PyRPL_IQ', 'DAQ_0DViewer_PyRPL_IQ')
    ]
    
    for name, module_path, class_name in plugins:
        try:
            print(f"\n=== {name} ===")
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            
            # Create instance to check parameters
            instance = cls()
            
            # Check available parameter names
            if hasattr(instance, 'params'):
                for param in instance.params:
                    if param.get('type') == 'group':
                        print(f"  Group parameter: '{param['name']}'")
                        if 'children' in param:
                            for child in param['children']:
                                if 'mock_mode' in child.get('name', ''):
                                    print(f"    - mock_mode found: '{child['name']}'")
                                if 'redpitaya_host' in child.get('name', ''):
                                    print(f"    - host found: '{child['name']}'")
            else:
                print("  No params attribute found")
                
        except Exception as e:
            print(f"  ERROR: {e}")

if __name__ == "__main__":
    check_plugin_parameters()