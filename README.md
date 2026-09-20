# PoE2 洗练工具 v2.0 - 剪贴板版

流放之路2 (Path of Exile 2) 自动洗练工具，使用剪贴板读取方式。

## 特点

- ✅ **无需OCR** - 使用 Ctrl+C 复制 + 剪贴板读取
- ✅ **100%准确** - 直接读取游戏文本，无识别错误
- ✅ **资源占用低** - 不需要安装 PyTorch 等大型依赖
- ✅ **简单易用** - 只需配置坐标和词缀条件

## 下载

### 从 GitHub Releases 下载

1. 访问 [Releases](../../releases) 页面
2. 下载最新版本的 `PoE2洗练工具.exe`
3. 直接运行（无需安装Python）

### 从 GitHub Actions 下载

1. 访问 [Actions](../../actions) 页面
2. 点击最新的构建任务
3. 在 "Artifacts" 部分下载 `poe2-crafter`

## 从源码运行

### 安装依赖

```bash
cd poe2_crafter
pip install -r requirements.txt
```

### 运行

```bash
# GUI模式
python main.py

# 命令行模式
python main.py --cli

# 测试模式
python main.py --test
```

## 使用方法

### 1. 配置坐标

1. 点击 **"点击捕获通货坐标"** 按钮
2. 将鼠标移到游戏中通货的位置，**点击一下鼠标**（该点击会被拦截，不会影响游戏）
3. 坐标自动填入输入框
4. 同理点击 **"点击捕获物品坐标"**，再点击游戏中物品的位置
5. 按 **ESC** 可取消捕获
6. 点击"保存坐标"

### 2. 配置词缀条件

**词缀库模式（推荐）：**
1. 选择装备类型（51种：武器/副手/护甲/项链/戒指/腰带）
2. 在列表中选中词缀组（显示 T阶范围 和 T1数值区间）
3. 选择 T阶（T1=最高阶），判定语义为**仅该阶**
4. 选择"包含/排除"，点击添加
5. 词缀数据过时可点击"更新数据"重新爬取 poe2db.tw（约2分钟）

**手动输入模式：**
1. 切换到"手动输入"
2. 输入关键词（如"生命"）+ 运算符 + 数值
3. 点击"添加"

### 3. 开始洗练

1. 点击"开始"按钮或按 F9
2. 程序将自动执行洗练操作
3. 按 F10 暂停，F11 停止
4. 按 F12 紧急停止

## 工作流程

```
1. 鼠标悬停在物品上
2. Ctrl+C 复制物品信息
3. 从剪贴板读取文本
4. 解析词缀
5. 判断是否满足条件
6. 满足 → 停止
7. 不满足 → 点击通货 → 点击物品 → 继续
```

## 热键说明

| 热键 | 功能 |
|------|------|
| F9 | 开始洗练 |
| F10 | 暂停/继续 |
| F11 | 停止 |
| F12 | 紧急停止 |

## 项目结构

```
poe2_crafter/
├── main.py                 # 主入口
├── requirements.txt        # Python依赖
├── build.spec              # PyInstaller配置
├── .github/
│   └── workflows/
│       └── build.yml       # GitHub Actions配置
├── core/
│   ├── clipboard.py        # 剪贴板操作
│   ├── parser.py           # 词缀解析
│   ├── input_sim.py        # 鼠标键盘模拟
│   ├── coordinates.py      # 坐标管理
│   └── crafter.py          # 洗练循环逻辑
├── gui/
│   └── main_window.py      # GUI界面
└── config/
    └── coordinates.json    # 坐标配置
```

## 打包为EXE

### 使用PyInstaller

```bash
pip install pyinstaller
pyinstaller build.spec
```

### 使用GitHub Actions

1. Fork本仓库
2. Push代码到main分支或创建tag
3. 自动构建并生成exe文件
4. 在Actions页面下载构建产物

## GitHub Actions 自动发布

### 创建Release

1. 创建新的tag：
```bash
git tag v1.0.0
git push origin v1.0.0
```

2. GitHub Actions会自动：
   - 构建exe文件
   - 创建Release
   - 上传exe到Release

### 手动触发构建

1. 访问Actions页面
2. 选择"Build EXE"工作流
3. 点击"Run workflow"

## 配置文件

### coordinates.json - 坐标配置

```json
{
  "currency": {"x": 500, "y": 300, "name": "通货"},
  "item": {"x": 600, "y": 400, "name": "物品"}
}
```

## 注意事项

1. **游戏设置**: 建议使用窗口模式
2. **坐标配置**: 确保坐标准确
3. **词缀条件**: 使用游戏中的实际词缀文本
4. **安全机制**: 建议设置最大尝试次数

## 常见问题

### Q: 如何获取物品坐标？

A: 将鼠标移到物品位置，点击"获取鼠标位置"按钮。

### Q: 词缀条件怎么设置？

A: 输入游戏中的词缀关键词，如"生命"、"抗性"、"伤害"等。

### Q: 如何停止程序？

A: 按 F12 紧急停止，或关闭命令行窗口。

### Q: GitHub Actions构建失败怎么办？

A: 检查Python版本和依赖是否正确，查看Actions日志获取详细错误信息。

## 免责声明

本工具仅供学习和研究使用。使用本工具产生的任何后果由用户自行承担。
