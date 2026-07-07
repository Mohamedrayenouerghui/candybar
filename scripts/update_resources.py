#!/usr/bin/env python3
"""
Regenerate Qt resource bundles (resource_rc.py) from .qrc files.
Must be run whenever QML, images, or other resources are added/changed.

Usage:
    python scripts/update_resources.py
"""
import os
import subprocess
import sys


def find_pyside6_rcc():
    """Locate pyside6-rcc in venv or system PATH."""
    # Try venv first
    venv_rcc = os.path.join('.', 'venv', 'bin', 'pyside6-rcc')
    if os.path.isfile(venv_rcc):
        return venv_rcc
    # Fall back to system
    return 'pyside6-rcc'


def generate_resource(project_name):
    """Generate resource_rc.py from resource.qrc for the given project."""
    qrc_path = os.path.join('.', project_name, 'imports', 'resource.qrc')
    out_path = os.path.join('.', project_name, 'imports', 'resource_rc.py')
    
    if not os.path.isfile(qrc_path):
        print(f"[SKIP] {qrc_path} not found")
        return False
    
    rcc = find_pyside6_rcc()
    cmd = [rcc, qrc_path, '-o', out_path]
    
    print(f"[GEN] {qrc_path} → {out_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[ERROR] {result.stderr}")
        return False
    
    print(f"[OK] {out_path} generated")
    return True


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    success = True
    success &= generate_resource("fluentui")
    success &= generate_resource("app")
    
    sys.exit(0 if success else 1)
