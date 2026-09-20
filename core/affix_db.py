"""词缀数据库模块 - 内置爬取 + T阶推导

T阶推导原理：
poe2db 的 ModsView JSON 中不含 Tier 字段，但同一词缀组内不同名称
对应不同数值区间（如冰冷抗性：海豹之6~10 → 哈斯特之41~45）。
按数值降序排列后自动编号：最高数值 = T1，次之 = T2 ...
"""

import json
import re
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from core.paths import data_dir

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


BASE_URL = "https://poe2db.tw/tw"
REQUEST_DELAY = 2.0
REQUEST_TIMEOUT = 30
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# 物品页面路径映射（与 poe2-crawler 保持一致）
ITEM_PAGES = {
    # 單手武器
    "claws": "Claws", "daggers": "Daggers", "wands": "Wands",
    "one_hand_swords": "One_Hand_Swords", "one_hand_axes": "One_Hand_Axes",
    "one_hand_maces": "One_Hand_Maces", "sceptres": "Sceptres",
    "spears": "Spears", "flails": "Flails",
    # 雙手武器
    "bows": "Bows", "staves": "Staves", "two_hand_swords": "Two_Hand_Swords",
    "two_hand_axes": "Two_Hand_Axes", "two_hand_maces": "Two_Hand_Maces",
    "quarterstaves": "Quarterstaves", "crossbows": "Crossbows",
    "traps": "Traps", "talismans": "Talismans",
    # 副手
    "quivers": "Quivers", "shields_str": "Shields_str",
    "shields_str_dex": "Shields_str_dex", "shields_str_int": "Shields_str_int",
    "bucklers": "Bucklers", "foci": "Foci",
    # 護甲-手套
    "gloves_str": "Gloves_str", "gloves_dex": "Gloves_dex", "gloves_int": "Gloves_int",
    "gloves_str_dex": "Gloves_str_dex", "gloves_str_int": "Gloves_str_int",
    "gloves_dex_int": "Gloves_dex_int",
    # 護甲-鞋子
    "boots_str": "Boots_str", "boots_dex": "Boots_dex", "boots_int": "Boots_int",
    "boots_str_dex": "Boots_str_dex", "boots_str_int": "Boots_str_int",
    "boots_dex_int": "Boots_dex_int",
    # 護甲-胸甲
    "body_armours_str": "Body_Armours_str", "body_armours_dex": "Body_Armours_dex",
    "body_armours_int": "Body_Armours_int", "body_armours_str_dex": "Body_Armours_str_dex",
    "body_armours_str_int": "Body_armours_str_int", "body_armours_dex_int": "Body_Armours_dex_int",
    "body_armours_str_dex_int": "Body_Armours_str_dex_int",
    # 護甲-頭部
    "helmets_str": "Helmets_str", "helmets_dex": "Helmets_dex", "helmets_int": "Helmets_int",
    "helmets_str_dex": "Helmets_str_dex", "helmets_str_int": "Helmets_str_int",
    "helmets_dex_int": "Helmets_dex_int",
    # 飾品
    "amulets": "Amulets", "rings": "Rings", "belts": "Belts",
}

# 中文显示名
ITEM_NAMES_CN = {
    "claws": "爪", "daggers": "匕首", "wands": "法杖(单手)",
    "one_hand_swords": "单手剑", "one_hand_axes": "单手斧", "one_hand_maces": "单手锤",
    "sceptres": "权杖", "spears": "长矛", "flails": "链锤",
    "bows": "弓", "staves": "长杖", "two_hand_swords": "双手剑",
    "two_hand_axes": "双手斧", "two_hand_maces": "双手锤", "quarterstaves": "细杖",
    "crossbows": "十字弓", "traps": "陷阱", "talismans": "魔符",
    "quivers": "箭袋", "shields_str": "力量盾", "shields_str_dex": "力敏盾",
    "shields_str_int": "智盾", "bucklers": "轻盾", "foci": "法器",
    "gloves_str": "力量手套", "gloves_dex": "敏捷手套", "gloves_int": "智慧手套",
    "gloves_str_dex": "力敏手套", "gloves_str_int": "力智手套", "gloves_dex_int": "敏智手套",
    "boots_str": "力量鞋", "boots_dex": "敏捷鞋", "boots_int": "智慧鞋",
    "boots_str_dex": "力敏鞋", "boots_str_int": "力智鞋", "boots_dex_int": "敏智鞋",
    "body_armours_str": "力量胸甲", "body_armours_dex": "敏捷胸甲", "body_armours_int": "智慧胸甲",
    "body_armours_str_dex": "力敏胸甲", "body_armours_str_int": "力智胸甲",
    "body_armours_dex_int": "敏智胸甲", "body_armours_str_dex_int": "三元胸甲",
    "helmets_str": "力量头盔", "helmets_dex": "敏捷头盔", "helmets_int": "智慧头盔",
    "helmets_str_dex": "力敏头盔", "helmets_str_int": "力智头盔", "helmets_dex_int": "敏智头盔",
    "amulets": "项链", "rings": "戒指", "belts": "腰带",
}


