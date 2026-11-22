import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "dataset", "gulf_synthetic"))
sys.path.insert(0, os.path.join(REPO, "research", "eval"))
sys.path.insert(0, os.path.join(REPO, "ml-service"))
