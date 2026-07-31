"""
视频号自动发布工具 - 视频内容分析模块
功能：提取视频关键帧，保存为PNG截图供AI分析
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
    duration = total_frames / fps

    timestamps = [int(duration * (i + 1) / (num_frames + 1)) for i in range(num_frames)]
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
    """获取视频基本信息"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")

    info = {
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "duration": cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS),
    }
    cap.release()
    return info


def scan_video_folder(folder_path):
    """扫描文件夹中的视频文件，返回列表"""
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v'}
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


def save_publish_record(video_path, title, description, hashtags, status, record_dir, extra=None):
    """保存发布记录"""
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
        record["publish_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    record_filename = os.path.splitext(os.path.basename(video_path))[0] + ".json"
    record_path = os.path.join(record_dir, record_filename)
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return record_path


if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else r"f:\TRAE SOLO CN\社媒发布\待发布视频"
    videos = scan_video_folder(folder)
    print(f"找到 {len(videos)} 个视频文件:")
    for v in videos:
        info = get_video_info(v["full_path"])
        print(f"  {v['filename']} | {info['width']}x{info['height']} | {info['duration']:.1f}s")
"""
视频号自动发布工具 - 视频内容分析模块
功能：提取视频关键帧，保存为PNG截图供AI分析
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
    duration = total_frames / fps

    timestamps = [int(duration * (i + 1) / (num_frames + 1)) for i in range(num_frames)]
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
    """获取视频基本信息"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")

    info = {
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "duration": cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS),
    }
    cap.release()
    return info


def scan_video_folder(folder_path):
    """扫描文件夹中的视频文件，返回列表"""
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v'}
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


def save_publish_record(video_path, title, description, hashtags, status, record_dir, extra=None):
    """保存发布记录"""
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
        record["publish_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    record_filename = os.path.splitext(os.path.basename(video_path))[0] + ".json"
    record_path = os.path.join(record_dir, record_filename)
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return record_path


if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else r"f:\TRAE SOLO CN\社媒发布\待发布视频"
    videos = scan_video_folder(folder)
    print(f"找到 {len(videos)} 个视频文件:")
    for v in videos:
        info = get_video_info(v["full_path"])
        print(f"  {v['filename']} | {info['width']}x{info['height']} | {info['duration']:.1f}s")
