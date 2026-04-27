"""
gen_flows.py - Node-RED flows 產生器
名稱：資料管理首頁 / LED紀錄 / 刷卡紀錄
Topics: test/led/control | test/led/status | test/rfid/UID
功能：排序 / 確認對話框 / 自動刷新 / 備註(異常) / 設定時間
"""
import json, sqlite3

DB_LED    = "D:/MQTT作業2/202603LED.db"
DB_RFID   = "D:/MQTT作業2/202603RFID.db"
EXPORT_PY = "D:/MQTT作業2/export_report.py"
CONFIG_FILE = "D:/MQTT作業2/rfid_config.json"

# ── 表頭樣式 ──────────────────────────────────────────────────────────────────
TH = "padding:10px 14px;text-align:center;cursor:pointer;user-select:none;white-space:nowrap"

# ── LED 資料表模板（含排序）────────────────────────────────────────────────────
LED_TMPL = """\
<div style="overflow-x:auto;padding:4px" ng-init="sc='id';sd=true">
  <table style="width:100%;border-collapse:collapse;font-size:13px;
                box-shadow:0 1px 4px rgba(0,0,0,.15)">
    <thead>
      <tr style="background:#1565C0;color:#fff">
        <th ng-click="sc='id';sd=!sd"     style="{TH}">ID     <span ng-show="sc=='id'"    >{{sd?'▼':'▲'}}</span></th>
        <th ng-click="sc='status';sd=!sd" style="{TH}">狀態   <span ng-show="sc=='status'">{{sd?'▼':'▲'}}</span></th>
        <th ng-click="sc='date';sd=!sd"   style="{TH}">日期   <span ng-show="sc=='date'"  >{{sd?'▼':'▲'}}</span></th>
        <th ng-click="sc='time';sd=!sd"   style="{TH}">時間   <span ng-show="sc=='time'"  >{{sd?'▼':'▲'}}</span></th>
      </tr>
    </thead>
    <tbody ng-if="msg.payload && msg.payload.length > 0">
      <tr ng-repeat="r in msg.payload | orderBy:sc:sd track by $index"
          ng-style="{background:
            r.status && r.status.toUpperCase().indexOf('ON')  !== -1 ? '#E8F5E9' :
            r.status && r.status.toUpperCase().indexOf('OFF') !== -1 ? '#FFEBEE' :
            $index%2===0 ? '#fafafa' : '#fff'}">
        <td style="padding:8px 14px;text-align:center;border-bottom:1px solid #e0e0e0">{{r.id}}</td>
        <td style="padding:8px 14px;text-align:center;border-bottom:1px solid #e0e0e0;font-weight:bold">{{r.status}}</td>
        <td style="padding:8px 14px;text-align:center;border-bottom:1px solid #e0e0e0">{{r.date}}</td>
        <td style="padding:8px 14px;text-align:center;border-bottom:1px solid #e0e0e0">{{r.time}}</td>
      </tr>
    </tbody>
    <tbody ng-if="!msg.payload || msg.payload.length===0">
      <tr><td colspan="4" style="text-align:center;padding:30px;color:#bbb;font-size:14px">（尚無資料）</td></tr>
    </tbody>
  </table>
</div>""".replace("{TH}", TH)

# ── RFID 資料表模板（含排序 + 備註欄）────────────────────────────────────────
RFID_TMPL = """\
<div style="overflow-x:auto;padding:4px" ng-init="sc='id';sd=true">
  <table style="width:100%;border-collapse:collapse;font-size:13px;
                box-shadow:0 1px 4px rgba(0,0,0,.15)">
    <thead>
      <tr style="background:#2E7D32;color:#fff">
        <th ng-click="sc='id';sd=!sd"     style="{TH}">ID   <span ng-show="sc=='id'"    >{{sd?'▼':'▲'}}</span></th>
        <th ng-click="sc='uid';sd=!sd"    style="{TH}">UID  <span ng-show="sc=='uid'"   >{{sd?'▼':'▲'}}</span></th>
        <th ng-click="sc='date';sd=!sd"   style="{TH}">日期 <span ng-show="sc=='date'"  >{{sd?'▼':'▲'}}</span></th>
        <th ng-click="sc='time';sd=!sd"   style="{TH}">時間 <span ng-show="sc=='time'"  >{{sd?'▼':'▲'}}</span></th>
        <th ng-click="sc='remark';sd=!sd" style="{TH}">備註 <span ng-show="sc=='remark'">{{sd?'▼':'▲'}}</span></th>
      </tr>
    </thead>
    <tbody ng-if="msg.payload && msg.payload.length > 0">
      <tr ng-repeat="r in msg.payload | orderBy:sc:sd track by $index"
          ng-style="{background: r.remark==='異常' ? '#FFF3E0' : ($index%2===0 ? '#fafafa' : '#fff')}">
        <td style="padding:8px 14px;text-align:center;border-bottom:1px solid #e0e0e0">{{r.id}}</td>
        <td style="padding:8px 14px;text-align:center;border-bottom:1px solid #e0e0e0;font-family:monospace;font-weight:bold">{{r.uid}}</td>
        <td style="padding:8px 14px;text-align:center;border-bottom:1px solid #e0e0e0">{{r.date}}</td>
        <td style="padding:8px 14px;text-align:center;border-bottom:1px solid #e0e0e0">{{r.time}}</td>
        <td ng-style="{color: r.remark==='異常' ? '#F44336' : '#333', fontWeight: r.remark==='異常' ? 'bold' : 'normal'}"
            style="padding:8px 14px;text-align:center;border-bottom:1px solid #e0e0e0">{{r.remark}}</td>
      </tr>
    </tbody>
    <tbody ng-if="!msg.payload || msg.payload.length===0">
      <tr><td colspan="5" style="text-align:center;padding:30px;color:#bbb;font-size:14px">（尚無資料）</td></tr>
    </tbody>
  </table>
</div>""".replace("{TH}", TH)

