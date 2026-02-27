import os
import sys

# Add project root and api directory to path
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(path)
sys.path.append(os.path.join(path, 'api'))

from main import app

