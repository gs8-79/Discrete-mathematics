from __future__ import annotations

import json
import subprocess
import html
from pathlib import Path
from typing import Any

import streamlit as st

from nl_parser import parse_natural_puzzle

ROOT = Path(__file__).resolve().parent

SCHEDULE_SAMPLE = """人员：张三、李四、王五
时段：上午、下午、晚上
每人恰好一个时段，每个时段只安排一个人。
张三不在上午。
李四不能在晚上。
王五在晚上。"""

ATTRIBUTE_SAMPLE = """人物：Ana、Ben、Cara
宠物：猫、狗、鸟
颜色：红色、蓝色、绿色
每个人恰好一种宠物和一种颜色，每种宠物和颜色恰好属于一个人。
Ben拥有狗。
Cara喜欢蓝色。
Ana不喜欢红色。
拥有猫的人也喜欢绿色。"""

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="命题逻辑推理系统",
    layout="wide",
    menu_items={
        "About": """
### 命题逻辑推理系统

离散数学课程项目。

**功能：** 公式解析 · 真值表 · CNF · DPLL · 自然语言谜题求解

[GitHub](https://github.com/gs8-79/Discrete-mathematics)
""",
        "Get help": "https://github.com/gs8-79/Discrete-mathematics",
        "Report a bug": "https://github.com/gs8-79/Discrete-mathematics/issues/new",
    },
)
st.markdown(
    """
    <style>
    .card {
        background: #fffaf0; border-radius: 10px; padding: 20px;
        border: 1px solid #c9bea7;
    }
    table { font-size: 14px; border-collapse: collapse; width: 100%; }
    table td, table th { padding: 6px 14px; }
    table thead th { background: #e8e1d2; color: #1f2933; font-weight: 600; }
    table tbody tr:nth-child(odd) { background: #fdfbf7; }
    table tbody tr:nth-child(even) { background: #fffaf0; }
    code { color: #1e40af; }
    .chip-true, .chip-false {
        display: inline-block; padding: 2px 10px; border-radius: 999px;
        font-size: 13px; font-weight: 600; margin: 2px 4px;
    }
    .chip-true  { background: #dcfce7; color: #15803d; }
    .chip-false { background: #fee2e2; color: #b91c1c; }
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


def _rev(var_map: dict[str, int]) -> dict[int, str]:
    return {v: k for k, v in var_map.items()}


def _fmt_clause(clause: list[int], rev: dict[int, str]) -> str:
    parts = []
    for lit in clause:
        var = rev.get(abs(lit), f"?{abs(lit)}")
        parts.append(var if lit > 0 else f"¬{var}")
    return "(" + " ∨ ".join(parts) + ")"


def _clauses_str(clauses: list[list[int]], rev: dict[int, str]) -> str:
    if not clauses:
        return "∅ (永真)"
    return " ∧ ".join(_fmt_clause(c, rev) for c in clauses)


def _card(html: str) -> None:
    st.markdown(f'<div class="card">{html}</div>', unsafe_allow_html=True)


def _h(value: object) -> str:
    return html.escape(str(value), quote=True)


# ============================================================
# 语法帮助
# ============================================================
def _help() -> None:
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
# 公式回显
# ============================================================
def _echo_formula(raw: str) -> str:
    """将 ASCII 运算符替换为 Unicode 数学符号"""
    return (
        raw.replace("<=>", "↔").replace("<->", "↔")
        .replace("=>", "→").replace("->", "→")
        .replace("&&", "∧").replace("&", "∧")
        .replace("||", "∨").replace("|", "∨")
        .replace("~", "¬").replace("!", "¬")
    )


# ============================================================
# AST 树形图
# ============================================================
def _render_ast(ast: dict) -> None:
    """递归渲染 AST 为水平内联树"""

    OP = {"not": "¬", "and": "∧", "or": "∨", "implies": "→", "equiv": "↔"}

    def _tree(node: dict) -> str:
        if "error" in node:
            return f'<span style="color:#b91c1c">错误：{node["error"]}</span>'

        typ = node.get("type", "?")

        if typ == "var":
            return (
                f'<span style="display:inline-block;padding:4px 12px;border-radius:8px;'
                f'background:#f1f5f9;color:#334155;font-weight:600;font-size:15px;'
                f'border:1px solid #cbd5e1">'
                f'{node.get("name", "?")}</span>'
            )

        if typ == "not":
            child = _tree(node.get("child", {}))
            return (
                f'<div style="display:flex;flex-direction:column;align-items:center;gap:4px">'
                f'<span style="padding:3px 12px;border-radius:8px;'
                f'background:#2563eb;color:#fff;font-weight:700;font-size:14px">¬</span>'
                f'<div style="width:2px;height:10px;background:#94a3b8"></div>'
                f'{child}</div>'
            )

        op = OP.get(typ, typ)

        if typ in ("and", "or") and "children" in node:
            kids = [_tree(c) for c in node["children"]]
        else:
            left = _tree(node.get("left", {}))
            right = _tree(node.get("right", {}))
            kids = [left, right]

        parts = []
        for i, kid in enumerate(kids):
            parts.append(kid)
            if i < len(kids) - 1:
                parts.append(
                    f'<span style="padding:2px 8px;border-radius:6px;'
                    f'background:#2563eb;color:#fff;font-weight:700;font-size:13px;margin:0 2px">{op}</span>'
                )

        return (
            f'<div style="display:flex;align-items:center;justify-content:center;'
            f'gap:4px;flex-wrap:wrap;padding:8px 0">'
            f'{"".join(parts)}</div>'
        )

    _card(_tree(ast))


# ============================================================
# 指标栏
# ============================================================
def _metrics(cnf: dict, dpll: dict) -> None:
    clauses = cnf.get("clauses", [])
    var_map = cnf.get("var_map", {})
    sat = dpll.get("sat")

    c1, c2, c3 = st.columns(3)

    # SAT 状态卡片整张变色
    if sat is True:
        sat_card = '<div style="text-align:center;color:#15803d"><div style="font-size:28px;font-weight:700">可满足</div><div style="font-size:12px;color:#64748b">SAT</div></div>'
    elif sat is False:
        sat_card = '<div style="text-align:center;color:#b91c1c"><div style="font-size:28px;font-weight:700">不可满足</div><div style="font-size:12px;color:#64748b">UNSAT</div></div>'
    else:
        sat_card = '<div style="text-align:center;color:#64748b">—</div>'

    with c1:
        st.metric("变量数", len(var_map))
    with c2:
        st.metric("子句数", len(clauses))
    with c3:
        st.markdown(f'<div class="card" style="text-align:center">{sat_card}</div>', unsafe_allow_html=True)


# ============================================================
# 公式测试视图
# ============================================================
def _formula_view() -> None:
    if "formula_text" not in st.session_state:
        st.session_state["formula_text"] = "(A∧B)→C"

    examples = [
        "(A∧B)→C",
        "A<->B",
        "¬(A∨B)↔(¬A∧¬B)",
        "(A∨B)∧(¬A∨C)∧(¬B∨¬C)",
    ]
    cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"ex_{i}", use_container_width=True):
            st.session_state["formula_text"] = ex
            st.rerun()

    with st.form("formula_form"):
        formula = st.text_input(
            "输入命题逻辑公式",
            key="formula_text",
            placeholder="例如: (A∧B)→C,  ¬(A∨B),  A<->B",
        )
        submitted = st.form_submit_button("运行", type="primary", use_container_width=True)

    if not submitted:
        st.info("点击「运行」按钮执行全链路分析")
        return

    # 公式回显
    st.markdown(
        f'<div style="text-align:center;font-size:22px;font-weight:600;'
        f'letter-spacing:2px;padding:10px 0;color:#0f172a">'
        f'{_echo_formula(formula)}</div>',
        unsafe_allow_html=True,
    )

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

    _metrics(cnf if "error" not in cnf else {}, dpll)

    tabs = st.tabs(["AST 语法树", "真值表", "CNF 子句集", "DPLL 求解"])
    with tabs[0]:
        _render_ast(ast)
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


# ============================================================
# 真值表
# ============================================================
def _truth_table(data: dict) -> None:
    vars_ = data.get("variables", [])
    rows = data.get("rows", [])
    if not rows:
        st.json(data)
        return

    header = "".join(f"<th>{v}</th>" for v in vars_) + "<th>结果</th>"
    body = ""
    for row in rows:
        r = row.get("result")
        bg = 'background:#dcfce7' if r else 'background:#fff'
        cells = ""
        for v in vars_:
            val = row.get(v)
            cells += f'<td style="color:{"#15803d" if val else "#b91c1c"}">{val}</td>'
        rc = "color:#15803d;font-weight:700" if r else "color:#b91c1c;font-weight:700"
        cells += f'<td style="{rc}">{r}</td>'
        body += f'<tr style="{bg}">{cells}</tr>'

    _card(
        f'<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>'
    )

    # 性质
    c1, c2, c3 = st.columns(3)
    sat = data.get("satisfiable", False)
    taut = data.get("tautology", False)
    contra = data.get("contradiction", False)
    c1.markdown(f"**可满足** {'✅' if sat else '❌'}  <small>— 存在赋值使结果为真</small>")
    c2.markdown(f"**永真式** {'✅' if taut else '❌'}  <small>— 所有赋值都为真</small>")
    c3.markdown(f"**矛盾式** {'✅' if contra else '❌'}  <small>— 所有赋值都为假</small>")


# ============================================================
# CNF
# ============================================================
def _cnf_view(data: dict) -> None:
    clauses = data.get("clauses", [])
    var_map = data.get("var_map", {})
    rev = _rev(var_map)

    c1, c2 = st.columns(2)
    with c1:
        if var_map:
            rows = "".join(
                f'<tr><td style="font-weight:600">{_h(k)}</td><td>{_h(v)}</td></tr>'
                for k, v in var_map.items()
            )
            _card(f'<h4>变量映射</h4><table><thead><tr><th>变量</th><th>编号</th></tr></thead><tbody>{rows}</tbody></table>')
        else:
            st.info("无变量")
    with c2:
        if clauses:
            readable = _clauses_str(clauses, rev)
            st.markdown('<h4>可读子句集</h4>', unsafe_allow_html=True)
            _card(f'<code style="font-size:15px;word-break:break-all">{_h(readable)}</code>')
        else:
            st.info("空子句集（永真）")

    with st.expander("原始 CNF JSON"):
        st.json(data)


# ============================================================
# DPLL
# ============================================================
def _dpll_view(data: dict) -> None:
    if data.get("sat"):
        st.success("SAT — 公式可满足")
        assignment = data.get("assignment", {})
        if assignment:
            chips = ""
            for var, val in sorted(assignment.items()):
                cls = "chip-true" if val else "chip-false"
                label = f"{var}=真" if val else f"{var}=假"
                chips += f'<span class="{cls}">{label}</span> '
            _card(f'<h4>赋值</h4><div style="line-height:2.2">{chips}</div>')
    else:
        st.warning("UNSAT — 公式不可满足")

    with st.expander("原始 DPLL JSON"):
        st.json(data)


# ============================================================
# 自然语言求解视图
# ============================================================
def _natural_language_view() -> None:
    st.subheader("自然语言谜题求解")
    st.caption("支持模板化中文线索：排课类、人物-属性匹配类。解析后会自动生成 CNF，并调用 DPLL 判断 SAT/UNSAT。")

    if "natural_input" not in st.session_state:
        st.session_state["natural_input"] = SCHEDULE_SAMPLE

    c1, c2 = st.columns(2)
    if c1.button("填入排课示例", use_container_width=True):
        st.session_state["natural_input"] = SCHEDULE_SAMPLE
    if c2.button("填入属性匹配示例", use_container_width=True):
        st.session_state["natural_input"] = ATTRIBUTE_SAMPLE

    with st.form("natural_language_form"):
        text = st.text_area(
            "输入自然语言线索",
            key="natural_input",
            height=220,
            placeholder="例如：人员：张三、李四、王五；时段：上午、下午、晚上；张三不在上午。",
        )
        submitted = st.form_submit_button("解析并判断", type="primary", use_container_width=True)

    if not submitted:
        st.info("输入题目线索后点击「解析并判断」。建议先声明人员/人物、时段或属性取值。")
        return

    parsed = parse_natural_puzzle(text)
    if not parsed.ok or parsed.puzzle is None:
        for error in parsed.errors:
            st.error(error)
        return

    puzzle = parsed.puzzle
    for warning in parsed.warnings:
        st.warning(warning)

    with st.spinner("DPLL 求解中…"):
        dpll = _run("dpll", stdin=puzzle.cnf)

    decoded = puzzle.decoder(dpll.get("assignment", {})) if dpll.get("sat") else None
    _metrics(puzzle.cnf, dpll)

    tabs = st.tabs(["判断结果", "解析预览", "CNF", "DPLL"])
    with tabs[0]:
        if "error" in dpll:
            st.error(dpll["error"])
        elif dpll.get("sat") is True and decoded is not None:
            st.success("SAT — 线索存在可满足解")
            if puzzle.id == "natural_schedule":
                _render_schedule(decoded)
            elif puzzle.id == "natural_attributes":
                _render_logic(decoded)
            else:
                st.json(decoded)
        elif dpll.get("sat") is False:
            st.warning("UNSAT — 线索互相冲突，无法同时满足")
        else:
            st.info("未得到可判断结果")

    with tabs[1]:
        st.markdown("#### 识别出的规则")
        if parsed.normalized_rules:
            rules = "".join(f"<li>{_h(rule)}</li>" for rule in parsed.normalized_rules)
            _card(f"<ul style='margin:0;padding-left:20px;line-height:1.9'>{rules}</ul>")
        else:
            st.info("没有识别出具体规则。")
        with st.expander("解析出的模型摘要"):
            st.write(puzzle.title)
            st.write(puzzle.description)
            st.json(
                {
                    "variables": len(puzzle.cnf.get("var_map", {})),
                    "clauses": len(puzzle.cnf.get("clauses", [])),
                    "type": puzzle.id,
                }
            )

    with tabs[2]:
        _cnf_view(puzzle.cnf)

    with tabs[3]:
        _dpll_view(dpll)


# ============================================================
# 渲染器
# ============================================================
def _render_sudoku(grid: list[list[int]]) -> None:
    size = len(grid)
    box = int(size ** 0.5)
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
                f'<td style="width:60px;height:60px;text-align:center;'
                f'font-size:24px;font-weight:700;'
                f'border:solid #334155;'
                f'border-width:{top}px {right}px {bottom}px {left}px;'
                f'background:#fff">'
                f'{val}</td>'
            )
        html += "</tr>"
    html += "</table>"
    _card(html)


def _render_schedule(schedule: dict[str, str]) -> None:
    order = {
        "Morning": ("🌅", "上午", "#fef3c7", "#c9bea7"),
        "Afternoon": ("☀️", "下午", "#fde68a", "#c9bea7"),
        "Evening": ("🌙", "晚上", "#fcd34d", "#c9bea7"),
        "上午": ("🌅", "上午", "#fef3c7", "#c9bea7"),
        "下午": ("☀️", "下午", "#fde68a", "#c9bea7"),
        "晚上": ("🌙", "晚上", "#fcd34d", "#c9bea7"),
        "早上": ("🌅", "早上", "#fef3c7", "#c9bea7"),
        "中午": ("◇", "中午", "#fef9c3", "#c9bea7"),
        "傍晚": ("◐", "傍晚", "#fed7aa", "#c9bea7"),
    }
    slot_order = {
        "Morning": 0,
        "早上": 0,
        "上午": 1,
        "中午": 2,
        "Afternoon": 3,
        "下午": 3,
        "傍晚": 4,
        "Evening": 5,
        "晚上": 5,
    }
    slots = sorted(set(schedule.values()), key=lambda s: slot_order.get(s, 99))
    cols = st.columns(len(slots))
    for i, slot in enumerate(slots):
        people = [p for p, s in schedule.items() if s == slot]
        who = "、".join(people)
        icon, label, bg, accent = order.get(slot, ("◇", slot, "#fff", "#64748b"))
        with cols[i]:
            st.markdown(
                f"""<div style="background:{bg};border-radius:14px;padding:24px 16px;
                text-align:center;border:2px solid {accent};">
                <div style="font-size:36px;margin-bottom:10px">{icon}</div>
                <div style="font-size:18px;font-weight:700;color:#0f172a;margin-bottom:4px">{_h(who)}</div>
                <div style="font-size:13px;color:#475569;font-weight:500">{_h(label)}</div>
                </div>""",
                unsafe_allow_html=True,
            )


def _render_logic(result: dict[str, dict[str, str]]) -> None:
    label_map = {"pet": "宠物", "color": "颜色"}
    categories: list[str] = []
    for attrs in result.values():
        for category in attrs:
            if category not in categories:
                categories.append(category)
    headers = ["姓名", *[label_map.get(category, category) for category in categories]]
    rows = ""
    for person, attrs in result.items():
        cells = "".join(f"<td>{_h(attrs.get(category, ''))}</td>" for category in categories)
        rows += f"<tr><td><strong>{_h(person)}</strong></td>{cells}</tr>"
    _card(
        f'<table><thead><tr>{"".join(f"<th>{_h(h)}</th>" for h in headers)}</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
    )


# ============================================================
# 入口
# ============================================================
def main() -> None:
    st.title("命题逻辑推理系统")
    st.caption("离散数学课程项目 — 公式解析 · 真值表 · CNF · DPLL · 自然语言谜题求解")

    with st.sidebar:
        st.markdown("**模式**")
        mode = st.radio("", ["公式测试", "自然语言求解"], label_visibility="collapsed")
        st.divider()
        _help()

    if mode == "公式测试":
        _formula_view()
    else:
        _natural_language_view()


if __name__ == "__main__":
    main()
