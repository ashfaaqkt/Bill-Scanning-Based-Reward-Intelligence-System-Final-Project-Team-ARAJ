import os
import sys

# Tests import the service modules the way app.py does: from ml-service/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
