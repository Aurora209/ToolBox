import time
import threading
from pathlib import Path


class FileMonitor:
    def __init__(self, app):
        self.app = app
        self.running = False
        self.last_scan_time = 0
        self.scan_interval = int(app.config['General'].get('scan_interval', '30'))
        self.thread = None

    def start(self):
        if not self.running:
            self.running = True
            self.app.auto_status_label.config(text="自动记录: 运行中", fg="#1abc9c")
            self.thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False

    def monitor_loop(self):
        while self.running:
            time.sleep(5)
            try:
                if time.time() - self.last_scan_time >= self.scan_interval:
                    self.last_scan_time = time.time()
                    self.app.root.after(0, self.app.refresh_tools)
            except Exception as exc:
                print(f"自动扫描出错: {exc}")
