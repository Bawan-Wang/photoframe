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
- 安裝完成後，縮圖功能會自動啟用，大圖片會自動創建縮圖以提高載入速度
