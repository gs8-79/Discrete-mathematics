from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import streamlit as st

from puzzles import Puzzle, all_puzzles

ROOT = Path(__file__).resolve().parent

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(page_title="命题逻辑推理系统", layout="wide")
st.markdown(
    """
    <style>
    /* 指标卡片 */
    div[data-testid="stMetric"] {
        background: #fffaf0; border: 1px solid #c9bea7;
        padding: 14px 16px; border-radius: 8px;
    }
    /* 自定义表格 */
    code { color: #1e40af; }
    table { font-size: 14px; }
    table td, table th { padding: 4px 12px; }
    table thead th { background: #e8e1d2; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 工具函数
# ============================================================
def _exe(name: str) -> Path:
    suffix = ".exe" if (ROOT / f"{name}.exe").exists() else ""
    return ROOT / f"{name}{suffix}"


@st.cache_data(show_spinner=False)
def _run(name: str, *args: str, stdin: dict[str, Any] | None = None) -> dict[str, Any]:
    exe = _exe(name)
    if not exe.exists():
        return {"error": f"可执行文件不存在: {exe.name}"}
    completed = subprocess.run(
        [str(exe), *args],
        input=json.dumps(stdin, ensure_ascii=False) if stdin is not None else None,
        capture_output=True, text=True, encoding="utf-8", timeout=10,
    )
    output = completed.stdout.strip()
    if not output:
        return {"error": completed.stderr.strip() or f"{name} 无输出"}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"error": f"{name} 返回了非法 JSON", "raw": output}


def _reverse_map(var_map: dict[str, int]) -> dict[int, str]:
    return {v: k for k, v in var_map.items()}


def _fmt_clause(clause: list[int], rev: dict[int, str]) -> str:
    parts = []
    for lit in clause:
        var = rev.get(abs(lit), f"?{abs(lit)}")
        parts.append(var if lit > 0 else f"¬{var}")
    return "(" + " ∨ ".join(parts) + ")"


def _clauses_readable(clauses: list[list[int]], rev: dict[int, str]) -> str:
    if not clauses:
        return "∅ (永真)"
    return " ∧ ".join(_fmt_clause(c, rev) for c in clauses)


# ============================================================
# 指标栏
# ============================================================
def _metric_row(cnf: dict, dpll: dict) -> None:
    clauses = cnf.get("clauses", [])
    var_map = cnf.get("var_map", {})
    sat = dpll.get("sat")
    c1, c2, c3 = st.columns(3)
    c1.metric("变量数", len(var_map))
    c2.metric("子句数", len(clauses))
    if sat is True:
        c3.metric("SAT", "可满足")
    elif sat is False:
        c3.metric("SAT", "不可满足")
    else:
        c3.metric("SAT", "—")


# ============================================================
# 语法帮助
# ============================================================
def _syntax_help() -> None:
    with st.sidebar.expander("语法帮助"):
        st.markdown(
            """
| 含义 | Unicode | ASCII 备用 |
|------|---------|-----------|
| 否定 | `¬` | `!` `~` |
| 合取 | `∧` | `&` `&&` |
| 析取 | `∨` | `\\|` `\\|\\|` |
| 蕴含 | `→` | `->` `=>` |
| 等价 | `↔` | `<->` `<=>` |

**优先级:** `¬` > `∧` > `∨` > `→` > `↔` (→ 右结合)

**变量名:** `[A-Za-z][A-Za-z0-9_]*`
"""
        )


# ============================================================
# 公式测试视图
# ============================================================
def _formula_view() -> None:
    st.subheader("公式测试")

    # 示例按钮
    examples = [
        "(A∧B)→C",
        "A<->B",
        "¬(A∨B)↔(¬A∧¬B)",
        "(A∨B)∧(¬A∨C)∧(¬B∨¬C)",
    ]
    cols = st.columns(len(examples))
    selected = None
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"ex_{i}", use_container_width=True):
            selected = ex

    with st.form("formula_form"):
        formula = st.text_input(
            "输入命题逻辑公式",
            value=selected or "(A∧B)→C",
            placeholder="例如: (A∧B)→C,  ¬(A∨B),  A<->B",
        )
        submitted = st.form_submit_button("运行", type="primary", use_container_width=True)

    if not submitted:
        if not selected:
            st.info("点击「运行」按钮执行全链路分析")
        return

    # 全链路
    with st.spinner("解析公式…"):
        ast = _run("parser", formula)
    if "error" in ast:
        st.error(f"解析失败: {ast['error']}")
        return

    with st.spinner("生成真值表…"):
        table = _run("truth_table", formula)
    with st.spinner("转换为 CNF…"):
        cnf = _run("cnf", formula)

    if "error" in cnf:
        st.error(f"CNF 转换失败: {cnf['error']}")
        dpll = {}
    else:
        with st.spinner("DPLL 求解…"):
            dpll = _run("dpll", stdin=cnf)

    _metric_row(cnf if "error" not in cnf else {}, dpll)

    tabs = st.tabs(["AST", "真值表", "CNF", "DPLL"])
    with tabs[0]:
        st.json(ast)
    with tabs[1]:
        if "error" in table:
            st.error(table["error"])
        else:
            _truth_table(table)
    with tabs[2]:
        if "error" in cnf:
            st.error(cnf["error"])
        else:
            _cnf_view(cnf)
    with tabs[3]:
        if "error" in dpll:
            st.error(dpll["error"])
        elif dpll:
            _dpll_view(dpll)


def _truth_table(data: dict) -> None:
    vars_ = data.get("variables", [])
    rows = data.get("rows", [])
    if not rows:
        st.json(data)
        return

    # HTML 表格
    header = "".join(f"<th>{v}</th>" for v in vars_) + "<th>结果</th>"
    body = ""
    for row in rows:
        cells = ""
        for v in vars_:
            val = row.get(v)
            cells += f'<td style="color:{"#15803d" if val else "#b91c1c"}">{val}</td>'
        r = row.get("result")
        rs = "color:#15803d;font-weight:600" if r else "color:#b91c1c;font-weight:600"
        cells += f'<td style="{rs}">{r}</td>'
        body += f"<tr>{cells}</tr>"

    st.markdown(
        f"""<table style="width:100%;border-collapse:collapse">
        <thead><tr style="background:#e8e1d2">{header}</tr></thead>
        <tbody>{body}</tbody></table>""",
        unsafe_allow_html=True,
    )

    # 性质
    c1, c2, c3 = st.columns(3)
    sat = data.get("satisfiable", False)
    taut = data.get("tautology", False)
    contra = data.get("contradiction", False)
    c1.markdown(f"**可满足** {'✅' if sat else '❌'} <small>— 存在一种赋值使结果为真</small>", unsafe_allow_html=True)
    c2.markdown(f"**永真式** {'✅' if taut else '❌'} <small>— 所有赋值结果都为真</small>", unsafe_allow_html=True)
    c3.markdown(f"**矛盾式** {'✅' if contra else '❌'} <small>— 所有赋值结果都为假</small>", unsafe_allow_html=True)


def _cnf_view(data: dict) -> None:
    clauses = data.get("clauses", [])
    var_map = data.get("var_map", {})
    rev = _reverse_map(var_map)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**变量映射**")
        if var_map:
            rows = "".join(f"<tr><td style='font-weight:600'>{k}</td><td>{v}</td></tr>" for k, v in var_map.items())
            st.markdown(
                f"<table style='width:100%'><thead><tr><th>变量</th><th>编号</th></tr></thead><tbody>{rows}</tbody></table>",
                unsafe_allow_html=True,
            )
        else:
            st.info("无变量")
    with c2:
        st.markdown("**可读子句集**")
        if clauses:
            st.code(_clauses_readable(clauses, rev), language="text")
        else:
            st.info("空子句集（永真）")

    with st.expander("原始 CNF JSON"):
        st.json(data)


def _dpll_view(data: dict) -> None:
    if data.get("sat"):
        st.success("SAT — 公式可满足")
        st.markdown("**赋值**")
        assignment = data.get("assignment", {})
        if assignment:
            cols = st.columns(min(len(assignment), 6))
            for i, (var, val) in enumerate(sorted(assignment.items())):
                cols[i % len(cols)].markdown(
                    f"`{var}` = {'**T**' if val else '**F**'}",
                    unsafe_allow_html=True,
                )
    else:
        st.warning("UNSAT — 公式不可满足")
    with st.expander("原始 DPLL JSON"):
        st.json(data)


# ============================================================
# 谜题求解视图
# ============================================================
def _puzzle_view(puzzles: list[Puzzle]) -> None:
    selected_title = st.sidebar.selectbox("谜题", [p.title for p in puzzles])
    puzzle = next(p for p in puzzles if p.title == selected_title)

    st.subheader(puzzle.title)
    st.write(puzzle.description)

    with st.spinner("DPLL 求解中…"):
        dpll = _run("dpll", stdin=puzzle.cnf)
    decoded = puzzle.decoder(dpll.get("assignment", {})) if dpll.get("sat") else None

    _metric_row(puzzle.cnf, dpll)

    tabs = st.tabs(["结果", "CNF", "DPLL", "公式"])
    with tabs[0]:
        if decoded is None:
            st.error("未找到可满足解")
        elif puzzle.id == "sudoku4":
            _render_sudoku(decoded)
        elif puzzle.id == "schedule":
            _render_schedule(decoded)
        elif puzzle.id == "logic":
            _render_logic(decoded)
        else:
            st.json(decoded)
    with tabs[1]:
        _cnf_view(puzzle.cnf)
    with tabs[2]:
        _dpll_view(dpll)
    with tabs[3]:
        if puzzle.formula:
            st.code(puzzle.formula, language="text")
            st.json(_run("parser", puzzle.formula))
        else:
            st.info("该谜题直接构造 CNF，避免把大量约束压成单个公式字符串。")


def _render_sudoku(grid: list[list[int]]) -> None:
    size = len(grid)
    # 宫边界加粗
    box = int(size ** 0.5)  # 4 → 2
    html = '<table style="border-collapse:collapse;margin:0 auto">'
    for r in range(size):
        html += "<tr>"
        for c in range(size):
            val = grid[r][c]
            top = 2 if r % box == 0 else 1
            left = 2 if c % box == 0 else 1
            bottom = 2 if r == size - 1 or r % box == box - 1 else 1
            right = 2 if c == size - 1 or c % box == box - 1 else 1
            html += (
                f'<td style="width:56px;height:56px;text-align:center;'
                f'font-size:22px;font-weight:bold;'
                f'border:solid #333;'
                f'border-width:{top}px {right}px {bottom}px {left}px;'
                f'background:#fff">'
                f'{val}</td>'
            )
        html += "</tr>"
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)


def _render_schedule(schedule: dict[str, str]) -> None:
    """三人排课 → 横向时间轴卡片"""
    order = {"Morning": ("🌅", "上午", "#fef3c7"), "Afternoon": ("☀️", "下午", "#fde68a"), "Evening": ("🌙", "晚上", "#fcd34d")}
    slots = sorted(set(schedule.values()), key=lambda s: {"Morning": 0, "Afternoon": 1, "Evening": 2}.get(s, 99))
    cols = st.columns(len(slots))
    for i, slot in enumerate(slots):
        who = [p for p, s in schedule.items() if s == slot][0]
        icon, label, bg = order.get(slot, ("", slot, "#fff"))
        with cols[i]:
            st.markdown(
                f"""<div style="background:{bg};border-radius:12px;padding:20px 16px;text-align:center;
                border:2px solid #c9bea7;min-height:140px">
                <div style="font-size:32px;margin-bottom:8px">{icon}</div>
                <div style="font-size:18px;font-weight:700;color:#1f2933;margin-bottom:4px">{who}</div>
                <div style="font-size:13px;color:#374151">{label}</div>
                </div>""",
                unsafe_allow_html=True,
            )


def _render_logic(result: dict[str, dict[str, str]]) -> None:
    """宠物与颜色 → 表格"""
    headers = ["姓名", "宠物", "颜色"]
    rows = []
    for person, attrs in result.items():
        rows.append(f"<tr><td><strong>{person}</strong></td><td>{attrs['pet']}</td><td>{attrs['color']}</td></tr>")
    st.markdown(
        f"""<table style="width:100%;border-collapse:collapse">
        <thead><tr style="background:#e8e1d2">{''.join(f'<th>{h}</th>' for h in headers)}</tr></thead>
        <tbody>{''.join(rows)}</tbody></table>""",
        unsafe_allow_html=True,
    )


# ============================================================
# 入口
# ============================================================
def main() -> None:
    puzzles = all_puzzles()
    st.title("命题逻辑推理系统")

    _syntax_help()
    mode = st.sidebar.radio("视图", ["谜题求解", "公式测试"])

    if mode == "公式测试":
        _formula_view()
    else:
        _puzzle_view(puzzles)


if __name__ == "__main__":
    main()
