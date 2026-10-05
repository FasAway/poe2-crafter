"""Input-independent crafting controller. All I/O goes through an adapter."""
from dataclasses import dataclass
import threading
import re
from item_parser import Item, check_condition, parse_item


@dataclass(frozen=True)
class Condition:
    keyword: str
    tier: int | None = None
    minimum: str | None = None
    value_index: int | None = None
    kind: str | None = None
    tier_max: int | None = None


def parse_tier_spec(text: str) -> tuple[int | None, int | None]:
    """Accept a single tier or inclusive range: 1, T1, 1-3, T1-T3."""
    if not text.strip():
        return None, None
    match = re.fullmatch(r'\s*[Tt]?\s*(\d+)\s*(?:[-–—~～至]\s*[Tt]?\s*(\d+)\s*)?', text)
    if not match:
        raise ValueError('阶层请填1或1-3，也支持T1-T3；留空则不限')
    low = int(match[1])
    high = int(match[2]) if match[2] is not None else None
    if low < 1 or high is not None and high < low:
        raise ValueError('阶层须大于0，区间请按1-3这样的顺序填写')
    return low, high


def evaluate(item: Item, conditions: list[Condition]) -> tuple[str, list[dict]]:
    if not conditions:
        raise ValueError('请先添加停止条件')
    results = [check_condition(item, **vars(c)) for c in conditions]
    # Fail closed even if another AND condition is definitely not satisfied.
    status = 'unknown' if any(r['status'] == 'unknown' for r in results) else 'matched' if all(r['status'] == 'matched' for r in results) else 'not_matched'
    return status, results


def identity(item: Item) -> tuple:
    # Rare names can change during crafting, so anchor to class/base/item level.
    return item.item_class, item.base, item.item_level, item.rarity


def fingerprint(item: Item) -> tuple:
    return tuple((m.kind, m.name, m.tier, m.fractured, m.crafted,
                  tuple(s.text for s in m.stats)) for m in item.modifiers)


class Cancelled(Exception):
    pass


class Crafter:
    def __init__(self, adapter, log, on_item=None):
        self.adapter = adapter
        self.log = log
        self.on_item = on_item
        self.stop = threading.Event()
        self.attempts = 0

    def checkpoint(self):
        if self.stop.is_set():
            raise Cancelled('已停止')
        self.adapter.guard()

    def read(self) -> Item:
        self.checkpoint()
        item = parse_item(self.adapter.copy_item(self.stop))
        if not item.detailed or item.warnings:
            raise ValueError('没有获得完整详细词缀，停止。请先用只读测试检查复制组合键。')
        if not item.item_class or item.item_level is None:
            raise ValueError('缺少物品类别或等级，不能验证目标装备身份')
        self.checkpoint()
        if self.on_item:
            self.on_item(item)
        return item

    def run(self, conditions: list[Condition], limit: int = 100):
        if not 1 <= limit <= 10000:
            raise ValueError('最大次数须为1至10000')
        self.attempts = 0
        try:
            before = self.read()
            anchor = identity(before)
            for _ in range(limit + 1):
                self.checkpoint()
                state, results = evaluate(before, conditions)
                self.log(f'条件判断：{state}；' + '；'.join(r['reason'] for r in results))
                if state == 'unknown':
                    raise ValueError('条件判断有歧义，已停止。明确前/后缀、阶层或数值位置后重试。')
                if state == 'matched':
                    self.log(f'已满足全部条件；本轮发送混沌石操作 {self.attempts} 次')
                    return 'matched'
                if self.attempts >= limit:
                    self.log('达到操作次数上限，已停止')
                    return 'limit'
                if before.corrupted or any(line in ('已複製', '已复制', 'Mirrored') for section in before.other_sections for line in section):
                    raise ValueError('装备有污染/复制标记，拒绝继续使用混沌石')
                if before.rarity not in ('稀有', 'Rare'):
                    raise ValueError('第一版仅对稀有装备使用混沌石')
                self.checkpoint()
                self.adapter.use_chaos(self.stop)
                self.attempts += 1
                self.log(f'已发送第 {self.attempts} 次操作，正在验证词缀变化')
                after = self.read()
                if identity(after) != anchor:
                    raise ValueError('读取到的装备基底/类别/等级变化，已停止')
                if fingerprint(after) == fingerprint(before):
                    # It can legitimately roll the same result. Stop conservatively;
                    # never automatically click again on inconclusive feedback.
                    raise ValueError('操作后词缀未变化：可能未生效、通货耗尽或出现相同结果。已停止，请检查游戏。')
                before = after
        except Cancelled:
            self.log('已停止')
            return 'cancelled'
        finally:
            self.adapter.release()
