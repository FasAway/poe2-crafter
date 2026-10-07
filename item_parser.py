"""Parse detailed PoE item clipboard text. No game input or third-party dependencies."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path

NUMBER = r"[+-]?\d+(?:\.\d+)?"
ROLL = re.compile(rf"(?P<value>{NUMBER})(?:\s*\(\s*(?P<low>{NUMBER})\s*[-–—]\s*(?P<high>{NUMBER})\s*\))?")
TIER = re.compile(r"(?:階層|阶层|Tier)\s*[:：]\s*(\d+)", re.I)


@dataclass
class Roll:
    value: str
    low: str | None = None
    high: str | None = None


@dataclass
class Stat:
    text: str
    template: str
    rolls: list[Roll]


@dataclass
class Modifier:
    kind: str
    name: str
    tier: int | None
    fractured: bool
    crafted: bool
    tags: list[str]
    annotation: str
    stats: list[Stat] = field(default_factory=list)


@dataclass
class Item:
    raw_text: str = ""
    item_class: str = ""
    rarity: str = ""
    name: str = ""
    base: str = ""
    item_level: int | None = None
    corrupted: bool = False
    modifiers: list[Modifier] = field(default_factory=list)
    other_sections: list[list[str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def detailed(self) -> bool:
        return bool(self.modifiers) and all(m.stats for m in self.modifiers)


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


def parse_stat(text: str) -> Stat:
    """Consume actual value and its optional range together, never read range as roll."""
    rolls = [Roll(m['value'], m['low'], m['high']) for m in ROLL.finditer(text)]
    return Stat(text, ROLL.sub("#", text), rolls)


def parse_item(text: str) -> Item:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("装备文本为空")
    lines = [line.strip() for line in text.replace("\r\n", "\n").splitlines() if line.strip()]
    sections: list[list[str]] = [[]]
    for line in lines:
        if re.fullmatch(r"-{4,}", line):
            if sections[-1]:
                sections.append([])
        else:
            sections[-1].append(line)
    sections = [s for s in sections if s]
    item = Item(raw_text=text)
    names = []
    for line in sections[0]:
        pair = re.match(r"^(物品種類|物品种类|Item Class|稀有度|Rarity)\s*[:：]\s*(.+)$", line, re.I)
        if pair:
            if pair[1].lower() in ('稀有度', 'rarity'):
                item.rarity = pair[2]
            else:
                item.item_class = pair[2]
        else:
            names.append(line)
    if not item.rarity or not names:
        raise ValueError("不是有效的装备复制文本：缺少稀有度或名称")
    item.name = names[0]
    item.base = names[-1]
    for section in sections[1:]:
        current: Modifier | None = None
        other = []
        for line in section:
            level = re.fullmatch(r"(?:物品等級|物品等级|Item Level)\s*[:：]\s*(\d+)", line, re.I)
            if level:
                item.item_level = int(level[1])
            if line in ('已汙染', '已污染', '已腐化', 'Corrupted'):
                item.corrupted = True
            if line.startswith('{') and line.endswith('}'):
                # Traditional client names base implicits 固定詞綴. They are
                # not rerollable explicit modifiers or crafting stop criteria.
                if re.search(r'固定詞綴|固定词缀', line):
                    current = None
                    other.append(line)
                    continue
                kind = re.search(r"前綴|前缀|後綴|后缀|Prefix|Suffix|Implicit|固有|隱性|隐性", line, re.I)
                if not kind:
                    current = None
                    other.append(line)
                    item.warnings.append(f"未识别词缀标记：{line}")
                    continue
                token = kind[0].lower()
                kind_name = 'prefix' if token in ('前綴', '前缀', 'prefix') else 'suffix' if token in ('後綴', '后缀', 'suffix') else 'implicit'
                name = re.search(r'["“](.*?)["”]', line)
                tier = TIER.search(line)
                tag_part = re.split(r'\s+[—–]\s+', line, maxsplit=1)
                tags = [v.strip() for v in re.split('[,，]', tag_part[1].rstrip('} '))] if len(tag_part) == 2 else []
                current = Modifier(kind_name, name[1] if name else '', int(tier[1]) if tier else None,
                                   bool(re.search('已破裂|Fractured', line, re.I)),
                                   bool(re.search('已工藝|已工艺|Crafted', line, re.I)), tags, line)
                item.modifiers.append(current)
            elif current is not None:
                current.stats.append(parse_stat(line))
            else:
                other.append(line)
        if other:
            item.other_sections.append(other)
    if not item.modifiers:
        item.warnings.append("未发现详细词缀标记，不能可靠区分前后缀及阶层；请复制详细装备文本")
    for modifier in item.modifiers:
        if not modifier.stats:
            item.warnings.append(f"词缀没有属性文本：{modifier.annotation}")
    return item


def check_condition(item: Item, *, keyword: str, tier: int | None = None,
                    minimum: str | None = None, value_index: int | None = None,
                    kind: str | None = None, tier_max: int | None = None) -> dict:
    """Check one explicit modifier condition. Ambiguity produces unknown, never success.

    Tier is exact unless tier_max specifies an inclusive upper bound.
    minimum applies to an actual roll, not the annotation range.
    Multiple actual rolls require a zero-based value_index supplied by the caller.
    Separate callers combine conditions as appropriate for the requested recipe.
    """
    if not keyword.strip():
        raise ValueError("词缀关键词不能为空")
    if tier is not None and tier < 1:
        raise ValueError("阶层必须大于0")
    if tier_max is not None and (tier is None or tier_max < tier):
        raise ValueError("阶层区间需有起始阶层，且结束阶层不能小于起始阶层")
    if kind not in (None, 'prefix', 'suffix', 'implicit'):
        raise ValueError("未知词缀类型")
    if value_index is not None and value_index < 0:
        raise ValueError("数值索引不能为负")
    threshold = Decimal(minimum) if minimum is not None else None
    if threshold is not None and not threshold.is_finite():
        raise ValueError("数值阈值必须是有限数")
    if not item.detailed or item.warnings:
        return {'status': 'unknown', 'reason': '装备详细词缀不完整或含未识别标记', 'matches': []}
    matches = []
    ambiguous = False
    for modifier in item.modifiers:
        if kind and modifier.kind != kind:
            continue
        for stat in modifier.stats:
            if normalize(keyword) not in normalize(stat.template.replace('#', '')):
                continue
            if tier is not None:
                if modifier.tier is None:
                    ambiguous = True
                    continue
                if not tier <= modifier.tier <= (tier if tier_max is None else tier_max):
                    continue
            if threshold is not None:
                if value_index is None and len(stat.rolls) != 1:
                    ambiguous = True
                    continue
                index = 0 if value_index is None else value_index
                if index >= len(stat.rolls):
                    ambiguous = True
                    continue
                if Decimal(stat.rolls[index].value) < threshold:
                    continue
            matches.append({'modifier': modifier.name, 'tier': modifier.tier, 'text': stat.text,
                            'fractured': modifier.fractured, 'crafted': modifier.crafted,
                            'values': [r.value for r in stat.rolls]})
    return {'status': 'matched' if matches else 'unknown' if ambiguous else 'not_matched',
            'reason': '找到匹配词缀' if matches else '缺少阶层或需要明确选择数值' if ambiguous else '未找到满足条件的词缀',
            'matches': matches}


def main() -> None:
    cli = argparse.ArgumentParser(description='装备文本解析验证；不操作游戏')
    cli.add_argument('file', type=Path)
    cli.add_argument('--keyword')
    cli.add_argument('--tier', type=int, help='精确阶层')
    cli.add_argument('--tier-max', type=int, help='与--tier一起指定可接受阶层区间，含两端')
    cli.add_argument('--minimum', help='实际数值下限')
    cli.add_argument('--value-index', type=int, help='多数值属性中的位置，从0开始')
    args = cli.parse_args()
    item = parse_item(args.file.read_text(encoding='utf-8-sig'))
    result = {'item': asdict(item)}
    if args.keyword:
        result['condition'] = check_condition(item, keyword=args.keyword, tier=args.tier,
                                               minimum=args.minimum, value_index=args.value_index, tier_max=args.tier_max)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
