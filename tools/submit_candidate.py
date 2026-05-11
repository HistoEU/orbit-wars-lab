from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.orbitlab.scheduler import run_tournament_from_config


def _import_check(bot: Path) -> None:
    code = (
        "import importlib.util, pathlib; "
        f"p=pathlib.Path(r'{bot}'); "
        "s=importlib.util.spec_from_file_location('candidate', p); "
        "m=importlib.util.module_from_spec(s); "
        "s.loader.exec_module(m); "
        "assert callable(m.agent)"
    )
    subprocess.run([".venv-ow/Scripts/python.exe", "-c", code], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and optionally submit an Orbit Wars candidate.")
    parser.add_argument("--bot", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    bot = Path(args.bot)
    _import_check(bot)
    smoke_config = {
        "label": f"{args.version}_submission_smoke",
        "seeds": list(range(1, 11)),
        "workers": 2,
        "matchups": [
            {
                "name": f"{args.version}_vs_starter",
                "agents": [str(bot), "bots/starter/main.py"],
                "player_count": 2,
                "rotate_slots": True,
            }
        ],
    }
    run_dir = run_tournament_from_config(smoke_config)
    target = Path("submissions") / args.version / "main.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bot, target)
    command = ["powershell", "-ExecutionPolicy", "Bypass", "-File", "kaggle.ps1", "competitions", "submit", "orbit-wars", "-f", str(target), "-m", args.message]
    print(f"Smoke run: {run_dir}")
    print("Submit command:")
    print(" ".join(command))
    if args.execute:
        raise SystemExit(subprocess.run(command, check=False).returncode)


if __name__ == "__main__":
    main()
