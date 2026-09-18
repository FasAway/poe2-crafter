#!/usr/bin/env python3
"""PoE2 洗练工具 v2.0 - 剪贴板版"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='PoE2 洗练工具 v2.0')
    parser.add_argument('--cli', action='store_true', help='命令行模式')
    parser.add_argument('--test', action='store_true', help='测试模式')
    
    args = parser.parse_args()
    
    if args.test:
        run_test()
    elif args.cli:
        run_cli()
    else:
        run_gui()


def run_gui():
    """运行GUI模式"""
    try:
        from gui.main_window import MainWindow
        
        print("启动 PoE2 洗练工具 v2.0 (剪贴板版)...")
        window = MainWindow()
        window.start()
    except ImportError as e:
        print(f"启动失败: {e}")
        print("\n请确保已安装所有依赖:")
        print("pip install pyperclip pyautogui PySimpleGUI")
        sys.exit(1)
    except Exception as e:
        print(f"运行错误: {e}")
        sys.exit(1)


def run_cli():
    """运行命令行模式"""
    from core.crafter import Crafter, CraftingState
    
    print("PoE2 洗练工具 v2.0 - 命令行模式")
    print("=" * 50)
    
    # 创建洗练器
    crafter = Crafter()
    
    # 设置坐标
    print("\n请设置坐标:")
    try:
        x = int(input("通货 X 坐标: "))
        y = int(input("通货 Y 坐标: "))
        crafter.coordinates.set_currency_position(x, y)
        
        x = int(input("物品 X 坐标: "))
        y = int(input("物品 Y 坐标: "))
        crafter.coordinates.set_item_position(x, y)
    except ValueError:
        print("坐标必须是数字")
        return
    
    # 设置词缀条件
    print("\n请设置词缀条件 (输入空行结束):")
    while True:
        keyword = input("关键词: ").strip()
        if not keyword:
            break
        
        operator = input("运算符 (>=, >, <=, <, ==, !=): ").strip()
        if not operator:
            operator = ">="
        
        value = input("数值: ").strip()
        value_int = int(value) if value else None
        
        is_include = input("类型 (1=包含, 2=排除): ").strip()
        is_include = is_include != "2"
        
        crafter.checker.add_requirement(keyword, operator, value_int, is_include)
        print(f"已添加: {keyword} {operator} {value_int or ''} ({'包含' if is_include else '排除'})")
    
    # 设置最大次数
    try:
        max_attempts = int(input("\n最大尝试次数 (默认100): ").strip() or "100")
        crafter.max_attempts = max_attempts
    except ValueError:
        pass
    
    # 开始洗练
    print("\n按 Enter 开始洗练...")
    input()
    
    # 设置回调
    def on_status_change(state, message):
        print(f"[状态] {state}: {message}")
    
    def on_attempt(count, item, result):
        print(f"[尝试 {count}] {item['name']}")
        for affix in item['affixes']:
            print(f"  - {affix.raw_text}")
    
    def on_success(count, item, result):
        print(f"\n{'='*50}")
        print(f"✓ 成功! 第 {count} 次尝试")
        print(f"{'='*50}")
    
    crafter.set_callbacks(
        on_status_change=on_status_change,
        on_attempt=on_attempt,
        on_success=on_success
    )
    
    # 开始
    crafter.start()
    
    # 等待完成或用户中断
    try:
        while crafter.state == CraftingState.RUNNING:
            import time
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n用户中断")
        crafter.stop()
    
    # 显示结果
    status = crafter.get_status()
    print(f"\n洗练结束:")
    print(f"  状态: {status['state']}")
    print(f"  尝试次数: {status['attempt_count']}")
    if status['elapsed']:
        print(f"  用时: {status['elapsed']:.1f} 秒")


def run_test():
    """运行测试"""
    print("PoE2 洗练工具 v2.0 - 测试模式")
    print("=" * 50)
    
    # 测试剪贴板
    print("\n1. 测试剪贴板模块")
    from core.clipboard import ClipboardManager
    
    cm = ClipboardManager()
    print(f"   使用方法: {cm.method}")
    
    text = cm.get_text()
    print(f"   当前剪贴板: {text[:50] if text else '空'}...")
    
    # 测试词缀解析
    print("\n2. 测试词缀解析模块")
    from core.parser import ItemParser, AffixChecker
    
    parser = ItemParser()
    checker = AffixChecker()
    
    test_text = """稀有度: 稀有
噩梦之紛擾
重型腰帶
--------
+25 至最大生命
增加 15% 冰冷抗性
增加 20% 火焰抗性
+30 至力量
--------
需求:
等級: 48"""
    
    item = parser.parse_item(test_text)
    print(f"   物品名称: {item['name']}")
    print(f"   词缀数量: {len(item['affixes'])}")
    for affix in item['affixes']:
        print(f"     - {affix.raw_text}")
    
    # 测试条件检查
    checker.add_requirement("生命", value=20)
    checker.add_requirement("抗性", value=10)
    
    result = checker.check(item['affixes'])
    print(f"   检查结果: {'满足' if result['satisfied'] else '不满足'}")
    
    # 测试输入模拟
    print("\n3. 测试输入模拟模块")
    from core.input_sim import InputSimulator
    
    sim = InputSimulator()
    print(f"   使用方法: {sim.method}")
    
    pos = sim.get_mouse_position()
    print(f"   当前鼠标位置: {pos}")
    
    # 测试坐标管理
    print("\n4. 测试坐标管理模块")
    from core.coordinates import CoordinateManager
    
    cm = CoordinateManager()
    cm.set_currency_position(500, 300)
    cm.set_item_position(600, 400)
    
    print(f"   通货位置: {cm.get_currency_position()}")
    print(f"   物品位置: {cm.get_item_position()}")
    print(f"   坐标有效: {cm.is_valid()}")
    
    print("\n测试完成")


if __name__ == "__main__":
    main()
