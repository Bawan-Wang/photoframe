"""照片與影片前處理：轉正方向、縮圖、轉檔、封面，寫入快取（exec-plan 042A／042B）。

只依賴 stdlib、Pillow 與 `heif-convert`／`ffmpeg`／`ffprobe` CLI，**不 import Kivy**，方便測試。
所有寫入都先寫到同目錄的 `<dst>.part` 再 `os.replace`，拔隨身碟、斷電或
相框被砍時不會留下半個檔案。
"""
import ctypes
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time

from PIL import Image as PILImage
from PIL import ImageOps

IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.heic', '.heif')
HEIF_EXTS = ('.heic', '.heif')
DEFAULT_MAX_IMAGE_SIZE = (1920, 1080)
THUMB_SIZE = (360, 360)
JPEG_QUALITY = 88
PART_SUFFIX = '.part'
FAILED_SUFFIX = '.failed'
HEIF_CONVERT_TIMEOUT = 120

VIDEO_EXTS = ('.mp4', '.mov', '.m4v', '.avi', '.mkv', '.3gp', '.mts', '.webm')
MEDIA_EXTS = IMAGE_EXTS + VIDEO_EXTS
# Phase 0 實測：gstplayer 播 1080p 只有約 20 fps，720p 約 27 fps
MAX_VIDEO_SHORT_SIDE = 720
MAX_VIDEO_FPS = 30
TRANSCODE_THREADS = 2  # 保留 CPU 給語音助理
TRANSCODE_TIMEOUT = 60 * 60
PROBE_TIMEOUT = 30
POSTER_TIMEOUT = 60
TRANSCODE_FAILED_SUFFIX = '.transcode-failed'


def is_image(path):
    return path.lower().endswith(IMAGE_EXTS)


def is_video(path):
    return path.lower().endswith(VIDEO_EXTS)


def is_media(path):
    return path.lower().endswith(MEDIA_EXTS)


def is_heif(path):
    return path.lower().endswith(HEIF_EXTS)


def is_fresh(src, cached):
    """快取存在、非空，且不比來源舊。"""
    try:
        st = os.stat(cached)
        return st.st_size > 0 and st.st_mtime >= os.stat(src).st_mtime
    except OSError:
        return False


def failed_marker(src, cache_dir, suffix=FAILED_SUFFIX):
    return os.path.join(cache_dir, os.path.basename(src) + suffix)


def has_failed(src, cache_dir, suffix=FAILED_SUFFIX):
    """標記檔比來源新就不再重試；來源被換掉（mtime 變新）就重試。"""
    marker = failed_marker(src, cache_dir, suffix)
    try:
        return os.stat(marker).st_mtime >= os.stat(src).st_mtime
    except OSError:
        return False


def mark_failed(src, cache_dir, suffix=FAILED_SUFFIX):
    try:
        with open(failed_marker(src, cache_dir, suffix), 'w', encoding='utf-8'):
            pass
    except OSError as e:
        print(f"無法寫入失敗標記 {src}: {e}")


def clean_partials(cache_dir):
    """刪除上次中斷留下的 *.part。"""
    try:
        names = os.listdir(cache_dir)
    except OSError:
        return
    for name in names:
        if name.endswith(PART_SUFFIX):
            try:
                os.remove(os.path.join(cache_dir, name))
            except OSError:
                pass


def has_heif_convert():
    return shutil.which('heif-convert') is not None


