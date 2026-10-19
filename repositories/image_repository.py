import os
import threading
from collections import deque

from services import media_prep

CACHE_VERSION = 'v2'

# 背景工作的順序：照片先出現，影片 probe 很快，縮圖／封面其次，轉檔最久放最後
_JOB_PRIORITY = {'image': 0, 'video': 1, 'thumb': 2, 'poster': 2, 'transcode': 3}


class ImageRepository:
    """隨身碟照片與影片的清單與快取（exec-plan 042A／042B）。

    打開相框時只做 stat（快取是否還新），解碼、轉正、縮圖、probe、轉檔都交給
    背景執行緒；處理好一項就加進清單並通知 listener。快取放在
    `<thumbnails_dir>/v2/`，042A 以前的舊快取（沒有轉正方向）因此自動失效。

    影片（042B）：
    - 相容（H.264、短邊 ≤ 720、≤ 30 fps、無旋轉）：直接用原檔
    - 播得動但太大（例如 iPhone 1080p）：先用原檔，轉成 720p 後在清單中原位替換
    - 播不動（HEVC、帶旋轉標記等）：轉完才加入清單
    - 與照片同名的影片（iPhone 原況照片的 MOV）略過
    """

    def __init__(self, images_dir, thumbnails_dir=None,
                 max_image_size=media_prep.DEFAULT_MAX_IMAGE_SIZE, background=True):
        self.images_dir = images_dir
        self.thumbnails_dir = thumbnails_dir or os.path.join(os.path.dirname(images_dir), 'thumbnails')
        self.cache_dir = os.path.join(self.thumbnails_dir, CACHE_VERSION)
        self.max_image_size = max_image_size
        self.background = background
        self.has_ffmpeg = media_prep.has_ffmpeg()
        self._ensure_cache_dir()

        self._lock = threading.RLock()
        self._queue = deque()
        self._pending = set()
        self._running_jobs = 0
        self._running = set()
        self._worker = None
        self._cancel = threading.Event()
        self._listeners = []

        self._sources = {}     # 顯示路徑 -> 原始檔
        self._thumbs = {}      # 照片的顯示路徑 -> 格狀頁小縮圖
        self._posters = {}     # 影片的原始檔 -> 封面（原檔換成轉檔結果後仍找得到）
        self._probe_info = {}  # 影片的原始檔 -> probe 結果（給轉檔用）

        # 緩存已處理的圖片列表
        self._processed_images_cache = None
        self._is_initialized = False

    def _ensure_cache_dir(self):
        """確保快取目錄存在（隨身碟唯讀時只印 log，之後的處理會失敗並略過）"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError as e:
            print(f"無法建立快取目錄 {self.cache_dir}: {e}")

    # --- 路徑 ---------------------------------------------------------------

    def _display_cache_path(self, src):
        return os.path.join(self.cache_dir, os.path.basename(src) + '.jpg')

    def _thumb_cache_path(self, src):
        return os.path.join(self.cache_dir, os.path.basename(src) + '.thumb.jpg')

    def _transcoded_path(self, src):
        return os.path.join(self.cache_dir, os.path.basename(src) + '.mp4')

    def _poster_path(self, src):
        return os.path.join(self.cache_dir, os.path.basename(src) + '.poster.jpg')

    def _list_sources(self):
        """images_dir 這一層的照片與影片，依原始檔路徑排序。

        略過 `.` 開頭的檔案（macOS 在隨身碟留下的 `._IMG_xxxx.JPG` 打不開），
        以及與照片同名的影片（iPhone 原況照片會同時有 IMG_x.HEIC 與 IMG_x.MOV，
        不略過的話輪播會穿插很多 3 秒的短片）。
        """
        try:
            names = os.listdir(self.images_dir)
        except OSError:
            return []
        files = []
        for name in names:
            if name.startswith('.') or not media_prep.is_media(name):
                continue
            path = os.path.join(self.images_dir, name)
            if os.path.isfile(path):
                files.append(path)
        photo_stems = {os.path.splitext(os.path.basename(p))[0].lower()
                       for p in files if media_prep.is_image(p)}
        sources = [p for p in files
                   if not (media_prep.is_video(p)
                           and os.path.splitext(os.path.basename(p))[0].lower() in photo_stems)]
        sources.sort()
        return sources

    def _sort_key(self, display_path):
        # 一律依原始檔排序；用顯示路徑排序的話，快取（thumbnails/）和原檔（images/）
        # 會分成兩群
        return self._sources.get(display_path, display_path)

    # --- 掃描 ---------------------------------------------------------------

    def _initialize_images(self):
        """初始化媒體列表：只做 stat，需要處理的排進背景工作"""
        with self._lock:
            if self._is_initialized:
                return self._processed_images_cache

            print("正在初始化圖片列表...")
            media_prep.clean_partials(self.cache_dir)
            ready = []
            queued = 0
            for src in self._list_sources():
                if media_prep.has_failed(src, self.cache_dir):
                    continue
                if media_prep.is_video(src):
                    display = self._scan_video(src)
                elif src.lower().endswith('.gif'):
                    # GIF 保留原檔，才會有動畫
                    display = src
                else:
                    display = self._display_cache_path(src)
                    if not media_prep.is_fresh(src, display):
                        display = None
                        self._enqueue('image', src)
                if display is None:
                    queued += 1
                    continue
                self._sources[display] = src
                ready.append(display)
                self._check_preview(display)

            self._processed_images_cache = ready
            self._is_initialized = True
            if queued:
                print(f"圖片初始化完成，{len(ready)} 項可直接顯示，{queued} 項在背景處理中")
            else:
                print(f"圖片初始化完成，共 {len(ready)} 項")
            return ready

    def _scan_video(self, src):
        """回傳可以立即放進清單的顯示路徑；需要先 probe 時排工作並回傳 None"""
        if not self.has_ffmpeg:
            # 沒有 ffmpeg 就無法判斷或轉檔，直接放原檔（播不動的由 UI 的看門狗跳過）
            return src
        cached = self._transcoded_path(src)
        if media_prep.is_fresh(src, cached):
            return cached
        # probe 要啟動子行程，不在掃描時做；排在照片之後、很快就會處理
        self._enqueue('video', src)
        return None

    def _check_preview(self, display):
        """照片：小縮圖；影片：封面。已新鮮就記下，否則排進背景工作"""
        src = self._sources[display]
        if media_prep.is_video(display):
            if not self.has_ffmpeg:
                return
            poster = self._poster_path(src)
            if media_prep.is_fresh(src, poster):
                self._posters[src] = poster
            else:
                self._enqueue('poster', display)
            return
        thumb = self._thumb_cache_path(src)
        if media_prep.is_fresh(display, thumb):
            self._thumbs[display] = thumb
        else:
            self._enqueue('thumb', display)

    # --- 背景工作 -----------------------------------------------------------

    def _enqueue(self, kind, path):
        with self._lock:
            job = (kind, path)
            if job in self._pending:
                return
            self._pending.add(job)
            self._insert_by_priority(job)
            if self.background and (self._worker is None or not self._worker.is_alive()):
                self._worker = threading.Thread(target=self._worker_loop, daemon=True,
                                                name='photoframe-media-prep')
                self._worker.start()

    def _insert_by_priority(self, job):
        priority = _JOB_PRIORITY[job[0]]
        for i, (kind, _) in enumerate(self._queue):
            if _JOB_PRIORITY[kind] > priority:
                self._queue.insert(i, job)
                return
        self._queue.append(job)

    def _take_job(self):
        with self._lock:
            if not self._queue or self._cancel.is_set():
                return None
            job = self._queue.popleft()
            self._running_jobs += 1
            self._running.add(job)
            return job

    def _finish_job(self, job):
        with self._lock:
            self._pending.discard(job)
            self._running_jobs -= 1
            self._running.discard(job)

    def _worker_loop(self):
        while not self._cancel.is_set():
            job = self._take_job()
            if job is None:
                with self._lock:
                    if not self._queue:
                        self._worker = None
                        return
                continue
            self._run_job(job)

    def process_pending(self, max_jobs=None):
        """在呼叫端執行緒處理佇列（background=False 時給測試用）；max_jobs 可一次只做幾項"""
        done = 0
        while max_jobs is None or done < max_jobs:
            job = self._take_job()
            if job is None:
                return
            self._run_job(job)
            done += 1

    def _run_job(self, job):
        kind, path = job
        handlers = {
            'image': self._process_image,
            'thumb': self._process_thumb,
            'video': self._process_video,
            'transcode': self._process_transcode,
            'poster': self._process_poster,
        }
        try:
            handlers[kind](path)
        except Exception as e:  # 背景執行緒不能死，個別檔案失敗就略過
            print(f"背景處理失敗 {kind} {path}: {e}")
        finally:
            self._finish_job(job)

    def _process_image(self, src):
        display = self._display_cache_path(src)
        try:
            media_prep.prepare_image(src, display, self.max_image_size)
        except Exception as e:
            print(f"照片處理失敗，略過: {src}: {e}")
            media_prep.mark_failed(src, self.cache_dir)
            return
        self._add_new(display, src)

    def _process_thumb(self, display):
        with self._lock:
            src = self._sources.get(display)
        if src is None:
            return
        thumb = self._thumb_cache_path(src)
        try:
            # 從顯示圖做（已轉正、較小），GIF 則是從原檔的第一格
            media_prep.prepare_image(display, thumb, media_prep.THUMB_SIZE)
        except Exception as e:
            print(f"小縮圖處理失敗 {display}: {e}")
            return
        with self._lock:
            self._thumbs[display] = thumb

    def _process_video(self, src):
        """probe 後決定：直接用原檔、先用原檔再轉檔、或轉完才加入"""
        try:
            info = media_prep.probe(src)
        except Exception as e:
            print(f"影片無法讀取，略過: {src}: {e}")
            media_prep.mark_failed(src, self.cache_dir)
            return
        with self._lock:
            self._probe_info[src] = info

        if media_prep.video_is_compatible(info):
            self._add_new(src, src)
        elif media_prep.video_is_playable(info):
            # 播得動但太大：先放原檔讓使用者馬上看得到，背景轉成較小的版本
            self._add_new(src, src)
            if not media_prep.has_failed(src, self.cache_dir, media_prep.TRANSCODE_FAILED_SUFFIX):
                print(f"影片背景轉檔中（先播原檔）: {os.path.basename(src)}")
                self._enqueue('transcode', src)
        else:
            print(f"影片背景轉檔中（轉完才會出現）: {os.path.basename(src)}")
            self._enqueue('transcode', src)

    def _process_transcode(self, src):
        dst = self._transcoded_path(src)
        with self._lock:
            info = self._probe_info.get(src)
        try:
            media_prep.transcode_video(src, dst, info, self._cancel)
        except media_prep.TranscodeCancelled:
            print(f"轉檔中止（相框關閉），下次打開再轉: {os.path.basename(src)}")
            return
        except Exception as e:
            if info is not None and media_prep.video_is_playable(info):
                # 原檔還能播：保留原檔，只是不再重試轉檔
                print(f"轉檔失敗，繼續使用原檔: {src}: {e}")
                media_prep.mark_failed(src, self.cache_dir, media_prep.TRANSCODE_FAILED_SUFFIX)
            else:
                print(f"轉檔失敗，略過: {src}: {e}")
                media_prep.mark_failed(src, self.cache_dir)
            return
        print(f"影片轉檔完成: {os.path.basename(src)}")
        with self._lock:
            self._sources[dst] = src
            replacing = src in (self._processed_images_cache or [])
        if replacing:
            self._replace_display(src, dst)
        else:
            self._add_new(dst, src)

    def _process_poster(self, display):
        with self._lock:
            src = self._sources.get(display)
        if src is None:
            return
        poster = self._poster_path(src)
        try:
            media_prep.extract_poster(display, poster)
        except Exception as e:
            print(f"封面處理失敗 {display}: {e}")
            return
        with self._lock:
            self._posters[src] = poster

    def _add_new(self, display, src):
        """新的一項：記下來源、加入清單、排小縮圖／封面"""
        with self._lock:
            self._sources[display] = src
        self._add_display(display)
        with self._lock:
            self._check_preview(display)

    def _add_display(self, display):
        """加入清單並通知 listener。

        一定要建立新 list：SlideshowService 拿的是同一個 list 物件，原地插入會讓
        它的 index 偷偷位移。
        """
        with self._lock:
            current = self._processed_images_cache or []
            if display in current:
                return
            self._processed_images_cache = sorted(current + [display], key=self._sort_key)
            listeners = list(self._listeners)
        self._notify(listeners, display)

    def _replace_display(self, old, new):
        """在清單中原位把 old 換成 new（同樣建立新 list），並通知 listener"""
        with self._lock:
            current = self._processed_images_cache or []
            self._processed_images_cache = [new if p == old else p for p in current]
            listeners = list(self._listeners)
        self._notify(listeners, new)

    @staticmethod
    def _notify(listeners, display):
        for cb in listeners:
            try:
                cb(display)
            except Exception as e:
                print(f"通知 listener 失敗: {e}")

    # --- 公開 API -----------------------------------------------------------

    def get_image_files(self):
        """獲取媒體檔案列表，使用緩存避免重複處理"""
        with self._lock:
            if self._processed_images_cache is None:
                return self._initialize_images()
            return self._processed_images_cache

    def refresh_images(self):
        """強制重新掃描（新鮮的快取直接沿用，不會重做）"""
        print("強制刷新圖片列表...")
        self.clear_cache()
        return self._initialize_images()

    def clear_cache(self):
        """清除記憶體中的清單（不刪除磁碟上的快取）"""
        with self._lock:
            self._processed_images_cache = None
            self._is_initialized = False
        print("圖片緩存已清除")

    def get_original_image_path(self, display_path):
        """根據顯示路徑獲取原始檔路徑"""
        with self._lock:
            return self._sources.get(display_path, display_path)

    def is_video(self, path):
        return media_prep.is_video(path)

    def get_thumbnail(self, display_path):
        """格狀頁／影片 preview 用的小圖。

        照片：小縮圖，還沒做好就回傳顯示圖本身；影片：封面，還沒做好回傳 None
        """
        with self._lock:
            if media_prep.is_video(display_path):
                return self._posters.get(self._sources.get(display_path, display_path))
            return self._thumbs.get(display_path, display_path)

    def add_listener(self, cb):
        """cb(display_path)：背景處理好一項（或影片換成轉檔版本）時呼叫，在背景執行緒上"""
        with self._lock:
            self._listeners.append(cb)

    def has_pending_jobs(self):
        with self._lock:
            return bool(self._queue) or self._running_jobs > 0

    def expects_more_items(self):
        """還有項目會加進清單嗎？（照片處理、影片 probe、轉完才出現的影片）

        原檔已在清單裡、只是要換成 720p 的轉檔不算：它不會增加項目。
        """
        with self._lock:
            listed = set(self._processed_images_cache or [])
            for kind, path in list(self._queue) + list(self._running):
                if kind in ('image', 'video'):
                    return True
                if kind == 'transcode' and path not in listed:
                    return True
            return False

    def shutdown(self, timeout=2.0):
        """停止背景工作：進行中的轉檔立即中止，其餘下次打開相框再做。

        最多等背景執行緒 timeout 秒，讓它刪掉轉到一半的 .part；背景執行緒是
        daemon，不等的話程式一結束它就被砍掉、來不及收拾（下次掃描仍會清掉）。
        """
        self._cancel.set()
        worker = self._worker
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout)
