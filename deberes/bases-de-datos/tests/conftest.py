import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))                                   # lp_db
sys.path.insert(0, str(HERE.parent.parent / "base" / "agent"))  # lpagent
