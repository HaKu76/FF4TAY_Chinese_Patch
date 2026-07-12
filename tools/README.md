# OBB 解包工具与文件格式文档

## 解包脚本

| 脚本 | 说明 |
|------|------|
| `extract_obb.py` | **主脚本** — 从 main.obb 解密并提取全部 9,373 个文件到目录结构 |
| `decrypt_obb.py` | LCG XOR 解密核心（早期调试版） |
| `crack_xor.py` | 已知明文攻击反推密钥参数（实验用） |
| `scan_obb.py` | 扫描 OBB 定位 GZip 数据流 |

### 使用

```bash
python extract_obb.py main.obb [output_dir]
例如python extract_obb.py main.obb output
```

默认输出到 `main_obb_extracted/`，完整目录结构（`files/`, `ja.lproj/`, `zh_CN.lproj/`...）。

---

## 加密算法

```
LCG XOR 流密码 (glibc rand 标准常量)

  seed = (98910408 + offset) & 0xFFFFFFFF
  for byte in data:
      seed = (seed × 0x41C64E6D + 12345) & 0xFFFFFFFF
      byte ^= (seed >> 24) & 0xFF
```

ARM64 反汇编 `libjniproxy.so` 中 `Java_..._MainActivity_encode` 函数确认。密钥常量 `98910408` 硬编码于 Java 层 `MainActivity.java`。

### OBB 内部结构

```
Header (16 字节，XOR 解密):
  [0..3]   魔数 LE32 = 0x31435241 "ARC1"
  [4..7]   保留
  [8..11]  TOC 偏移 LE32
  [12..15] TOC 大小 LE32

TOC (独立 XOR 解密 + GZip 解压):
  [0..3]   条目数量 LE32
  [4..]    条目列表，每个 12 字节:
              name_offset LE32    指向下方字符串池
              file_offset LE32    文件在 OBB 中的绝对偏移
              file_length LE32    文件加密数据长度
  条目后   字符串池（'\0' 分隔的文件名）

每个文件 (独立 XOR 解密 + GZip 解压):
  [0..3]   解压后大小 BE32 (注意：Big-Endian)
  [4..]    GZip 压缩数据 (RFC 1952)
```

---

## 目录结构 (9,373 文件)

```
files/              # 共享游戏资源 (5,276 文件)
  *.dat            # 游戏参数/配置
  *.msd            # 消息文本
  *.bbd            # 二进制数据
  MOTION/           # 角色动作动画
  CAST/             # 角色模型
  OBJ/              # 3D 物件
  EVENT/2D/         # CG 事件图片
  MAP/              # 地图数据
  MENU/             # 菜单 UI
  sound/            # 音频 (CRI ADX2)

[lang].lproj/       # 各语言本地化 (12 种，每种 121 文件)
  ru/ ja/ en/ fr/ de/ it/ es/
  zh_CN/ zh_TW/ ko/ pt/ th/
```

---

## 文件格式详解

### .msd — 消息文本

```
文件头: "MSDA" (4 字节)
内部结构: 字符编码表 + 消息条目
引擎通过 .NCER 映射字符索引到 .NCBR 字形
```

### .NCBR — 字符位图

Nintendo 字符位图资源，字形纹理图集。

### .NCER — 字符编码资源

字符编码 → .NCBR 字形坐标映射表。

### .NANR — 动画资源

字体布局参数（字间距、行距、动画）。

### .dat — SSAM 容器

```
文件头: "SSAM" (4 字节)
内容: 预渲染 UI 布局和纹理
```

---

## 文本渲染流程

```
scenario.msd → 字符索引
      ↓
.NCER → 查找字形坐标
      ↓
.NCBR → 取字形像素
      ↓
.NANR → 布局
      ↓
   渲染到屏幕
```

## 参考

- [NaGaa95/ff4tay_nx](https://github.com/NaGaa95/ff4tay_nx) — Switch 移植版，`obb.c` 提供解密实现
- Capstone — ARM64 反汇编确认加密算法
