import sys
from pathlib import Path

# Ensures `import config...`, `import preprocessing...`, etc. resolve the same
# way whether the pipeline is run as a script (`python run_pipeline.py`, which
# puts this directory on sys.path automatically) or via `pytest` from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))
