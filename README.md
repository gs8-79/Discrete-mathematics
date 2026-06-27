# Discrete Mathematics Project: Propositional Logic Parser

This repository contains the parser module for a discrete mathematics course project. The project focuses on building a propositional logic reasoning system, starting from formula parsing and extending toward truth-table generation, CNF conversion, DPLL SAT solving, and puzzle visualization.

## About

### Goal

The goal of this project is to implement a propositional logic reasoning pipeline:

1. Parse propositional logic formulas from strings.
2. Build a shared abstract syntax tree (AST).
3. Use the AST as the common input for later modules such as truth-table evaluation, CNF conversion, and SAT solving.
4. Provide JSON output so that C++ core modules can be called from a Python visualization layer.

The current repository contains the completed parser module.

### Result Format

The parser reads a formula string and prints a compact JSON AST to `stdout`.

Example input:

```text
(A∧B)→C
```

Example output:

```json
{"type":"implies","left":{"type":"and","children":[{"type":"var","name":"A"},{"type":"var","name":"B"}]},"right":{"type":"var","name":"C"}}
```

Invalid input returns a JSON object with an `error` field:

```json
{"error":"Unexpected end of input"}
```

### Team Division

The full course project is divided into the following modules:

| Member | Responsibility | Deliverable |
| --- | --- | --- |
| Person 1 | Formula parser | `parser.cpp`, `parser.h`, executable `parser` / `parser.exe` |
| Person 2 | Truth-table module | `truth_table.cpp`, JSON truth-table output |
| Person 3 | CNF converter | `cnf.cpp`, JSON clause-set output |
| Person 4 | DPLL SAT solver | `dpll.cpp`, SAT result and assignment output |
| Person 5 | Presentation slides | Final project presentation |
| Person 6 | Puzzle modeling and Streamlit visualization | `puzzles.py`, `app.py`, visualization UI |
| Person 7 | Theory explanation and oral presentation | Presentation outline and script |

## Supported Syntax

Variables:

```text
[A-Za-z][A-Za-z0-9_]*
```

Operators:

| Logic | Unicode | ASCII aliases |
| --- | --- | --- |
| NOT | `¬` | `!`, `~` |
| AND | `∧` | `&`, `&&` |
| OR | `∨` | `|`, `||` |
| IMPLIES | `→` | `->`, `=>` |
| IFF | `↔` | `<->`, `<=>` |

Precedence:

```text
¬ > ∧ > ∨ > → > ↔
```

`→` is right-associative.

## Build

MSVC:

```powershell
cl /std:c++17 /EHsc /utf-8 /W4 /Fe:parser.exe parser.cpp
```

GCC or Clang:

```bash
g++ -std=c++17 -Wall -Wextra -o parser parser.cpp
```

## Run

Windows:

```powershell
.\parser.exe "(A∧B)→C"
```

Linux or macOS:

```bash
./parser "(A∧B)→C"
```

## Files

- `ast.h`: AST node definitions and JSON helper functions.
- `parser.h`: Tokenizer and parser interfaces.
- `parser.cpp`: Tokenizer, recursive-descent parser, and command-line entry point.
