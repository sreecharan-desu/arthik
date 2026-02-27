import os
import sys

# Ensure the project root is in the path so we can import from the main directory
# In Vercel, the current working directory is /var/task
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Also ensure 'api' is not masking anything
# and that site-packages are looked at correctly
try:
    from main import app
except ImportError as e:
    # Diagnostic: if it fails, try to show what's in the path
    print(f"Import Error: {e}")
    print(f"sys.path: {sys.path}")
    print(f"Contents of {root_dir}: {os.listdir(root_dir)}")
    raise
