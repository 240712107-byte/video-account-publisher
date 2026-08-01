---
name: "社媒发布"
description: "通过 Chrome DevTools Protocol (CDP) 远程控制 Edge 浏览器，自动向微信视频号助手上传并发布视频。当用户想要发布/上传视频到视频号、提到社媒发布/视频号发布/自动发视频、需要批量发布视频到视频号时调用此技能。"
---

# 社媒发布 - 视频号自动发布技能

## 1. 技能概述

本技能通过 Chrome DevTools Protocol (CDP) 远程控制 Edge 浏览器，自动完成微信视频号助手的视频上传与发布全流程。支持单视频发布和批量发布，自动处理标题清洗、描述生成、上传等待、封面检测、提交发布等环节。

**重要规则（必须遵守）：**

1. **发布前必须提醒用户确认已注册并开通视频号**——未开通视频号的账号无法使用发布功能，脚本会在发布前检测账号开通状态，若检测到未开通将中止流程并提示用户先开通。
2. **发布后必须验证是否真正成功**——点击"发表"按钮后不能立即报告成功，必须通过检测浏览器页面状态（URL 跳转、成功/失败提示、按钮状态）来确认视频是否真正发布成功。
3. **发布失败自动重试**——若验证发现未发布成功，自动刷新页面重置状态，重新上传视频并发布，最多重试 3 次。

### 核心能力

- **发布前检查**：提醒用户确认已注册开通视频号，自动检测页面是否有"开通视频号"引导
- 自动启动 Edge 浏览器调试模式（端口 9222）
- 自动检测登录状态，支持首次扫码登录
- 扫描待发布文件夹中的所有视频
- 自动清洗标题（移除非法特殊字符）、补齐标题长度
- 自动生成含话题标签的视频描述
- 通过 CDP 注入文件到 `<input type="file">` 上传视频
- 智能轮询等待视频转码、封面生成、发表按钮可用
- 在 wujie 微前端 Shadow DOM 中模拟真实鼠标点击和键盘输入
- **发布后验证**：检测页面 URL 跳转、成功/失败提示，确认真正发布成功
- **失败自动重试**：未成功则刷新页面重新上传发布，最多重试 3 次
- 自动保存发布记录（JSON 格式）
- 支持单视频发布和批量发布

---

## 2. 触发条件

当用户提出以下需求时调用此技能：

- "发布视频到视频号" / "上传视频到视频号"
- "社媒发布" / "视频号发布" / "自动发视频"
- "批量发布视频" / "把文件夹里的视频都发了"
- 提到待发布视频文件夹、视频号助手等关键词

---

## 3. 前置条件

### 3.1 环境要求

- **操作系统**：Windows
- **Python**：3.8+
- **浏览器**：Microsoft Edge（或 Chrome）
- **Python 依赖**：
  ```
  websocket-client
  opencv-python
  ```
  安装命令：
  ```bash
  pip install websocket-client opencv-python --break-system-packages
  ```

### 3.2 首次使用准备

1. **必须先注册并开通微信视频号**（这是使用本技能的前提条件）：
   - 开通路径：微信 → 发现 → 视频号 → 右上角个人中心 → 创建账号
   - 需完善头像、名称等账号信息
   - 确保账号状态正常，无封禁或限制
   - 脚本运行前会打印提醒并自动检测开通状态，未开通将中止发布
2. 确保 Edge 浏览器已安装
3. 首次运行需要手动扫码登录视频号助手
4. 视频号助手地址：`https://channels.weixin.qq.com/platform`
5. 将待发布视频放入"待发布视频"文件夹

### 3.3 视频格式支持

`.mp4`、`.mov`、`.avi`、`.mkv`、`.flv`、`.wmv`、`.m4v`

---

## 4. 目录结构

技能部署后，工作目录结构如下：

```
视频号流程/
├── 待发布视频/                    ← 将待发布的视频文件放这里
│   └── .frames/                  ← （自动生成）视频关键帧缓存
│   └── .screenshots/             ← （自动生成）页面截图缓存
├── 已发布记录/                    ← 发布结果 JSON 记录
└── .trae/skills/社媒发布/
    ├── SKILL.md                   ← 本技能说明文件
    ├── publish.py                 ← 主发布脚本
    ├── chrome_cdp.py              ← CDP 浏览器控制模块
    ├── video_analyzer.py          ← 视频分析模块
    ├── requirements.txt           ← Python 依赖
    └── config/
        └── settings.json          ← 配置文件
```

---

## 5. 配置文件

配置文件路径：`config/settings.json`

```json
{
  "chrome_path": "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "chrome_debug_port": 9222,
  "chrome_user_data_dir": "<技能目录>\\chrome-debug-profile",
  "platform": "channels",
  "platform_url": "https://channels.weixin.qq.com/platform",
  "publish_url": "https://channels.weixin.qq.com/platform/post/create",
  "video_folder": "<工作目录>\\待发布视频",
  "record_folder": "<工作目录>\\已发布记录",
  "frames_folder": "<工作目录>\\待发布视频\\.frames",
  "default_location": "苏州市",
  "max_title_length": 16,
  "max_description_length": 1000,
  "screenshot_dir": "<工作目录>\\待发布视频\\.screenshots"
}
```

### 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `chrome_path` | Edge/Chrome 可执行文件路径 | Edge 默认安装路径 |
| `chrome_debug_port` | CDP 调试端口 | 9222 |
| `chrome_user_data_dir` | 浏览器用户数据目录（保留登录态） | chrome-debug-profile |
| `platform_url` | 视频号助手主页地址 | channels.weixin.qq.com/platform |
| `publish_url` | 视频发布页地址 | .../platform/post/create |
| `video_folder` | 待发布视频文件夹 | 待发布视频 |
| `record_folder` | 发布记录保存文件夹 | 已发布记录 |
| `max_title_length` | 标题最大长度 | 16（视频号短标题限制） |
| `max_description_length` | 描述最大长度 | 1000 |

---

## 6. 使用方法

### 6.1 批量发布（默认）

发布"待发布视频"文件夹中的所有视频：

```bash
python publish.py
```

### 6.2 发布单个视频

```bash
python publish.py "C:\path\to\video.mp4"
```

自动从文件名生成标题和描述。

### 6.3 批量发布指定文件夹

```bash
python publish.py "C:\path\to\video_folder"
```

---

## 7. 发布流程详解

### 7.1 整体流程

