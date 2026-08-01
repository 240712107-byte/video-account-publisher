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
    """清理标题，移除视频号不支持的字符

    视频号标题规则：
    - 仅支持：中文、字母、数字、书名号《》、引号""''、
      冒号:、加号+、问号?、百分号%、摄氏度℃、空格
    - 逗号可用空格代替
    """
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
    """发布前检查：提醒用户确认已注册并开通视频号

    视频号助手页面如果账号未开通，会显示开通引导页而非发布界面。
    此函数检测当前页面状态，判断账号是否已具备发布权限。
    返回 True 表示已开通可继续，False 表示需要用户先开通。
    """
    print("\n" + "="*50)
    print("【发布前检查】视频号开通状态确认")
    print("="*50)
    print("请确认您已完成以下步骤：")
    print("  1. 已在微信中注册视频号（我 -> 视频号 -> 创建账号）")
    print("  2. 已在视频号助手 channels.weixin.qq.com 完成登录")
    print("  3. 账号状态正常，无封禁或限制")
    print("  4. 已完善账号信息（头像、名称等）")
    print("="*50)

    # 检测页面是否有"开通视频号"或"注册"类引导
    js_check_account = """
    (() => {
        const bodyText = document.body ? (document.body.innerText || '') : '';
        // 如果页面包含开通/注册引导关键词，说明账号未开通
        const needOpenKeywords = ['开通视频号', '注册视频号', '创建视频号', '立即开通', '申请开通'];
        for (const kw of needOpenKeywords) {
            if (bodyText.includes(kw)) {
                return JSON.stringify({opened: false, reason: '页面提示需开通: ' + kw});
            }
        }
        // 如果能正常访问平台主页或发布页，说明已开通
        const url = window.location.href;
        if (url.includes('/platform/post/create') || url.includes('/platform/home')) {
            return JSON.stringify({opened: true, reason: '已进入平台页面'});
        }
        return JSON.stringify({opened: true, reason: '未检测到开通引导'});
    })()
    """
    result = cdp.eval_js(js_check_account)
    try:
        status = json.loads(result.get("value", "{}"))
        if not status.get("opened", True):
            print(f"\n⚠️  检测到账号可能未开通视频号：{status.get('reason', '')}")
            print("请先在微信中开通视频号后再运行本工具。")
            print("开通路径：微信 -> 发现 -> 视频号 -> 右上角个人中心 -> 创建账号")
            return False
        print(f"✓ 账号状态正常（{status.get('reason', '')}）")
        return True
    except Exception:
        # 解析失败时不阻断流程，仅打印提醒
        print("✓ 未检测到异常，继续发布流程")
        return True


def verify_publish_success(cdp, timeout=30):
    """发布后验证：通过检测浏览器页面状态确认视频是否真正发布成功

    检测逻辑：
    1. URL 是否跳转到了 /platform/post/list（发布成功的标志）
    2. 是否出现"发表成功"类提示
    3. 是否仍停留在发布页且有错误提示（发布失败）
    4. 发表按钮是否恢复可用（说明提交未生效）

    返回: (success: bool, reason: str)
    """
    print("正在验证发布结果...")
    start = time.time()

    while time.time() - start < timeout:
        url = cdp.get_url()

        # 条件1：已跳转到作品列表页 —— 最可靠的成功标志
        if "post/list" in url:
            return True, "页面已跳转到作品列表"

        # 检测页面中的成功/失败提示
        js_check = """
        (() => {
            const wujie = document.querySelector('wujie-app');
            const root = (wujie && wujie.shadowRoot) ? wujie.shadowRoot : document;
            const bodyText = (root.innerText || root.textContent || '').substring(0, 3000);

            // 成功提示关键词
            const successKeywords = ['发表成功', '发布成功', '已发表', '发布完成', '上传成功'];
            for (const kw of successKeywords) {
                if (bodyText.includes(kw)) return JSON.stringify({status: 'success', msg: kw});
            }

            // 失败提示关键词
            const failKeywords = ['发表失败', '发布失败', '上传失败', '网络异常',
                                  '内容审核不通过', '发布失败请重试', '系统繁忙'];
            for (const kw of failKeywords) {
                if (bodyText.includes(kw)) return JSON.stringify({status: 'failed', msg: kw});
            }

            // 检查是否有错误弹窗/toast
            const toasts = root.querySelectorAll(
                '.weui-desktop-dialog__bd, .weui-desktop-toast, .toast-msg, .error-msg');
            for (const t of toasts) {
                const txt = (t.innerText || '').trim();
                if (txt && txt.length < 200) {
                    if (txt.includes('失败') || txt.includes('错误') || txt.includes('异常')) {
                        return JSON.stringify({status: 'failed', msg: txt});
                    }
                    if (txt.includes('成功')) {
                        return JSON.stringify({status: 'success', msg: txt});
                    }
                }
            }

            // 检查是否仍在发布页且发表按钮可用（说明点击未生效）
            if (window.location.href.includes('post/create')) {
                const buttons = root.querySelectorAll('button');
                for (const btn of buttons) {
                    const text = (btn.innerText || '').trim();
                    if (text === '发表' && !btn.disabled) {
                        return JSON.stringify({status: 'still_on_form', msg: '发表按钮仍可用'});
                    }
                }
            }

            return JSON.stringify({status: 'waiting', msg: ''});
        })()
        """
        result = cdp.eval_js(js_check)
        try:
            status = json.loads(result.get("value", "{}"))
            s = status.get("status", "waiting")
            msg = status.get("msg", "")
            if s == "success":
                return True, f"检测到成功提示：{msg}"
            elif s == "failed":
                return False, f"检测到失败提示：{msg}"
            # still_on_form 和 waiting 继续轮询
        except Exception:
            pass

        time.sleep(2)

    # 超时后做最终判断
    url = cdp.get_url()
    if "post/list" in url:
        return True, "页面已跳转到作品列表"
    if "post/create" in url:
        return False, "超时后仍停留在发布页面"
    return False, "验证超时，无法确认发布状态"


