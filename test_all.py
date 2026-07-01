from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from nl_parser import parse_natural_puzzle
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


def test_natural_language_schedule_sat() -> None:
    parsed = parse_natural_puzzle(
        """人员：张三、李四、王五
时段：上午、下午、晚上
每人恰好一个时段，每个时段只安排一个人。
张三不在上午。
李四不能在晚上。
王五在晚上。"""
    )
    assert parsed.ok, parsed.errors
    assert parsed.puzzle is not None

    result = run_json("dpll", stdin=parsed.puzzle.cnf)
    assert_no_error("natural_schedule", result)
    assert result["sat"] is True

    decoded = parsed.puzzle.decoder(result["assignment"])
    assert decoded["王五"] == "晚上"
    assert decoded["张三"] != "上午"
    assert decoded["李四"] != "晚上"


def test_natural_language_schedule_unsat() -> None:
    parsed = parse_natural_puzzle(
        """人员：张三、李四
时段：上午、下午
张三在上午。
张三不在上午。"""
    )
    assert parsed.ok, parsed.errors
    assert parsed.puzzle is not None

    result = run_json("dpll", stdin=parsed.puzzle.cnf)
    assert_no_error("natural_schedule_unsat", result)
    assert result["sat"] is False


def test_natural_language_attributes_sat() -> None:
    parsed = parse_natural_puzzle(
        """人物：Ana、Ben、Cara
宠物：猫、狗、鸟
颜色：红色、蓝色、绿色
每个人恰好一种宠物和一种颜色，每种宠物和颜色恰好属于一个人。
Ben拥有狗。
Cara喜欢蓝色。
Ana不喜欢红色。
拥有猫的人也喜欢绿色。"""
    )
    assert parsed.ok, parsed.errors
    assert parsed.puzzle is not None

    result = run_json("dpll", stdin=parsed.puzzle.cnf)
    assert_no_error("natural_attributes", result)
    assert result["sat"] is True

    decoded = parsed.puzzle.decoder(result["assignment"])
    assert decoded["Ben"]["宠物"] == "狗"
    assert decoded["Cara"]["颜色"] == "蓝色"
    assert decoded["Ana"]["颜色"] != "红色"


def test_natural_language_unsupported_text() -> None:
    parsed = parse_natural_puzzle("今天阳光很好，我们随便聊聊。")
    assert parsed.ok is False
    assert parsed.errors


def main() -> int:
    test_core_modules()
    test_puzzles()
    test_natural_language_schedule_sat()
    test_natural_language_schedule_unsat()
    test_natural_language_attributes_sat()
    test_natural_language_unsupported_text()
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
