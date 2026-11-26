import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))                                   # np_lab
sys.path.insert(0, str(HERE.parent.parent / "base" / "agent"))  # lpagent (solo para la prueba de integración)
