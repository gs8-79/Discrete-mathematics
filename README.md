# 离散数学课程项目：命题逻辑解析器

本仓库是离散数学课程结课项目中的公式解析器模块。整个项目目标是实现一个命题逻辑推理系统，从公式字符串输入开始，逐步完成 AST 构建、真值表生成、CNF 转换、DPLL SAT 求解，并最终服务于谜题建模和可视化展示。

## 项目说明

### 项目目标

本项目希望实现一条完整的命题逻辑推理流程：

1. 从字符串中解析命题逻辑公式。
2. 构建统一的抽象语法树 AST。
3. 将 AST 作为后续真值表、CNF 转换、SAT 求解等模块的公共输入。
4. 通过 JSON 输出，让 C++ 核心模块可以被 Python 可视化层调用。

当前仓库已经整合了解析器、真值表、CNF、DPLL，以及人 6 负责的谜题建模和 Streamlit 可视化入口。

### 结果形式

解析器读取一个公式字符串，并向标准输出 `stdout` 打印紧凑格式的 JSON AST。

示例输入：

```text
(A∧B)→C
```

示例输出：

```json
{"type":"implies","left":{"type":"and","children":[{"type":"var","name":"A"},{"type":"var","name":"B"}]},"right":{"type":"var","name":"C"}}
```

如果输入非法，程序会返回包含 `error` 字段的 JSON：

```json
{"error":"Unexpected end of input"}
```

### 小组分工

完整课程项目分为以下模块：

| 成员 | 负责内容 | 交付物 |
| --- | --- | --- |
| 人 1 | 公式解析器 | `parser.cpp`、`parser.h`、可执行文件 `parser` / `parser.exe` |
| 人 2 | 真值表模块 | `truth_table.cpp`、JSON 真值表输出 |
| 人 3 | CNF 转换器 | `cnf.cpp`、JSON 子句集输出 |
| 人 4 | DPLL SAT 求解器 | `dpll.cpp`、SAT 结果和赋值输出 |
| 人 5 | PPT 制作 | 项目汇报 PPT |
| 人 6 | 谜题建模与 Streamlit 可视化 | `puzzles.py`、`app.py`、可视化界面 |
| 人 7 | 理论讲解与汇报主讲 | 理论提纲和演讲稿 |

## 支持的公式语法

变量命名规则：

```text
[A-Za-z][A-Za-z0-9_]*
```

支持的运算符：

| 逻辑含义 | Unicode 写法 | ASCII 备用写法 |
| --- | --- | --- |
| 否定 | `¬` | `!`、`~` |
| 合取 | `∧` | `&`、`&&` |
| 析取 | `∨` | `|`、`||` |
| 蕴含 | `→` | `->`、`=>` |
| 等价 | `↔` | `<->`、`<=>` |

运算符优先级：

```text
¬ > ∧ > ∨ > → > ↔
```

其中 `→` 按右结合解析，例如 `A->B->C` 会被解析为 `A -> (B -> C)`。

## 编译方法

使用 MSVC：

```powershell
cl /std:c++17 /EHsc /utf-8 /W4 /Fe:parser.exe parser.cpp
cl /std:c++17 /EHsc /utf-8 /W4 /DPARSER_NO_MAIN /Fe:truth_table.exe truth_table.cpp parser.cpp
cl /std:c++17 /EHsc /utf-8 /W4 /DPARSER_NO_MAIN /Fe:cnf.exe cnf.cpp parser.cpp
cl /std:c++17 /EHsc /utf-8 /W4 /Fe:dpll.exe dpll.cpp
```

使用 GCC 或 Clang：

```bash
g++ -std=c++17 -Wall -Wextra -o parser parser.cpp
g++ -std=c++17 -Wall -Wextra -DPARSER_NO_MAIN -o truth_table truth_table.cpp parser.cpp
g++ -std=c++17 -Wall -Wextra -DPARSER_NO_MAIN -o cnf cnf.cpp parser.cpp
g++ -std=c++17 -Wall -Wextra -o dpll dpll.cpp
```

## 运行方法

Windows：

```powershell
.\parser.exe "(A∧B)→C"
```

Linux 或 macOS：

```bash
./parser "(A∧B)→C"
```

真值表：

```powershell
.\truth_table.exe "A<->B"
```

CNF：

```powershell
.\cnf.exe "(A∨¬B)∧(¬A∨C)"
```

DPLL：

```powershell
'{"clauses":[[1],[-1]],"var_map":{"A":1}}' | .\dpll.exe
```

## 可视化运行

人 6 的可视化入口是 `app.py`：

```powershell
streamlit run app.py
```

页面中可以选择三人排课、4x4 数独、宠物与颜色逻辑谜题，也可以直接输入公式测试解析、真值表、CNF 和 DPLL 全链路。

## 测试

```powershell
python test_all.py
```

测试覆盖：

- `parser.exe` 输出 AST JSON。
- `truth_table.exe` 输出真值表 JSON。
- `cnf.exe` 输出 CNF 子句集 JSON。
- `dpll.exe` 求解 SAT / UNSAT。
- 三个人 6 谜题均能通过 DPLL 求得解。

## 文件说明

- `ast.h`：AST 节点定义和 JSON 辅助函数。
- `parser.h`：Tokenizer 和 Parser 的接口声明。
- `parser.cpp`：Tokenizer、递归下降解析器和命令行入口实现。
- `truth_table.cpp`：人 2 真值表模块。
- `cnf.cpp`：人 3 CNF 转换模块。
- `dpll.cpp`：人 4 DPLL SAT 求解模块。
- `puzzles.py`：人 6 谜题建模。
- `app.py`：人 6 Streamlit 可视化页面。
- `test_all.py`：端到端测试脚本。
