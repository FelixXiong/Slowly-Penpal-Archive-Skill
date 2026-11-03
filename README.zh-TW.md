# Slowly-Penpal-Archive-Skill

[简体中文](README.md) | [English](README.en.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [العربية](README.ar.md)

## 起源
> 用心封存每一段筆友關係。

有些通信漸漸停下，有些筆友需要告別。

但清理筆友名單之前，我們仍想留下那些認真寫過、收到過的信。

下載所有 PDF 之後，該如何整理，並重新閱讀每一封信、回顧每一段筆友關係？

使用 Slowly App 的朋友都知道，若沒有 Plus，我們只有 100 個筆友名額。如果曾訂閱 Slowly Plus，到期後不打算續訂，就可能需要清理筆友名單。

於是我製作了這個 skill。

本 skill：
1. 不會代替使用者下載網頁上的信件。
2. 將你儲存的信件整理成可以搜尋、翻閱的本機檔案館，讓每一段通信都有地方安放。

目前僅針對 Slowly 進行歸檔，其他可匯出信件 PDF 的 App 尚未測試，歡迎嘗試並在 Issues 區提供回饋。

## 使用前準備
進入 Slowly 網頁版，先自行將筆友的信件儲存為 PDF，每位筆友放在獨立資料夾中，例如：

```text
信件目錄/
└── 某位筆友/
    ├── Slowly.pdf
    ├── Slowly2.pdf
    ├── 郵票/
    │   ├── 郵票一.png
    │   └── 郵票二.png
    └── 個人資料/
        └── 頭像.png
```

註：手動匯出檔案的實際相容性，需要自行驗證。

## 流程
儲存信件 PDF → 依筆友建立資料夾（同一位筆友的多封信放在一起）→ 選用：請 AI 協助統一檔名 → 讓 skill 產生檔案館 → 開啟閱讀。

## 開始使用
1. 解壓縮 skill ZIP，將整個 `slowly-offline-archive` 資料夾放到工具設定的 skills 目錄，或使用工具提供的本機技能匯入功能。請保留 `SKILL.md` 與 `scripts/`，不要只複製單一 Markdown 檔案。
2. 對支援 Skills 的辦公工具（WorkBuddy、千问办公或豆包工作）或 IDE 說：

> 使用 slowly-offline-archive（Slowly 離線歸檔技能），將（你的信件儲存路徑）裡的 PDF 整理成離線檔案館，保留原始檔案，完成後幫我開啟入口。

追加信件：

> 使用 Slowly 離線歸檔 skill，資料目錄是（你的信件儲存路徑），將新信追加到現有檔案館。

首次執行仍需要可執行 Python 的宿主環境；若缺少 `pypdf`，AI 會依該環境允許的方式處理。

首次取得相依套件可能需要連網，歸檔與閱讀流程不會存取 Slowly。

產生後，開啟本機 `index.html` 即可閱讀，之後不需要讓 AI 或本機服務持續執行。

## 產生結果

| 檔案 | 用途 |
| --- | --- |
| `index.html` | 可直接開啟的離線檔案館 |
| `slowly_pdf.db` | 信件資料庫 |
| `letters.jsonl` | 結構化信件紀錄 |
| `build.json` | 匯入統計、失敗紀錄與待確認數量 |
| `media.json` | 本機圖文及關聯索引 |

## 效果
「筆友檔案館」預覽：

<img width="1440" height="1000" alt="信件清單" src="https://github.com/user-attachments/assets/a36b1725-bb47-465f-8345-772511a49c02" />
<img width="1920" height="1080" alt="筆友檔案館預覽二" src="https://github.com/user-attachments/assets/c26fa704-91a7-432c-af86-03447fffb644" />
<img width="1920" height="1080" alt="筆友檔案館預覽三" src="https://github.com/user-attachments/assets/195632ad-4681-450e-9e95-f1b345cd3767" />

## 資料安全
本 skill 本身不連網、不自動操作 Slowly 網頁、不讀取登入狀態，也不需要登入 Slowly。它只讀取你已儲存的「信件 PDF」，透過 `pypdf` 還原內文，產生可搜尋的 SQLite 資料庫，以及單一檔案、內嵌資料、按兩下即可開啟的網頁檔案館。

相依套件：`pypdf`。首次安裝需要連網下載。

## 常見問題
**Q：更換信件目錄時該怎麼辦？**

A：回到 IDE／WorkBuddy，告訴 AI 新路徑，重新產生即可。

## 贊助
<img width="1920" height="1080" alt="贊助此專案" src="https://github.com/user-attachments/assets/b84194e5-e9d3-4149-81ae-f9d664d9f813" />
