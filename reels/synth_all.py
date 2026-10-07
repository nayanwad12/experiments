"""Generate (or refresh) every Reel's narration takes: python3 synth_all.py"""
import importlib.util, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "common"))
from voice import narrate
for d in sorted(p for p in HERE.iterdir() if p.is_dir() and p.name[:2].isdigit()):
    spec = importlib.util.spec_from_file_location("s", d / "script.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    print(d.name)
    vo = narrate(m.LINES, d / "work", voice=m.VOICE)
    print(f"  total speech {sum(v['dur'] for v in vo.values()):.1f}s")