# ── 設定時間模板（下拉選單：時/分）─────────────────────────────────────────
TIME_TMPL = """\
<div style="padding:10px 4px">
  <div style="display:flex;align-items:center;gap:10px;font-size:16px;flex-wrap:wrap">
    <span style="font-weight:bold;color:#333">異常判定時間：</span>
    <select ng-model="selH" ng-change="update()"
            style="font-size:16px;padding:5px 8px;border-radius:4px;border:1px solid #bbb;
                   min-width:65px;text-align:center">
      <option ng-repeat="h in hours track by $index" value="{{h}}">{{h < 10 ? '0'+h : h}}</option>
    </select>
    <span>時</span>
    <select ng-model="selM" ng-change="update()"
            style="font-size:16px;padding:5px 8px;border-radius:4px;border:1px solid #bbb;
                   min-width:65px;text-align:center">
      <option ng-repeat="m in mins track by $index" value="{{m}}">{{m < 10 ? '0'+m : m}}</option>
    </select>
    <span>分</span>
    <span ng-if="saved" style="color:#4CAF50;font-size:14px;margin-left:8px;font-weight:bold">已儲存</span>
  </div>
  <div style="margin-top:8px;color:#999;font-size:12px">
    超過此時間刷卡，備註欄將標記「異常」（設為 00:00 則不判定）
  </div>
</div>
<script>
(function(scope) {
  scope.hours = [];
  for (var i = 0; i < 24; i++) scope.hours.push(i);
  scope.mins = [];
  for (var i = 0; i < 60; i++) scope.mins.push(i);
  scope.selH = '0';
  scope.selM = '0';
  scope.saved = false;
  scope.update = function() {
    scope.send({payload: {hour: parseInt(scope.selH), min: parseInt(scope.selM)}});
    scope.saved = true;
    if (scope._st) clearTimeout(scope._st);
    scope._st = setTimeout(function() {
      scope.$apply(function() { scope.saved = false; });
    }, 2000);
  };
  scope.$watch('msg', function(msg) {
    if (msg && msg.payload && msg.payload.hour !== undefined) {
      scope.selH = String(msg.payload.hour);
      scope.selM = String(msg.payload.min);
    }
  });
})(scope);
</script>"""

# ── JS 程式片段 ──────────────────────────────────────────────────────────────
SET_SQL = "msg.topic = msg.payload;\nmsg.params = [];\nreturn msg;"

# 確認對話框回應（output1=確定, output2=取消）
OK_CANCEL = (
    "var t = String(msg.payload||'');\n"
    "if(t === 'Cancel' || t === 'NO'){return [null, msg];}\n"
    "return [msg, null];"
)

def insert_ts_led():
    """LED INSERT（無備註）"""
    return (
        "var n=new Date();\n"
        "var d=n.getFullYear()+'/'+(n.getMonth()+1).toString().padStart(2,'0')"
        "+'/'+n.getDate().toString().padStart(2,'0');\n"
        "var t=n.getHours().toString().padStart(2,'0')+':'"
        "+n.getMinutes().toString().padStart(2,'0')+':'"
        "+n.getSeconds().toString().padStart(2,'0');\n"
        "var v=String(msg.payload).replace(/'/g,\"''\");\n"
        "msg.topic=\"INSERT INTO LED_LOG (status, date, time) VALUES ('\" + v + \"', '\" + d + \"', '\" + t + \"')\";\n"
        "msg.params=[];\n"
        "return msg;"
    )

def insert_ts_rfid():
    """RFID INSERT（含備註判定）"""
    return (
        "var n=new Date();\n"
        "var d=n.getFullYear()+'/'+(n.getMonth()+1).toString().padStart(2,'0')"
        "+'/'+n.getDate().toString().padStart(2,'0');\n"
        "var t=n.getHours().toString().padStart(2,'0')+':'"
        "+n.getMinutes().toString().padStart(2,'0')+':'"
        "+n.getSeconds().toString().padStart(2,'0');\n"
        "var v=String(msg.payload).replace(/'/g,\"''\");\n"
        "var th=flow.get('threshold')||{hour:0,min:0};\n"
        "var curM=n.getHours()*60+n.getMinutes();\n"
        "var thM=th.hour*60+th.min;\n"
        "var remark='';\n"
        "if(thM>0 && curM>thM){remark='異常';}\n"
        "msg.topic=\"INSERT INTO RFID_LOG (uid, date, time, remark) VALUES ('\" + v + \"', '\" + d + \"', '\" + t + \"', '\" + remark + \"')\";\n"
        "msg.params=[];\n"
        "return msg;"
    )

def router(label):
    """3 outputs: [0]=array→template [1]=toast [2]=trigger refresh"""
    return (
        "var sql=(msg.topic||'').trim().toUpperCase();\n"
        "var op=sql.split(' ')[0];\n"
        "if(Array.isArray(msg.payload)){return [msg,null,null];}\n"
        "if(op==='INSERT'){return null;}\n"
        "if(op==='DROP'){return [{payload:[]},{payload:'" + label + " 資料表已刪除'},null];}\n"
        "var m={'CREATE':'" + label + " 資料庫建立完成','DELETE':'" + label + " 資料已全部清除'};\n"
        "var txt=m[op]||'操作完成';\n"
        "return [null,{payload:txt},{payload:txt}];"
    )

def auto_select(table):
    return "msg.topic='SELECT * FROM " + table + " ORDER BY id DESC';\nreturn msg;"