def strip_html(html_str: str) -> str:
    """去除HTML标签"""
    if not html_str:
        return ""
    return re.sub(r'<[^>]+>', '', html_str).strip()


def normalize_desc(description: str) -> str:
    """将词缀描述归一化为匹配模板（数字→N，统一破折号）"""
    d = strip_html(description)
    d = re.sub(r'[—–-]', '-', d)
    d = re.sub(r'\d+(?:\.\d+)?', 'N', d)
    d = re.sub(r'\s+', '', d)
    return d


def extract_last_range(description: str) -> Optional[tuple]:
    """提取描述中最后一个数值区间 (lo, hi)，用于T阶数值判定"""
    ranges = re.findall(r'(\d+)(?:\.\d+)?[—–-](\d+)(?:\.\d+)?', strip_html(description))
    if ranges:
        lo, hi = ranges[-1]
        return (float(lo), float(hi))
    single = re.findall(r'(\d+(?:\.\d+)?)', strip_html(description))
    if single:
        v = float(single[-1])
        return (v, v)
    return None


def effect_display_name(description: str) -> str:
    """从描述提取显示用效果名，如 '+（6—10)%冰冷抗性' → '冰冷抗性'"""
    d = strip_html(description)
    d = re.sub(r'\d+(?:\.\d+)?[—–-]?\d*(?:\.\d+)?%?', '', d)
    d = re.sub(r'[+()（）%\s.。]', '', d)
    d = re.sub(r'^(增加|附加|获得)', r'\1', d)
    d = d.lstrip('至')
    return d or strip_html(description)


