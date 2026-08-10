import os
import subprocess
import time
import select
import threading
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

BASE_DIR = r"/root/afk/afk r"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mcc_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# เก็บสถานะและ Process ของแต่ละ MCC
bot_statuses = {}
active_processes = {}

# HTML / CSS / JS UI สำหรับหน้าเว็บ Dashboard
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCC Web Dashboard</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #38bdf8;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
        }
        .btn-group {
            display: flex;
            gap: 10px;
        }
        .btn {
            border: none;
            padding: 10px 18px;
            font-size: 14px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            transition: 0.2s;
        }
        .btn-start { background-color: #22c55e; color: white; }
        .btn-start:hover { background-color: #16a34a; }
        
        .btn-restart { background-color: #f59e0b; color: white; }
        .btn-restart:hover { background-color: #d97706; }

        .btn-stop { background-color: #ef4444; color: white; }
        .btn-stop:hover { background-color: #dc2626; }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .card {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #334155;
            padding-bottom: 10px;
            margin-bottom: 10px;
        }
        .bot-name { font-weight: bold; color: #38bdf8; }
        .badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        .badge-waiting { background-color: #eab308; color: black; }
        .badge-running { background-color: #22c55e; color: white; }
        .badge-2fa { background-color: #a855f7; color: white; }
        .badge-error { background-color: #ef4444; color: white; }
        .badge-offline { background-color: #64748b; color: white; }
        
        .terminal {
            background-color: #020617;
            color: #22c55e;
            font-family: 'Courier New', Courier, monospace;
            padding: 10px;
            border-radius: 6px;
            height: 200px;
            overflow-y: auto;
            font-size: 12px;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>
            <span>🎮 MinecraftClient Manager Dashboard</span>
            <div class="btn-group">
                <button class="btn btn-start" onclick="startAllBots()">🚀 Start Automation</button>
                <button class="btn btn-restart" onclick="restartAllBots()">🔄 Stop & Rerun All</button>
                <button class="btn btn-stop" onclick="stopAllBots()">🛑 Stop All</button>
            </div>
        </h1>
        <div id="bot-grid" class="grid">
            <!-- Dynamic cards will appear here -->
        </div>
    </div>

    <script>
        const socket = io();

        socket.on('log_update', function(data) {
            appendLog(data.folder_name, data.line);
        });

        socket.on('status_update', function(data) {
            updateStatus(data.folder_name, data.status, data.badge_class);
        });

        function startAllBots() {
            socket.emit('start_bots');
        }

        function restartAllBots() {
            if (confirm("ต้องการสั่งปิด MCC ทั้งหมดและรันใหม่ใช่หรือไม่?")) {
                socket.emit('restart_bots');
            }
        }

        function stopAllBots() {
            if (confirm("ต้องการสั่งปิด MCC ทั้งหมดใช่หรือไม่?")) {
                socket.emit('stop_bots');
            }
        }

        function createCardIfNotExists(folderName) {
            if (document.getElementById(`card-${folderName}`)) return;

            const grid = document.getElementById('bot-grid');
            const card = document.createElement('div');
            card.className = 'card';
            card.id = `card-${folderName}`;
            card.innerHTML = `
                <div class="card-header">
                    <span class="bot-name">${folderName}</span>
                    <span id="badge-${folderName}" class="badge badge-offline">Offline</span>
                </div>
                <div class="terminal" id="term-${folderName}"></div>
            `;
            grid.appendChild(card);
        }

        function updateStatus(folderName, statusText, badgeClass) {
            createCardIfNotExists(folderName);
            const badge = document.getElementById(`badge-${folderName}`);
            badge.className = `badge ${badgeClass}`;
            badge.innerText = statusText;
        }

        function appendLog(folderName, message) {
            createCardIfNotExists(folderName);
            const term = document.getElementById(`term-${folderName}`);
            term.innerText += message + "\\n";
            term.scrollTop = term.scrollHeight;
        }
    </script>
</body>
</html>
"""

def find_mcc_paths():
    """ค้นหาไฟล์ MinecraftClient ทั้งหมด"""
    exe_paths = []
    for root, dirs, files in os.walk(BASE_DIR):
        if ".qodo" in root or "lang" in root or "venv" in root:
            continue
        for file in files:
            if file.lower().startswith("minecraftclient") and not file.lower().endswith((".ini", ".txt", ".bak", ".exe")):
                full_path = os.path.join(root, file)
                os.chmod(full_path, 0o755)
                exe_paths.append(full_path)
    return exe_paths

def log_and_emit(folder_name, message):
    """ส่ง Log ไปยัง Terminal เซิร์ฟเวอร์ และดึงขึ้น Web UI"""
    print(f"[{folder_name}] {message}")
    socketio.emit('log_update', {'folder_name': folder_name, 'line': message})

def set_status(folder_name, status_text, badge_class):
    """อัปเดตสถานะขึ้น Web UI"""
    socketio.emit('status_update', {
        'folder_name': folder_name,
        'status': status_text,
        'badge_class': badge_class
    })

def stop_all_bots():
    """สั่งปิด Process MCC ทั้งหมดที่กำลังทำงานอยู่"""
    print("🛑 Terminating all active processes...")
    for folder_name, p in list(active_processes.items()):
        try:
            if p.poll() is None: # ถ้ากระบวนการยังทำงานอยู่
                p.terminate()
                p.wait(timeout=2)
        except Exception:
            try:
                p.kill() # บังคับปิดถ้า terminate ไม่สำเร็จ
            except Exception:
                pass
        set_status(folder_name, "Stopped", "badge-offline")
        log_and_emit(folder_name, "🛑 Process stopped.")
    active_processes.clear()

def read_process_output(p, folder_name):
    """อ่าน Output จาก MCC แบบเรียลไทม์ และส่งขึ้นเว็บ"""
    while p.poll() is None:
        rlist, _, _ = select.select([p.stdout], [], [], 1.2)
        if rlist:
            line = p.stdout.readline()
            if line:
                log_and_emit(folder_name, line.strip())

def launch_and_login_task(exe_path, current_idx, total_count):
    folder_path = os.path.dirname(exe_path)
    folder_name = os.path.basename(folder_path)

    set_status(folder_name, "Starting...", "badge-waiting")
    log_and_emit(folder_name, f"[{current_idx}/{total_count}] Starting process...")

    try:
        p = subprocess.Popen(
            [exe_path],
            cwd=folder_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )
        active_processes[folder_name] = p

        # Thread แยกสำหรับดึง Terminal Output จาก MCC ขึ้นเว็บตลอดเวลา
        threading.Thread(target=read_process_output, args=(p, folder_name), daemon=True).start()

        # 1. หน่วงเวลารอเชื่อมต่อ
        set_status(folder_name, "Connecting...", "badge-waiting")
        log_and_emit(folder_name, "⏳ Waiting to connect...")
        time.sleep(15)

        # 2. ส่งคำสั่งล็อกอิน
        set_status(folder_name, "Logging in...", "badge-waiting")
        log_and_emit(folder_name, "🔑 Sending login credentials...")
        p.stdin.write("/dialog set pass tang2547\n")
        p.stdin.flush()
        time.sleep(2.5)

        p.stdin.write("/dialog click 1\n")
        p.stdin.flush()
        time.sleep(5)

        # 3. ตรวจสอบ 2FA (ดักจาก Log ล่าสุด)
        log_and_emit(folder_name, "🔍 Checking 2FA state...")
        time.sleep(5)
        
        log_and_emit(folder_name, "🔐 Sending '/dialog click 2'...")
        set_status(folder_name, "2FA Verification", "badge-2fa")
        p.stdin.write("/dialog click 2\n")
        p.stdin.flush()
        time.sleep(5)

        # 4. ส่งคำสั่งในเกมที่เหลือ
        log_and_emit(folder_name, "🤖 Executing remaining commands...")
        remaining_commands = [
            "/useitem\n",
            "/inventory container click 10\n",
            "/afk\n",
        ]

        for cmd in remaining_commands:
            p.stdin.write(cmd)
            p.stdin.flush()
            time.sleep(6)

        set_status(folder_name, "Running AFK", "badge-running")
        log_and_emit(folder_name, "✅ Initialization Complete!")

    except Exception as e:
        set_status(folder_name, "Error", "badge-error")
        log_and_emit(folder_name, f"❌ Error: {str(e)}")

def run_all_bots():
    exe_paths = find_mcc_paths()
    total_instances = len(exe_paths)

    for idx, exe_path in enumerate(exe_paths, 1):
        threading.Thread(target=launch_and_login_task, args=(exe_path, idx, total_instances), daemon=True).start()
        time.sleep(50) # ทิ้งช่วงเปิดทีละจอ

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('start_bots')
def handle_start_bots():
    print("🚀 Request received: Starting all MCC processes...")
    threading.Thread(target=run_all_bots, daemon=True).start()

@socketio.on('restart_bots')
def handle_restart_bots():
    print("🔄 Request received: Stopping all and restarting...")
    stop_all_bots()
    time.sleep(3) # รอให้ Process เกียร์ปิดตัวเรียบร้อย
    threading.Thread(target=run_all_bots, daemon=True).start()

@socketio.on('stop_bots')
def handle_stop_bots():
    print("🛑 Request received: Stopping all MCC processes...")
    stop_all_bots()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
