---
name: "社媒发布"
description: "Automates publishing videos to WeChat Video Account (视频号) via Chrome DevTools Protocol. Invoke when user wants to publish/upload videos to 视频号 or asks about social media auto-publishing."
---

# 社媒发布 - 视频号自动发布工具

## 功能说明

通过 Chrome DevTools Protocol (CDP) 远程控制浏览器，自动向微信视频号助手上传并发布视频。支持单视频发布和批量发布。

## 触发条件

当用户提出以下需求时调用此技能：
- 想要发布/上传视频到视频号
- 提到"社媒发布"、"视频号发布"、"自动发视频"
- 需要批量发布多个视频到视频号

## 使用前准备

1. 确保已安装 Python 依赖：`websocket-client` 和 `opencv-python`
2. 确保 Edge/Chrome 浏览器已安装
3. 首次使用需要手动扫码登录视频号助手

## 使用方法

### 批量发布（发布"待发布视频"文件夹中的所有视频）

```bash
python "D:\TRAE SOLO CN\视频号流程\.trae\skills\社媒发布\publish.py"
```

### 发布单个视频

```bash
python "D:\TRAE SOLO CN\视频号流程\.trae\skills\社媒发布\publish.py" "视频文件路径.mp4"
```

### 批量发布指定文件夹

```bash
python "D:\TRAE SOLO CN\视频号流程\.trae\skills\社媒发布\publish.py" "文件夹路径"
```

## 工作流程

1. 自动启动浏览器调试模式（如未启动）
2. 连接到视频号助手页面
3. 等待用户扫码登录（首次需要）
4. 扫描待发布视频文件夹
5. 逐个上传视频并填写标题/描述
6. 提交发布并保存发布记录

## 目录结构

```
视频号流程/
├── 待发布视频/          ← 将视频文件放这里
├── 已发布记录/          ← 发布结果记录（JSON）
└── .trae/skills/社媒发布/
    ├── SKILL.md         ← 技能描述
    ├── publish.py       ← 主发布脚本
    ├── chrome_cdp.py    ← 浏览器控制模块
    ├── video_analyzer.py ← 视频分析模块
    ├── requirements.txt ← Python依赖
    └── config/
        └── settings.json ← 配置文件
```

## 配置说明

配置文件位于 `config/settings.json`，主要配置项：
- `chrome_path`: 浏览器可执行文件路径
- `chrome_debug_port`: 调试端口（默认 9222）
- `video_folder`: 待发布视频文件夹路径
- `record_folder`: 发布记录保存路径
- `max_title_length`: 标题最大长度（默认 16）

## 注意事项

- 首次运行需要手动扫码登录视频号助手
- 发布过程中请勿手动操作浏览器
- 视频格式支持：mp4、mov、avi、mkv、flv、wmv、m4v
- 标题最长 16 字，描述最长 1000 字
---
name: "社媒发布"
description: "Automates publishing videos to WeChat Video Account (视频号) via Chrome DevTools Protocol. Invoke when user wants to publish/upload videos to 视频号 or asks about social media auto-publishing."
---

# 社媒发布 - 视频号自动发布工具

## 功能说明

通过 Chrome DevTools Protocol (CDP) 远程控制浏览器，自动向微信视频号助手上传并发布视频。支持单视频发布和批量发布。

## 触发条件

当用户提出以下需求时调用此技能：
- 想要发布/上传视频到视频号
- 提到"社媒发布"、"视频号发布"、"自动发视频"
- 需要批量发布多个视频到视频号

## 使用前准备

1. 确保已安装 Python 依赖：`websocket-client` 和 `opencv-python`
2. 确保 Edge/Chrome 浏览器已安装
3. 首次使用需要手动扫码登录视频号助手

## 使用方法

### 批量发布（发布"待发布视频"文件夹中的所有视频）

```bash
python publish.py
```

### 发布单个视频

```bash
python publish.py "视频文件路径.mp4"
```

### 批量发布指定文件夹

```bash
python publish.py "文件夹路径"
```

## 工作流程

1. 自动启动浏览器调试模式（如未启动）
2. 连接到视频号助手页面
3. 等待用户扫码登录（首次需要）
4. 扫描待发布视频文件夹
5. 逐个上传视频并填写标题/描述
6. 提交发布并保存发布记录

## 目录结构

```
video-account-publisher/
├── SKILL.md         ← 技能描述
├── publish.py       ← 主发布脚本
├── chrome_cdp.py    ← 浏览器控制模块
├── video_analyzer.py ← 视频分析模块
├── requirements.txt ← Python依赖
└── config/
    └── settings.json ← 配置文件
```

## 配置说明

配置文件位于 `config/settings.json`，主要配置项：
- `chrome_path`: 浏览器可执行文件路径
- `chrome_debug_port`: 调试端口（默认 9222）
- `video_folder`: 待发布视频文件夹路径
- `record_folder`: 发布记录保存路径
- `max_title_length`: 标题最大长度（默认 16）

## 注意事项

- 首次运行需要手动扫码登录视频号助手
- 发布过程中请勿手动操作浏览器
- 视频格式支持：mp4、mov、avi、mkv、flv、wmv、m4v
- 标题最长 16 字，描述最长 1000 字
