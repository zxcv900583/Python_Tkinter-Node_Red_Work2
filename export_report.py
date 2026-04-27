"""
export_report.py - 由 Node-RED exec 節點呼叫，匯出 LED + RFID 報表
"""
import sqlite3
import pandas as pd
import sys
import os
from datetime import datetime

DB_LED   = "D:/MQTT作業2/202603LED.db"
DB_RFID  = "D:/MQTT作業2/202603RFID.db"
OUT_DIR  = "D:/MQTT作業2"

try:
    conn_led  = sqlite3.connect(DB_LED)
    conn_rfid = sqlite3.connect(DB_RFID)

    try:
        df_led = pd.read_sql_query(
            "SELECT * FROM LED_LOG ORDER BY id DESC", conn_led)
    except Exception:
        df_led = pd.DataFrame(columns=["id", "status", "date", "time"])

    try:
        df_rfid = pd.read_sql_query(
            "SELECT * FROM RFID_LOG ORDER BY id DESC", conn_rfid)
    except Exception:
        df_rfid = pd.DataFrame(columns=["id", "uid", "date", "time", "remark"])

    conn_led.close()
    conn_rfid.close()

    fname = os.path.join(
        OUT_DIR,
        f"RFID_Report_{datetime.now().strftime('%m%d_%H%M')}.xlsx"
    )

    with pd.ExcelWriter(fname, engine="openpyxl") as writer:
        df_led.to_excel(writer,  sheet_name="LED紀錄",  index=False)
        df_rfid.to_excel(writer, sheet_name="刷卡紀錄", index=False)

    print(
        f"匯出成功：{fname}  "
        f"LED:{len(df_led)} 筆  "
        f"刷卡:{len(df_rfid)} 筆"
    )

except Exception as e:
    print(f"匯出失敗：{e}", file=sys.stderr)
    sys.exit(1)