def _remove_quietly(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _open_heif(src):
    """HEIC 用 heif-convert 轉成暫存 JPEG，回傳暫存檔路徑（呼叫端負責刪除）。

    bookworm 的 apt 沒有 pillow_heif，Pillow 9.4 也讀不了 HEIC，只能走這條路。
    """
    if not has_heif_convert():
        raise RuntimeError("沒有 heif-convert，無法讀取 HEIC（請 apt install libheif-examples）")
    fd, tmp = tempfile.mkstemp(suffix='.jpg')
    os.close(fd)
    try:
        subprocess.run(
            ['heif-convert', '-q', '95', src, tmp],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            timeout=HEIF_CONVERT_TIMEOUT,
        )
        if os.path.getsize(tmp) == 0:
            raise RuntimeError(f"heif-convert 輸出為空: {src}")
    except Exception:
        _remove_quietly(tmp)
        raise
    return tmp


def _to_rgb_on_black(img):
    """透明或調色盤模式貼到黑底上，透明處才會是黑色而不是隨機顏色。"""
    if img.mode in ('RGB', 'L'):
        return img
    rgba = img.convert('RGBA')
    background = PILImage.new('RGB', rgba.size, (0, 0, 0))
    background.paste(rgba, mask=rgba.getchannel('A'))
    return background


def prepare_image(src, dst, max_size=DEFAULT_MAX_IMAGE_SIZE):
    """把 src 轉正方向、縮到 max_size 以內（只縮不放），存成 JPEG 到 dst。

    失敗時丟例外，且不留下 dst、.part 或 HEIC 暫存檔。
    """
    heif_tmp = _open_heif(src) if is_heif(src) else None
    part = dst + PART_SUFFIX
    try:
        with PILImage.open(heif_tmp or src) as img:
            if img.format == 'JPEG':
                # 讓解碼器直接縮小 2 的次方倍，大圖快好幾倍；用正方形上限，
                # 之後轉 90 度時尺寸才不會不夠
                side = max(max_size)
                img.draft('RGB', (side, side))
            img = ImageOps.exif_transpose(img)
            img = _to_rgb_on_black(img)
            img.thumbnail(max_size, PILImage.Resampling.LANCZOS)
            img.save(part, 'JPEG', quality=JPEG_QUALITY)
        os.replace(part, dst)
    except Exception:
        _remove_quietly(part)
        raise
    finally:
        if heif_tmp:
            _remove_quietly(heif_tmp)
    return dst


# --- 影片 -------------------------------------------------------------------

class TranscodeCancelled(Exception):
    """相框關閉（shutdown）時中止轉檔；不算失敗，下次打開會重轉。"""


def has_ffmpeg():
    return shutil.which('ffmpeg') is not None and shutil.which('ffprobe') is not None


def _parse_rate(rate):
    num, _, den = (rate or '0/1').partition('/')
    try:
        return float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return 0.0


def probe(src):
    """回傳 vcodec, pix_fmt, width, height, fps, acodec, rotation；沒有影像串流就丟例外。"""
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', src],
        check=True, capture_output=True, text=True, timeout=PROBE_TIMEOUT,
    )
    streams = json.loads(out.stdout or '{}').get('streams', [])
    video = next((s for s in streams if s.get('codec_type') == 'video'
                  and not s.get('disposition', {}).get('attached_pic')), None)
    if video is None:
        raise ValueError(f"沒有影像串流: {src}")
    audio = next((s for s in streams if s.get('codec_type') == 'audio'), None)

    rotation = 0
    for side in video.get('side_data_list') or []:
        if 'rotation' in side:
            rotation = int(float(side['rotation']))
            break
    else:
        rotation = int(float(video.get('tags', {}).get('rotate', 0) or 0))

    fps = _parse_rate(video.get('avg_frame_rate')) or _parse_rate(video.get('r_frame_rate'))
    return {
        'vcodec': video.get('codec_name'),
        'pix_fmt': video.get('pix_fmt'),
        'width': int(video.get('width') or 0),
        'height': int(video.get('height') or 0),
        'fps': fps,
        'acodec': audio.get('codec_name') if audio else None,
        'rotation': rotation % 360,
    }


def video_is_playable(info):
    """gstplayer 播得動（1080p 也能播，只是約 20 fps）。帶旋轉標記的一律不算：
    方向要靠轉檔燒進畫面。"""
    return (info['vcodec'] == 'h264'
            and info['pix_fmt'] in ('yuv420p', 'yuvj420p')
            and info['acodec'] in (None, 'aac', 'mp3')
            and info['rotation'] == 0)


def video_is_compatible(info):
    """可以直接用原檔、不必轉檔。"""
    return (video_is_playable(info)
            and min(info['width'], info['height']) <= MAX_VIDEO_SHORT_SIDE
            and info['fps'] <= MAX_VIDEO_FPS + 0.5)