```
┌──────────────────────────────────────────────────────────┐
│  Step 0  启动 Edge 调试模式（端口 9222）                   │
│          ensure_chrome_running()                          │
├──────────────────────────────────────────────────────────┤
│  Step 1  通过 WebSocket 连接视频号助手标签页               │
│          cdp.connect(tab_filter="channels.weixin.qq.com") │
├──────────────────────────────────────────────────────────┤
│  Step 2  检查登录状态，未登录则等待扫码（最多 120 秒）      │
│          wait_for_login()                                 │
├──────────────────────────────────────────────────────────┤
│  Step 3  ★发布前检查：提醒并检测视频号是否已开通           │
│          check_account_opened()                           │
│          （未开通则中止流程，提示用户先开通）               │
├──────────────────────────────────────────────────────────┤
│  Step 4  扫描"待发布视频"文件夹，列出所有视频              │
│          scan_video_folder()                              │
├──────────────────────────────────────────────────────────┤
│  Step 5  逐个执行 publish_single_video()（含重试）：       │
│          ① 进入发布页面  navigate_to_publish()            │
│          ② 上传视频      upload_video()                   │
│          ③ 填写并发布    fill_and_publish()               │
│          ④ ★验证发布结果 verify_publish_success()         │
│          ⑤ 成功→保存记录 / 失败→重置页面重试（最多3次）    │
├──────────────────────────────────────────────────────────┤
│  Step 6  汇总成功/失败数量                                 │
└──────────────────────────────────────────────────────────┘
```

### 7.2 发布前检查 `check_account_opened()`

这是**必须执行**的第一步检查，在登录成功后、开始发布前运行：

1. 打印提醒信息，告知用户需确认已注册开通视频号
2. 通过 JS 检测页面是否包含"开通视频号""注册视频号""立即开通"等引导关键词
3. 若检测到未开通，中止发布流程并提示开通路径
4. 若已正常进入平台页面，则继续发布流程

### 7.3 单视频发布子流程（含验证与重试）

`publish_single_video()` 内部是一个重试循环（最多 3 次）：

```
开始
  │
  ├─ ① 进入发布页面 navigate_to_publish()
  │     └─ 失败 → 重置页面 → 重试（未超3次）/ 记录失败
  │
  ├─ ② 上传视频 upload_video()
  │     └─ 失败 → 重置页面 → 重试（未超3次）/ 记录失败
  │
  ├─ ③ 填写标题描述并点击发表 fill_and_publish()
  │     └─ 失败 → 重置页面 → 重试（未超3次）/ 记录失败
  │
  ├─ ④ ★验证发布结果 verify_publish_success()（轮询30秒）
  │     ├─ 成功 → 保存记录 → 返回 True
  │     └─ 失败 → reset_publish_page() 重置页面 → 重试
  │
  └─ 达到3次仍失败 → 记录 failed_after_retries → 返回 False
```

#### ① 进入发布页面 `navigate_to_publish()`

1. 检查当前 URL 是否已在 `post/create` 页面
2. 若已在页面，检测 `wujie-app` Shadow DOM 中是否存在 `input[type="file"]`
3. 若不在，导航到 `publish_url`，等待 5-8 秒
4. 若导航后仍不在发布页，尝试点击"发表视频"按钮
5. 页面就绪判定：`wujie-app.shadowRoot.querySelector('input[type="file"]')` 存在

#### ② 上传视频 `upload_video()`

1. 通过 CDP `DOM.setFileInputFiles` 将视频文件路径注入到 Shadow DOM 中的 `<input type="file">`
2. 轮询等待（每 2 秒一次，最多 120 秒），依次检测：
   - **上传中**：页面存在可见的"上传中"/"处理中"提示弹窗
   - **封面生成中**：关键帧图片或封面图（`finder.video.qq.com` CDN 地址）未加载完成
   - **处理中**："发表"按钮处于 disabled 状态
   - **就绪**：发表按钮可用 **且** 视频元素 `readyState >= 2`
3. 就绪后额外等待 3 秒确保稳定

#### ③ 填写标题和描述 `fill_and_publish()`

**顺序要求：先填标题，再填描述**（避免焦点冲突）

1. **填写标题** `fill_title()`：
   - 在 Shadow DOM 中查找 placeholder 含"短标题"的 `<input type="text">`
   - 点击获取焦点，清空原值
   - 使用 CDP `Input.insertText` 模拟真实键盘输入
   - 触发 `change` 和 `blur` 事件
   - 验证输入值

2. **填写描述** `fill_description()`：
   - 在 Shadow DOM 中查找 `.input-editor`（contenteditable div）
   - 点击获取焦点，清空 innerHTML/innerText
   - 使用 CDP `Input.insertText` 模拟真实键盘输入
   - 触发 `input`、`change`、`blur` 事件
   - 验证字符数

3. **点击发表**：
   - 在 Shadow DOM 中查找文本为"发表"的 `<button>`
   - 派发完整鼠标事件序列：`pointerdown` → `mousedown` → `mouseup` → `pointerup` → `click`
   - **注意：点击后不再立即判定成功，交由 ④ 验证**

#### ④ ★验证发布结果 `verify_publish_success()`

这是**关键步骤**，点击发表后必须通过检测浏览器页面状态来确认是否真正发布成功。轮询检测 30 秒，每 2 秒一次：

**成功判定（任一满足）：**
- URL 跳转到 `/platform/post/list`（作品列表页）——最可靠的标志
- 页面出现"发表成功""发布成功""已发表""发布完成""上传成功"等提示
- 弹出包含"成功"字样的 toast/dialog

**失败判定（任一满足）：**
- 页面出现"发表失败""发布失败""上传失败""网络异常""内容审核不通过""系统繁忙"等提示
- 弹出包含"失败""错误""异常"字样的弹窗
- 超时后仍停留在 `post/create` 页面且发表按钮恢复可用（说明提交未生效）

**验证逻辑：**
```javascript
// 检测 Shadow DOM 中的页面文本和按钮状态
// 成功关键词 → 返回 success
// 失败关键词 → 返回 failed
// 仍在表单页且按钮可用 → 返回 still_on_form（继续等待）
// 其他 → 返回 waiting（继续轮询）
```

#### ⑤ 失败重试 `reset_publish_page()`

验证失败后，**必须先重置页面状态**再重试：

1. 禁用 `beforeunload` 弹窗
2. 通过 `Page.navigate` 重新导航到发布页 URL
3. 等待 wujie-app 和 file input 重新加载就绪（最多 16 秒）
4. 页面就绪后重新执行上传和发布流程
5. 最多重试 3 次，全部失败则记录 `failed_after_retries`

#### 保存记录 `save_publish_record()`

- 在"已发布记录"文件夹中生成与视频同名的 `.json` 文件
- 记录内容：视频文件名、路径、标题、描述、话题标签、状态（success/failed_navigate/failed_upload/failed_publish/failed_after_retries）、发布时间、失败原因

---

## 8. 标题与描述处理规则

### 8.1 标题清洗 `sanitize_title(title)`

视频号标题有严格的字符限制，处理规则如下：

