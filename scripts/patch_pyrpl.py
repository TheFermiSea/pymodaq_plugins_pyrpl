#!/usr/bin/env python3
"""
Automated PyRPL Bug Fix Patcher

This script automatically patches critical bugs in PyRPL 0.9.6.0 that prevent
hardware initialization with Red Pitaya devices.

Usage:
    python scripts/patch_pyrpl.py

The script will:
1. Locate the installed PyRPL package
2. Check if patches are needed
3. Apply fixes to pyrpl/attributes.py
4. Verify the patches were applied successfully
"""

import sys
import os
from pathlib import Path
import shutil


def find_pyrpl_attributes():
    """Find the pyrpl/attributes.py file in the installed package."""
    try:
        import pyrpl
        pyrpl_path = Path(pyrpl.__file__).parent
        attributes_file = pyrpl_path / "attributes.py"
        
        if attributes_file.exists():
            return attributes_file
        else:
            print(f"❌ Could not find attributes.py in {pyrpl_path}")
            return None
    except ImportError:
        print("❌ PyRPL is not installed. Please install it first:")
        print("   pip install --no-deps git+https://github.com/pyrpl-fpga/pyrpl.git")
        return None


def check_if_patched(file_path):
    """Check if the patches are already applied."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for our patch markers
    patch1_applied = "Fix: Handle zero _MINBW" in content
    patch2_applied = "Fix: Handle empty lists from iterable" in content
    
    return patch1_applied, patch2_applied


def backup_file(file_path):
    """Create a backup of the original file."""
    backup_path = file_path.with_suffix('.py.backup')
    
    if not backup_path.exists():
        shutil.copy2(file_path, backup_path)
        print(f"✓ Backup created: {backup_path}")
        return True
    else:
        print(f"ℹ Backup already exists: {backup_path}")
        return False


def apply_patch_1(content):
    """Apply patch 1: Fix ZeroDivisionError in _MAXSHIFT()"""
    
    old_code = """        return clog2(125000000.0/float(self._MINBW(obj)))"""
    
    new_code = """        # Fix: Handle zero _MINBW to prevent ZeroDivisionError
        min_bw = self._MINBW(obj)
        if min_bw == 0 or min_bw is None:
            return 25  # Reasonable default for Red Pitaya (125 MHz / 2^25 ≈ 3.7 Hz)
        return clog2(125000000.0/float(min_bw))"""
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        print("✓ Patch 1 applied: ZeroDivisionError fix in _MAXSHIFT()")
        return content, True
    else:
        print("⚠ Patch 1 location not found or already applied")
        return content, False


def apply_patch_2(content):
    """Apply patch 2: Fix IndexError in valid_frequencies()"""
    
    old_code = """        pos = [val if not np.iterable(val) else val[0] for val in pos]"""
    
    new_code = """        # Fix: Handle empty lists from iterable values
        pos = [val if not np.iterable(val) else (val[0] if len(val) > 0 else 0) for val in pos]"""
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        print("✓ Patch 2 applied: IndexError fix in valid_frequencies()")
        return content, True
    else:
        print("⚠ Patch 2 location not found or already applied")
        return content, False


def main():
    print("="*70)
    print("PyRPL Bug Fix Patcher")
    print("="*70)
    print()
    
    # Find PyRPL attributes.py
    print("1. Locating PyRPL installation...")
    attributes_file = find_pyrpl_attributes()
    
    if not attributes_file:
        sys.exit(1)
    
    print(f"   Found: {attributes_file}")
    print()
    
    # Check if already patched
    print("2. Checking patch status...")
    patch1_done, patch2_done = check_if_patched(attributes_file)
    
    if patch1_done and patch2_done:
        print("   ✓ Both patches already applied!")
        print()
        print("="*70)
        print("✅ PyRPL is already patched and ready to use!")
        print("="*70)
        return 0
    
    if not patch1_done:
        print("   ⚠ Patch 1 (ZeroDivisionError) needs to be applied")
    else:
        print("   ✓ Patch 1 (ZeroDivisionError) already applied")
    
    if not patch2_done:
        print("   ⚠ Patch 2 (IndexError) needs to be applied")
    else:
        print("   ✓ Patch 2 (IndexError) already applied")
    print()
    
    # Confirm with user
    print("3. Ready to apply patches...")
    response = input("   Continue? (y/N): ").strip().lower()
    
    if response != 'y':
        print("   Cancelled by user")
        return 1
    print()
    
    # Backup original file
    print("4. Creating backup...")
    backup_file(attributes_file)
    print()
    
    # Read file
    print("5. Applying patches...")
    with open(attributes_file, 'r') as f:
        content = f.read()
    
    # Apply patches
    applied = []
    
    if not patch1_done:
        content, success = apply_patch_1(content)
        if success:
            applied.append("Patch 1")
    
    if not patch2_done:
        content, success = apply_patch_2(content)
        if success:
            applied.append("Patch 2")
    
    # Write patched file
    if applied:
        with open(attributes_file, 'w') as f:
            f.write(content)
        print()
        print(f"✓ File updated: {attributes_file}")
    else:
        print()
        print("⚠ No patches were applied (may already be patched)")
    
    print()
    
    # Verify
    print("6. Verifying patches...")
    patch1_done, patch2_done = check_if_patched(attributes_file)
    
    if patch1_done and patch2_done:
        print("   ✓ Patch 1: Verified")
        print("   ✓ Patch 2: Verified")
        print()
        print("="*70)
        print("✅ SUCCESS: PyRPL has been patched!")
        print("="*70)
        print()
        print("You can now use PyRPL with Red Pitaya hardware.")
        print()
        print("Test your connection:")
        print("  python -c \"import pyrpl; p = pyrpl.Pyrpl(hostname='YOUR_RP_IP', gui=False)\"")
        print()
        return 0
    else:
        print("   ✗ Verification failed")
        print()
        print("="*70)
        print("⚠ WARNING: Patching may not have been successful")
        print("="*70)
        print()
        print("You can manually apply the patches by editing:")
        print(f"  {attributes_file}")
        print()
        print("See docs/HARDWARE_TESTING.md for manual patch instructions")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
