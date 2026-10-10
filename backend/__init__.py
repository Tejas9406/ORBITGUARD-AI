# SatShield & OrbitGuard AI Backend Package
from pathlib import Path
_pkg_dir = Path(__file__).parent / "backend"
if _pkg_dir.exists():
    __path__.append(str(_pkg_dir))