1. **逗号替换为空格**：`,` 和 `，` → 空格
2. **分隔符替换为空格**：`-`、`_`、`.`、`·`、`|`、`/`、`\` → 空格
3. **白名单过滤**，仅保留：
   - 中文（`\u4e00-\u9fff`、`\u3400-\u4dbf`）
   - 字母（a-z, A-Z）
   - 数字（0-9）
   - 空格
   - 书名号 `《》`
   - 引号 `""''`
   - 冒号 `:`
   - 加号 `+`
   - 问号 `?`
   - 百分号 `%`
   - 摄氏度 `℃`
4. **合并多余空格**，去除首尾空格

### 8.2 标题长度 `ensure_title_length(title)`

视频号短标题要求 **6-16 个字符**：

- **为空**：使用默认值"精彩视频分享"
- **不足 6 字**：依次追加后缀补足：
  - "精彩分享" → "视频分享" → "日常记录" → "精彩瞬间" → "一起来看" → "不容错过" → "超好看" → "必看"
  - 仍不够则循环追加"精彩视频"
- **超过 16 字**：截断到 16 字

### 8.3 描述生成 `generate_description(filename, title)`

- 以标题为描述主体
- 自动追加话题标签（增加曝光）：`#视频号 #精彩视频 #分享`
- 格式：`{标题}\n\n{话题标签}`
- 不超过 1000 字

---

## 9. 关键技术要点

### 9.1 为什么必须用 CDP Input.insertText

视频号发布页使用 Vue/React 框架，存在以下问题：

- **直接设置 `input.value`**：框架内部状态不会更新，表单校验不通过
- **直接设置 `innerText`/`innerHTML`**：contenteditable 编辑器的框架状态不同步
- **必须使用 `Input.insertText`**：模拟真实键盘输入事件，框架才能正确检测值变化并更新校验状态

### 9.2 Shadow DOM 穿透

视频号平台使用 **wujie 微前端**框架，所有表单元素位于 `<wujie-app>` 的 Shadow Root 内部：

```javascript
// 常规 querySelector 无法穿透 Shadow DOM
document.querySelector('input[type="file"]')  // null

// 必须先进入 shadowRoot
const wujie = document.querySelector('wujie-app');
const shadow = wujie.shadowRoot;
shadow.querySelector('input[type="file"]')  // 正确
```

所有元素查找、点击、输入操作都必须在 `wujieApp.shadowRoot` 内执行。

### 9.3 文件上传机制

不通过模拟文件选择对话框，而是直接使用 CDP 命令：

1. 在页面中找到 `<input type="file">` 元素
2. 通过 `Runtime.evaluate`（`returnByValue: false`）获取元素的 `objectId`
3. 调用 `DOM.setFileInputFiles`，传入 `objectId` 和文件绝对路径数组
4. 浏览器自动触发文件上传，无需操作系统级文件对话框交互

### 9.4 模拟点击事件序列

仅派发 `click` 事件在某些 UI 框架中不生效，需要派发完整的指针/鼠标事件序列：

```javascript
const events = [
  'pointerdown', 'mousedown',
  'mouseup', 'pointerup', 'click'
];
```

每个事件都设置 `bubbles: true` 和正确的 `clientX/clientY` 坐标。

---

## 10. 脚本代码

### 10.1 requirements.txt

```
websocket-client
opencv-python
```

### 10.2 config/settings.json

```json
{
  "chrome_path": "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "chrome_debug_port": 9222,
  "chrome_user_data_dir": "",
  "platform": "channels",
  "platform_url": "https://channels.weixin.qq.com/platform",
  "publish_url": "https://channels.weixin.qq.com/platform/post/create",
  "video_folder": "",
  "record_folder": "",
  "frames_folder": "",
  "default_location": "",
  "max_title_length": 16,
  "max_description_length": 1000,
  "screenshot_dir": ""
}
```

> 部署时将空字符串路径替换为实际绝对路径。`chrome_user_data_dir` 建议设为技能目录下的 `chrome-debug-profile`，以保留登录态。

### 10.3 chrome_cdp.py

