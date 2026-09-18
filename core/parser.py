"""词缀解析模块 - 从剪贴板文本解析物品词缀"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class AffixType(Enum):
    """词缀类型"""
    PREFIX = "prefix"      # 前缀
    SUFFIX = "suffix"      # 后缀
    IMPLICIT = "implicit"  # 隐式
    EXPLICIT = "explicit"  # 显式（如腐化词缀）


class MatchMode(Enum):
    """匹配模式"""
    CONTAINS = "contains"      # 包含关键词
    EXACT = "exact"            # 精确匹配
    REGEX = "regex"            # 正则匹配
    VALUE_RANGE = "value_range"  # 数值范围匹配


@dataclass
class Affix:
    """词缀数据"""
    name: str                    # 词缀名称
    value: Optional[int] = None  # 数值
    min_value: Optional[int] = None  # 最小值
    max_value: Optional[int] = None  # 最大值
    raw_text: str = ""           # 原始文本
    affix_type: AffixType = AffixType.EXPLICIT  # 词缀类型
    is_percentage: bool = False  # 是否百分比


@dataclass
class AffixRequirement:
    """词缀需求"""
    keyword: str                     # 关键词
    operator: str = ">="             # 运算符
    value: Optional[int] = None      # 目标值
    match_mode: MatchMode = MatchMode.CONTAINS  # 匹配模式
    is_include: bool = True          # 是否包含（True=Included, False=Excluded）
    
    def matches(self, affix: Affix) -> bool:
        """检查词缀是否匹配需求
        
        Args:
            affix: 词缀数据
        
        Returns:
            是否匹配
        """
        # 检查关键词
        if self.match_mode == MatchMode.CONTAINS:
            if self.keyword not in affix.name and self.keyword not in affix.raw_text:
                return False
        elif self.match_mode == MatchMode.EXACT:
            if self.keyword != affix.name:
                return False
        elif self.match_mode == MatchMode.REGEX:
            if not re.search(self.keyword, affix.raw_text):
                return False
        
        # 检查数值
        if self.value is not None and affix.value is not None:
            if not self._check_value(affix.value):
                return False
        
        return True
    
    def _check_value(self, actual_value: int) -> bool:
        """检查数值是否满足条件
        
        Args:
            actual_value: 实际值
        
        Returns:
            是否满足
        """
        if self.operator == ">=":
            return actual_value >= self.value
        elif self.operator == ">":
            return actual_value > self.value
        elif self.operator == "<=":
            return actual_value <= self.value
        elif self.operator == "<":
            return actual_value < self.value
        elif self.operator == "==":
            return actual_value == self.value
        elif self.operator == "!=":
            return actual_value != self.value
        return True


class ItemParser:
    """物品文本解析器"""
    
    # 数值模式
    VALUE_PATTERNS = [
        # 模式: +(XX—YY)% 或 +(XX-YY)%
        (r'\+?\(?(\d+)[—–-](\d+)\)?%?', 'range'),
        # 模式: +XX% 或 +XX
        (r'\+?(\d+)%?', 'single'),
        # 模式: 增加XX%
        (r'增加\s*(\d+)%?', 'single'),
        # 模式: XX到YY
        (r'(\d+)\s*到\s*(\d+)', 'range'),
        # 模式: XX-YY
        (r'(\d+)\s*-\s*(\d+)', 'range'),
    ]
    
    def __init__(self):
        """初始化解析器"""
        pass
    
    def parse_item(self, text: str) -> Dict:
        """解析物品文本
        
        Args:
            text: 物品文本（从剪贴板读取）
        
        Returns:
            解析结果字典
        """
        lines = text.strip().split('\n')
        
        result = {
            'name': '',
            'type': '',
            'rarity': '',
            'affixes': [],
            'requirements': [],
            'raw_text': text
        }
        
        # 按分隔符分割 sections
        sections = []
        current_section = []
        
        for line in lines:
            line = line.strip()
            if '--------' in line:
                if current_section:
                    sections.append(current_section)
                    current_section = []
            else:
                if line:
                    current_section.append(line)
        
        if current_section:
            sections.append(current_section)
        
        # 解析每个 section
        for i, section in enumerate(sections):
            if i == 0:
                # 第一个 section 是头部信息
                for line in section:
                    if line.startswith('稀有度:'):
                        result['rarity'] = line.split(':', 1)[1].strip()
                    elif not result['name']:
                        result['name'] = line
                    elif not result['type']:
                        result['type'] = line
            elif '需求:' in section[0] or 'Requires:' in section[0]:
                # 需求 section
                result['requirements'] = section
            else:
                # 词缀 section
                for line in section:
                    affix = self.parse_affix(line)
                    if affix:
                        result['affixes'].append(affix)
        
        return result
    
    def parse_affix(self, text: str) -> Optional[Affix]:
        """解析单个词缀
        
        Args:
            text: 词缀文本
        
        Returns:
            Affix对象，解析失败返回None
        """
        text = text.strip()
        if not text:
            return None
        
        # 跳过非词缀文本
        if any(skip in text for skip in ['--------', '需求:', 'Requires:', '物品等级:']):
            return None
        
        affix = Affix(name=text, raw_text=text)
        
        # 提取数值
        for pattern, pattern_type in self.VALUE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if pattern_type == 'range' and len(groups) == 2:
                    affix.min_value = int(groups[0])
                    affix.max_value = int(groups[1])
                    affix.value = affix.max_value  # 取最大值
                elif pattern_type == 'single' and len(groups) >= 1:
                    affix.value = int(groups[0])
                
                # 判断是否百分比
                if '%' in text:
                    affix.is_percentage = True
                
                break
        
        # 提取词缀名称（移除数值部分）
        name = text
        name = re.sub(r'\+?\d+[—–-]?\d*%?', '', name)
        name = re.sub(r'增加\s*', '', name)
        name = name.strip()
        if name:
            affix.name = name
        
        return affix
    
    def parse_affixes(self, text: str) -> List[Affix]:
        """解析多个词缀
        
        Args:
            text: 包含多个词缀的文本
        
        Returns:
            Affix列表
        """
        affixes = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and '--------' not in line:
                affix = self.parse_affix(line)
                if affix:
                    affixes.append(affix)
        
        return affixes


class AffixChecker:
    """词缀条件检查器"""
    
    def __init__(self):
        """初始化检查器"""
        self.included_requirements: List[AffixRequirement] = []
        self.excluded_requirements: List[AffixRequirement] = []
    
    def add_requirement(self, keyword: str, operator: str = ">=", 
                       value: int = None, is_include: bool = True):
        """添加词缀需求
        
        Args:
            keyword: 关键词
            operator: 运算符
            value: 目标值
            is_include: 是否包含
        """
        req = AffixRequirement(
            keyword=keyword,
            operator=operator,
            value=value,
            is_include=is_include
        )
        
        if is_include:
            self.included_requirements.append(req)
        else:
            self.excluded_requirements.append(req)
    
    def remove_requirement(self, index: int, is_include: bool = True):
        """删除词缀需求
        
        Args:
            index: 索引
            is_include: 是否包含
        """
        if is_include:
            if 0 <= index < len(self.included_requirements):
                self.included_requirements.pop(index)
        else:
            if 0 <= index < len(self.excluded_requirements):
                self.excluded_requirements.pop(index)
    
    def clear_requirements(self):
        """清空所有需求"""
        self.included_requirements.clear()
        self.excluded_requirements.clear()
    
    def check(self, affixes: List[Affix]) -> Dict:
        """检查词缀是否满足条件
        
        Args:
            affixes: 词缀列表
        
        Returns:
            检查结果
        """
        result = {
            'satisfied': True,
            'included_matched': [],
            'excluded_matched': [],
            'details': []
        }
        
        # 检查 Included 词缀
        for req in self.included_requirements:
            matched = False
            for affix in affixes:
                if req.matches(affix):
                    matched = True
                    result['included_matched'].append({
                        'requirement': req.keyword,
                        'affix': affix.raw_text,
                        'value': affix.value
                    })
                    break
            
            if not matched:
                result['satisfied'] = False
                result['details'].append(f"未找到包含的词缀: {req.keyword}")
        
        # 检查 Excluded 词缀
        for req in self.excluded_requirements:
            for affix in affixes:
                if req.matches(affix):
                    result['satisfied'] = False
                    result['excluded_matched'].append({
                        'requirement': req.keyword,
                        'affix': affix.raw_text,
                        'value': affix.value
                    })
                    result['details'].append(f"找到排除的词缀: {req.keyword}")
                    break
        
        return result
    
    def get_requirements_summary(self) -> Dict:
        """获取需求摘要
        
        Returns:
            需求摘要
        """
        return {
            'included': [
                {
                    'keyword': req.keyword,
                    'operator': req.operator,
                    'value': req.value
                }
                for req in self.included_requirements
            ],
            'excluded': [
                {
                    'keyword': req.keyword,
                    'operator': req.operator,
                    'value': req.value
                }
                for req in self.excluded_requirements
            ]
        }


# 测试代码
if __name__ == "__main__":
    print("词缀解析模块测试")
    print("=" * 60)
    
    # 测试物品文本
    test_text = """稀有度: 稀有
