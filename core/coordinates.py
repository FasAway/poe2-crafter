"""坐标校准模块 - 管理游戏坐标"""

import json
from typing import Dict, Tuple, Optional
from pathlib import Path


class CoordinateManager:
    """坐标管理器"""
    
    def __init__(self, config_path: str = None):
        """初始化坐标管理器
        
        Args:
            config_path: 配置文件路径
        """
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "config" / "coordinates.json")
        
        self.config_path = config_path
        self.coordinates = {
            'currency': {'x': 0, 'y': 0, 'name': '通货'},
            'item': {'x': 0, 'y': 0, 'name': '物品'},
        }
        
        # 加载配置
        self.load()
    
    def set_currency_position(self, x: int, y: int):
        """设置通货位置
        
        Args:
            x: X坐标
            y: Y坐标
        """
        self.coordinates['currency'] = {
            'x': x,
            'y': y,
            'name': '通货'
        }
        print(f"[坐标] 通货位置已设置: ({x}, {y})")
    
    def set_item_position(self, x: int, y: int):
        """设置物品位置
        
        Args:
            x: X坐标
            y: Y坐标
        """
        self.coordinates['item'] = {
            'x': x,
            'y': y,
            'name': '物品'
        }
        print(f"[坐标] 物品位置已设置: ({x}, {y})")
    
    def get_currency_position(self) -> Tuple[int, int]:
        """获取通货位置
        
        Returns:
            (x, y) 坐标
        """
        pos = self.coordinates['currency']
        return (pos['x'], pos['y'])
    
    def get_item_position(self) -> Tuple[int, int]:
        """获取物品位置
        
        Returns:
            (x, y) 坐标
        """
        pos = self.coordinates['item']
        return (pos['x'], pos['y'])
    
    def is_valid(self) -> bool:
        """检查坐标是否有效
        
        Returns:
            是否有效
        """
        currency = self.coordinates['currency']
        item = self.coordinates['item']
        
        return (currency['x'] > 0 and currency['y'] > 0 and
                item['x'] > 0 and item['y'] > 0)
    
    def save(self) -> bool:
        """保存配置到文件
        
        Returns:
            是否成功
        """
        try:
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.coordinates, f, ensure_ascii=False, indent=2)
            
            print(f"[坐标] 配置已保存: {self.config_path}")
            return True
        except Exception as e:
            print(f"[坐标] 保存配置失败: {e}")
            return False
    
    def load(self) -> bool:
        """从文件加载配置
        
        Returns:
            是否成功
        """
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.coordinates = json.load(f)
                print(f"[坐标] 配置已加载: {self.config_path}")
                return True
            else:
                print(f"[坐标] 配置文件不存在: {self.config_path}")
                return False
        except Exception as e:
            print(f"[坐标] 加载配置失败: {e}")
            return False
    
    def get_summary(self) -> Dict:
        """获取坐标摘要
        
        Returns:
            坐标摘要
        """
        currency = self.coordinates['currency']
        item = self.coordinates['item']
        
        return {
            'currency': f"({currency['x']}, {currency['y']})",
            'item': f"({item['x']}, {item['y']})",
            'valid': self.is_valid()
        }


# 测试代码
if __name__ == "__main__":
    print("坐标校准模块测试")
    print("=" * 40)
    
    cm = CoordinateManager()
    
    # 设置测试坐标
    cm.set_currency_position(500, 300)
    cm.set_item_position(600, 400)
    
    # 获取坐标
    print(f"\n通货位置: {cm.get_currency_position()}")
    print(f"物品位置: {cm.get_item_position()}")
    print(f"坐标有效: {cm.is_valid()}")
    
    # 保存配置
    cm.save()
    
    # 重新加载
    cm2 = CoordinateManager()
    print(f"\n重新加载后:")
    print(f"通货位置: {cm2.get_currency_position()}")
    print(f"物品位置: {cm2.get_item_position()}")