def reset_publish_page(cdp):
    """发布失败后重置页面状态：刷新并重新进入发布页

    必须刷新页面清除残留状态，否则重新上传会出现各种异常。
    """
    print("正在重置页面状态...")
    try:
        cdp.eval_js("window.onbeforeunload = null; window.onunload = null;")
        cdp.send_cmd("Page.navigate", {
            "url": CONFIG["publish_url"]
        })
        time.sleep(8)
        # 等待 wujie-app 和 file input 就绪
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
    """填写标题和描述，然后点击发表按钮

    注意：此函数只负责填写表单并点击发表。
    发布是否真正成功由 verify_publish_success() 单独验证。
    """
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
    """发布单个视频的完整流程，包含发布后验证和失败自动重试

    流程：
    1. 进入发布页面
    2. 上传视频并等待处理完成
    3. 填写标题和描述，点击发表
    4. 验证发布是否真正成功（检测页面跳转和提示）
    5. 若失败则重置页面并重新上传，最多重试 max_retries 次
    """
    filename = os.path.basename(video_path)
    print(f"\n{'='*50}")
    print(f"开始发布: {filename}")
    print(f"{'='*50}")

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            print(f"\n--- 第 {attempt}/{max_retries} 次重试 ---")

        # Step 1: 进入发布页面
        if not navigate_to_publish(cdp):
            print("无法进入发布页面")
            if attempt < max_retries:
                print("等待3秒后重试...")
                time.sleep(3)
                reset_publish_page(cdp)
                continue
            save_publish_record(
                video_path, title, description, [],
                "failed_navigate", record_dir)
            return False

        # Step 2: 上传视频
        if not upload_video(cdp, video_path):
            if attempt < max_retries:
                print("上传失败，等待3秒后重置页面重试...")
                time.sleep(3)
                reset_publish_page(cdp)
                continue
            save_publish_record(
                video_path, title, description, [],
                "failed_upload", record_dir)
            return False

        # Step 3: 填写并点击发表
        if not fill_and_publish(cdp, title, description):
            if attempt < max_retries:
                print("点击发表失败，等待3秒后重置页面重试...")
                time.sleep(3)
                reset_publish_page(cdp)
                continue
            save_publish_record(
                video_path, title, description, [],
                "failed_publish", record_dir)
            return False

        # Step 4: 验证发布是否真正成功
        success, reason = verify_publish_success(cdp, timeout=30)
        if success:
            print(f"✓ 发布成功！{reason}")
            record_path = save_publish_record(
                video_path, title, description, [],
                "success", record_dir)
            print(f"发布记录已保存: {record_path}")
            return True

        # Step 5: 发布失败，准备重试
        print(f"✗ 发布未成功：{reason}")
        if attempt < max_retries:
            print(f"将在3秒后重置页面并重新上传（剩余重试次数: {max_retries - attempt}）...")
            time.sleep(3)
            reset_publish_page(cdp)
        else:
            print(f"已达到最大重试次数 {max_retries}，发布失败")
            save_publish_record(
                video_path, title, description, [],
                "failed_after_retries", record_dir,
                extra={"last_reason": reason, "retries": attempt})
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
