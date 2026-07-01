from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Callable


Clause = list[int]
CNFData = dict[str, object]
Assignment = dict[str, bool]


@dataclass(frozen=True)
class Puzzle:
    id: str
    title: str
    description: str
    cnf: CNFData
    decoder: Callable[[Assignment], object]
    formula: str | None = None


def make_var_map(names: list[str]) -> dict[str, int]:
    return {name: idx + 1 for idx, name in enumerate(sorted(names))}


def pos(var_map: dict[str, int], name: str) -> int:
    return var_map[name]


def neg(var_map: dict[str, int], name: str) -> int:
    return -var_map[name]


def exactly_one(var_map: dict[str, int], names: list[str]) -> list[Clause]:
    clauses: list[Clause] = [[pos(var_map, name) for name in names]]
    for left, right in combinations(names, 2):
        clauses.append([neg(var_map, left), neg(var_map, right)])
    return clauses


def schedule_puzzle() -> Puzzle:
    people = ["Alice", "Bob", "Carol"]
    slots = ["Morning", "Afternoon", "Evening"]
    names = [f"{person}_{slot}" for person in people for slot in slots]
    var_map = make_var_map(names)
    clauses: list[Clause] = []

    for person in people:
        clauses.extend(exactly_one(var_map, [f"{person}_{slot}" for slot in slots]))
    for slot in slots:
        clauses.extend(exactly_one(var_map, [f"{person}_{slot}" for person in people]))

    clauses.append([neg(var_map, "Alice_Morning")])
    clauses.append([neg(var_map, "Bob_Evening")])
    clauses.append([pos(var_map, "Carol_Evening")])

    formula = (
        "(!Alice_Morning)&(!Bob_Evening)&Carol_Evening&"
        "(Alice_Morning|Alice_Afternoon|Alice_Evening)&"
        "(Bob_Morning|Bob_Afternoon|Bob_Evening)&"
        "(Carol_Morning|Carol_Afternoon|Carol_Evening)"
    )

    def decode(assignment: Assignment) -> dict[str, str]:
        result: dict[str, str] = {}
        for person in people:
            for slot in slots:
                name = f"{person}_{slot}"
                if assignment.get(name):
                    result[person] = slot
        return result

    return Puzzle(
        id="schedule",
        title="三人排课",
        description="Alice、Bob、Carol 各选择一个时段，每个时段只安排一个人，并满足给定线索。",
        cnf={"clauses": clauses, "var_map": var_map},
        decoder=decode,
        formula=formula,
    )


def sudoku4_puzzle() -> Puzzle:
    size = 4
    nums = range(1, size + 1)
    cells = [(r, c) for r in range(1, size + 1) for c in range(1, size + 1)]
    names = [f"R{r}C{c}_{n}" for r, c in cells for n in nums]
    var_map = make_var_map(names)
    clauses: list[Clause] = []

    for r, c in cells:
        clauses.extend(exactly_one(var_map, [f"R{r}C{c}_{n}" for n in nums]))

    for r in range(1, size + 1):
        for n in nums:
            clauses.extend(exactly_one(var_map, [f"R{r}C{c}_{n}" for c in range(1, size + 1)]))

    for c in range(1, size + 1):
        for n in nums:
            clauses.extend(exactly_one(var_map, [f"R{r}C{c}_{n}" for r in range(1, size + 1)]))

    for box_r in (1, 3):
        for box_c in (1, 3):
            for n in nums:
                box_cells = [
                    f"R{r}C{c}_{n}"
                    for r in range(box_r, box_r + 2)
                    for c in range(box_c, box_c + 2)
                ]
                clauses.extend(exactly_one(var_map, box_cells))

    givens = {
        (1, 1): 1,
        (1, 4): 4,
        (2, 3): 1,
        (3, 2): 3,
        (4, 1): 2,
        (4, 4): 3,
    }
    for (r, c), n in givens.items():
        clauses.append([pos(var_map, f"R{r}C{c}_{n}")])

    def decode(assignment: Assignment) -> list[list[int]]:
        grid = [[0 for _ in range(size)] for _ in range(size)]
        for r, c in cells:
            for n in nums:
                if assignment.get(f"R{r}C{c}_{n}"):
                    grid[r - 1][c - 1] = n
        return grid

    return Puzzle(
        id="sudoku4",
        title="4x4 数独",
        description="使用 SAT 约束表达 4x4 数独的行、列、宫和已知数字。",
        cnf={"clauses": clauses, "var_map": var_map},
        decoder=decode,
    )


def logic_puzzle() -> Puzzle:
    people = ["Ana", "Ben", "Cara"]
    pets = ["猫", "狗", "鸟"]
    colors = ["红色", "蓝色", "绿色"]
    names = [f"{person}_Pet_{pet}" for person in people for pet in pets]
    names += [f"{person}_Color_{color}" for person in people for color in colors]
    var_map = make_var_map(names)
    clauses: list[Clause] = []

    for person in people:
        clauses.extend(exactly_one(var_map, [f"{person}_Pet_{pet}" for pet in pets]))
        clauses.extend(exactly_one(var_map, [f"{person}_Color_{color}" for color in colors]))

    for pet in pets:
        clauses.extend(exactly_one(var_map, [f"{person}_Pet_{pet}" for person in people]))
    for color in colors:
        clauses.extend(exactly_one(var_map, [f"{person}_Color_{color}" for person in people]))

    clauses.append([pos(var_map, "Ben_Pet_狗")])
    clauses.append([pos(var_map, "Cara_Color_蓝色")])
    clauses.append([neg(var_map, "Ana_Color_红色")])

    for person in people:
        cat = f"{person}_Pet_猫"
        green = f"{person}_Color_绿色"
        clauses.append([neg(var_map, cat), pos(var_map, green)])
        clauses.append([neg(var_map, green), pos(var_map, cat)])

    def decode(assignment: Assignment) -> dict[str, dict[str, str]]:
        result: dict[str, dict[str, str]] = {}
        for person in people:
            pet_value = next((pet for pet in pets if assignment.get(f"{person}_Pet_{pet}")), "")
            color_value = next(
                (color for color in colors if assignment.get(f"{person}_Color_{color}")), ""
            )
            result[person] = {"pet": pet_value, "color": color_value}
        return result

    return Puzzle(
        id="logic",
        title="宠物与颜色逻辑谜题",
        description="三个人各有一种宠物和一种喜欢的颜色，根据线索用 SAT 求唯一解。",
        cnf={"clauses": clauses, "var_map": var_map},
        decoder=decode,
    )


def all_puzzles() -> list[Puzzle]:
    return [schedule_puzzle(), sudoku4_puzzle(), logic_puzzle()]


def get_puzzle(puzzle_id: str) -> Puzzle:
    for puzzle in all_puzzles():
        if puzzle.id == puzzle_id:
            return puzzle
    raise KeyError(f"Unknown puzzle: {puzzle_id}")