```python
"""
视频号自动发布工具 - CDP浏览器控制模块
通过Chrome DevTools Protocol远程控制浏览器
"""

import json
import websocket
import time
import base64
import os
import urllib.request


class ChromeCDP:
    """Chrome DevTools Protocol 封装"""

    def __init__(self, port=9222):
        self.port = port
        self.ws = None
        self.ws_id = 0

    def connect(self, tab_filter=None):
        """连接到Chrome浏览器，可按URL过滤标签页"""
        tabs = json.loads(urllib.request.urlopen(
            f"http://localhost:{self.port}/json/list").read())
        page_tab = None
        for t in tabs:
            if t['type'] != 'page':
                continue
            if tab_filter and tab_filter not in t.get('url', ''):
                continue
            page_tab = t
            break
        if not page_tab:
            for t in tabs:
                if t['type'] == 'page':
                    page_tab = t
                    break
        if not page_tab:
            raise ConnectionError("没有找到可用的浏览器标签页")
        self.ws = websocket.create_connection(
            page_tab['webSocketDebuggerUrl'], timeout=30)
        return page_tab

    def send_cmd(self, method, params=None, timeout=15):
        """发送CDP命令"""
        self.ws_id += 1
        my_id = self.ws_id
        msg = {"id": my_id, "method": method}
        if params:
            msg["params"] = params
        self.ws.send(json.dumps(msg))
        start = time.time()
        while time.time() - start < timeout:
            try:
                self.ws.settimeout(3)
                raw = self.ws.recv()
                resp = json.loads(raw)
                if resp.get("id") == my_id:
                    return resp
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                break
        return None

    def enable_domains(self):
        """启用必要的CDP域"""
        self.send_cmd("Runtime.enable")
        self.send_cmd("DOM.enable")
        self.send_cmd("Page.enable")
        self.send_cmd("Input.enable")
        time.sleep(1)

    def navigate(self, url, wait=8):
        """导航到指定URL，自动处理beforeunload弹窗"""
        self.eval_js("window.onbeforeunload = null; window.onunload = null;")
        self.send_cmd("Page.enable")
        self.send_cmd("Page.setInterceptFileChooserDialog",
                      {"enabled": False})
        result = self.send_cmd("Page.navigate", {"url": url})
        time.sleep(wait)
        self.send_cmd("Page.handleJavaScriptDialog", {"accept": True})
        return result

    def eval_js(self, expression, return_by_value=True, timeout=15):
        """执行JavaScript"""
        params = {"expression": expression,
                  "returnByValue": return_by_value}
        result = self.send_cmd("Runtime.evaluate", params, timeout=timeout)
        if result and result.get("result"):
            return result["result"].get("result", {})
        return {}

    def screenshot(self, save_path=None):
        """截取当前页面截图"""
        result = self.send_cmd("Page.captureScreenshot", {"format": "png"})
        if result and result.get("result", {}).get("data"):
            img_data = base64.b64decode(result["result"]["data"])
            if save_path:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(img_data)
            return img_data
        return None

    def get_url(self):
        """获取当前页面URL"""
        result = self.eval_js("window.location.href")
        return result.get("value", "")

    def shadow_click(self, text_match, tag=None):
        """在wujie微前端的shadow DOM中点击元素"""
        js = f"""
        (() => {{
            const wujieApp = document.querySelector('wujie-app');
            if (!wujieApp || !wujieApp.shadowRoot) return JSON.stringify({{error: 'no shadow'}});
            const shadow = wujieApp.shadowRoot;
            const allEls = shadow.querySelectorAll('{tag or '*'}');
            for (const el of allEls) {{
                const text = el.textContent ? el.textContent.trim() : '';
                if (text === {json.dumps(text_match)}) {{
                    const rect = el.getBoundingClientRect();
                    const x = rect.x + rect.width / 2;
                    const y = rect.y + rect.height / 2;
                    const events = [
                        new MouseEvent('pointerdown', {{bubbles: true, clientX: x, clientY: y, button: 0}}),
                        new MouseEvent('mousedown', {{bubbles: true, clientX: x, clientY: y, button: 0}}),
                        new MouseEvent('mouseup', {{bubbles: true, clientX: x, clientY: y, button: 0}}),
                        new MouseEvent('pointerup', {{bubbles: true, clientX: x, clientY: y, button: 0}}),
                        new MouseEvent('click', {{bubbles: true, clientX: x, clientY: y, button: 0}}),
                    ];
                    for (const evt of events) {{ el.dispatchEvent(evt); }}
                    return JSON.stringify({{ok: true, x: x, y: y, tag: el.tagName}});
                }}
            }}
            return JSON.stringify({{error: 'not found'}});
        }})()
        """
        result = self.eval_js(js)
        try:
            return json.loads(result.get("value", "{}"))
        except:
            return {"error": "parse error"}

    def upload_file_via_cdp(self, file_path):
        """通过CDP的DOM.setFileInputFiles上传文件"""
        js_get_obj = """
        (() => {
            const wujieApp = document.querySelector('wujie-app');
            const shadow = wujieApp.shadowRoot;
            const fileInput = shadow.querySelector('input[type="file"]');
            window.__fileInput = fileInput;
            return fileInput ? 'found' : 'not found';
        })()
        """
        status = self.eval_js(js_get_obj)
        if status.get("value") != "found":
            return False

        result = self.send_cmd("Runtime.evaluate", {
            "expression": "window.__fileInput",
            "returnByValue": False
        })
        obj_id = result.get("result", {}).get(
            "result", {}).get("objectId")
        if not obj_id:
            return False

        result = self.send_cmd("DOM.setFileInputFiles", {
            "objectId": obj_id,
            "files": [os.path.abspath(file_path).replace("/", "\\")]
        })
        return result is not None

    def fill_description(self, text):
        """填写视频描述（contenteditable div）- 使用CDP模拟真实输入"""
        js_focus = """
        (() => {
            const wujieApp = document.querySelector('wujie-app');
            const shadow = wujieApp.shadowRoot;
            const editor = shadow.querySelector('.input-editor');
            if (!editor) return 'Editor not found';
            editor.scrollIntoView({block: 'center'});
            editor.focus();
            editor.innerHTML = '';
            editor.innerText = '';
            editor.click();
            return 'focused';
        })()
        """
        result = self.eval_js(js_focus)
        if result.get("value") != "focused":
            return result.get("value", "focus failed")

        time.sleep(0.5)
        self.send_cmd("Input.insertText", {"text": text})
        time.sleep(0.5)

        js_verify = """
        (() => {
            const wujieApp = document.querySelector('wujie-app');
            const shadow = wujieApp.shadowRoot;
            const editor = shadow.querySelector('.input-editor');
            editor.dispatchEvent(new Event('input', { bubbles: true }));
            editor.dispatchEvent(new Event('change', { bubbles: true }));
            editor.dispatchEvent(new Event('blur', { bubbles: true }));
            return 'OK: ' + editor.innerText.length + ' chars';
        })()
        """
        result = self.eval_js(js_verify)
        return result.get("value", "")

    def fill_title(self, text):
        """填写短标题 - 使用CDP模拟真实键盘输入"""
        js_focus = """
        (() => {
            const wujieApp = document.querySelector('wujie-app');
            const shadow = wujieApp.shadowRoot;
            const inputs = shadow.querySelectorAll('input[type="text"]');
            for (const inp of inputs) {
                if (inp.placeholder && (inp.placeholder.includes('短标题') || inp.placeholder.includes('填写短标题'))) {
                    inp.scrollIntoView({block: 'center'});
                    inp.click();
                    inp.focus();
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeInputValueSetter.call(inp, '');
                    inp.dispatchEvent(new Event('input', { bubbles: true }));
                    return 'focused:' + inp.placeholder;
                }
            }
            return 'NOT FOUND';
        })()
        """
        result = self.eval_js(js_focus)
        focus_result = result.get("value", "")
        if not focus_result.startswith("focused"):
            return focus_result

        time.sleep(0.5)
        self.send_cmd("Input.insertText", {"text": text})
        time.sleep(0.5)

        js_verify = """
        (() => {
            const wujieApp = document.querySelector('wujie-app');
            const shadow = wujieApp.shadowRoot;
            const inputs = shadow.querySelectorAll('input[type="text"]');
            for (const inp of inputs) {
                if (inp.placeholder && (inp.placeholder.includes('短标题') || inp.placeholder.includes('填写短标题'))) {
                    inp.dispatchEvent(new Event('change', { bubbles: true }));
                    inp.dispatchEvent(new Event('blur', { bubbles: true }));
                    return 'OK: ' + inp.value + ' (len=' + inp.value.length + ')';
                }
            }
            return 'NOT FOUND after fill';
        })()
        """
        result = self.eval_js(js_verify)
        return result.get("value", "")

    def close(self):
        """关闭连接"""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None
```

### 10.4 video_analyzer.py

