# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

离散数学课程项目 — 命题逻辑推理系统。从公式字符串到 AST、真值表、CNF、DPLL SAT 求解，再到谜题建模和自然语言输入。

## Commands

```bash
# 测试
python test_all.py              # 全量集成测试（核心模块 + 谜题 + 自然语言解析）

# 可视化
streamlit run app.py            # 启动 Web 界面，http://localhost:8501

# 手动调用各 C++ 模块
./parser.exe "(A∧B)→C"                                    # 输出 AST JSON
./truth_table.exe "A<->B"                                 # 输出真值表 JSON
./cnf.exe "(A∨¬B)∧(¬A∨C)"                                # 输出 CNF JSON
echo '{"clauses":[[1],[-1]],"var_map":{"A":1}}' | ./dpll.exe   # DPLL SAT/UNSAT
```

## Architecture

```
User input (formula / NL text)
  → parser.exe          C++ 公式解析 → AST JSON
  → truth_table.exe     C++ 真值表生成（链接 parser.cpp，宏 PARSER_NO_MAIN）
  → cnf.exe             C++ CNF 转换（同样链接 parser.cpp）
  → dpll.exe            C++ DPLL SAT 求解（独立编译，从 stdin 读 CNF JSON）
  → nl_parser.py        Python 自然语言谜题解析 → CNF → dpll.exe
```

C++ 模块通过 JSON stdin/stdout 通信。Python 层用 `subprocess.run()` 调用 exe，`@st.cache_data` 缓存结果。

## Key files

| File | Role |
|------|------|
| `ast.h` | AST 节点定义和 JSON 序列化，所有 C++ 模块共享 |
| `parser.h/cpp` | Tokenizer + 递归下降解析器，`PARSER_NO_MAIN` 宏控制是否编译 main() |
| `truth_table.cpp` | 调用 parser 解析公式 → 枚举赋值 → JSON 真值表 |
| `cnf.cpp` | 调用 parser 解析公式 → Tseitin 转换 → JSON 子句集 + var_map |
| `dpll.cpp` | 独立编译，stdin 读 CNF JSON → DPLL 求解 → SAT/UNSAT + assignment |
| `puzzles.py` | Puzzle dataclass + 三个硬编码谜题（排课/数独/宠物颜色），提供 `exactly_one` 约束构造工具 |
| `nl_parser.py` | 自然语言谜题解析器，`parse_natural_puzzle(text)` → `NaturalParseResult`（含 Puzzle 或错误） |
| `app.py` | Streamlit 可视化，两个视图：公式测试 + 自然语言求解 |
| `test_all.py` | 集成测试，调用所有 exe 和 `nl_parser` |
| `.streamlit/config.toml` | Streamlit 主题配色 |

## CNF variable numbering convention

`var_map` 按变量名字母序从 1 开始编号。`clauses` 中正数=正文字，负数=负文字。dpll 的 assignment 覆盖 `var_map` 中所有变量。

## Natural language parser (`nl_parser.py`)

`parse_natural_puzzle(text)` 返回 `NaturalParseResult(ok, puzzle, errors, warnings, normalized_rules)`。支持两种题型：

- **排课类**：`人员：张三、李四；时段：上午、下午、晚上` + 线索如 `张三不在上午。`
- **属性匹配类**：`人物：Ana、Ben；宠物：猫、狗；颜色：红色、蓝色` + 线索如 `Ben拥有狗。` + 蕴含规则如 `拥有猫的人也喜欢绿色。`

每种题型自动生成 CNF 约束（exactly_one / at_most_one + 直接线索 + 蕴含规则），解析后的 Puzzle 可直接传入 dpll。