def _scale_filter(short_side=MAX_VIDEO_SHORT_SIDE):
    # 以短邊限制，直式影片才不會被縮過頭；trunc(.../2)*2 確保寬高是偶數
    # （libx264 + yuv420p 遇到奇數寬度會失敗）。ffmpeg 預設 -autorotate，
    # 這裡的 iw/ih 已經是轉正後的尺寸
    s = short_side
    return (f"scale='if(gt(iw,ih),-2,trunc(min({s},iw)/2)*2)'"
            f":'if(gt(iw,ih),trunc(min({s},ih)/2)*2,-2)'")


def _die_with_parent():
    """子行程在相框被砍時一起結束（PR_SET_PDEATHSIG）。

    注意：觸發條件是「建立子行程的那個執行緒」結束；轉檔在背景執行緒裡
    同步等待 ffmpeg，等待期間執行緒不會結束。
    """
    try:
        libc = ctypes.CDLL('libc.so.6', use_errno=True)
        libc.prctl(1, signal.SIGTERM)  # 1 = PR_SET_PDEATHSIG
    except Exception:
        pass


def _run_ffmpeg(args, timeout, cancel_event=None):
    """執行 ffmpeg；被 cancel_event 中止時丟 TranscodeCancelled，逾時或失敗丟 RuntimeError。"""
    # stderr 寫到暫存檔而不是 pipe：等待期間沒人讀 pipe，輸出一多就會互相卡住
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(
            args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=err,
            preexec_fn=_die_with_parent,
        )
        deadline = time.monotonic() + timeout
        try:
            while True:
                try:
                    proc.wait(timeout=0.5)
                    break
                except subprocess.TimeoutExpired:
                    pass
                if cancel_event is not None and cancel_event.is_set():
                    raise TranscodeCancelled()
                if time.monotonic() > deadline:
                    raise RuntimeError(f"ffmpeg 逾時（{timeout} 秒）")
        except BaseException:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            raise
        if proc.returncode != 0:
            err.seek(0)
            tail = err.read()[-300:].decode(errors='replace')
            raise RuntimeError(f"ffmpeg 失敗（{proc.returncode}）: {tail}")


def transcode_video(src, dst, info=None, cancel_event=None, short_side=MAX_VIDEO_SHORT_SIDE):
    """轉成 H.264 yuv420p + AAC 的 mp4，短邊 ≤ short_side、fps ≤ 30、方向燒進畫面。

    寫到 dst.part 再 os.replace；失敗或中止時不留下任何檔案。
    """
    filters = []
    if info is None or info['fps'] > MAX_VIDEO_FPS + 0.5:
        filters.append(f'fps={MAX_VIDEO_FPS}')
    filters += [_scale_filter(short_side), 'format=yuv420p']
    part = dst + PART_SUFFIX
    args = [
        'nice', '-n', '10', 'ffmpeg', '-y', '-nostdin', '-v', 'error', '-i', src,
        '-map', '0:v:0', '-map', '0:a:0?',
        '-threads', str(TRANSCODE_THREADS),
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
        '-vf', ','.join(filters),
        '-c:a', 'aac', '-b:a', '128k', '-ac', '2',
        '-movflags', '+faststart', '-f', 'mp4', part,
    ]
    try:
        _run_ffmpeg(args, TRANSCODE_TIMEOUT, cancel_event)
        if os.path.getsize(part) == 0:
            raise RuntimeError(f"轉檔輸出為空: {src}")
        os.replace(part, dst)
    except BaseException:
        _remove_quietly(part)
        raise
    return dst


def extract_poster(src, dst):
    """抽一張封面（第 1 秒；影片短於 1 秒時改抽第一格）。"""
    part = dst + PART_SUFFIX
    try:
        for seek in ('1', '0'):
            _remove_quietly(part)
            args = ['ffmpeg', '-y', '-nostdin', '-v', 'error', '-ss', seek, '-i', src,
                    '-frames:v', '1', '-vf', _scale_filter(), '-q:v', '3', '-f', 'image2', part]
            _run_ffmpeg(args, POSTER_TIMEOUT)
            if os.path.exists(part) and os.path.getsize(part) > 0:
                os.replace(part, dst)
                return dst
        raise RuntimeError(f"抽不出封面: {src}")
    except BaseException:
        _remove_quietly(part)
        raise
