# Raspberry Pi 環境安裝說明

## 相依安裝方式

本專案**不使用 `pip` / `requirements.txt`**。在 Raspberry Pi OS 上，Pillow 與
Kivy 都由系統套件庫提供，用 `apt` 安裝才能拿到對應這台機器的預編譯版本；用
`pip` 反而可能就地編譯或裝到與系統 Kivy 衝突的版本。

因此請照下面的步驟逐一用 `apt` 安裝。

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

### 3. 安裝其他依賴

```bash
# 安裝 Python 套件管理工具
sudo apt install python3-pip python3-setuptools
```

### 4. HEIC 照片與測試工具

```bash
# heif-convert：讀取 iPhone 的 HEIC 照片（bookworm 的 apt 沒有 pillow_heif）
# python3-pytest：執行 tests/
sudo apt install libheif-examples python3-pytest
```

沒裝 `libheif-examples` 時相框照常運作，只是 HEIC 照片會被略過並印 log。

> **OTA 不會安裝 apt 套件。** `rabbitctl.sh update` 只替換檔案並執行 `pip install`，
> 已經出貨的裝置要手動執行上面的 `apt install`。

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

## 測試

```bash
cd photoframe && python3 -m pytest -q tests
```

測試不依賴 Kivy；HEIC 測試在沒有 `heif-convert` 時會略過。