噩梦之紛擾
重型腰帶
--------
需求:
等級: 48
--------
+25 至最大生命
增加 15% 冰冷抗性
增加 20% 火焰抗性
+30 至力量
--------
物品等级: 72"""
    
    # 解析物品
    parser = ItemParser()
    item = parser.parse_item(test_text)
    
    print(f"物品名称: {item['name']}")
    print(f"物品类型: {item['type']}")
    print(f"稀有度: {item['rarity']}")
    print(f"\n词缀列表 ({len(item['affixes'])} 个):")
    for i, affix in enumerate(item['affixes'], 1):
        print(f"  {i}. {affix.raw_text}")
        print(f"     名称: {affix.name}, 数值: {affix.value}, 百分比: {affix.is_percentage}")
    
    # 测试条件检查
    print("\n" + "=" * 60)
    print("条件检查测试")
    print("=" * 60)
    
    checker = AffixChecker()
    checker.add_requirement("生命", value=20)
    checker.add_requirement("抗性", value=15)
    
    result = checker.check(item['affixes'])
    print(f"\n检查结果: {'满足' if result['satisfied'] else '不满足'}")
    print(f"匹配的Included词缀: {result['included_matched']}")
    print(f"匹配的Excluded词缀: {result['excluded_matched']}")
    print(f"详情: {result['details']}")
