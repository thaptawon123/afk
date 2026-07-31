import os
import subprocess
import time

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
    """รัน MCC แบบซ่อน Log ในเกม แสดงเฉพาะ Status ของ Python"""
    folder_path = os.path.dirname(exe_path)
    folder_name = os.path.basename(folder_path)

    print(f"[{current_idx}/{total_count}] Starting process for: {folder_name}")

    try:
        p = subprocess.Popen(
            [exe_path],
            cwd=folder_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )

        # 1. หน่วงเวลารอโหลดเข้าเซิร์ฟเวอร์
        print(f"  ├─ ⏳ Waiting for {folder_name} to connect...")
        time.sleep(8)

        # 2. ส่งคำสั่งล็อกอิน
        print(f"  ├─ 🔑 Sending login credentials for {folder_name}...")
        p.stdin.write("/dialog set pass tang2547\n")
        p.stdin.flush()
        time.sleep(1.5)

        p.stdin.write("/dialog click 1\n")
        p.stdin.flush()
        time.sleep(3)

        # 3. ส่ง /dialog click 2 เพื่อข้าม 2FA
        p.stdin.write("/dialog click 2\n")
        p.stdin.flush()
        time.sleep(2)

        # 4. รันชุดคำสั่งที่เหลือ
        print(f"  ├─ 🤖 Executing in-game commands for {folder_name}...")
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

# 1. รอบแรก: เปิดและล็อกอินทีละจอจนเสร็จสมบูรณ์ก่อนเริ่มอันถัดไป
for idx, exe_path in enumerate(exe_paths, 1):
    p = launch_and_login(exe_path, idx, total_instances)
    if p:
        active_processes[exe_path] = p
    
    # หน่วงเวลาสั้นๆ ก่อนสลับไปเปิดจอถัดไป
    time.sleep(5)

print("🚀 All instances have been launched and configured sequentially!")
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
                
                # สั่งเปิดและล็อกอินใหม่เฉพาะจอนั้นจนจบกระบวนการ
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
