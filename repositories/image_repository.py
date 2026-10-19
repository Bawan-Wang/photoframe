import os
import threading
from collections import deque

from services import media_prep

CACHE_VERSION = 'v2'


class ImageRepository:
    """隨身碟照片的清單與快取（exec-plan 042A）。

    打開相框時只做 stat（快取是否還新），解碼、轉正、縮圖都交給背景執行緒；
    處理好一張就加進清單並通知 listener。快取放在 `<thumbnails_dir>/v2/`，
    042A 以前的舊快取（沒有轉正方向）因此自動失效。
    """

    def __init__(self, images_dir, thumbnails_dir=None,
                 max_image_size=media_prep.DEFAULT_MAX_IMAGE_SIZE, background=True):
        self.images_dir = images_dir
        self.thumbnails_dir = thumbnails_dir or os.path.join(os.path.dirname(images_dir), 'thumbnails')
        self.cache_dir = os.path.join(self.thumbnails_dir, CACHE_VERSION)
        self.max_image_size = max_image_size
        self.background = background
        self._ensure_cache_dir()

        self._lock = threading.RLock()
        self._queue = deque()
        self._pending = set()
        self._running_jobs = 0
        self._worker = None
        self._cancel = threading.Event()
        self._listeners = []

        self._sources = {}  # 顯示路徑 -> 原始檔
        self._thumbs = {}   # 顯示路徑 -> 格狀頁小縮圖

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

    def _list_sources(self):
        """images_dir 這一層的照片，依原始檔路徑排序。略過 `.` 開頭的檔案
        （macOS 在隨身碟留下的 `._IMG_xxxx.JPG` 打不開）。"""
        try:
            names = os.listdir(self.images_dir)
        except OSError:
            return []
        sources = []
        for name in names:
            if name.startswith('.') or not media_prep.is_image(name):
                continue
            path = os.path.join(self.images_dir, name)
            if os.path.isfile(path):
                sources.append(path)
        sources.sort()
        return sources

    def _sort_key(self, display_path):
        # 一律依原始檔排序；用顯示路徑排序的話，快取（thumbnails/）和原檔（images/）
        # 會分成兩群
        return self._sources.get(display_path, display_path)

    # --- 掃描 ---------------------------------------------------------------

    def _initialize_images(self):
        """初始化圖片列表：只做 stat，需要處理的照片排進背景工作"""
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
                if src.lower().endswith('.gif'):
                    # GIF 保留原檔，才會有動畫
                    display = src
                else:
                    display = self._display_cache_path(src)
                    if not media_prep.is_fresh(src, display):
                        self._enqueue('image', src)
                        queued += 1
                        continue
                self._sources[display] = src
                ready.append(display)
                self._check_thumb(display)

            self._processed_images_cache = ready
            self._is_initialized = True
            if queued:
                print(f"圖片初始化完成，{len(ready)} 張可直接顯示，{queued} 張在背景處理中")
            else:
                print(f"圖片初始化完成，共 {len(ready)} 張圖片")
            return ready

    def _check_thumb(self, display):
        """小縮圖已新鮮就記下，否則排進背景工作"""
        thumb = self._thumb_cache_path(self._sources[display])
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
            # 顯示圖優先於小縮圖：先讓照片盡快出現在輪播裡
            if kind == 'image':
                self._insert_before_thumbs(job)
            else:
                self._queue.append(job)
            if self.background and (self._worker is None or not self._worker.is_alive()):
                self._worker = threading.Thread(target=self._worker_loop, daemon=True,
                                                name='photoframe-media-prep')
                self._worker.start()

    def _insert_before_thumbs(self, job):
        for i, (kind, _) in enumerate(self._queue):
            if kind == 'thumb':
                self._queue.insert(i, job)
                return
        self._queue.append(job)

    def _take_job(self):
        with self._lock:
            if not self._queue or self._cancel.is_set():
                return None
            job = self._queue.popleft()
            self._running_jobs += 1
            return job

    def _finish_job(self, job):
        with self._lock:
            self._pending.discard(job)
            self._running_jobs -= 1

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

    def process_pending(self):
        """在呼叫端執行緒把佇列做完（background=False 時給測試用）"""
        while True:
            job = self._take_job()
            if job is None:
                return
            self._run_job(job)

    def _run_job(self, job):
        kind, path = job
        try:
            if kind == 'image':
                self._process_image(path)
            elif kind == 'thumb':
                self._process_thumb(path)
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
        with self._lock:
            self._sources[display] = src
        self._add_display(display)
        with self._lock:
            self._check_thumb(display)

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
        for cb in listeners:
            try:
                cb(display)
            except Exception as e:
                print(f"通知 listener 失敗: {e}")

    # --- 公開 API -----------------------------------------------------------

    def get_image_files(self):
        """獲取圖片檔案列表，使用緩存避免重複處理"""
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
        """根據顯示路徑獲取原圖路徑"""
        with self._lock:
            return self._sources.get(display_path, display_path)

    def get_thumbnail(self, display_path):
        """格狀頁用的小縮圖；還沒做好就回傳顯示圖本身"""
        with self._lock:
            return self._thumbs.get(display_path, display_path)

    def add_listener(self, cb):
        """cb(display_path)：背景處理好一張照片時呼叫（在背景執行緒上）"""
        with self._lock:
            self._listeners.append(cb)

    def has_pending_jobs(self):
        with self._lock:
            return bool(self._queue) or self._running_jobs > 0

    def shutdown(self):
        """停止背景工作：目前這一項做完後結束，佇列裡其餘的下次打開相框再做"""
        self._cancel.set()