```python
"""
视频号自动发布工具 - 视频内容分析模块
功能：扫描视频文件夹、获取视频信息、提取关键帧、保存发布记录
"""

import cv2
import os
import json


def extract_frames(video_path, output_dir, num_frames=5):
    """从视频中均匀提取关键帧"""
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    timestamps = [int(duration * (i + 1) / (num_frames + 1))
                  for i in range(num_frames)]
    frame_paths = []

    for i, ts in enumerate(timestamps):
        frame_num = int(ts * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if ret:
            h, w = frame.shape[:2]
            if w > 1280:
                scale = 1280 / w
                frame = cv2.resize(frame, (1280, int(h * scale)))
            out_path = os.path.join(output_dir, f"frame_{i:02d}.png")
            cv2.imwrite(out_path, frame)
            frame_paths.append(out_path)

    cap.release()
    return frame_paths, duration


def get_video_info(video_path):
    """获取视频基本信息：分辨率、帧率、时长"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    info = {
        "fps": fps,
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "total_frames": total_frames,
        "duration": total_frames / fps if fps > 0 else 0,
    }
    cap.release()
    return info


def scan_video_folder(folder_path):
    """扫描文件夹中的视频文件，返回列表"""
    video_extensions = {'.mp4', '.mov', '.avi',
                        '.mkv', '.flv', '.wmv', '.m4v'}
    videos = []
    for f in sorted(os.listdir(folder_path)):
        ext = os.path.splitext(f)[1].lower()
        if ext in video_extensions:
            videos.append({
                "filename": f,
                "full_path": os.path.join(folder_path, f),
                "extension": ext
            })
    return videos


def save_publish_record(video_path, title, description, hashtags, status,
                        record_dir, extra=None):
    """保存发布记录为JSON文件"""
    os.makedirs(record_dir, exist_ok=True)
    record = {
        "video_filename": os.path.basename(video_path),
        "video_path": video_path,
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "status": status,
        "publish_time": None,
        "extra": extra or {}
    }
    if status == "success":
        from datetime import datetime
        record["publish_time"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S")

    record_filename = os.path.splitext(
        os.path.basename(video_path))[0] + ".json"
    record_path = os.path.join(record_dir, record_filename)
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return record_path
```

### 10.5 publish.py

