"""
视频号自动发布工具 - 主发布脚本
用法: python publish.py [视频文件路径或文件夹路径]

流程:
1. 启动Chrome调试模式（如未启动）
2. 导航到视频号助手
3. 进入发布页面
4. 上传视频
5. 填写描述和标题
6. 提交发布
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

# 加载配置
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "settings.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


def sanitize_title(title):
    """清理标题，移除视频号不支持的字符
    
    视频号标题规则：
    - 最少6个字，最多30个字
    - 仅支持：中文、字母、数字、书名号《》、引号""''、
      冒号:、加号+、问号?、百分号%、摄氏度℃、空格
    - 禁用特殊符号（※★等）作为起始字符
    - 不得包含二维码、联系方式等导流信息
    - 逗号可用空格代替
    """
    # 允许的字符：中文、字母、数字、空格、书名号、引号、冒号、加号、问号、百分号、摄氏度
    allowed_pattern = r'[\u4e00-\u9fff\u3400-\u4dbfa-zA-Z0-9\s《》""'':+?%℃]'
    
    # 先把逗号替换成空格
    title = title.replace(',', ' ')
    title = title.replace('，', ' ')
    
    # 把常见的分隔符替换成空格
    for sep in ['-', '_', '.', '·', '|', '/', '\\']:
        title = title.replace(sep, ' ')
    
    # 移除所有不允许的字符
    title = ''.join(re.findall(allowed_pattern, title))
    
    # 合并多余空格
    title = re.sub(r'\s+', ' ', title).strip()
    
    return title


def ensure_title_length(title, min_len=6, max_len=16):
    """确保标题长度符合视频号要求
    
    视频号短标题最少6字，最多16字。
    如果不足6字，追加"精彩视频"等补充词。
    如果超过16字，截断。
    """
    title = title.strip()
    
    # 如果标题为空，使用默认标题
    if not title:
        title = "精彩视频分享"
    
    # 不足最小长度，补充内容
    if len(title) < min_len:
        # 常见补充词
        suffixes = [
            "精彩分享", "视频分享", "日常记录", "精彩瞬间",
            "一起来看", "不容错过", "超好看", "必看"
        ]
        for suffix in suffixes:
            candidate = title + suffix
            if len(candidate) >= min_len:
                title = candidate
                break
        # 如果还是不够，直接补到够
        while len(title) < min_len:
            title = title + "精彩视频"
    
    # 超过最大长度，截断
    if len(title) > max_len:
        title = title[:max_len]
    
    return title


def generate_description(filename, title):
    """生成视频描述，确保有内容
    
    视频号描述规则：
    - 不超过1000字（含话题标签）
    - 需要有实质内容
    - 建议加入2-5个话题标签增加曝光
    """
    # 去掉扩展名作为基础描述
    base_name = os.path.splitext(filename)[0]
    base_name = sanitize_title(base_name)
    
    # 如果标题有内容，用标题作为描述基础
    desc = title if title else base_name
    
    # 添加话题标签（增加曝光）
    hashtags = ["#视频号", "#精彩视频", "#分享"]
    
    # 组合描述
    description = f"{desc}\n\n{' '.join(hashtags)}"
    
    # 确保不超过1000字
    if len(description) > 1000:
        description = description[:1000]
    
    return description


def create_chrome_cdp():
    """创建浏览器控制对象，并在缺少依赖时给出安装提示"""
    try:
        from chrome_cdp import ChromeCDP
        return ChromeCDP(port=CONFIG["chrome_debug_port"])
    except ModuleNotFoundError as e:
        if e.name == "websocket":
            print("缺少依赖：websocket-client")
            print("请先运行：python -m pip install websocket-client")
        else:
            print(f"缺少依赖：{e.name}")
        raise


def ensure_chrome_running():
    """确保Chrome以调试模式运行"""
    import urllib.request
    try:
        urllib.request.urlopen(f"http://localhost:{CONFIG['chrome_debug_port']}/json/version", timeout=2)
        return True
    except:
        pass

    # 检查是否已有chrome进程
    try:
        subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
                       capture_output=True, text=True, timeout=5)
    except:
        pass

    # 启动Chrome
    print("正在启动Chrome调试模式...")
    subprocess.Popen([
        CONFIG["chrome_path"],
        f"--remote-debugging-port={CONFIG['chrome_debug_port']}",
        f"--remote-allow-origins=*",
        f"--user-data-dir={CONFIG['chrome_user_data_dir']}"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 等待启动
    for i in range(10):
        time.sleep(2)
        try:
            urllib.request.urlopen(f"http://localhost:{CONFIG['chrome_debug_port']}/json/version", timeout=2)
            print("Chrome已启动")
            return True
        except:
            continue

    print("Chrome启动失败，请手动执行以下命令：")
    cmd = f'{CONFIG["chrome_path"]} --remote-debugging-port={CONFIG["chrome_debug_port"]} --remote-allow-origins=* --user-data-dir={CONFIG["chrome_user_data_dir"]}'
    print(f"  {cmd}")
    return False


def wait_for_login(cdp, timeout=120):
    """等待用户完成登录，返回是否已登录"""
    print(f"请在Chrome中扫码登录视频号助手（等待最多{timeout}秒）...")
    start = time.time()
    while time.time() - start < timeout:
        url = cdp.get_url()
        if "login" not in url and "login.html" not in url:
            print("登录成功！")
            return True
        time.sleep(3)
    return False


def navigate_to_publish(cdp):
    """导航到视频发布页面"""
    url = cdp.get_url()
    if "post/create" in url:
        print("已在发布页面")
        # 检查页面是否加载完成（wujie-app是否存在）
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
            status = result.get("value", "loading")
            if status == "ready":
                print("发布页面已就绪")
                return True
            print(f"  等待页面加载... ({i+1}/5)")
            time.sleep(3)
    
    print("正在进入发布页面...")
    cdp.navigate(CONFIG["publish_url"], wait=8)
    url = cdp.get_url()
    if "post/create" in url:
        # 等待wujie-app加载
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

    # 尝试点击"发表视频"按钮
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
    if result:
        print("视频文件已发送，等待服务器处理（转码、生成封面）...")
        
        # 等待视频上传并处理完成
        # 检测条件：
        # 1. "文件上传中"提示消失
        # 2. 关键帧图片加载完成
        # 3. "发表"按钮可用
        js_check_ready = """
        (() => {
            const wujie = document.querySelector('wujie-app');
            if (!wujie || !wujie.shadowRoot) return 'loading';
            const shadow = wujie.shadowRoot;
            
            // 1. 检查是否有可见的"上传中"提示弹窗
            // 注意：popover-wrap容器本身始终可见，需要检查内部popover的display
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
            
            // 2. 检查关键帧图片是否加载完成（至少有一个可见且有宽度）
            const keyFrames = shadow.querySelectorAll('.key-frames, .current-key-frame-img, .preview-image');
            let hasKeyFrame = false;
            for (const img of keyFrames) {
                if (img.complete && img.naturalWidth > 0 && img.offsetWidth > 0) {
                    hasKeyFrame = true;
                    break;
                }
            }
            if (!hasKeyFrame) {
                // 即使关键帧不可见，检查封面图片是否已加载
                const coverImgs = shadow.querySelectorAll('img[class*="cover"]');
                let hasCover = false;
                for (const img of coverImgs) {
                    if (img.complete && img.naturalWidth > 0 && img.src.includes('finder.video.qq.com')) {
                        hasCover = true;
                        break;
                    }
                }
                if (!hasCover) return 'processing_cover';
            }
            
            // 3. 检查发表按钮是否可用
            const buttons = shadow.querySelectorAll('button');
            for (const btn of buttons) {
                const text = (btn.innerText || btn.textContent || '').trim();
                if (text === '发表') {
                    if (btn.disabled || btn.classList.contains('disabled')) {
                        return 'processing';
                    }
                    // 再确认有视频
                    const video = shadow.querySelector('video');
                    if (video && video.src && video.readyState >= 2) {
                        return 'ready';
                    }
                }
            }
            
            return 'processing';
        })()
        """
        
        max_wait = 120  # 最多等待120秒
        for i in range(max_wait):
            time.sleep(2)
            result = cdp.eval_js(js_check_ready)
            status = result.get("value", "loading")
            
            if status == "ready":
                print(f"视频和封面处理完成！（等待了{(i+1)*2}秒）")
                # 额外等待3秒确保完全稳定
                time.sleep(3)
                return True
            elif status == "uploading":
                if (i+1) % 5 == 0:
                    print(f"  视频上传中... ({(i+1)*2}秒)")
            elif status == "processing":
                if (i+1) % 5 == 0:
                    print(f"  服务器处理中... ({(i+1)*2}秒)")
            elif status == "processing_cover":
                if (i+1) % 5 == 0:
                    print(f"  等待封面和关键帧生成... ({(i+1)*2}秒)")
            else:
                if (i+1) % 5 == 0:
                    print(f"  等待中... ({(i+1)*2}秒)")
        
        # 超时
        print("等待超时，视频可能还在处理中，尝试继续发布...")
        return True
    else:
        print("视频上传失败")
        return False


def fill_and_publish(cdp, title, description):
    """填写信息并发布"""
    # 先填标题（标题在描述下方，但先填标题避免焦点冲突）
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
        print("已点击发表按钮，等待跳转...")
        time.sleep(8)
        url = cdp.get_url()
        if "post/list" in url or "post/create" not in url:
            print("发布成功！页面已跳转")
            return True
        else:
            print("可能需要确认，检查页面状态...")
            return True
    else:
        print("未找到发表按钮")
        return False


def publish_single_video(cdp, video_path, title, description, record_dir):
    """发布单个视频的完整流程"""
    filename = os.path.basename(video_path)
    print(f"\n{'='*50}")
    print(f"开始发布: {filename}")
    print(f"{'='*50}")

    # Step 1: 进入发布页面
    if not navigate_to_publish(cdp):
        print("无法进入发布页面")
        save_publish_record(video_path, title, description, [], "failed_navigate", record_dir)
        return False

    # Step 2: 上传视频
    if not upload_video(cdp, video_path):
        save_publish_record(video_path, title, description, [], "failed_upload", record_dir)
        return False

    # Step 3: 填写并发布
    success = fill_and_publish(cdp, title, description)

    # 保存记录
    status = "success" if success else "failed_publish"
    record_path = save_publish_record(video_path, title, description, [], status, record_dir)
    print(f"发布记录已保存: {record_path}")

    return success


def batch_publish(video_folder=None, titles=None, descriptions=None):
    """批量发布视频"""
    if not video_folder:
        video_folder = CONFIG["video_folder"]

    # Step 0: 确保Chrome运行
    if not ensure_chrome_running():
        return

    # Step 1: 连接浏览器
    cdp = create_chrome_cdp()
    try:
        tab = cdp.connect(tab_filter="channels.weixin.qq.com")
        print(f"已连接到: {tab['url']}")
    except ConnectionError:
        print("连接失败，请确保Chrome已打开视频号助手页面")
        return

    cdp.enable_domains()

    # Step 2: 检查登录状态
    url = cdp.get_url()
    if "login" in url:
        if not wait_for_login(cdp):
            print("登录超时")
            cdp.close()
            return

    # Step 3: 扫描视频文件
    videos = scan_video_folder(video_folder)
    if not videos:
        print(f"文件夹中没有找到视频文件: {video_folder}")
        print("请将视频文件（.mp4/.mov/.avi等）放入该文件夹后重试")
        cdp.close()
        return

    print(f"\n找到 {len(videos)} 个视频待发布:")
    for i, v in enumerate(videos):
        info = get_video_info(v["full_path"])
        print(f"  [{i+1}] {v['filename']} | {info['width']}x{info['height']} | {info['duration']:.1f}s")

    # Step 4: 逐个发布
    record_dir = CONFIG["record_folder"]
    success_count = 0
    fail_count = 0

    for i, v in enumerate(videos):
        # 获取标题和描述
        if titles and i < len(titles):
            raw_title = titles[i]
        else:
            raw_title = os.path.splitext(v['filename'])[0]

        if descriptions and i < len(descriptions):
            description = descriptions[i]
        else:
            description = None  # 稍后自动生成

        # 清理标题中的特殊字符
        title = sanitize_title(raw_title)
        
        # 确保标题长度符合要求（最少6字，最多30字）
        title = ensure_title_length(title, min_len=6, max_len=CONFIG.get("max_title_length", 30))
        
        if title != raw_title:
            print(f"  标题处理: '{raw_title}' -> '{title}'")
        
        # 如果没有提供描述，自动生成
        if not description:
            description = generate_description(v['filename'], title)
        
        print(f"  标题: {title} ({len(title)}字)")
        print(f"  描述: {description[:50]}...")

        if publish_single_video(cdp, v["full_path"], title, description, record_dir):
            success_count += 1
        else:
            fail_count += 1

        # 如果不是最后一个，等待一下再处理下一个
        if i < len(videos) - 1:
            print(f"\n等待5秒后处理下一个视频...")
            time.sleep(5)

    # 汇总
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
        tab = cdp.connect(tab_filter="channels.weixin.qq.com")
    except ConnectionError:
        print("连接失败")
        return False

    cdp.enable_domains()

    url = cdp.get_url()
    if "login" in url:
        if not wait_for_login(cdp):
            cdp.close()
            return False

    record_dir = CONFIG["record_folder"]
    result = publish_single_video(cdp, video_path, title, description, record_dir)
    cdp.close()
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("视频号自动发布工具")
        print("")
        print("用法:")
        print("  python publish.py                          # 批量发布 待发布视频 文件夹中的所有视频")
        print("  python publish.py <视频文件路径>            # 发布单个视频（自动生成标题）")
        print("  python publish.py <文件夹路径>              # 批量发布指定文件夹中的视频")
        print("")
        print("文件夹结构:")
        print("  社媒发布/")
        print("  ├── 待发布视频/        ← 将视频文件放这里")
        print("  ├── 已发布记录/        ← 发布结果记录")
        print("  ├── config/")
        print("  │   └── settings.json  ← 配置文件")
        print("  ├── publish.py         ← 主脚本")
        print("  ├── chrome_cdp.py      ← 浏览器控制模块")
        print("  └── video_analyzer.py  ← 视频分析模块")
        sys.exit(0)

    arg = sys.argv[1]

    if os.path.isfile(arg):
        # 单个视频文件
        raw_title = os.path.splitext(os.path.basename(arg))[0]
        title = sanitize_title(raw_title)
        title = ensure_title_length(title, min_len=6, max_len=CONFIG.get("max_title_length", 30))
        if title != raw_title:
            print(f"标题处理: '{raw_title}' -> '{title}'")
        
        # 自动生成描述
        description = generate_description(os.path.basename(arg), title)
        print(f"标题: {title} ({len(title)}字)")
        print(f"描述: {description[:50]}...")
        
        publish_one(arg, title, description)
    elif os.path.isdir(arg):
        # 文件夹
        batch_publish(arg)
    else:
        print(f"路径不存在: {arg}")
