# 2026 MQTT 作業：RFID + Node-RED + Python + SQLite IoT 監控系統

## 系統架構

本專案透過 **ESP32 + MFRC522 RFID 讀卡機**，結合 **MQTT 通訊協定**，實現兩套即時監控介面：

```
                        broker.mqtt-dashboard.com (MQTT Broker)
                                    │
        ┌──────── 發布/訂閱 ────────┼──────── 發布/訂閱 ────────┐
        ▼                           │                           ▼
 ESP32 + MFRC522                    │                  Python Tkinter 應用
 (RFID 刷卡 + LED)                  │                 2026_MQTT_RFID_Monitor.py
                                    │                           │
                                    ▼                           ▼
                            Node-RED Dashboard              SQLite DB
                           (nodered_flows.json)          202603LED.db
                                    │                    202603RFID.db
                                    ▼
                                SQLite DB
                             202603LED.db
                             202603RFID.db
```

### 三大組件說明

| 組件 | 說明 |
|------|------|
| **ESP32 (Arduino)** | 透過 MFRC522 讀取 RFID 卡片 UID，**發布 (Publish)** 至 MQTT Broker；同時 **訂閱 (Subscribe)** LED 控制指令，執行 ON/OFF/FLASH/TIMER 等動作，並回報 LED 狀態 |
| **Python + Tkinter** | 桌面 GUI 監控程式，訂閱 MQTT 取得即時 RFID 刷卡與 LED 狀態，寫入本地 **SQLite 資料庫 (.db)** 儲存歷史紀錄 |
| **Node-RED Dashboard** | 瀏覽器本地端監控介面，訂閱 MQTT 即時顯示數據，透過 **SQLite node** 讀寫本地資料庫，提供建立/查詢/清除/刪除/匯出等完整資料庫操作 |

---

## MQTT Topics

| Topic | 方向 | 說明 |
|-------|------|------|
| `test/rfid/UID` | ESP32 → PC | RFID 卡片 UID |
| `test/led/control` | PC → ESP32 | LED 控制指令 (on/off/flash/timer) |
| `test/led/status` | ESP32 → PC | LED 狀態回報 |

> **Broker:** `broker.mqtt-dashboard.com:1883`（公開測試用 Broker，無需帳號密碼）

---

## 資料庫結構

### 202603LED.db → LED_LOG

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵 (自動遞增) |
| status | TEXT | LED 狀態 (on/off/flash/timer) |
| date | TEXT | 日期 YYYY/MM/DD |
| time | TEXT | 時間 HH:MM:SS |

### 202603RFID.db → RFID_LOG

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵 (自動遞增) |
| uid | TEXT | RFID 卡片 UID |
| date | TEXT | 日期 YYYY/MM/DD |
| time | TEXT | 時間 HH:MM:SS |
| remark | TEXT | 備註（超過異常判定時間則標記「異常」） |

---

## Node-RED Dashboard 功能

三個頁面：**資料管理首頁** / **LED紀錄** / **刷卡紀錄**

### 資料管理首頁
- 頁面導覽（LED 紀錄 / 刷卡紀錄）
- LED 控制按鈕（ON / OFF / TIMER / FLASH）+ 語音播報
- 即時顯示目前 UID 卡號與 LED 狀態

### LED紀錄 / 刷卡紀錄
| 按鈕 | 功能 |
|------|------|
| 建立資料庫 | CREATE TABLE — 建立資料表（.db 不存在時自動產生） |
| 查詢所有資料 | SELECT * — 顯示所有歷史紀錄（支援欄位排序） |
| 清除資料庫內容 | 清除 Dashboard UI 畫面顯示（不影響 .db 檔案） |
| 刪除資料庫 | DROP TABLE — 刪除資料表結構與所有資料 |
| 匯出報表 | 產生 Excel (.xlsx) 報表，包含 LED 與 RFID 兩個工作表 |

### 刷卡紀錄特有功能
- **異常判定時間設定**：可設定時/分，超過該時間刷卡自動在備註欄標記「異常」
- 設定值儲存於 `rfid_config.json`，Node-RED 重啟後自動載入

---

## 安裝步驟

### 1. Python 環境

```bash
pip install paho-mqtt pandas pyttsx3 openpyxl
python 2026_MQTT_RFID_Monitor.py
```

### 2. Node-RED

```bash
# 安裝 Node.js LTS (https://nodejs.org)
npm install -g --unsafe-perm node-red
node-red
```

在 Node-RED 管理面板安裝套件（Manage Palette）：
- `node-red-dashboard` (v3.6.6)
- `node-red-node-sqlite` (v2.0.0)

匯入方式 **擇一**：
- **方式 A**：執行 `python gen_flows.py` 產生 `nodered_flows.json`，再透過 Node-RED 選單 → Import 匯入
- **方式 B**：直接複製 `nodered_flows.json` 到 `~/.node-red/flows.json`，重啟 Node-RED

Dashboard 網址：http://localhost:1880/ui

### 3. ESP32 硬體

**接線：**

| 元件 | ESP32 腳位 |
|------|-----------|
| RFID SDA (SS) | GPIO 5 |
| RFID RST | GPIO 22 |
| LED | GPIO 2 (內建) |
| LCD SDA | GPIO 17 |
| LCD SCL | GPIO 16 |

**需安裝 Arduino 函式庫：**
- MFRC522
- PubSubClient
- LiquidCrystal_I2C

燒錄 `ESP32_RFID_MQTT/ESP32_RFID_MQTT.ino` 至 ESP32

---

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `ESP32_RFID_MQTT/ESP32_RFID_MQTT.ino` | ESP32 Arduino 韌體（RFID 讀卡 + MQTT 發布/訂閱 + LED 控制） |
| `2026_MQTT_RFID_Monitor.py` | Python Tkinter 桌面監控程式（MQTT + SQLite） |
| `gen_flows.py` | Node-RED flows 產生器（Python 腳本，產生 nodered_flows.json） |
| `nodered_flows.json` | Node-RED flows 設定檔（由 gen_flows.py 產生） |
| `export_report.py` | Excel 報表匯出腳本（LED + RFID 雙工作表） |

> `.db` 檔案、`.xlsx` 報表、`rfid_config.json` 設定檔皆為程式執行時動態產生，不包含在版本控制中。