```python
"""
视频号自动发布工具 - 主发布脚本
用法: python publish.py [视频文件路径或文件夹路径]

流程:
0. 【发布前检查】提醒用户确认已注册并开通视频号
1. 启动Chrome调试模式（如未启动）
2. 连接到视频号助手
3. 进入发布页面
4. 上传视频
5. 填写描述和标题
6. 提交发布
7. 【发布后验证】检测页面状态确认是否真正发布成功
8. 【失败重试】未成功则刷新页面重新上传发布，最多重试3次
"""

import os
import sys
import json
import re
import time
import subprocess

from video_analyzer import (
    scan_video_folder, extract_frames, get_video_info,
    save_publish_record
)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "settings.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


def sanitize_title(title):
    """清理标题，移除视频号不支持的字符"""
    allowed_pattern = r'[\u4e00-\u9fff\u3400-\u4dbfa-zA-Z0-9\s《》""'':+?%℃]'
    title = title.replace(',', ' ')
    title = title.replace('，', ' ')
    for sep in ['-', '_', '.', '·', '|', '/', '\\']:
        title = title.replace(sep, ' ')
    title = ''.join(re.findall(allowed_pattern, title))
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def ensure_title_length(title, min_len=6, max_len=16):
    """确保标题长度符合视频号要求（6-16字）"""
    title = title.strip()
    if not title:
        title = "精彩视频分享"
    if len(title) < min_len:
        suffixes = [
            "精彩分享", "视频分享", "日常记录", "精彩瞬间",
            "一起来看", "不容错过", "超好看", "必看"
        ]
        for suffix in suffixes:
            candidate = title + suffix
            if len(candidate) >= min_len:
                title = candidate
                break
        while len(title) < min_len:
            title = title + "精彩视频"
    if len(title) > max_len:
        title = title[:max_len]
    return title


def generate_description(filename, title):
    """生成视频描述，自动追加话题标签"""
    base_name = os.path.splitext(filename)[0]
    base_name = sanitize_title(base_name)
    desc = title if title else base_name
    hashtags = ["#视频号", "#精彩视频", "#分享"]
    description = f"{desc}\n\n{' '.join(hashtags)}"
    if len(description) > 1000:
        description = description[:1000]
    return description


def create_chrome_cdp():
    """创建浏览器控制对象"""
    try:
        from chrome_cdp import ChromeCDP
        return ChromeCDP(port=CONFIG["chrome_debug_port"])
    except ModuleNotFoundError as e:
        if e.name == "websocket":
            print("缺少依赖：websocket-client")
            print("请先运行：pip install websocket-client")
        else:
            print(f"缺少依赖：{e.name}")
        raise


def ensure_chrome_running():
    """确保Chrome以调试模式运行"""
    import urllib.request
    try:
        urllib.request.urlopen(
            f"http://localhost:{CONFIG['chrome_debug_port']}/json/version",
            timeout=2)
        return True
    except:
        pass

    print("正在启动Chrome调试模式...")
    subprocess.Popen([
        CONFIG["chrome_path"],
        f"--remote-debugging-port={CONFIG['chrome_debug_port']}",
        f"--remote-allow-origins=*",
        f"--user-data-dir={CONFIG['chrome_user_data_dir']}"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for i in range(10):
        time.sleep(2)
        try:
            urllib.request.urlopen(
                f"http://localhost:{CONFIG['chrome_debug_port']}/json/version",
                timeout=2)
            print("Chrome已启动")
            return True
        except:
            continue

    print("Chrome启动失败，请手动执行：")
    cmd = (f'{CONFIG["chrome_path"]} '
           f'--remote-debugging-port={CONFIG["chrome_debug_port"]} '
           f'--remote-allow-origins=* '
           f'--user-data-dir={CONFIG["chrome_user_data_dir"]}')
    print(f"  {cmd}")
    return False


def wait_for_login(cdp, timeout=120):
    """等待用户完成扫码登录"""
    print(f"请在浏览器中扫码登录视频号助手（等待最多{timeout}秒）...")
    start = time.time()
    while time.time() - start < timeout:
        url = cdp.get_url()
        if "login" not in url and "login.html" not in url:
            print("登录成功！")
            return True
        time.sleep(3)
    return False


def check_account_opened(cdp):
    """发布前检查：提醒用户确认已注册并开通视频号。
    检测页面是否有"开通视频号"引导，未开通则中止流程。"""
    print("\n" + "="*50)
    print("【发布前检查】视频号开通状态确认")
    print("="*50)
    print("请确认您已完成以下步骤：")
    print("  1. 已在微信中注册视频号（我 -> 视频号 -> 创建账号）")
    print("  2. 已在视频号助手完成登录")
    print("  3. 账号状态正常，无封禁或限制")
    print("  4. 已完善账号信息（头像、名称等）")
    print("="*50)
    js_check_account = """
    (() => {
        const bodyText = document.body ? (document.body.innerText || '') : '';
        const needOpenKeywords = ['开通视频号', '注册视频号', '创建视频号', '立即开通', '申请开通'];
        for (const kw of needOpenKeywords) {
            if (bodyText.includes(kw)) return JSON.stringify({opened: false, reason: '页面提示需开通: ' + kw});
        }
        const url = window.location.href;
        if (url.includes('/platform/post/create') || url.includes('/platform/home'))
            return JSON.stringify({opened: true, reason: '已进入平台页面'});
        return JSON.stringify({opened: true, reason: '未检测到开通引导'});
    })()
    """
    result = cdp.eval_js(js_check_account)
    try:
        status = json.loads(result.get("value", "{}"))
        if not status.get("opened", True):
            print(f"\n⚠️  检测到账号可能未开通视频号：{status.get('reason', '')}")
            print("请先在微信中开通视频号后再运行本工具。")
            return False
        print(f"✓ 账号状态正常（{status.get('reason', '')}）")
        return True
    except Exception:
        print("✓ 未检测到异常，继续发布流程")
        return True


def verify_publish_success(cdp, timeout=30):
    """发布后验证：通过检测浏览器页面状态确认是否真正发布成功。
    返回 (success: bool, reason: str)"""
    print("正在验证发布结果...")
    start = time.time()
    while time.time() - start < timeout:
        url = cdp.get_url()
        if "post/list" in url:
            return True, "页面已跳转到作品列表"
        js_check = """
        (() => {
            const wujie = document.querySelector('wujie-app');
            const root = (wujie && wujie.shadowRoot) ? wujie.shadowRoot : document;
            const bodyText = (root.innerText || root.textContent || '').substring(0, 3000);
            const successKeywords = ['发表成功', '发布成功', '已发表', '发布完成', '上传成功'];
            for (const kw of successKeywords)
                if (bodyText.includes(kw)) return JSON.stringify({status: 'success', msg: kw});
            const failKeywords = ['发表失败', '发布失败', '上传失败', '网络异常', '内容审核不通过', '系统繁忙'];
            for (const kw of failKeywords)
                if (bodyText.includes(kw)) return JSON.stringify({status: 'failed', msg: kw});
            const toasts = root.querySelectorAll('.weui-desktop-dialog__bd, .weui-desktop-toast, .toast-msg, .error-msg');
            for (const t of toasts) {
                const txt = (t.innerText || '').trim();
                if (txt && txt.length < 200) {
                    if (txt.includes('失败') || txt.includes('错误') || txt.includes('异常'))
                        return JSON.stringify({status: 'failed', msg: txt});
                    if (txt.includes('成功'))
                        return JSON.stringify({status: 'success', msg: txt});
                }
            }
            if (window.location.href.includes('post/create')) {
                const buttons = root.querySelectorAll('button');
                for (const btn of buttons) {
                    const text = (btn.innerText || '').trim();
                    if (text === '发表' && !btn.disabled)
                        return JSON.stringify({status: 'still_on_form', msg: '发表按钮仍可用'});
                }
            }
            return JSON.stringify({status: 'waiting', msg: ''});
        })()
        """
        result = cdp.eval_js(js_check)
        try:
            status = json.loads(result.get("value", "{}"))
            s = status.get("status", "waiting")
            if s == "success":
                return True, f"检测到成功提示：{status.get('msg')}"
            elif s == "failed":
                return False, f"检测到失败提示：{status.get('msg')}"
        except Exception:
            pass
        time.sleep(2)
    url = cdp.get_url()
    if "post/list" in url:
        return True, "页面已跳转到作品列表"
    if "post/create" in url:
        return False, "超时后仍停留在发布页面"
    return False, "验证超时，无法确认发布状态"


def reset_publish_page(cdp):
    """发布失败后重置页面状态：刷新并重新进入发布页。
    必须刷新页面清除残留状态，否则重新上传会出现异常。"""
    print("正在重置页面状态...")
    try:
        cdp.eval_js("window.onbeforeunload = null; window.onunload = null;")
        cdp.send_cmd("Page.navigate", {"url": CONFIG["publish_url"]})
        time.sleep(8)
        js_check = """
        (() => {
            const wujie = document.querySelector('wujie-app');
            if (!wujie || !wujie.shadowRoot) return 'loading';
            const fileInput = wujie.shadowRoot.querySelector('input[type="file"]');
            return fileInput ? 'ready' : 'waiting';
        })()
        """
        for i in range(8):
            result = cdp.eval_js(js_check)
            if result.get("value") == "ready":
                print("页面已重置，可以重新上传")
                return True
            time.sleep(2)
        print("页面重置后未就绪")
        return False
    except Exception as e:
        print(f"页面重置异常: {e}")
        return False


def navigate_to_publish(cdp):
    """导航到视频发布页面，等待wujie-app加载"""
    url = cdp.get_url()
    if "post/create" in url:
        print("已在发布页面")
        js_check = """
        (() => {
            const wujie = document.querySelector('wujie-app');
            if (!wujie || !wujie.shadowRoot) return 'loading';
            const fileInput = wujie.shadowRoot.querySelector('input[type="file"]');
            return fileInput ? 'ready' : 'waiting';
        })()
        """
        for i in range(5):
            result = cdp.eval_js(js_check)
            if result.get("value") == "ready":
                print("发布页面已就绪")
                return True
            time.sleep(3)

    print("正在进入发布页面...")
    cdp.navigate(CONFIG["publish_url"], wait=8)
    time.sleep(5)
    js_check = """
    (() => {
        const wujie = document.querySelector('wujie-app');
        if (!wujie || !wujie.shadowRoot) return 'loading';
        const fileInput = wujie.shadowRoot.querySelector('input[type="file"]');
        return fileInput ? 'ready' : 'waiting';
    })()
    """
    result = cdp.eval_js(js_check)
    if result.get("value") == "ready":
        print("已进入发布页面")
        return True

    result = cdp.shadow_click("发表视频", "button")
    if result.get("ok"):
        time.sleep(5)
        url = cdp.get_url()
        if "post/create" in url:
            print("已进入发布页面")
            return True

    return False


def upload_video(cdp, video_path):
    """上传视频文件，等待视频和封面完全处理完毕"""
    print(f"正在上传视频: {os.path.basename(video_path)}")

    result = cdp.upload_file_via_cdp(video_path)
    if not result:
        print("视频上传失败")
        return False

    print("视频文件已发送，等待服务器处理（转码、生成封面）...")

    js_check_ready = """
    (() => {
        const wujie = document.querySelector('wujie-app');
        if (!wujie || !wujie.shadowRoot) return 'loading';
        const shadow = wujie.shadowRoot;

        // 1. 检查"上传中/处理中"提示
        const popovers = shadow.querySelectorAll('.weui-desktop-popover');
        for (const pop of popovers) {
            const text = (pop.innerText || pop.textContent || '').trim();
            if (text.includes('上传中') || text.includes('处理中')) {
                const style = window.getComputedStyle(pop);
                if (style.display !== 'none' && style.visibility !== 'hidden') {
                    return 'uploading';
                }
            }
        }

        // 2. 检查关键帧/封面图片是否加载完成
        const keyFrames = shadow.querySelectorAll(
            '.key-frames, .current-key-frame-img, .preview-image');
        let hasKeyFrame = false;
        for (const img of keyFrames) {
            if (img.complete && img.naturalWidth > 0 && img.offsetWidth > 0) {
                hasKeyFrame = true;
                break;
            }
        }
        if (!hasKeyFrame) {
            const coverImgs = shadow.querySelectorAll('img[class*="cover"]');
            let hasCover = false;
            for (const img of coverImgs) {
                if (img.complete && img.naturalWidth > 0
                        && img.src.includes('finder.video.qq.com')) {
                    hasCover = true;
                    break;
                }
            }
            if (!hasCover) return 'processing_cover';
        }

        // 3. 检查发表按钮是否可用且视频已就绪
        const buttons = shadow.querySelectorAll('button');
        for (const btn of buttons) {
            const text = (btn.innerText || btn.textContent || '').trim();
            if (text === '发表') {
                if (btn.disabled || btn.classList.contains('disabled')) {
                    return 'processing';
                }
                const video = shadow.querySelector('video');
                if (video && video.src && video.readyState >= 2) {
                    return 'ready';
                }
            }
        }
        return 'processing';
    })()
    """

    max_wait = 120
    for i in range(max_wait):
        time.sleep(2)
        result = cdp.eval_js(js_check_ready)
        status = result.get("value", "loading")

        if status == "ready":
            print(f"视频和封面处理完成！（等待了{(i+1)*2}秒）")
            time.sleep(3)
            return True
        elif status == "uploading":
            if (i + 1) % 5 == 0:
                print(f"  视频上传中... ({(i+1)*2}秒)")
        elif status == "processing":
            if (i + 1) % 5 == 0:
                print(f"  服务器处理中... ({(i+1)*2}秒)")
        elif status == "processing_cover":
            if (i + 1) % 5 == 0:
                print(f"  等待封面和关键帧生成... ({(i+1)*2}秒)")

    print("等待超时，视频可能还在处理中，尝试继续发布...")
    return True


def fill_and_publish(cdp, title, description):
    """填写标题和描述，然后点击发表按钮。
    注意：只负责点击，是否成功由 verify_publish_success() 单独验证。"""
    # 先填标题（避免焦点冲突）
    print(f"填写标题: {title}")
    title_result = cdp.fill_title(title)
    print(f"  标题结果: {title_result}")
    time.sleep(2)

    # 再填描述
    print(f"填写描述: {description[:30]}...")
    desc_result = cdp.fill_description(description)
    print(f"  描述结果: {desc_result}")
    time.sleep(2)

    # 点击发表
    print("正在提交发布...")
    result = cdp.shadow_click("发表", "button")
    if result.get("ok"):
        print("已点击发表按钮")
        return True
    else:
        print("未找到发表按钮")
        return False


def publish_single_video(cdp, video_path, title, description, record_dir,
                         max_retries=3):
    """发布单个视频的完整流程，包含发布后验证和失败自动重试（最多3次）"""
    filename = os.path.basename(video_path)
    print(f"\n{'='*50}")
    print(f"开始发布: {filename}")
    print(f"{'='*50}")

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            print(f"\n--- 第 {attempt}/{max_retries} 次重试 ---")

        if not navigate_to_publish(cdp):
            print("无法进入发布页面")
            if attempt < max_retries:
                time.sleep(3); reset_publish_page(cdp); continue
            save_publish_record(video_path, title, description, [], "failed_navigate", record_dir)
            return False

        if not upload_video(cdp, video_path):
            if attempt < max_retries:
                print("上传失败，3秒后重置页面重试...")
                time.sleep(3); reset_publish_page(cdp); continue
            save_publish_record(video_path, title, description, [], "failed_upload", record_dir)
            return False

        if not fill_and_publish(cdp, title, description):
            if attempt < max_retries:
                time.sleep(3); reset_publish_page(cdp); continue
            save_publish_record(video_path, title, description, [], "failed_publish", record_dir)
            return False

        # ★验证发布是否真正成功
        success, reason = verify_publish_success(cdp, timeout=30)
        if success:
            print(f"✓ 发布成功！{reason}")
            record_path = save_publish_record(video_path, title, description, [], "success", record_dir)
            print(f"发布记录已保存: {record_path}")
            return True

        print(f"✗ 发布未成功：{reason}")
        if attempt < max_retries:
            print(f"3秒后重置页面重新上传（剩余重试: {max_retries - attempt}）...")
            time.sleep(3)
            reset_publish_page(cdp)
        else:
            print(f"已达最大重试次数 {max_retries}，发布失败")
            save_publish_record(video_path, title, description, [], "failed_after_retries",
                                record_dir, extra={"last_reason": reason, "retries": attempt})
            return False
    return False


def batch_publish(video_folder=None, titles=None, descriptions=None):
    """批量发布视频"""
    if not video_folder:
        video_folder = CONFIG["video_folder"]

    if not ensure_chrome_running():
        return

    cdp = create_chrome_cdp()
    try:
        tab = cdp.connect(tab_filter="channels.weixin.qq.com")
        print(f"已连接到: {tab['url']}")
    except ConnectionError:
        print("连接失败，请确保浏览器已打开视频号助手页面")
        return

    cdp.enable_domains()

    url = cdp.get_url()
    if "login" in url:
        if not wait_for_login(cdp):
            print("登录超时")
            cdp.close()
            return

    # 发布前检查：确认视频号已开通
    if not check_account_opened(cdp):
        print("\n发布已取消：请先开通视频号后再试。")
        cdp.close()
        return

    videos = scan_video_folder(video_folder)
    if not videos:
        print(f"文件夹中没有找到视频文件: {video_folder}")
        cdp.close()
        return

    print(f"\n找到 {len(videos)} 个视频待发布:")
    for i, v in enumerate(videos):
        info = get_video_info(v["full_path"])
        print(f"  [{i+1}] {v['filename']} | "
              f"{info['width']}x{info['height']} | "
              f"{info['duration']:.1f}s")

    record_dir = CONFIG["record_folder"]
    success_count = 0
    fail_count = 0

    for i, v in enumerate(videos):
        raw_title = (titles[i] if titles and i < len(titles)
                     else os.path.splitext(v['filename'])[0])
        description = (descriptions[i]
                       if descriptions and i < len(descriptions)
                       else None)

        title = sanitize_title(raw_title)
        title = ensure_title_length(
            title, min_len=6,
            max_len=CONFIG.get("max_title_length", 16))

        if title != raw_title:
            print(f"  标题处理: '{raw_title}' -> '{title}'")
        if not description:
            description = generate_description(v['filename'], title)

        print(f"  标题: {title} ({len(title)}字)")

        if publish_single_video(
                cdp, v["full_path"], title, description, record_dir):
            success_count += 1
        else:
            fail_count += 1

        if i < len(videos) - 1:
            print("\n等待5秒后处理下一个视频...")
            time.sleep(5)

    print(f"\n{'='*50}")
    print(f"发布完成！成功: {success_count}, 失败: {fail_count}")
    print(f"发布记录保存在: {record_dir}")
    print(f"{'='*50}")
    cdp.close()


def publish_one(video_path, title, description):
    """发布单个视频（供外部调用）"""
    if not ensure_chrome_running():
        return False

    cdp = create_chrome_cdp()
    try:
        cdp.connect(tab_filter="channels.weixin.qq.com")
    except ConnectionError:
        print("连接失败")
        return False

    cdp.enable_domains()
    if "login" in cdp.get_url():
        if not wait_for_login(cdp):
            cdp.close()
            return False

    # 发布前检查：确认视频号已开通
    if not check_account_opened(cdp):
        print("\n发布已取消：请先开通视频号后再试。")
        cdp.close()
        return False

    record_dir = CONFIG["record_folder"]
    result = publish_single_video(
        cdp, video_path, title, description, record_dir)
    cdp.close()
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("视频号自动发布工具\n")
        print("功能：自动上传视频到微信视频号，发布前检查账号状态，发布后验证结果，失败自动重试\n")
        print("用法:")
        print("  python publish.py                 # 批量发布 待发布视频 文件夹")
        print("  python publish.py <视频文件路径>   # 发布单个视频")
        print("  python publish.py <文件夹路径>     # 批量发布指定文件夹")
        print("\n注意：使用前请确保已注册并开通微信视频号")
        sys.exit(0)

    arg = sys.argv[1]
    if os.path.isfile(arg):
        raw_title = os.path.splitext(os.path.basename(arg))[0]
        title = sanitize_title(raw_title)
        title = ensure_title_length(
            title, min_len=6,
            max_len=CONFIG.get("max_title_length", 16))
        description = generate_description(os.path.basename(arg), title)
        print(f"标题: {title} ({len(title)}字)")
        print(f"描述: {description[:50]}...")
        publish_one(arg, title, description)
    elif os.path.isdir(arg):
        batch_publish(arg)
    else:
        print(f"路径不存在: {arg}")
```

