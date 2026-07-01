from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import streamlit as st

from puzzles import Puzzle, all_puzzles


ROOT = Path(__file__).resolve().parent


def exe_path(name: str) -> Path:
    suffix = ".exe" if (ROOT / f"{name}.exe").exists() else ""
    return ROOT / f"{name}{suffix}"


def run_executable(name: str, *args: str, stdin: dict[str, Any] | None = None) -> dict[str, Any]:
    exe = exe_path(name)
    if not exe.exists():
        return {"error": f"Executable not found: {exe.name}"}

    completed = subprocess.run(
        [str(exe), *args],
        input=json.dumps(stdin, ensure_ascii=False) if stdin is not None else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
    )
    output = completed.stdout.strip()
    if not output:
        return {"error": completed.stderr.strip() or f"{name} returned no output"}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"error": f"{name} returned invalid JSON", "raw": output}


def solve_puzzle(puzzle: Puzzle) -> dict[str, Any]:
    dpll_result = run_executable("dpll", stdin=puzzle.cnf)
    decoded = None
    if dpll_result.get("sat") is True:
        decoded = puzzle.decoder(dpll_result.get("assignment", {}))
    return {"dpll": dpll_result, "decoded": decoded}


def render_metric_row(cnf_data: dict[str, Any], dpll_data: dict[str, Any]) -> None:
    clauses = cnf_data.get("clauses", [])
    var_map = cnf_data.get("var_map", {})
    cols = st.columns(3)
    cols[0].metric("变量数", len(var_map))
    cols[1].metric("子句数", len(clauses))
    cols[2].metric("SAT", "true" if dpll_data.get("sat") else "false")


def main() -> None:
    st.set_page_config(page_title="命题逻辑推理系统", layout="wide")
    st.markdown(
        """
        <style>
        .stApp { background: #f6f4ef; color: #1f2933; }
        section[data-testid="stSidebar"] { background: #e8e1d2; }
        div[data-testid="stMetric"] {
            background: #fffaf0;
            border: 1px solid #c9bea7;
            padding: 14px 16px;
            border-radius: 8px;
        }
        code { color: #314f7d; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    puzzles = all_puzzles()
    st.title("命题逻辑推理系统")

    mode = st.sidebar.radio("视图", ["谜题求解", "公式测试"])

    if mode == "公式测试":
        formula = st.text_input("公式", value="(A∧B)→C")
        ast = run_executable("parser", formula)
        table = run_executable("truth_table", formula)
        cnf = run_executable("cnf", formula)
        dpll = run_executable("dpll", stdin=cnf) if "error" not in cnf else {"error": "CNF failed"}

        render_metric_row(cnf if "error" not in cnf else {}, dpll)
        tabs = st.tabs(["AST", "真值表", "CNF", "DPLL"])
        tabs[0].json(ast)
        tabs[1].json(table)
        tabs[2].json(cnf)
        tabs[3].json(dpll)
        return

    selected_title = st.sidebar.selectbox("谜题", [p.title for p in puzzles])
    puzzle = next(p for p in puzzles if p.title == selected_title)
    solved = solve_puzzle(puzzle)

    st.subheader(puzzle.title)
    st.write(puzzle.description)
    render_metric_row(puzzle.cnf, solved["dpll"])

    tabs = st.tabs(["结果", "CNF", "DPLL", "公式"])
    with tabs[0]:
        if solved["decoded"] is None:
            st.error("未找到可满足解")
        else:
            st.json(solved["decoded"])
    with tabs[1]:
        st.json(puzzle.cnf)
    with tabs[2]:
        st.json(solved["dpll"])
    with tabs[3]:
        if puzzle.formula:
            st.code(puzzle.formula, language="text")
            st.json(run_executable("parser", puzzle.formula))
        else:
            st.info("该谜题直接构造 CNF，避免把大量约束压成单个公式字符串。")


if __name__ == "__main__":
    main()
