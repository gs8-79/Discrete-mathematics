from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from puzzles import all_puzzles


ROOT = Path(__file__).resolve().parent


def exe(name: str) -> Path:
    candidate = ROOT / f"{name}.exe"
    return candidate if candidate.exists() else ROOT / name


def run_json(name: str, *args: str, stdin: dict | None = None) -> dict:
    completed = subprocess.run(
        [str(exe(name)), *args],
        input=json.dumps(stdin, ensure_ascii=False) if stdin is not None else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
    )
    output = completed.stdout.strip()
    if not output:
        raise AssertionError(f"{name} produced no stdout: {completed.stderr}")
    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{name} produced invalid JSON: {output}") from exc
    return data


def assert_no_error(name: str, data: dict) -> None:
    if "error" in data:
        raise AssertionError(f"{name} returned error: {data['error']}")


def test_core_modules() -> None:
    ast = run_json("parser", "(A∧B)→C")
    assert_no_error("parser", ast)
    assert ast["type"] == "implies"

    table = run_json("truth_table", "A<->B")
    assert_no_error("truth_table", table)
    assert table["variables"] == ["A", "B"]
    assert len(table["rows"]) == 4
    assert table["satisfiable"] is True

    cnf = run_json("cnf", "(A∨¬B)∧(¬A∨C)")
    assert_no_error("cnf", cnf)
    assert cnf["var_map"] == {"A": 1, "B": 2, "C": 3}

    sat = run_json("dpll", stdin=cnf)
    assert_no_error("dpll", sat)
    assert sat["sat"] is True
    assert set(sat["assignment"]) == {"A", "B", "C"}

    unsat = run_json("dpll", stdin={"clauses": [[1], [-1]], "var_map": {"A": 1}})
    assert_no_error("dpll_unsat", unsat)
    assert unsat == {"sat": False, "assignment": {}}


def test_puzzles() -> None:
    for puzzle in all_puzzles():
        result = run_json("dpll", stdin=puzzle.cnf)
        assert_no_error(puzzle.id, result)
        assert result["sat"] is True
        decoded = puzzle.decoder(result["assignment"])
        assert decoded, puzzle.id


def main() -> int:
    test_core_modules()
    test_puzzles()
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
