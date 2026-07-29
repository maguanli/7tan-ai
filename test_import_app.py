"""Test import of launch_app to diagnose startup issues"""
import sys, traceback
sys.path.insert(0, ".")
try:
    from src.ui.app import launch_app
    print("OK: import launch_app succeeded")
except Exception as e:
    traceback.print_exc()
