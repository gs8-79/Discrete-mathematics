from __future__ import annotations

import re
from dataclasses import dataclass

from puzzles import Assignment, Clause, Puzzle, make_var_map, neg, pos


@dataclass(frozen=True)
class NaturalParseResult:
    ok: bool
    puzzle: Puzzle | None
    errors: list[str]
    warnings: list[str]
    normalized_rules: list[str]


@dataclass(frozen=True)
class ValueRef:
    category: str
    value: str
    index: int


PEOPLE_LABELS = {"人", "人员", "人物", "姓名", "学生", "成员"}
SLOT_LABELS = {"时段", "时间", "时间段", "排课时段", "班次"}
KNOWN_SLOTS = ["上午", "下午", "晚上", "早上", "中午", "傍晚", "周一", "周二", "周三", "周四", "周五"]
NEGATIVE_WORDS = ("不在", "不能在", "无法在", "不可以在", "不喜欢", "没有", "不拥有", "不是", "不养", "不能")
STRUCTURAL_WORDS = ("每人", "每个人", "每个时段", "每种", "恰好", "正好", "至多", "最多", "只安排")


def parse_natural_puzzle(text: str) -> NaturalParseResult:
    lines = _split_lines(text)
    if not lines:
        return _fail("请输入自然语言线索。")

    people, slots, categories, declarations = _read_declarations(lines)
    looks_like_schedule = bool(slots) or any(slot in text for slot in KNOWN_SLOTS)
    looks_like_attribute = bool(categories)

    if looks_like_schedule and (slots or _infer_slots(lines)):
        return _parse_schedule(lines, people, slots, declarations)
    if looks_like_attribute:
        return _parse_attributes(lines, people, categories, declarations)

    return _fail(
        "无法识别题目类型。请使用“人员：张三、李四；时段：上午、下午”或“人物：Ana、Ben；宠物：猫、狗；颜色：红色、蓝色”这类模板。"
    )


def _split_lines(text: str) -> list[str]:
    pieces = re.split(r"[\n。；;]+", text)
    return [_clean_line(piece) for piece in pieces if _clean_line(piece)]


def _clean_line(line: str) -> str:
    return line.strip().strip("-*• ").replace("：", ":")


def _split_items(raw: str) -> list[str]:
    raw = raw.replace("，", "、").replace(",", "、").replace("/", "、")
    raw = raw.replace(" 和 ", "、").replace("和", "、")
    return [item.strip() for item in re.split(r"[、\s]+", raw) if item.strip()]


def _read_declarations(lines: list[str]) -> tuple[list[str], list[str], dict[str, list[str]], set[str]]:
    people: list[str] = []
    slots: list[str] = []
    categories: dict[str, list[str]] = {}
    declarations: set[str] = set()

    for line in lines:
        if ":" not in line:
            continue
        label, raw_items = line.split(":", 1)
        label = label.strip()
        items = _split_items(raw_items)
        if len(items) < 2:
            continue

        declarations.add(line)
        if label in PEOPLE_LABELS:
            people = _dedupe([*people, *items])
        elif label in SLOT_LABELS:
            slots = _dedupe([*slots, *items])
        else:
            categories[label] = _dedupe(items)

    return people, slots, categories, declarations


