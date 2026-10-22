# Raspberry Pi 環境安裝說明

## 相依安裝方式

本專案**不使用 `pip` / `requirements.txt`**。在 Raspberry Pi OS 上，Pillow 與
Kivy 都由系統套件庫提供，用 `apt` 安裝才能拿到對應這台機器的預編譯版本；用
`pip` 反而可能就地編譯或裝到與系統 Kivy 衝突的版本。

因此請照下面的步驟逐一用 `apt` 安裝。

> **在 digitalassist 中使用時（`photoframe/` submodule）**，以上層 repo 的
> `system-packages.txt` 為準，在上層目錄執行 `./rabbitctl.sh deps`（開發機加 `--dev`）
> 一次裝齊，不必照下面逐段安裝。下面的步驟是單獨使用 photoframe 時用的。

### 1. 安裝 Pillow (Python Imaging Library)

```bash
# 更新套件列表
sudo apt update

# 安裝 Pillow
sudo apt install python3-pil python3-pil.imagetk
```

### 2. 檢查 Kivy 安裝

```bash
# 檢查 Kivy 是否已安裝
python3 -c "import kivy"

# 如果沒有安裝，使用以下命令安裝
sudo apt install python3-kivy
```

### 3. HEIC 照片與測試工具

```bash
# heif-convert：讀取 iPhone 的 HEIC 照片（bookworm 的 apt 沒有 pillow_heif）
# python3-pytest：執行 tests/
sudo apt install libheif-examples python3-pytest
```

沒裝 `libheif-examples` 時相框照常運作，只是 HEIC 照片會被略過並印 log。

### 4. 影片播放與轉檔

```bash
# ffmpeg／ffprobe：判斷影片格式、轉檔、抽封面
# gstreamer：Kivy 的影片播放（video provider 為 gstplayer）
sudo apt install ffmpeg \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad gstreamer1.0-libav
```

沒裝 ffmpeg 時影片直接用原檔播放，不判斷、不轉檔；播不動的影片會在 10 秒後被跳過。

> **OTA 不會安裝 apt 套件。** `rabbitctl.sh update` 只替換檔案並執行 `pip install`，
> 已經出貨的裝置要在上層目錄手動執行 `./rabbitctl.sh deps`；`./rabbitctl.sh deps --check`
> 不需要 root，會列出缺少的套件。

## 驗證安裝

安裝完成後，使用以下命令驗證：

```bash
# 檢查 Pillow
python3 -c "from PIL import Image; print('Pillow 安裝成功')"

# 檢查 Kivy
python3 -c "import kivy; print('Kivy 安裝成功')"
```

## 注意事項

- 在 Raspberry Pi 環境下，建議使用 `apt` 而不是 `pip` 來安裝套件。
  repo 內刻意**沒有** `requirements.txt`——避免有人（或 CI）看到檔名就去
  `pip install -r`，拿到空結果卻以為相依已經滿足
- 如果遇到權限問題，請確保使用 `sudo`

## 照片快取

- 快取放在隨身碟根目錄的 `thumbnails/v2/`（沒插隨身碟時是 `photoframe/thumbnails/v2/`）：
  - `<原檔名>.jpg`：顯示用，已依 EXIF 轉正，最大 1920×1080，只縮不放
  - `<原檔名>.thumb.jpg`：播放清單頁的小縮圖（360×360 以內）
  - `<原檔名>.failed`：處理失敗的標記，來源檔沒換就不再重試；刪掉這個檔案就會重試
- 快取比原檔新就直接沿用；原檔被換掉（修改時間變新）會自動重做
- 打開相框時只檢查快取，需要處理的照片在背景做，處理好一張就加進輪播
- 舊版留下的 `thumbnails/` 根目錄下的檔案（不在 `v2/` 裡的）已不再使用，可以刪除
- GIF 直接用原檔（保留動畫）

## 影片

- 支援 `.mp4 .mov .m4v .avi .mkv .3gp .mts .webm`；自動播放遇到影片會等它播完才切換
- Raspberry Pi 5 沒有 H.264 硬體解碼，實測 1080p 只有約 20 fps、720p 約 27 fps，因此影片以短邊 720 為上限：
  - H.264、短邊 ≤ 720、≤ 30 fps、沒有旋轉標記：直接播放原檔
  - H.264 但比較大（例如 iPhone 1080p）：**先播原檔**，同時在背景轉成 720p，轉好後自動換成轉檔版本
  - 其他（HEVC、帶旋轉標記、pcm 音訊等）：背景轉檔，轉好才出現在輪播裡
- 轉檔只在相框開著時進行，1 分鐘的 1080p 影片大約要轉 1.3 分鐘；關掉相框會中止，下次打開重轉
- 與照片同名的影片（iPhone 原況照片的 `IMG_x.MOV`）會被略過
- 快取（同在 `thumbnails/v2/`）：
  - `<原檔名>.mp4`：轉檔結果
  - `<原檔名>.poster.jpg`：封面（播放前的預覽與播放清單頁的縮圖）
  - `<原檔名>.failed`：讀不了也轉不了，整支略過；`<原檔名>.transcode-failed`：原檔能播但轉檔失敗，繼續播原檔
  - 轉檔結果需要隨身碟上有空間（大約是原影片的 1/5 到 1/2）
- 影片預設**靜音**（`ui/slide_page.py` 的 `VIDEO_VOLUME = 0`）：麥克風與喇叭是同一個 USB 裝置，影片有聲音時
  語音助理幾乎聽不到喚醒詞。要讓影片有聲音，需先做回音消除（尚未實作）

## 測試

```bash
cd photoframe && python3 -m pytest -q tests
```

測試不依賴 Kivy；HEIC 測試在沒有 `heif-convert` 時會略過。