---

## 11. 部署步骤

1. 在工作目录下创建以下文件夹结构：
   ```
   视频号流程/
   ├── 待发布视频/
   ├── 已发布记录/
   └── .trae/skills/社媒发布/
       └── config/
   ```

2. 将上述代码分别保存为：
   - `.trae/skills/社媒发布/SKILL.md`
   - `.trae/skills/社媒发布/publish.py`
   - `.trae/skills/社媒发布/chrome_cdp.py`
   - `.trae/skills/社媒发布/video_analyzer.py`
   - `.trae/skills/社媒发布/requirements.txt`
   - `.trae/skills/社媒发布/config/settings.json`

3. 修改 `config/settings.json` 中的路径为实际绝对路径：
   - `chrome_user_data_dir`：设为技能目录下的 `chrome-debug-profile`
   - `video_folder`：设为"待发布视频"文件夹的绝对路径
   - `record_folder`：设为"已发布记录"文件夹的绝对路径

4. 安装 Python 依赖：
   ```bash
   pip install websocket-client opencv-python --break-system-packages
   ```

5. 首次运行：
   ```bash
   python publish.py
   ```
   浏览器会自动启动并打开视频号助手，手动扫码登录后，脚本会自动继续。

---

## 12. 注意事项与经验教训

### 12.1 必须遵守的规则

