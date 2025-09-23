#!/usr/bin/env python3
"""
PyRPL Installation Script for PyMoDAQ Plugins PyRPL

This script installs PyRPL with Python 3 compatibility fixes.
PyRPL has a 'futures' dependency that's Python 2 only, so we install 
it without dependencies and handle the deps manually.
"""

import subprocess
import sys
import importlib.util

def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"Running: {description}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} successful")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def check_import(module_name):
    """Check if a module can be imported."""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return False
        # Try actual import to check for runtime errors
        __import__(module_name)
        return True
    except (ImportError, TypeError, AttributeError) as e:
        print(f"Import warning for {module_name}: {e}")
        return False

def apply_python312_fixes():
    """Apply Python 3.12 compatibility fixes to PyRPL."""
    import os
    
    # Find PyRPL installation path without importing pyrpl
    try:
        # Get the Python packages directory
        import site
        site_packages = site.getsitepackages()[0]
        pyrpl_path = os.path.join(site_packages, 'pyrpl')
        memory_py = os.path.join(pyrpl_path, 'memory.py')
        
        if os.path.exists(memory_py):
            # Read the file
            with open(memory_py, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Apply fix for setInterval float issue  
            content = content.replace(
                'self._savetimer.setInterval(self._loadsavedeadtime*1000)',
                'self._savetimer.setInterval(int(self._loadsavedeadtime*1000))'
            )
            
            # Apply additional float->int fixes
            content = content.replace(
                '.setInterval(self._loadsavedeadtime*1000)',
                '.setInterval(int(self._loadsavedeadtime*1000))'
            )
            
            if content != original_content:
                # Write back the fixed file
                with open(memory_py, 'w') as f:
                    f.write(content)
                print("✓ Applied setInterval float->int compatibility fix")
            else:
                print("✓ setInterval fix already applied or not needed")
        else:
            print("✓ PyRPL memory.py not found - fix may not be needed")
            
    except Exception as e:
        print(f"⚠ Could not apply compatibility fixes: {e}")
        print("PyRPL may still work in mock mode")

def install_pyrpl():
    """Install PyRPL with Python 3 compatibility."""
    print("Installing PyRPL for PyMoDAQ plugins...")
    
    # Step 1: Install PyRPL without its dependencies
    if not run_command("uv pip install --no-deps pyrpl>=0.9.3.0", "Installing PyRPL without dependencies"):
        return False
    
    # Step 2: Install PyRPL's dependencies (excluding futures)
    deps = [
        "nose>=1.3.0",
        "numpy>=1.20.0", 
        "pandas>=1.0.0",
        "paramiko>=2.7.0",
        "pyqtgraph>=0.12.0",
        "pyyaml>=5.0.0",
        "qtpy>=1.11.0", 
        "scipy>=1.7.0",
        "scp>=0.13.0",
        "PyQt5>=5.15.0",  # Qt bindings required for PyRPL
        "quamash>=0.6.1"  # Async Qt event loop for PyRPL GUI
    ]
    
    dep_str = " ".join(deps)
    if not run_command(f"uv pip install {dep_str}", "Installing PyRPL dependencies"):
        return False
    
    # Step 3: Apply Python 3.12 compatibility fix
    print("\nApplying Python 3.12 compatibility fixes...")
    apply_python312_fixes()
    
    # Step 4: Test PyRPL import
    print("\nTesting PyRPL import...")
    if check_import('pyrpl'):
        print("✓ PyRPL imported successfully!")
        return True
    else:
        print("✗ PyRPL import failed - see warnings above")
        print("Note: PyRPL may have Qt compatibility issues in some environments")
        print("Consider using mock_mode=True in plugin parameters for development")
        return False

def main():
    """Main installation function."""
    print("PyMoDAQ Plugins PyRPL - PyRPL Installation Script")
    print("=" * 50)
    
    success = install_pyrpl()
    
    if success:
        print("\n✓ PyRPL installation completed successfully!")
        print("\nNext steps:")
        print("1. Run 'uv sync' to install the plugin")
        print("2. Use PyRPL plugins with real Red Pitaya hardware")
        print("3. For development without hardware, use mock_mode=True")
    else:
        print("\n⚠ PyRPL installation completed with warnings")
        print("The plugin will work in mock mode for development")
        print("For hardware use, troubleshoot PyRPL import issues")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())