def _parse_schedule(
    lines: list[str],
    declared_people: list[str],
    declared_slots: list[str],
    declarations: set[str],
) -> NaturalParseResult:
    warnings: list[str] = []
    normalized: list[str] = []
    people = list(declared_people)
    slots = list(declared_slots) or _infer_slots(lines)
    direct_rules: list[tuple[str, str, bool]] = []

    for line in lines:
        if line in declarations or _is_structural(line):
            continue
        person, slot, is_positive = _read_schedule_rule(line, people, slots)
        if not person or not slot:
            continue
        if person not in people:
            people.append(person)
        if slot not in slots:
            slots.append(slot)
        direct_rules.append((person, slot, is_positive))
        normalized.append(f"{person} {'在' if is_positive else '不在'} {slot}")

    if len(people) < 2:
        return _fail("排课题至少需要 2 个人。请用“人员：张三、李四、王五”声明。")
    if len(slots) < 2:
        return _fail("排课题至少需要 2 个时段。请用“时段：上午、下午、晚上”声明。")

    var_names = [f"{person}_{slot}" for person in people for slot in slots]
    var_map = make_var_map(var_names)
    clauses: list[Clause] = []

    for person in people:
        clauses.extend(_exactly_one(var_map, [f"{person}_{slot}" for slot in slots]))

    slot_mode = _slot_mode(lines)
    for slot in slots:
        names = [f"{person}_{slot}" for person in people]
        if slot_mode == "exactly_one":
            clauses.extend(_exactly_one(var_map, names))
        else:
            clauses.extend(_at_most_one(var_map, names))

    if slot_mode == "at_most_one":
        normalized.append("结构约束：每人恰好一个时段；每个时段至多一个人")
    else:
        normalized.append("结构约束：每人恰好一个时段；每个时段恰好一个人")

    for person, slot, is_positive in direct_rules:
        literal = pos(var_map, f"{person}_{slot}") if is_positive else neg(var_map, f"{person}_{slot}")
        clauses.append([literal])

    if not direct_rules:
        warnings.append("没有识别到具体线索，仅按人员和时段结构约束求解。")

    def decode(assignment: Assignment) -> dict[str, str]:
        result: dict[str, str] = {}
        for person in people:
            for slot in slots:
                if assignment.get(f"{person}_{slot}"):
                    result[person] = slot
                    break
        return result

    puzzle = Puzzle(
        id="natural_schedule",
        title="自然语言排课题",
        description="由自然语言线索自动解析生成的排课 SAT 模型。",
        cnf={"clauses": clauses, "var_map": var_map},
        decoder=decode,
    )
    return NaturalParseResult(True, puzzle, [], warnings, normalized)


def _parse_attributes(
    lines: list[str],
    people: list[str],
    categories: dict[str, list[str]],
    declarations: set[str],
) -> NaturalParseResult:
    if len(people) < 2:
        return _fail("属性匹配题至少需要 2 个人。请用“人物：Ana、Ben、Cara”声明。")
    if not categories:
        return _fail("属性匹配题需要至少 1 类属性。请用“宠物：猫、狗、鸟”或“颜色：红色、蓝色、绿色”声明。")

    warnings: list[str] = []
    normalized: list[str] = []
    direct_rules: list[tuple[str, str, str, bool]] = []
    implication_rules: list[tuple[str, str, str, str, bool]] = []

    for category, values in categories.items():
        if len(values) != len(people):
            warnings.append(f"“{category}”数量为 {len(values)}，人物数量为 {len(people)}；精确匹配约束可能导致 UNSAT。")

    for line in lines:
        if line in declarations or _is_structural(line):
            continue

        implication = _read_implication_rule(line, categories)
        if implication:
            implication_rules.append(implication)
            left_cat, left_value, right_cat, right_value, is_positive = implication
            relation = "满足" if is_positive else "不满足"
            normalized.append(f"{left_cat}={left_value} 的人 {relation} {right_cat}={right_value}")
            continue

        direct = _read_attribute_rule(line, people, categories)
        if direct:
            direct_rules.append(direct)
            person, category, value, is_positive = direct
            normalized.append(f"{person} {'满足' if is_positive else '不满足'} {category}={value}")

    var_names = [
        f"{person}_{category}_{value}"
        for person in people
        for category, values in categories.items()
        for value in values
    ]
    var_map = make_var_map(var_names)
    clauses: list[Clause] = []

    for person in people:
        for category, values in categories.items():
            clauses.extend(_exactly_one(var_map, [f"{person}_{category}_{value}" for value in values]))

    for category, values in categories.items():
        for value in values:
            clauses.extend(_exactly_one(var_map, [f"{person}_{category}_{value}" for person in people]))

    normalized.append("结构约束：每个人每类属性恰好一个值；每个属性值恰好属于一个人")

    for person, category, value, is_positive in direct_rules:
        name = f"{person}_{category}_{value}"
        clauses.append([pos(var_map, name) if is_positive else neg(var_map, name)])

    for left_cat, left_value, right_cat, right_value, is_positive in implication_rules:
        for person in people:
            left = f"{person}_{left_cat}_{left_value}"
            right = f"{person}_{right_cat}_{right_value}"
            clauses.append([neg(var_map, left), pos(var_map, right) if is_positive else neg(var_map, right)])

    if not direct_rules and not implication_rules:
        warnings.append("没有识别到具体线索，仅按人物和属性结构约束求解。")

    def decode(assignment: Assignment) -> dict[str, dict[str, str]]:
        result: dict[str, dict[str, str]] = {}
        for person in people:
            attrs: dict[str, str] = {}
            for category, values in categories.items():
                for value in values:
                    if assignment.get(f"{person}_{category}_{value}"):
                        attrs[category] = value
                        break
            result[person] = attrs
        return result

    puzzle = Puzzle(
        id="natural_attributes",
        title="自然语言属性匹配题",
        description="由自然语言线索自动解析生成的人物-属性 SAT 模型。",
        cnf={"clauses": clauses, "var_map": var_map},
        decoder=decode,
    )
    return NaturalParseResult(True, puzzle, [], warnings, normalized)


