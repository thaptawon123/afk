import os
import subprocess
import time
import select

BASE_DIR = r"/root/afk/afk r"

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

def launch_and_login(exe_path, current_idx, total_count):
    """รัน MCC ทีละตัว ตรวจสอบหน้าต่าง 2FA จาก Log ใน Terminal ก่อนส่ง /dialog click 2"""
    folder_path = os.path.dirname(exe_path)
    folder_name = os.path.basename(folder_path)

    print(f"[{current_idx}/{total_count}] Starting process for: {folder_name}")

    try:
        # เปิดอ่าน Log จาก Terminal ของ MCC
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

        # 1. หน่วงเวลารอโหลดเข้าเซิร์ฟเวอร์
        print(f"  ├─ ⏳ Waiting for {folder_name} to connect...")
        time.sleep(8)

        # 2. ส่งคำสั่งล็อกอินขั้นแรก
        print(f"  ├─ 🔑 Sending login credentials for {folder_name}...")
        p.stdin.write("/dialog set pass tang2547\n")
        p.stdin.flush()
        time.sleep(3)

        p.stdin.write("/dialog click 1\n")
        p.stdin.flush()
        time.sleep(5)

        # 3. ตรวจสอบ Log จาก Terminal ของจอนี้ว่าขึ้น 2FA หรือไม่
        print(f"  ├─ 🔍 Checking Terminal logs for 2FA prompt...")
        has_2fa = False
        start_time = time.time()

        # วนส่องข้อความใน Terminal 2.5 วินาที
        while time.time() - start_time < 4.5:
            rlist, _, _ = select.select([p.stdout], [], [], 0.5)
            if rlist:
                line = p.stdout.readline()
                if line:
                    line_lower = line.lower()
                    # ตรวจหาคีย์เวิร์ดใน Terminal เช่น 2fa, pin, dialog, auth
                    if "2fa" in line_lower or "pin" in line_lower or "dialog" in line_lower or "auth" in line_lower:
                        has_2fa = True
                        break

        # รันคำสั่ง /dialog click 2 เฉพาะเมื่อเจอ 2FA ใน Terminal เท่านั้น
        if has_2fa:
            print(f"  ├─ 🔐 [2FA Found] Sending '/dialog click 2' for {folder_name}...")
            p.stdin.write("/dialog click 2\n")
            p.stdin.flush()
            time.sleep(2)
        else:
            print(f"  ├─ ⏩ No 2FA detected on {folder_name} Terminal, skipping '/dialog click 2'")

        # 4. รันชุดคำสั่งในเกมที่เหลือ
        print(f"  ├─ 🤖 Executing remaining commands for {folder_name}...")
        remaining_commands = [
            "/useitem\n",
            "/inventory container click 10\n",
            "/afk\n",
        ]

        for cmd in remaining_commands:
            p.stdin.write(cmd)
            p.stdin.flush()
            time.sleep(1.5)

        print(f"  └─ ✅ Fully completed initialization for {folder_name}\n")
        return p

    except Exception as e:
        print(f"  └─ ❌ Error with {folder_name}: {e}\n")
        return None

# ==================== MAIN EXECUTION ====================

print("🔍 Searching for all MinecraftClient files on Linux...")
exe_paths = find_mcc_paths()
total_instances = len(exe_paths)
print(f"✨ Found {total_instances} instances to run!\n")

active_processes = {}

# 1. รอบแรก: เปิดทีละจอ ตรวจเช็กและทำงานให้เสร็จสิ้นเรียบร้อยทีละอัน
for idx, exe_path in enumerate(exe_paths, 1):
    p = launch_and_login(exe_path, idx, total_instances)
    if p:
        active_processes[exe_path] = p
    
    time.sleep(1)

print("🚀 All instances have been launched successfully!")
print("🛡️ Monitoring mode activated... (Press Ctrl+C to stop)\n")

# 2. ระบบเฝ้าระวัง (Monitoring Loop): ตรวจเช็คทุกๆ 10 วินาที
try:
    while True:
        for idx, exe_path in enumerate(exe_paths, 1):
            p = active_processes.get(exe_path)
            
            # ถ้าโปรแกรมดับไปแล้ว
            if p is None or p.poll() is not None:
                folder_name = os.path.basename(os.path.dirname(exe_path))
                print(f"⚠️ [WARNING] Detected '{folder_name}' has stopped/crashed! Restarting...")
                
                new_p = launch_and_login(exe_path, idx, total_instances)
                if new_p:
                    active_processes[exe_path] = new_p
                
                time.sleep(2)

        time.sleep(10)

except KeyboardInterrupt:
    print("\n🛑 Stopping all instances...")
    for p in active_processes.values():
        if p and p.poll() is None:
            p.terminate()
    print("✅ All processes stopped.")