class AffixDB:
    """词缀数据库：查询 + T阶推导 + 内置爬取"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(data_dir() / "poe2.db")
            # 打包运行时：首次启动从内嵌数据释放数据库到exe目录
            if getattr(sys, 'frozen', False) and not Path(db_path).exists():
                bundled = Path(sys._MEIPASS) / "data" / "poe2.db"
                if bundled.exists():
                    shutil.copy(bundled, db_path)
        self.db_path = db_path
        self._groups_cache: Dict[str, List[Dict]] = {}

    # ==================== 查询 ====================

    def get_available_item_types(self) -> List[tuple]:
        """返回数据库中已有词缀数据的装备类型 [(key, 中文名, 词缀组数), ...]"""
        import collections
        counts = collections.Counter()
        try:
            conn = sqlite3.connect(self.db_path)
            for (classes,) in conn.execute(
                    "SELECT item_classes FROM modifiers WHERE mod_type IN ('prefix','suffix')"):
                try:
                    for k in json.loads(classes):
                        counts[k] += 1
                except Exception:
                    pass
            conn.close()
        except Exception:
            pass

        result = []
        for key in ITEM_PAGES:
            if counts.get(key, 0) > 0:
                result.append((key, ITEM_NAMES_CN.get(key, key), counts[key]))
        return result

    def get_affix_groups(self, item_key: str) -> List[Dict]:
        """获取某装备类型的词缀组（含T阶推导）

        Returns:
            [{effect, mod_type, template, tiers: [{tier, name, lo, hi, description}]}]
        """
        if item_key in self._groups_cache:
            return self._groups_cache[item_key]

        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT name, description, mod_type FROM modifiers "
            "WHERE item_classes LIKE ? AND mod_type IN ('prefix','suffix') "
            "AND is_essence_only = 0",
            (f'%{item_key}%',)
        ).fetchall()
        conn.close()

        # 按 (归一化模板, mod_type) 分组，组内按描述去重
        groups: Dict[tuple, Dict[float, Dict]] = {}
        for name, description, mod_type in rows:
            description = strip_html(description)
            name = strip_html(name)
            if not description or '<' in name:
                continue
            template = normalize_desc(description)
            rng = extract_last_range(description)
            if not rng:
                continue
            key = (template, mod_type)
            groups.setdefault(key, {})
            # 同模板同数值区间只保留一条
            if rng[0] not in groups[key]:
                groups[key][rng[0]] = {
                    'name': name,
                    'lo': rng[0],
                    'hi': rng[1],
                    'description': description,
                }

        result = []
        for (template, mod_type), tiers_dict in groups.items():
            # 数值降序 → T1, T2, T3...
            sorted_tiers = sorted(tiers_dict.values(), key=lambda t: t['lo'], reverse=True)
            if not sorted_tiers:
                continue
            tier_list = []
            for i, t in enumerate(sorted_tiers):
                t = dict(t)
                t['tier'] = i + 1
                tier_list.append(t)
            result.append({
                'effect': effect_display_name(tier_list[0]['description']),
                'mod_type': mod_type,
                'template': template,
                'tiers': tier_list,
            })

        result.sort(key=lambda g: (g['mod_type'], g['effect']))
        self._groups_cache[item_key] = result
        return result

    def find_group(self, item_key: str, template: str) -> Optional[Dict]:
        """按模板查找词缀组"""
        for g in self.get_affix_groups(item_key):
            if g['template'] == template:
                return g
        return None

    def reload(self):
        """清空缓存（爬取新数据后调用）"""
        self._groups_cache.clear()

    # ==================== 内置爬取 ====================

    @staticmethod
    def crawl(item_keys: List[str],
              progress_cb: Callable[[str], None] = None,
              stop_cb: Callable[[], bool] = None,
              delay: float = REQUEST_DELAY) -> Dict[str, int]:
        """爬取指定装备类型的词缀并写入数据库

        Args:
            item_keys: 要爬取的类型key列表
            progress_cb: 进度回调（写日志）
            stop_cb: 返回True则中止
            delay: 请求间隔秒数

        Returns:
            {item_key: 新增词缀数}
        """
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("需要安装requests: pip install requests")

        def log(msg):
            if progress_cb:
                progress_cb(msg)

        saved = {}
        conn = sqlite3.connect(AffixDB._db_path_static())

        for i, key in enumerate(item_keys):
            if stop_cb and stop_cb():
                log("[爬取] 已中止")
                break
            page = ITEM_PAGES.get(key)
            if not page:
                continue

            log(f"[爬取] ({i+1}/{len(item_keys)}) {ITEM_NAMES_CN.get(key, key)} ...")
            try:
                mods = AffixDB._crawl_one(key, page)
            except Exception as e:
                log(f"[爬取] {key} 失败: {e}")
                continue

            # 去重后写入
            seen = set()
            count = 0
            for m in mods:
                dedup_key = (m['name'], m['description'], m['mod_type'])
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                cur = conn.execute(
                    "INSERT OR IGNORE INTO modifiers (name, name_en, mod_group, mod_type, item_classes, "
                    "tier, level_requirement, description, values_min, values_max, tags, weight, "
                    "generation_type, is_essence_only, is_crafted) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (m['name'], m['name'], '', m['mod_type'], json.dumps([key]),
                     0, m.get('level', 0), m['description'], m['values_min'], m['values_max'],
                     '[]', 0, m.get('gen_type', 0), 0, 0))
                count += cur.rowcount
            conn.commit()
            saved[key] = count
            log(f"[爬取] {ITEM_NAMES_CN.get(key, key)}: 新增 {count} 条词缀")

            if i < len(item_keys) - 1:
                time.sleep(delay)

        conn.close()
        return saved

    @staticmethod
    def _db_path_static() -> str:
        return str(data_dir() / "poe2.db")

    @staticmethod
    def _crawl_one(item_key: str, page_path: str) -> List[Dict]:
        """爬取单个类型页面的 normal 词缀池"""
        url = f"{BASE_URL}/{page_path}"
        resp = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        html = resp.text

        start = html.find('new ModsView(')
        if start == -1:
            raise RuntimeError("页面中未找到 ModsView 数据")
        start += len('new ModsView(')

        decoder = json.JSONDecoder()
        data, _ = decoder.raw_decode(html, start)

        mods = []
        normal_list = data.get('normal', [])
        if isinstance(normal_list, dict):
            normal_list = list(normal_list.values())

        for item in normal_list:
            if not isinstance(item, dict):
                continue
            m = AffixDB._parse_mod(item, item_key)
            if m:
                mods.append(m)
        return mods

    @staticmethod
    def _parse_mod(data: dict, item_key: str) -> Optional[Dict]:
        """解析单条 ModsView 词缀数据"""
        try:
            name = strip_html(str(data.get('Name', '')))
            if not name:
                return None
            raw_desc = str(data.get('str', ''))
            description = strip_html(raw_desc)
            if not description:
                return None

            ranges = re.findall(r'(\d+)[—\-](\d+)', description)
            values_min = ",".join(r[0] for r in ranges)
            values_max = ",".join(r[1] for r in ranges)

            gen_type = data.get('ModGenerationTypeID', 0)
            if isinstance(gen_type, str):
                gen_type = int(gen_type) if gen_type.isdigit() else 0
            mod_type = "prefix" if gen_type == 1 else "suffix" if gen_type == 2 else ""
            if not mod_type:
                return None

            return {
                'name': name,
                'description': description,
                'mod_type': mod_type,
                'values_min': values_min,
                'values_max': values_max,
                'gen_type': gen_type,
                'level': data.get('Level', 0),
            }
        except Exception:
            return None


# 测试
if __name__ == "__main__":
    db = AffixDB()

    print("=== 可用装备类型 ===")
    for key, cn, count in db.get_available_item_types():
        print(f"  {cn} ({key}): {count} 条词缀")

    print("\n=== 冰冷抗性 T阶推导 (rings) ===")
    for g in db.get_affix_groups('rings'):
        if '冰冷抗性' in g['effect']:
            print(f"  效果: {g['effect']} ({g['mod_type']})")
            for t in g['tiers']:
                print(f"    T{t['tier']}: {t['name']} {t['lo']}~{t['hi']}")
            break
