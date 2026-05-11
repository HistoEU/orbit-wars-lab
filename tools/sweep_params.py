from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.orbitlab.scheduler import run_tournament_from_config


def _parameter_product(parameters: dict[str, list]) -> list[dict]:
    keys = list(parameters.keys())
    return [dict(zip(keys, values)) for values in itertools.product(*(parameters[key] for key in keys))]


def _replace_constant(source: str, name: str, value: object) -> str:
    pattern = re.compile(rf"^({re.escape(name)}\s*=\s*)(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one assignment for {name}, found {len(matches)}")
    literal = repr(value)
    return pattern.sub(rf"\g<1>{literal}", source)


def generate_variants(config: dict, limit: int | None = None, dry_run: bool = False) -> tuple[list[str], dict]:
    base_path = Path(config["base_bot"])
    source = base_path.read_text(encoding="utf-8")
    variant_dir = Path(config.get("variant_dir", "bots/generated"))
    combos = _parameter_product(config.get("parameters", {}))
    if limit is not None:
        combos = combos[:limit]
    variant_paths = []
    for index, combo in enumerate(combos):
        variant_source = source
        for name, value in combo.items():
            variant_source = _replace_constant(variant_source, name, value)
        variant_name = "variant_" + str(index).zfill(3)
        variant_path = variant_dir / variant_name / "main.py"
        variant_paths.append(str(variant_path))
        if not dry_run:
            variant_path.parent.mkdir(parents=True, exist_ok=True)
            header = f"# Generated sweep variant {variant_name}: {json.dumps(combo, sort_keys=True)}\n"
            variant_path.write_text(header + variant_source, encoding="utf-8")

    matchups = []
    for variant_path in variant_paths:
        for opponent in config.get("opponents", []):
            matchups.append(
                {
                    "name": f"{Path(variant_path).parent.name}_vs_{Path(opponent).parent.name}",
                    "agents": [variant_path, opponent],
                    "player_count": 2,
                    "rotate_slots": True,
                }
            )
    tournament_config = {
        "label": "parameter_sweep",
        "seeds": config.get("seeds", []),
        "workers": config.get("workers", 1),
        "matchups": matchups,
    }
    return variant_paths, tournament_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate parameter variants and run a tournament sweep.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    _, tournament_config = generate_variants(config, limit=args.limit, dry_run=args.dry_run)
    if args.dry_run:
        print(json.dumps(tournament_config, indent=2))
        return
    print(run_tournament_from_config(tournament_config))


if __name__ == "__main__":
    main()
