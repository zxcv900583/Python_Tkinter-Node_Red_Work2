import tkinter as tk

from tkinter import messagebox, ttk, simpledialog

import paho.mqtt.client as mqtt

import sqlite3

import pandas as pd

import pyttsx3

import threading

from datetime import datetime



# --- 設定區 ---

MQTT_SERVER = "broker.mqtt-dashboard.com"

TOPIC_RFID_UID = "test/rfid/UID"

TOPIC_LED_CONTROL = "test/led/control"

TOPIC_LED_STATUS = "test/led/status"



DB_LED = "202603LED.db"

DB_RFID = "202603RFID.db"



# --- 語音功能 ---

def speak(text):

    def _run_speak():

        try:

            engine = pyttsx3.init()

            engine.setProperty('rate', 150)

            voices = engine.getProperty('voices')

            for voice in voices:

                if "Chinese" in voice.name or "ZH-TW" in voice.id:

                    engine.setProperty('voice', voice.id)

                    break

            engine.say(text)

            engine.runAndWait()

        except:

            pass

    threading.Thread(target=_run_speak, daemon=True).start()



# --- 資料庫初始化 ---

def init_dbs():

    conn_led = sqlite3.connect(DB_LED)

    conn_led.execute('''CREATE TABLE IF NOT EXISTS LED_LOG 

                     (id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT, date TEXT, time TEXT)''')

    conn_led.close()

    

    conn_rfid = sqlite3.connect(DB_RFID)

    conn_rfid.execute('''CREATE TABLE IF NOT EXISTS RFID_LOG
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, date TEXT, time TEXT, remark TEXT DEFAULT '')''')

    conn_rfid.close()



# --- MQTT 邏輯 ---

def on_connect(client, userdata, flags, rc, properties=None):

    if rc == 0:

        app.set_connection_status(True)

        client.subscribe([(TOPIC_RFID_UID, 0), (TOPIC_LED_STATUS, 0)])

    else:

        app.set_connection_status(False)



