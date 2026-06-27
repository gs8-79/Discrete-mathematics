# Propositional Logic Parser

C++ recursive-descent parser for propositional logic formulas. It tokenizes a formula string, builds an AST, and prints the AST as compact JSON on stdout.

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

```powershell
.\parser.exe "(A∧B)→C"
```

Example output:

```json
{"type":"implies","left":{"type":"and","children":[{"type":"var","name":"A"},{"type":"var","name":"B"}]},"right":{"type":"var","name":"C"}}
```

Invalid input returns JSON with an `error` key:

```json
{"error":"Unexpected end of input"}
```

## Files

- `ast.h`: AST node definitions and JSON helpers.
- `parser.h`: Tokenizer and parser interfaces.
- `parser.cpp`: Tokenizer, parser, and command-line entry point.