1. **发布前必须提醒用户确认已注册开通视频号**：未开通的账号无法发布。脚本通过 `check_account_opened()` 检测，若发现页面有"开通视频号"引导则中止流程。
2. **发布后必须验证是否真正成功**：点击"发表"后不能立即报告成功，必须调用 `verify_publish_success()` 检测页面 URL 跳转和成功/失败提示。
3. **发布失败必须自动重试**：验证未成功时调用 `reset_publish_page()` 刷新页面后重新上传发布，最多重试 3 次。
4. **标题字符限制**：标题仅允许中文、字母、数字、书名号、引号、冒号、加号、问号、百分号、摄氏度；逗号必须替换为空格。标题长度必须为 **6-16 字**。
5. **描述必须含话题标签**：如 `#视频号 #精彩视频 #分享`，以增加曝光。
6. **必须使用 `Input.insertText`**：禁止直接通过 JS 设置 `input.value` 或 `innerText`，否则 Vue/React 框架状态不同步，发布按钮不会激活。
7. **先填标题后填描述**：顺序不能反，否则会导致焦点冲突。
8. **Shadow DOM 穿透**：所有 DOM 操作必须在 `wujie-app.shadowRoot` 内执行。
9. **发布失败重试前必须刷新页面**：通过 `reset_publish_page()` 重置页面状态，避免残留状态干扰。

### 12.2 发布成功验证标准

`verify_publish_success()` 通过以下条件判定发布结果（轮询 30 秒，每 2 秒一次）：

**成功（任一满足即可）：**
1. URL 跳转到 `/platform/post/list`（最可靠）
2. 页面出现"发表成功""发布成功""已发表"等提示
3. 弹出含"成功"字样的 toast/dialog

**失败（任一满足即可）：**
1. 页面出现"发表失败""上传失败""网络异常""内容审核不通过"等提示
2. 弹出含"失败""错误""异常"字样的弹窗
3. 超时 30 秒后仍停留在发布页且发表按钮恢复可用

### 12.3 封面上传检测要点

判断视频是否处理完成需要同时检查三个条件：
1. 视频元素 `readyState >= 2`（有足够数据播放）
2. 封面/关键帧图片已加载（`naturalWidth > 0`，CDN 地址含 `finder.video.qq.com`）
3. "发表"按钮处于可用状态（非 disabled）

### 12.4 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 提示未开通视频号 | 账号未注册视频号 | 先在微信中开通视频号再运行 |
| 点击发表后仍报告失败 | 视频处理未完成或网络异常 | 脚本会自动刷新页面重试（最多3次） |
| 标题被拒绝 | 含特殊字符 | 检查 `sanitize_title()` 是否过滤完全 |
| 发表按钮灰色不可点 | 框架状态不同步 | 确认使用了 `Input.insertText` 而非直接设值 |
| 找不到输入框 | Shadow DOM 未加载 | 增加等待时间，检测 `wujie-app.shadowRoot` |
| 登录过期 | Cookie 失效 | 重新扫码登录，`chrome_user_data_dir` 可保留登录态 |
| 视频上传后一直处理中 | 网络慢或视频过大 | 最多等待 120 秒，超时后仍尝试发布 |
| 点击发表无反应 | 事件不完整 | 使用完整的鼠标事件序列（5 个事件） |
| 重试后仍失败 | 视频内容违规或账号限制 | 检查 `已发布记录` 中的 `last_reason` 字段 |

### 12.5 安全提示

- 发布过程中请勿手动操作浏览器
- 首次登录请使用自己的微信扫码
- `chrome_user_data_dir` 保存了登录态，请勿分享给他人
- 视频不得包含二维码、联系方式等导流信息（视频号平台规则）