def on_message(client, userdata, msg):

    topic = msg.topic

    payload = msg.payload.decode()

    now = datetime.now()

    

    if topic == TOPIC_LED_STATUS:

        conn = sqlite3.connect(DB_LED)

        conn.execute("INSERT INTO LED_LOG (status, date, time) VALUES (?, ?, ?)",

                     (payload, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")))

        conn.commit()

        conn.close()

        speak(f"LED 狀態更新為 {payload}")

        root.after(0, lambda: app.update_table("LED"))

        

    elif topic == TOPIC_RFID_UID:

        conn = sqlite3.connect(DB_RFID)

        conn.execute("INSERT INTO RFID_LOG (uid, date, time) VALUES (?, ?, ?)",

                      (payload, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")))

        conn.commit()

        conn.close()

        speak(f"偵測到卡片，末四位 {payload[-4:]}")

        root.after(0, lambda: app.update_table("RFID"))



# --- GUI 介面 ---

class MQTTApp:

    def __init__(self, root):

        self.root = root

        self.root.title("2026 MQTT RFID 專業監控系統")

        self.root.geometry("900x700")



        # 狀態燈區

        status_frame = tk.Frame(root)

        status_frame.pack(side="top", fill="x", padx=10, pady=5)

        self.canvas = tk.Canvas(status_frame, width=20, height=20)

        self.canvas.pack(side="left")

        self.status_light = self.canvas.create_oval(2, 2, 18, 18, fill="red")

        self.status_text = tk.Label(status_frame, text="嘗試連線中...", fg="red")

        self.status_text.pack(side="left", padx=5)



        # 控制面板

        ctrl_frame = tk.LabelFrame(root, text="遠端指令控制")

        ctrl_frame.pack(pady=5, padx=10, fill="x")

        btns = [("LED ON", "#4CAF50", "on"), ("LED OFF", "#F44336", "off"), 

                ("閃爍", "#FFEB3B", "flash"), ("計時", "#2196F3", "timer")]

        for i, (txt, clr, cmd) in enumerate(btns):

            tk.Button(ctrl_frame, text=txt, bg=clr, width=12, 

                      command=lambda c=cmd: self.send_cmd(c)).grid(row=0, column=i, padx=20, pady=10)



        # 分頁系統

        notebook = ttk.Notebook(root)

        notebook.pack(pady=5, padx=10, expand=True, fill="both")



        self.led_frame = ttk.Frame(notebook)

        self.rfid_frame = ttk.Frame(notebook)

        notebook.add(self.led_frame, text=" LED 歷史紀錄 ")

        notebook.add(self.rfid_frame, text=" RFID 刷卡資料庫 ")



        self.setup_db_ui(self.led_frame, "LED")

        self.setup_db_ui(self.rfid_frame, "RFID")



    def setup_db_ui(self, frame, db_type):

        cols = ('ID', '內容資料', '日期', '時間')

        tree = ttk.Treeview(frame, columns=cols, show='headings')

        for col in cols: tree.heading(col, text=col)

        tree.column('ID', width=50, anchor='center')

        

        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)

        tree.configure(yscrollcommand=scroll.set)

        tree.pack(side="left", fill="both", expand=True)

        scroll.pack(side="right", fill="y")

        

        if db_type == "LED": 

            self.led_tree = tree

            tree.tag_configure('on_tag', background='#E8F5E9')

            tree.tag_configure('off_tag', background='#FFEBEE')

        else: 

            self.rfid_tree = tree

            tree.tag_configure('stripe', background='#F2F2F2')



        # 右側管理按鈕

        btn_frame = tk.Frame(frame)

        btn_frame.pack(side="right", padx=10)

        tk.Button(btn_frame, text="搜尋 ID", width=12, command=lambda: self.query_data(db_type)).pack(pady=5)

        tk.Button(btn_frame, text="匯出 Excel", bg="#2196F3", fg="white", width=12, command=lambda: self.export_excel(db_type)).pack(pady=5)

        tk.Button(btn_frame, text="清空資料", bg="#FF9800", fg="white", width=12, command=lambda: self.clear_all(db_type)).pack(pady=5)



    def set_connection_status(self, connected):

        color = "#4CAF50" if connected else "#F44336"

        self.canvas.itemconfig(self.status_light, fill=color)

        self.status_text.config(text="連線正常" if connected else "連線中斷", fg=color)



    def send_cmd(self, cmd):

        client.publish(TOPIC_LED_CONTROL, cmd)

        speak(f"發送{cmd}")



    def update_table(self, db_type):

        db_file, tree, table = (DB_LED, self.led_tree, "LED_LOG") if db_type == "LED" else (DB_RFID, self.rfid_tree, "RFID_LOG")

        for row in tree.get_children(): tree.delete(row)

        conn = sqlite3.connect(db_file)

        rows = conn.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT 50").fetchall()

        for i, row in enumerate(rows):

            tag = ''

            if db_type == "LED":

                if "on" in str(row[1]).lower(): tag = 'on_tag'

                elif "off" in str(row[1]).lower(): tag = 'off_tag'

            else:

                if i % 2 == 0: tag = 'stripe'

            tree.insert("", "end", values=row, tags=(tag,))

        conn.close()



    def export_excel(self, db_type):

        db_file, table = (DB_LED, "LED_LOG") if db_type == "LED" else (DB_RFID, "RFID_LOG")

        conn = sqlite3.connect(db_file)

        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)

        conn.close()

        if not df.empty:

            fname = f"{table}_{datetime.now().strftime('%m%d_%H%M')}.xlsx"

            df.to_excel(fname, index=False)

            messagebox.showinfo("成功", f"匯出至 {fname}")

            speak("匯出完成")

        else:

            messagebox.showwarning("提示", "無資料可匯出")



    def query_data(self, db_type):

        q_id = simpledialog.askinteger("搜尋", "輸入搜尋 ID:")

        if q_id:

            db_file, table = (DB_LED, "LED_LOG") if db_type == "LED" else (DB_RFID, "RFID_LOG")

            conn = sqlite3.connect(db_file)

            res = conn.execute(f"SELECT * FROM {table} WHERE id=?", (q_id,)).fetchone()

            conn.close()

            if res: messagebox.showinfo("查詢結果", f"內容: {res[1]}\n日期: {res[2]}\n時間: {res[3]}")

            else: messagebox.showwarning("失敗", "找不到此 ID")



    def clear_all(self, db_type):

        if messagebox.askyesno("警告", "確定要清空所有紀錄？"):

            db_file, table = (DB_LED, "LED_LOG") if db_type == "LED" else (DB_RFID, "RFID_LOG")

            conn = sqlite3.connect(db_file)

            conn.execute(f"DELETE FROM {table}")

            conn.commit()

            conn.close()

            self.update_table(db_type)

            speak("資料已清空")



# --- 啟動 ---

if __name__ == "__main__":

    init_dbs()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    client.on_connect = on_connect

    client.on_message = on_message

    

    def mqtt_loop():

        while True:

            try:

                client.connect(MQTT_SERVER, 1883, 60)

                client.loop_forever()

            except:

                threading.Event().wait(5)



    threading.Thread(target=mqtt_loop, daemon=True).start()

    root = tk.Tk()

    app = MQTTApp(root)

    app.update_table("LED")

    app.update_table("RFID")

    root.mainloop()