# 儲存設定時間
SAVE_TIME = (
    "flow.set('threshold', msg.payload);\n"
    "msg.payload = JSON.stringify(msg.payload);\n"
    "return msg;"
)

# 載入設定時間
LOAD_TIME = (
    "try {\n"
    "  var cfg = JSON.parse(msg.payload);\n"
    "  flow.set('threshold', cfg);\n"
    "  return {payload: cfg};\n"
    "} catch(e) {\n"
    "  flow.set('threshold', {hour:0, min:0});\n"
    "  return {payload: {hour:0, min:0}};\n"
    "}"
)

EXPORT_OK  = "msg.payload=String(msg.payload||'').trim();if(!msg.payload)return null;return msg;"
EXPORT_ERR = "var s=String(msg.payload||'').trim();if(!s)return null;msg.payload='[ERROR] '+s;return msg;"

# ═══════════════════════════════════════════════════════════════════════════════
# Build flows
# ═══════════════════════════════════════════════════════════════════════════════
flows = []

# ── Config nodes ──────────────────────────────────────────────────────────────
flows += [
    {"id":"b9efc827e98bf7f9","type":"mqtt-broker",
     "name":"broker.mqtt-dashboard.com",
     "broker":"broker.mqtt-dashboard.com","port":"1883",
     "clientid":"","autoConnect":True,"usetls":False,
     "protocolVersion":"4","keepalive":"60","cleansession":True,
     "autoUnsubscribe":True,
     "birthTopic":"","birthQos":"0","birthRetain":"false","birthPayload":"","birthMsg":{},
     "closeTopic":"","closeQos":"0","closeRetain":"false","closePayload":"","closeMsg":{},
     "willTopic":"","willQos":"0","willRetain":"false","willPayload":"","willMsg":{},
     "userProps":"","sessionExpiry":""},
    {"id":"db_led",  "type":"sqlitedb","db":DB_LED,  "mode":"RWC"},
    {"id":"db_rfid", "type":"sqlitedb","db":DB_RFID, "mode":"RWC"},
]

# ── Dashboard Tabs ────────────────────────────────────────────────────────────
flows += [
    {"id":"f514574c3ff83395","type":"ui_tab","name":"資料管理首頁",
     "icon":"dashboard","order":1,"disabled":False,"hidden":False},
    {"id":"ui_tab_sub1","type":"ui_tab","name":"LED紀錄",
     "icon":"lightbulb_outline","order":2,"disabled":False,"hidden":False},
    {"id":"ui_tab_sub2","type":"ui_tab","name":"刷卡紀錄",
     "icon":"credit_card","order":3,"disabled":False,"hidden":False},
]

# ── Dashboard Groups ──────────────────────────────────────────────────────────
flows += [
    {"id":"a7f1622545f7e3c5","type":"ui_group","name":"刷卡紀錄與LED控制",
     "tab":"f514574c3ff83395","order":1,"disp":True,"width":"6","collapse":False,"className":""},
    # Sub1
    {"id":"grp_s1_ops", "type":"ui_group","name":"LED 操作",
     "tab":"ui_tab_sub1","order":1,"disp":True,"width":"14","collapse":False},
    {"id":"grp_s1_data","type":"ui_group","name":"LED 資料",
     "tab":"ui_tab_sub1","order":2,"disp":True,"width":"14","collapse":False},
    # Sub2
    {"id":"grp_s2_time","type":"ui_group","name":"異常時間設定",
     "tab":"ui_tab_sub2","order":1,"disp":True,"width":"14","collapse":False},
    {"id":"grp_s2_ops", "type":"ui_group","name":"RFID 操作",
     "tab":"ui_tab_sub2","order":2,"disp":True,"width":"14","collapse":False},
    {"id":"grp_s2_data","type":"ui_group","name":"RFID 資料",
     "tab":"ui_tab_sub2","order":3,"disp":True,"width":"14","collapse":False},
]

# ── Canvas Tabs ───────────────────────────────────────────────────────────────
flows += [
    {"id":"3897cf2f308c39ee","type":"tab","label":"資料管理首頁","disabled":False,"info":""},
    {"id":"tab_sub1","type":"tab","label":"LED紀錄","disabled":False,"info":""},
    {"id":"tab_sub2","type":"tab","label":"刷卡紀錄","disabled":False,"info":""},
]

# ═══════════════════════════════════════════════════════════════════════════════
# 資料管理首頁
# ═══════════════════════════════════════════════════════════════════════════════
Z_HOME = "3897cf2f308c39ee"
G_HOME = "a7f1622545f7e3c5"

