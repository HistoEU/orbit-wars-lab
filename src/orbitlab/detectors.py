from __future__ import annotations

from collections import defaultdict

from .issues import Issue


def detect_crashes(match: dict) -> list[Issue]:
    issues = []
    for slot, status in enumerate(match.get("statuses", [])):
        if status != "DONE":
            issues.append(
                Issue(
                    detector="crash",
                    severity="P0",
                    message=f"Slot {slot} ended with status {status}.",
                    match_id=match.get("match_id", ""),
                    slot=slot,
                    evidence={"status": status, "error_text": match.get("error_text")},
                )
            )
    return issues


def detect_slot_bias(matches: list[dict], focus_agent: str, min_games_per_slot: int = 20) -> list[Issue]:
    by_slot: dict[int, list[bool]] = defaultdict(list)
    for match in matches:
        agents = match.get("agents", [])
        if focus_agent not in agents:
            continue
        slot = agents.index(focus_agent)
        by_slot[slot].append(match.get("winner_agent") == focus_agent)

    rates = {}
    for slot, outcomes in by_slot.items():
        if len(outcomes) >= min_games_per_slot:
            rates[slot] = sum(outcomes) / len(outcomes)
    if len(rates) < 2:
        return []
    spread = max(rates.values()) - min(rates.values())
    if spread <= 0.15:
        return []
    return [
        Issue(
            detector="slot_bias",
            severity="P3",
            message=f"{focus_agent} has {spread:.1%} win-rate spread by player slot.",
            match_id="aggregate",
            evidence={"rates": rates, "focus_agent": focus_agent},
        )
    ]


def detect_low_expansion(turn_metrics: list[dict], focus_slot: int) -> list[Issue]:
    by_match: dict[str, list[dict]] = defaultdict(list)
    for metric in turn_metrics:
        if int(metric.get("slot", -1)) == focus_slot:
            by_match[str(metric.get("match_id", ""))].append(metric)
    issues = []
    for match_id, rows in by_match.items():
        late_one_planet = [row for row in rows if int(row.get("step", 0)) >= 60 and int(row.get("planets", 0)) <= 1]
        if late_one_planet:
            first = min(late_one_planet, key=lambda row: int(row.get("step", 0)))
            issues.append(
                Issue(
                    detector="slow_expansion",
                    severity="P2",
                    message="Bot still owned one or fewer planets after step 60.",
                    match_id=match_id,
                    step=int(first.get("step", 0)),
                    slot=focus_slot,
                    evidence={"planets": first.get("planets")},
                )
            )
    return issues


def detect_timeout_or_slow_match(match: dict, max_elapsed_seconds: float) -> list[Issue]:
    elapsed = float(match.get("elapsed_seconds", 0.0))
    if elapsed <= max_elapsed_seconds:
        return []
    return [
        Issue(
            detector="slow_match",
            severity="P1",
            message=f"Match took {elapsed:.2f}s, above {max_elapsed_seconds:.2f}s threshold.",
            match_id=match.get("match_id", ""),
            evidence={"elapsed_seconds": elapsed, "threshold": max_elapsed_seconds},
        )
    ]


def detect_match_issues(match: dict, slow_threshold_seconds: float = 30.0) -> list[Issue]:
    return detect_crashes(match) + detect_timeout_or_slow_match(match, slow_threshold_seconds)