def _read_schedule_rule(line: str, people: list[str], slots: list[str]) -> tuple[str | None, str | None, bool]:
    slot = _find_first(line, slots or KNOWN_SLOTS)
    if not slot:
        return None, None, True

    person = _find_first(line, people)
    if not person:
        match = re.match(r"^(.+?)(?:不在|不能在|无法在|不可以在|在)", line)
        if match:
            person = match.group(1).strip()
    if not person:
        return None, None, True

    is_positive = not any(word in line for word in ("不在", "不能在", "无法在", "不可以在"))
    return person, slot, is_positive


def _read_attribute_rule(
    line: str,
    people: list[str],
    categories: dict[str, list[str]],
) -> tuple[str, str, str, bool] | None:
    person = _find_first(line, people)
    value_ref = _find_value(line, categories)
    if not person or not value_ref:
        return None

    is_positive = not any(word in line for word in NEGATIVE_WORDS)
    return person, value_ref.category, value_ref.value, is_positive


def _read_implication_rule(
    line: str,
    categories: dict[str, list[str]],
) -> tuple[str, str, str, str, bool] | None:
    if "的人" not in line:
        return None

    refs = _find_values(line, categories)
    if len(refs) < 2:
        return None

    left = refs[0]
    right = refs[1]
    tail = line[line.find("的人") + len("的人") :]
    is_positive = not any(word in tail for word in NEGATIVE_WORDS)
    return left.category, left.value, right.category, right.value, is_positive


def _find_value(line: str, categories: dict[str, list[str]]) -> ValueRef | None:
    values = _find_values(line, categories)
    return values[0] if values else None


def _find_values(line: str, categories: dict[str, list[str]]) -> list[ValueRef]:
    refs: list[ValueRef] = []
    for category, values in categories.items():
        for value in values:
            index = line.find(value)
            if index >= 0:
                refs.append(ValueRef(category, value, index))
    return sorted(refs, key=lambda ref: ref.index)


def _infer_slots(lines: list[str]) -> list[str]:
    found: list[str] = []
    for line in lines:
        for slot in KNOWN_SLOTS:
            if slot in line and slot not in found:
                found.append(slot)
    return found


def _slot_mode(lines: list[str]) -> str:
    joined = "。".join(lines)
    if "每个时段" in joined and any(word in joined for word in ("恰好", "正好", "必须", "都安排")):
        return "exactly_one"
    return "at_most_one"


def _exactly_one(var_map: dict[str, int], names: list[str]) -> list[Clause]:
    return [[pos(var_map, name) for name in names], *_at_most_one(var_map, names)]


def _at_most_one(var_map: dict[str, int], names: list[str]) -> list[Clause]:
    clauses: list[Clause] = []
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            clauses.append([neg(var_map, left), neg(var_map, right)])
    return clauses


def _find_first(line: str, candidates: list[str]) -> str | None:
    matches = [candidate for candidate in candidates if candidate and candidate in line]
    if not matches:
        return None
    return max(matches, key=len)


def _is_structural(line: str) -> bool:
    return any(word in line for word in STRUCTURAL_WORDS)


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def _fail(message: str) -> NaturalParseResult:
    return NaturalParseResult(False, None, [message], [], [])