flows += [
    # ── 導覽按鈕 ──
    {"id":"d927438ef7105fcb","type":"ui_button","z":Z_HOME,
     "name":"","group":G_HOME,"order":1,"width":3,"height":1,
     "passthru":False,"label":"LED 紀錄","tooltip":"前往 LED 紀錄頁面",
     "color":"white","bgcolor":"#1565C0","className":"","icon":"lightbulb_outline",
     "payload":"","payloadType":"str","topic":"topic","topicType":"msg",
     "x":140,"y":60,"wires":[["fd1d07c6d633f24f"]]},
    {"id":"fd1d07c6d633f24f","type":"function","z":Z_HOME,
     "name":"goto LED紀錄",
     "func":"msg.payload={\"tab\":\"LED紀錄\"};\nreturn msg;",
     "outputs":1,"timeout":0,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":340,"y":60,"wires":[["bd19f4282b1404ac"]]},
    {"id":"bd19f4282b1404ac","type":"ui_ui_control","z":Z_HOME,
     "name":"","events":"all","x":540,"y":80,"wires":[[]]},

    {"id":"f9839196994e4e12","type":"ui_button","z":Z_HOME,
     "name":"","group":G_HOME,"order":2,"width":3,"height":1,
     "passthru":False,"label":"刷卡紀錄","tooltip":"前往刷卡紀錄頁面",
     "color":"white","bgcolor":"#2E7D32","className":"","icon":"credit_card",
     "payload":"","payloadType":"str","topic":"topic","topicType":"msg",
     "x":140,"y":120,"wires":[["5f2de4fb03923e90"]]},
    {"id":"5f2de4fb03923e90","type":"function","z":Z_HOME,
     "name":"goto 刷卡紀錄",
     "func":"msg.payload={\"tab\":\"刷卡紀錄\"};\nreturn msg;",
     "outputs":1,"timeout":0,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":340,"y":120,"wires":[["bd19f4282b1404ac"]]},

    # ── LED 控制按鈕 ──
    {"id":"e6a04ebb7a023bf4","type":"ui_button","z":Z_HOME,
     "name":"","group":G_HOME,"order":4,"width":3,"height":1,
     "passthru":False,"label":"ON","tooltip":"","color":"white","bgcolor":"#43A047",
     "className":"","icon":"","payload":"on","payloadType":"str",
     "topic":"topic","topicType":"msg","x":110,"y":220,
     "wires":[["fbd45b6c63ee72c2","32737c9374bb2e01","38f9ca19329b8265"]]},
    {"id":"ec3ef8fbc2d10ffb","type":"ui_button","z":Z_HOME,
     "name":"","group":G_HOME,"order":5,"width":3,"height":1,
     "passthru":False,"label":"OFF","tooltip":"","color":"white","bgcolor":"#E53935",
     "className":"","icon":"","payload":"off","payloadType":"str",
     "topic":"topic","topicType":"msg","x":110,"y":260,
     "wires":[["fbd45b6c63ee72c2","32737c9374bb2e01","38f9ca19329b8265"]]},
    {"id":"470bd8eb959d0c9c","type":"ui_button","z":Z_HOME,
     "name":"","group":G_HOME,"order":6,"width":3,"height":1,
     "passthru":False,"label":"TIMER","tooltip":"","color":"white","bgcolor":"#FB8C00",
     "className":"","icon":"","payload":"timer","payloadType":"str",
     "topic":"topic","topicType":"msg","x":120,"y":300,
     "wires":[["fbd45b6c63ee72c2","32737c9374bb2e01","38f9ca19329b8265"]]},
    {"id":"0d2a7c475996f588","type":"ui_button","z":Z_HOME,
     "name":"","group":G_HOME,"order":7,"width":3,"height":1,
     "passthru":False,"label":"FLASH","tooltip":"","color":"white","bgcolor":"#8E24AA",
     "className":"","icon":"","payload":"flash","payloadType":"str",
     "topic":"topic","topicType":"msg","x":120,"y":340,
     "wires":[["fbd45b6c63ee72c2","32737c9374bb2e01","38f9ca19329b8265"]]},

    # audio + debug + mqtt out
    {"id":"fbd45b6c63ee72c2","type":"ui_audio","z":Z_HOME,
     "name":"","group":G_HOME,
     "voice":"Microsoft Hanhan - Chinese (Traditional, Taiwan)",
     "always":True,"x":285,"y":220,"wires":[],"l":False},
    {"id":"38f9ca19329b8265","type":"debug","z":Z_HOME,
     "name":"debug","active":True,"tosidebar":True,"console":False,
     "tostatus":False,"complete":"payload","targetType":"msg",
     "statusVal":"","statusType":"auto","x":330,"y":260,"wires":[]},
    {"id":"32737c9374bb2e01","type":"mqtt out","z":Z_HOME,
     "name":"LED Control","topic":"test/led/control",
     "qos":"1","retain":"true","respTopic":"","contentType":"",
     "userProps":"","correl":"","expiry":"",
     "broker":"b9efc827e98bf7f9","x":350,"y":300,"wires":[]},

    # ── MQTT in: RFID UID ──
    {"id":"371fba0e98260ca7","type":"mqtt in","z":Z_HOME,
     "name":"RFID in","topic":"test/rfid/UID",
     "qos":"1","datatype":"auto-detect","broker":"b9efc827e98bf7f9",
     "nl":False,"rap":True,"rh":0,"inputs":0,
     "x":110,"y":440,"wires":[["b8f297adcdfc7fad","a7bdb84c9fe6df8c"]]},
    {"id":"b8f297adcdfc7fad","type":"debug","z":Z_HOME,
     "name":"debug","active":True,"tosidebar":True,"console":False,
     "tostatus":False,"complete":"payload","targetType":"msg",
     "statusVal":"","statusType":"auto","x":250,"y":420,"wires":[]},
    {"id":"a7bdb84c9fe6df8c","type":"ui_text","z":Z_HOME,
     "group":G_HOME,"order":9,"width":0,"height":0,
     "name":"","label":"目前 UID卡號","format":"{{msg.payload}}",
     "layout":"row-left","className":"","style":False,
     "font":"","fontSize":16,"color":"#000000","x":310,"y":460,"wires":[]},

    # ── MQTT in: LED Status（新增）──
    {"id":"home_mqtt_led","type":"mqtt in","z":Z_HOME,
     "name":"LED Status in","topic":"test/led/status",
     "qos":"1","datatype":"auto-detect","broker":"b9efc827e98bf7f9",
     "nl":False,"rap":True,"rh":0,"inputs":0,
     "x":110,"y":520,"wires":[["home_led_text"]]},
    {"id":"home_led_text","type":"ui_text","z":Z_HOME,
     "group":G_HOME,"order":8,"width":0,"height":0,
     "name":"","label":"目前LED狀態","format":"{{msg.payload}}",
     "layout":"row-left","className":"","style":False,
     "font":"","fontSize":16,"color":"#000000","x":310,"y":520,"wires":[]},

    # comment
    {"id":"6ac927abd4f5995a","type":"comment","z":Z_HOME,
     "name":"MQTT Topics: test/rfid/UID, test/led/control, test/led/status",
     "info":"","x":300,"y":180,"wires":[]},
]

# ═══════════════════════════════════════════════════════════════════════════════
# LED紀錄（RFIDSubpage1）
# ═══════════════════════════════════════════════════════════════════════════════
Z_S1 = "tab_sub1"

flows += [
    # ── 回主頁 ──
    {"id":"s1_btn_home","type":"ui_button","z":Z_S1,
     "group":"grp_s1_ops","order":0,"width":2,"height":1,"passthru":False,
     "label":"回主頁","color":"white","bgcolor":"#FF6F00","className":"","icon":"home",
     "payload":"","payloadType":"str","topic":"topic","topicType":"msg",
     "x":100,"y":40,"wires":[["s1_fn_home"]]},
    {"id":"s1_fn_home","type":"function","z":Z_S1,"name":"goto 首頁",
     "func":"msg.payload={\"tab\":\"資料管理首頁\"};\nreturn msg;",
     "outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":280,"y":40,"wires":[["s1_ui_ctrl"]]},
    {"id":"s1_ui_ctrl","type":"ui_ui_control","z":Z_S1,
     "name":"","events":"all","x":460,"y":40,"wires":[[]]},

    # ── 建立資料庫 ──
    {"id":"s1_btn_create","type":"ui_button","z":Z_S1,
     "group":"grp_s1_ops","order":1,"width":3,"height":1,"passthru":False,
     "label":"建立資料庫","color":"white","bgcolor":"#4CAF50","className":"","icon":"",
     "payload":"CREATE TABLE IF NOT EXISTS LED_LOG (id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT, date TEXT, time TEXT)",
     "payloadType":"str","topic":"","topicType":"str",
     "x":120,"y":100,"wires":[["fn_s1_sql"]]},

    # ── 查詢所有資料 ──
    {"id":"s1_btn_select","type":"ui_button","z":Z_S1,
     "group":"grp_s1_ops","order":2,"width":3,"height":1,"passthru":False,
     "label":"查詢所有資料","color":"white","bgcolor":"#2196F3","className":"","icon":"",
     "payload":"SELECT * FROM LED_LOG ORDER BY id DESC",
     "payloadType":"str","topic":"","topicType":"str",
     "x":120,"y":160,"wires":[["fn_s1_sql"]]},

    # ── 清除資料庫內容（語音 + YES/NO → DELETE FROM）──
    {"id":"s1_btn_delete","type":"ui_button","z":Z_S1,
     "group":"grp_s1_ops","order":3,"width":3,"height":1,"passthru":False,
     "label":"清除資料庫內容","color":"white","bgcolor":"#FF9800","className":"","icon":"",
     "payload":"是否清除資料庫內容","payloadType":"str","topic":"","topicType":"str",
     "x":120,"y":220,"wires":[["s1_audio_confirm","s1_toast_del"]]},
    {"id":"s1_audio_confirm","type":"ui_audio","z":Z_S1,
     "name":"","group":"grp_s1_ops",
     "voice":"Microsoft Hanhan - Chinese (Taiwan)",
     "always":True,"x":305,"y":190,"wires":[],"l":False},
    {"id":"s1_toast_del","type":"ui_toast","z":Z_S1,
     "position":"prompt","displayTime":"0","highlight":"",
     "sendall":True,"outputs":1,"ok":"YES","cancel":"NO",
     "raw":True,"className":"","topic":"確定要清除 LED 資料庫內容？",
     "name":"確認清除","x":330,"y":220,"wires":[["s1_fn_del_ok"]]},
    {"id":"s1_fn_del_ok","type":"function","z":Z_S1,"name":"YES/NO",
     "func":OK_CANCEL,"outputs":2,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":510,"y":220,"wires":[["s1_fn_del_sql"],[]]},
    {"id":"s1_fn_del_sql","type":"function","z":Z_S1,"name":"清除畫面",
     "func":"return [{payload:[]}, {payload:'LED 畫面資料已清除'}];",
     "outputs":2,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":700,"y":220,"wires":[["tmpl_led"],["toast_s1"]]},

    # ── 刪除資料庫（語音 + YES/NO → DROP TABLE）──
    {"id":"s1_btn_drop","type":"ui_button","z":Z_S1,
     "group":"grp_s1_ops","order":4,"width":3,"height":1,"passthru":False,
     "label":"刪除資料庫","color":"white","bgcolor":"#F44336","className":"","icon":"",
     "payload":"是否刪除資料庫","payloadType":"str","topic":"","topicType":"str",
     "x":120,"y":280,"wires":[["s1_audio_confirm","s1_toast_drop"]]},
    {"id":"s1_toast_drop","type":"ui_toast","z":Z_S1,
     "position":"prompt","displayTime":"0","highlight":"",
     "sendall":True,"outputs":1,"ok":"YES","cancel":"NO",
     "raw":True,"className":"","topic":"確定要刪除 LED 資料庫？",
     "name":"確認刪除","x":330,"y":280,"wires":[["s1_fn_drop_ok"]]},
    {"id":"s1_fn_drop_ok","type":"function","z":Z_S1,"name":"YES/NO",
     "func":OK_CANCEL,"outputs":2,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":510,"y":280,"wires":[["s1_fn_drop_sql"],[]]},
    {"id":"s1_fn_drop_sql","type":"function","z":Z_S1,"name":"DROP TABLE",
     "func":"msg.topic='DROP TABLE IF EXISTS LED_LOG';\nmsg.params=[];\nreturn msg;",
     "outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":700,"y":280,"wires":[["sqlite_led"]]},

    # ── 匯出報表 ──
    {"id":"s1_btn_export","type":"ui_button","z":Z_S1,
     "group":"grp_s1_ops","order":5,"width":"12","height":1,"passthru":False,
     "label":"匯出 LED + RFID 報表 (Excel)","color":"white","bgcolor":"#7B1FA2","className":"","icon":"file_download",
     "payload":"","payloadType":"str","topic":"","topicType":"str",
     "x":120,"y":340,"wires":[["exec_s1_exp"]]},

    # ── 公用 SQL function ──
    {"id":"fn_s1_sql","type":"function","z":Z_S1,"name":"設定 SQL",
     "func":SET_SQL,"outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":700,"y":160,"wires":[["sqlite_led"]]},

    # ── MQTT 自動 INSERT ──
    {"id":"s1_sub_status","type":"mqtt in","z":Z_S1,
     "name":"LED Status in","topic":"test/led/status",
     "qos":"1","datatype":"auto-detect","broker":"b9efc827e98bf7f9",
     "nl":False,"rap":True,"rh":0,"inputs":0,
     "x":120,"y":460,"wires":[["fn_s1_ins"]]},
    {"id":"fn_s1_ins","type":"function","z":Z_S1,"name":"INSERT LED_LOG",
     "func":insert_ts_led(),
     "outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":350,"y":460,"wires":[["sqlite_led"]]},

    # ── SQLite ──
    {"id":"sqlite_led","type":"sqlite","z":Z_S1,
     "mydb":"db_led","sqlquery":"msg.topic","sql":"","name":"SQLite LED",
     "x":920,"y":260,"wires":[["fn_s1_router"]]},

    # ── Router（3 outputs）──
    {"id":"fn_s1_router","type":"function","z":Z_S1,"name":"路由",
     "func":router("LED"),
     "outputs":3,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":1100,"y":260,"wires":[["tmpl_led"],["toast_s1"],["s1_link_out"]]},

    # ── Template ──
    {"id":"tmpl_led","type":"ui_template","z":Z_S1,
     "group":"grp_s1_data","name":"LED 資料表",
     "order":1,"width":"14","height":12,
     "format":LED_TMPL,
     "storeOutMessages":True,"fwdInMessages":True,
     "resendOnRefresh":True,"templateScope":"local",
     "x":1300,"y":220,"wires":[[]]},

    # ── Toast ──
    {"id":"toast_s1","type":"ui_toast","z":Z_S1,
     "position":"top right","displayTime":"3","highlight":"",
     "sendall":True,"outputs":0,"ok":"OK","cancel":"",
     "raw":False,"topic":"LED","name":"Toast",
     "x":1300,"y":280,"wires":[]},

    # ── Auto-refresh link ──
    {"id":"s1_link_out","type":"link out","z":Z_S1,
     "name":"refresh out","mode":"link","links":["s1_link_in"],
     "x":1300,"y":340,"wires":[]},
    {"id":"s1_link_in","type":"link in","z":Z_S1,
     "name":"refresh in","links":["s1_link_out"],
     "x":560,"y":120,"wires":[["s1_fn_auto_sel"]]},
    {"id":"s1_fn_auto_sel","type":"function","z":Z_S1,"name":"AUTO SELECT",
     "func":auto_select("LED_LOG"),
     "outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":720,"y":120,"wires":[["sqlite_led"]]},

    # ── 匯出 exec ──
    {"id":"exec_s1_exp","type":"exec","z":Z_S1,
     "command":'python "' + EXPORT_PY + '"',
     "addpay":False,"append":"","useSpawn":False,"timer":"","name":"匯出腳本",
     "x":330,"y":340,"wires":[["fn_s1_exp_ok"],["fn_s1_exp_err"],[]]},
    {"id":"fn_s1_exp_ok","type":"function","z":Z_S1,"name":"成功",
     "func":EXPORT_OK,"outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":530,"y":320,"wires":[["toast_s1_exp"]]},
    {"id":"fn_s1_exp_err","type":"function","z":Z_S1,"name":"失敗",
     "func":EXPORT_ERR,"outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":530,"y":360,"wires":[["toast_s1_exp"]]},
    {"id":"toast_s1_exp","type":"ui_toast","z":Z_S1,
     "position":"top right","displayTime":"5","highlight":"",
     "sendall":True,"outputs":0,"ok":"OK","cancel":"",
     "raw":False,"topic":"匯出報表","name":"匯出 Toast",
     "x":730,"y":340,"wires":[]},
]

# ═══════════════════════════════════════════════════════════════════════════════
# 刷卡紀錄（RFIDSubpage2）
# ═══════════════════════════════════════════════════════════════════════════════
Z_S2 = "tab_sub2"

flows += [
    # ── 回主頁 ──
    {"id":"s2_btn_home","type":"ui_button","z":Z_S2,
     "group":"grp_s2_ops","order":0,"width":2,"height":1,"passthru":False,
     "label":"回主頁","color":"white","bgcolor":"#FF6F00","className":"","icon":"home",
     "payload":"","payloadType":"str","topic":"topic","topicType":"msg",
     "x":100,"y":40,"wires":[["s2_fn_home"]]},
    {"id":"s2_fn_home","type":"function","z":Z_S2,"name":"goto 首頁",
     "func":"msg.payload={\"tab\":\"資料管理首頁\"};\nreturn msg;",
     "outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":280,"y":40,"wires":[["s2_ui_ctrl"]]},
    {"id":"s2_ui_ctrl","type":"ui_ui_control","z":Z_S2,
     "name":"","events":"all","x":460,"y":40,"wires":[[]]},

    # ── 設定時間 ui_template ──
    {"id":"s2_tmpl_time","type":"ui_template","z":Z_S2,
     "group":"grp_s2_time","name":"設定時間",
     "order":1,"width":"14","height":2,
     "format":TIME_TMPL,
     "storeOutMessages":False,"fwdInMessages":True,
     "resendOnRefresh":True,"templateScope":"local",
     "x":300,"y":680,"wires":[["s2_fn_save_time"]]},

    # 儲存設定
    {"id":"s2_fn_save_time","type":"function","z":Z_S2,"name":"儲存設定",
     "func":SAVE_TIME,"outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":500,"y":680,"wires":[["s2_file_save"]]},
    {"id":"s2_file_save","type":"file","z":Z_S2,
     "name":"寫入設定檔","filename":CONFIG_FILE,
     "appendNewline":False,"createDir":False,"overwriteFile":"true",
     "encoding":"utf8","x":700,"y":680,"wires":[[]]},

    # 啟動時載入設定
    {"id":"s2_inject_load","type":"inject","z":Z_S2,
     "name":"啟動載入","props":[],"repeat":"","crontab":"",
     "once":True,"onceDelay":"1","topic":"",
     "x":120,"y":740,"wires":[["s2_file_load"]]},
    {"id":"s2_file_load","type":"file in","z":Z_S2,
     "name":"讀取設定檔","filename":CONFIG_FILE,
     "format":"utf8","chunk":False,"sendError":False,
     "encoding":"utf8","allProps":False,
     "x":300,"y":740,"wires":[["s2_fn_load_time"]]},
    {"id":"s2_fn_load_time","type":"function","z":Z_S2,"name":"載入設定",
     "func":LOAD_TIME,"outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":500,"y":740,"wires":[["s2_tmpl_time"]]},

    # ── 建立資料庫 ──
    {"id":"s2_btn_create","type":"ui_button","z":Z_S2,
     "group":"grp_s2_ops","order":1,"width":3,"height":1,"passthru":False,
     "label":"建立資料庫","color":"white","bgcolor":"#4CAF50","className":"","icon":"",
     "payload":"CREATE TABLE IF NOT EXISTS RFID_LOG (id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, date TEXT, time TEXT, remark TEXT DEFAULT '')",
     "payloadType":"str","topic":"","topicType":"str",
     "x":120,"y":100,"wires":[["fn_s2_sql"]]},

    # ── 查詢所有資料 ──
    {"id":"s2_btn_select","type":"ui_button","z":Z_S2,
     "group":"grp_s2_ops","order":2,"width":3,"height":1,"passthru":False,
     "label":"查詢所有資料","color":"white","bgcolor":"#2196F3","className":"","icon":"",
     "payload":"SELECT * FROM RFID_LOG ORDER BY id DESC",
     "payloadType":"str","topic":"","topicType":"str",
     "x":120,"y":160,"wires":[["fn_s2_sql"]]},

    # ── 清除資料庫內容（語音 + YES/NO → DELETE FROM）──
    {"id":"s2_btn_delete","type":"ui_button","z":Z_S2,
     "group":"grp_s2_ops","order":3,"width":3,"height":1,"passthru":False,
     "label":"清除資料庫內容","color":"white","bgcolor":"#FF9800","className":"","icon":"",
     "payload":"是否清除資料庫內容","payloadType":"str","topic":"","topicType":"str",
     "x":120,"y":220,"wires":[["s2_audio_confirm","s2_toast_del"]]},
    {"id":"s2_audio_confirm","type":"ui_audio","z":Z_S2,
     "name":"","group":"grp_s2_ops",
     "voice":"Microsoft Hanhan - Chinese (Taiwan)",
     "always":True,"x":305,"y":190,"wires":[],"l":False},
    {"id":"s2_toast_del","type":"ui_toast","z":Z_S2,
     "position":"prompt","displayTime":"0","highlight":"",
     "sendall":True,"outputs":1,"ok":"YES","cancel":"NO",
     "raw":True,"className":"","topic":"確定要清除 RFID 資料庫內容？",
     "name":"確認清除","x":330,"y":220,"wires":[["s2_fn_del_ok"]]},
    {"id":"s2_fn_del_ok","type":"function","z":Z_S2,"name":"YES/NO",
     "func":OK_CANCEL,"outputs":2,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":510,"y":220,"wires":[["s2_fn_del_sql"],[]]},
    {"id":"s2_fn_del_sql","type":"function","z":Z_S2,"name":"清除畫面",
     "func":"return [{payload:[]}, {payload:'RFID 畫面資料已清除'}];",
     "outputs":2,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":700,"y":220,"wires":[["tmpl_rfid"],["toast_s2"]]},

    # ── 刪除資料庫（語音 + YES/NO → DROP TABLE）──
    {"id":"s2_btn_drop","type":"ui_button","z":Z_S2,
     "group":"grp_s2_ops","order":4,"width":3,"height":1,"passthru":False,
     "label":"刪除資料庫","color":"white","bgcolor":"#F44336","className":"","icon":"",
     "payload":"是否刪除資料庫","payloadType":"str","topic":"","topicType":"str",
     "x":120,"y":280,"wires":[["s2_audio_confirm","s2_toast_drop"]]},
    {"id":"s2_toast_drop","type":"ui_toast","z":Z_S2,
     "position":"prompt","displayTime":"0","highlight":"",
     "sendall":True,"outputs":1,"ok":"YES","cancel":"NO",
     "raw":True,"className":"","topic":"確定要刪除 RFID 資料庫？",
     "name":"確認刪除","x":330,"y":280,"wires":[["s2_fn_drop_ok"]]},
    {"id":"s2_fn_drop_ok","type":"function","z":Z_S2,"name":"YES/NO",
     "func":OK_CANCEL,"outputs":2,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":510,"y":280,"wires":[["s2_fn_drop_sql"],[]]},
    {"id":"s2_fn_drop_sql","type":"function","z":Z_S2,"name":"DROP TABLE",
     "func":"msg.topic='DROP TABLE IF EXISTS RFID_LOG';\nmsg.params=[];\nreturn msg;",
     "outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":700,"y":280,"wires":[["sqlite_rfid"]]},

    # ── 匯出報表 ──
    {"id":"s2_btn_export","type":"ui_button","z":Z_S2,
     "group":"grp_s2_ops","order":5,"width":"12","height":1,"passthru":False,
     "label":"匯出 LED + RFID 報表 (Excel)","color":"white","bgcolor":"#7B1FA2","className":"","icon":"file_download",
     "payload":"","payloadType":"str","topic":"","topicType":"str",
     "x":120,"y":340,"wires":[["exec_s2_exp"]]},

    # ── 公用 SQL function ──
    {"id":"fn_s2_sql","type":"function","z":Z_S2,"name":"設定 SQL",
     "func":SET_SQL,"outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":700,"y":160,"wires":[["sqlite_rfid"]]},

    # ── MQTT 自動 INSERT（含備註判定）──
    {"id":"s2_sub_uid","type":"mqtt in","z":Z_S2,
     "name":"RFID UID in","topic":"test/rfid/UID",
     "qos":"1","datatype":"auto-detect","broker":"b9efc827e98bf7f9",
     "nl":False,"rap":True,"rh":0,"inputs":0,
     "x":120,"y":460,"wires":[["fn_s2_ins"]]},
    {"id":"fn_s2_ins","type":"function","z":Z_S2,"name":"INSERT RFID_LOG",
     "func":insert_ts_rfid(),
     "outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":350,"y":460,"wires":[["sqlite_rfid"]]},

    # ── SQLite ──
    {"id":"sqlite_rfid","type":"sqlite","z":Z_S2,
     "mydb":"db_rfid","sqlquery":"msg.topic","sql":"","name":"SQLite RFID",
     "x":920,"y":260,"wires":[["fn_s2_router"]]},

    # ── Router（3 outputs）──
    {"id":"fn_s2_router","type":"function","z":Z_S2,"name":"路由",
     "func":router("RFID"),
     "outputs":3,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":1100,"y":260,"wires":[["tmpl_rfid"],["toast_s2"],["s2_link_out"]]},

    # ── Template ──
    {"id":"tmpl_rfid","type":"ui_template","z":Z_S2,
     "group":"grp_s2_data","name":"RFID 資料表",
     "order":1,"width":"14","height":12,
     "format":RFID_TMPL,
     "storeOutMessages":True,"fwdInMessages":True,
     "resendOnRefresh":True,"templateScope":"local",
     "x":1300,"y":220,"wires":[[]]},

    # ── Toast ──
    {"id":"toast_s2","type":"ui_toast","z":Z_S2,
     "position":"top right","displayTime":"3","highlight":"",
     "sendall":True,"outputs":0,"ok":"OK","cancel":"",
     "raw":False,"topic":"RFID","name":"Toast",
     "x":1300,"y":280,"wires":[]},

    # ── Auto-refresh link ──
    {"id":"s2_link_out","type":"link out","z":Z_S2,
     "name":"refresh out","mode":"link","links":["s2_link_in"],
     "x":1300,"y":340,"wires":[]},
    {"id":"s2_link_in","type":"link in","z":Z_S2,
     "name":"refresh in","links":["s2_link_out"],
     "x":560,"y":120,"wires":[["s2_fn_auto_sel"]]},
    {"id":"s2_fn_auto_sel","type":"function","z":Z_S2,"name":"AUTO SELECT",
     "func":auto_select("RFID_LOG"),
     "outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":720,"y":120,"wires":[["sqlite_rfid"]]},

    # ── 匯出 exec ──
    {"id":"exec_s2_exp","type":"exec","z":Z_S2,
     "command":'python "' + EXPORT_PY + '"',
     "addpay":False,"append":"","useSpawn":False,"timer":"","name":"匯出腳本",
     "x":330,"y":340,"wires":[["fn_s2_exp_ok"],["fn_s2_exp_err"],[]]},
    {"id":"fn_s2_exp_ok","type":"function","z":Z_S2,"name":"成功",
     "func":EXPORT_OK,"outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":530,"y":320,"wires":[["toast_s2_exp"]]},
    {"id":"fn_s2_exp_err","type":"function","z":Z_S2,"name":"失敗",
     "func":EXPORT_ERR,"outputs":1,"noerr":0,"initialize":"","finalize":"","libs":[],
     "x":530,"y":360,"wires":[["toast_s2_exp"]]},
    {"id":"toast_s2_exp","type":"ui_toast","z":Z_S2,
     "position":"top right","displayTime":"5","highlight":"",
     "sendall":True,"outputs":0,"ok":"OK","cancel":"",
     "raw":False,"topic":"匯出報表","name":"匯出 Toast",
     "x":730,"y":340,"wires":[]},
]

# ═══════════════════════════════════════════════════════════════════════════════
# Write JSON
# ═══════════════════════════════════════════════════════════════════════════════
OUT = "D:/MQTT作業2/nodered_flows.json"
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(flows, f, ensure_ascii=False, indent=2)
print(f"OK: {len(flows)} nodes written to {OUT}")

# ── 自動升級 RFID_LOG 加入 remark 欄位（若表存在但缺欄位）──
try:
    conn = sqlite3.connect(DB_RFID)
    conn.execute("ALTER TABLE RFID_LOG ADD COLUMN remark TEXT DEFAULT ''")
    conn.commit()
    print("RFID_LOG: added remark column")
except Exception:
    pass  # 欄位已存在或表不存在
finally:
    conn.close()
