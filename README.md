# FF4 The After Years Chinese Patch / 最终幻想4：月之归还 简体中文补丁

Steam 版《FINAL FANTASY IV: THE AFTER YEARS》简体中文补丁，基于 Android 官方中文版资源制作。

## 安装

将 `FF4TAY_Chinese_Patch_Install.exe` 放入游戏根目录（与 `FF4A.exe` 同级），双击运行，点击「安装补丁」。

> 要求：Windows 10/11 + [.NET Desktop Runtime 9.0](https://dotnet.microsoft.com/download/dotnet/9.0)
> 安装前请先关闭游戏。

备用方式：运行 `Install.bat`。

## 卸载

Steam 右键游戏 → 属性 → 已安装文件 → 验证游戏文件的完整性。

## 修改内容

| 文件 | 说明 |
|------|------|
| `Resources/en.lproj/*` | 121 个简体中文游戏文件（文本、字体、UI），内置于 EXE |
| `menu.txt` | 暂停菜单中文字符串 |
| `arial.ttf` | 自动检测并复制系统中文字体 |

## 项目结构

```
FF4TAY_Chinese_Patch/
├── README.md               ← 本文档
├── Install.bat             ← 备用命令行安装
├── menu.txt                ← 暂停菜单中文
├── Resources/en.lproj/     ← 中文资源文件（开发参考）
├── src/                    ← C# WPF 安装器源码
│   ├── ff4_patcher.csproj
│   ├── MainWindow.xaml
│   ├── MainWindow.xaml.cs
│   ├── background.png
│   └── patch_data.zip
└── tools/                  ← OBB 解包工具 + 原始中文文件
    ├── extract_obb.py
    ├── decrypt_obb.py
    └── extracted_zh_CN/
```

## 安装器工作流

1. 检测 FF4A.exe 是否运行 → 提示关闭

2. 备份 Resources/en.lproj → Resources/en.lproj.backup

3. 从内嵌 ZIP 解压 121 个中文文件 → Resources/en.lproj/

4. 写入 menu.txt 中文暂停菜单

5. 检测系统字体 → 复制到 arial.ttf

   优先级: SimHei → Microsoft YaHei → DengXian → SimSun

## 字体替换

补丁将全部 108 个英文字体文件替换为 Android 官方的中文字体：

| 原英文 (.NCBR) | → 替换为中文版 | 用途 |
|---------------|---------------|------|
| `font_prologue` (207KB) | `font_prologue` (63KB) | 序章/标题 |
| `font_cain` (232KB) | `font_cain` (13KB) | 凯因对话 |
| `font_edge` (232KB) | `font_edge` (15KB) | 艾吉对话 |
| `font_gilbart` 等 8 种 | 同上 (9-19KB) | 各角色对话 |
| 22 种 `introduce_*` | 同上 (5-18KB) | 角色介绍 |
| `.NCER` ×36 + `.NANR` ×36 | 同上 | 字符映射 & 布局 |

中文字形比英文小，因为只包含游戏实际使用的 CJK 字符集。

### 系统中文字体兼容性

| 字体 | 状态 |
|------|------|
| SimHei（黑体） | 正常 |
| 其他 Windows 系统字体 | （已排除：YaHei为ttc格式不支持，DengXian系统不带，SimSun会闪退） |
| Source Han Sans / 思源黑体 | 闪退 |
| Noto Sans SC | 闪退 |

开源字体闪退原因：SDL2_ttf 2.0 搭载的 FreeType 版本过旧，无法解析新版 OpenType 字体的 CFF 表结构。

## 游戏文字渲染系统

实测验证，游戏内有两套相互独立的文字渲染：

### 系统一：预渲染纹理 — 不受字体文件影响

| 场景 | 关键文件 |
|------|---------|
| 标题大文字、章节选择 | `TITLE_Localize.dat` |
| CG 过场独白字幕 | `event2d.dat` |

### 系统二：Nintendo 动态字体 — 依赖 .NCBR/.NCER/.NANR

| 场景 | 关键文件 |
|------|---------|
| 暂停菜单 | `font_prologue.*` |
| 剧情对话 | `font_cain.*`, `font_edge.*` 等 |
| 战斗/道具/技能 | 各角色 `font_*.NCBR` |

验证方法：删除全部 108 个字体文件，标题正常，菜单和对话变为方块。

## 面向开发者

OBB 解包算法、文件格式详解、文本渲染流程参阅 [tools/README.md](tools/README.md)。

安装器源码在 `src/`，使用 C# + WPF (.NET 9) 构建：

```bash
cd src
dotnet publish -c Release -r win-x64 -p:PublishSingleFile=true -o publish
```

## 致谢

- [NaGaa95/ff4tay_nx](https://github.com/NaGaa95/ff4tay_nx) — Switch 移植版，OBB 解密技术参考
- Square Enix — Android 官方中文版

## 许可

不含 Square Enix 原始游戏程序。中文本地化资源版权归 Square Enix 所有。项目代码以 MIT 协议发布。
