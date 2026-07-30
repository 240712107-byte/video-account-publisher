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
        tabs = json.loads(urllib.request.urlopen(f"http://localhost:{self.port}/json/list").read())
        page_tab = None
        for t in tabs:
            if t['type'] != 'page':
                continue
            if tab_filter and tab_filter not in t.get('url', ''):
                continue
            page_tab = t
            break
        if not page_tab:
            # fallback
            for t in tabs:
                if t['type'] == 'page':
                    page_tab = t
                    break
        if not page_tab:
            raise ConnectionError("没有找到可用的浏览器标签页")
        self.ws = websocket.create_connection(page_tab['webSocketDebuggerUrl'], timeout=30)
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
        """导航到指定URL"""
        result = self.send_cmd("Page.navigate", {"url": url})
        time.sleep(wait)
        return result

    def eval_js(self, expression, return_by_value=True, timeout=15):
        """执行JavaScript"""
        params = {"expression": expression, "returnByValue": return_by_value}
        result = self.send_cmd("Runtime.evaluate", params, timeout=timeout)
        if result and result.get("result"):
            return result["result"].get("result", {})
        return {}

    def eval_js_with_args(self, expression, args, return_by_value=True, timeout=15):
        """执行带参数的JavaScript（参数直接嵌入JS字符串）"""
        result = self.send_cmd("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": return_by_value
        }, timeout=timeout)
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

    def shadow_find(self, text_match, tag=None):
        """在shadow DOM中查找元素，返回坐标信息"""
        js = f"""
        (() => {{
            const wujieApp = document.querySelector('wujie-app');
            if (!wujieApp || !wujieApp.shadowRoot) return JSON.stringify({{error: 'no shadow'}});
            const shadow = wujieApp.shadowRoot;
            const allEls = shadow.querySelectorAll('{tag or '*'}');
            const matches = [];
            for (const el of allEls) {{
                const text = el.textContent ? el.textContent.trim() : '';
                if (text === {json.dumps(text_match)} && el.children.length === 0) {{
                    const rect = el.getBoundingClientRect();
                    matches.push({{
                        tag: el.tagName,
                        class: el.className.toString().substring(0, 80),
                        x: rect.x + rect.width/2,
                        y: rect.y + rect.height/2,
                        w: rect.width,
                        h: rect.height
                    }});
                }}
            }}
            return JSON.stringify({{count: matches.length, matches: matches}});
        }})()
        """
        result = self.eval_js(js)
        try:
            return json.loads(result.get("value", "{}"))
        except:
            return {"error": "parse error"}

    def upload_file_via_cdp(self, file_path):
        """通过CDP的DOM.setFileInputFiles上传文件"""
        # 获取file input的objectId
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

        # 获取objectId
        result = self.send_cmd("Runtime.evaluate", {
            "expression": "window.__fileInput",
            "returnByValue": False
        })
        obj_id = result.get("result", {}).get("result", {}).get("objectId")
        if not obj_id:
            return False

        # 设置文件
        result = self.send_cmd("DOM.setFileInputFiles", {
            "objectId": obj_id,
            "files": [os.path.abspath(file_path).replace("/", "\\")]
        })
        return result is not None

    def fill_description(self, text):
        """填写视频描述（contenteditable div）"""
        js = f"""
        (() => {{
            const wujieApp = document.querySelector('wujie-app');
            const shadow = wujieApp.shadowRoot;
            const editor = shadow.querySelector('.input-editor');
            if (!editor) return 'Editor not found';
            editor.focus();
            editor.innerText = {json.dumps(text)};
            editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
            editor.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return 'OK: ' + editor.innerText.length + ' chars';
        }})()
        """
        result = self.eval_js(js)
        return result.get("value", "")

    def fill_title(self, text):
        """填写短标题"""
        js = f"""
        (() => {{
            const wujieApp = document.querySelector('wujie-app');
            const shadow = wujieApp.shadowRoot;
            const inputs = shadow.querySelectorAll('input[type="text"]');
            for (const inp of inputs) {{
                if (inp.placeholder && inp.placeholder.includes('短标题')) {{
                    inp.focus();
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    setter.call(inp, '');
                    inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    setter.call(inp, {json.dumps(text)});
                    inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return 'OK: ' + inp.value;
                }}
            }}
            return 'NOT FOUND';
        }})()
        """
        result = self.eval_js(js)
        return result.get("value", "")

    def close(self):
        """关闭连接"""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None
