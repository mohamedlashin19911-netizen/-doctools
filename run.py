"""نقطة تشغيل الأداة — شغّل: python run.py"""
import sys
import threading
import webbrowser

import uvicorn

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    url = "http://127.0.0.1:8750"
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"أدوات المستندات شغّالة على: {url}  — تقفلها بـ Ctrl+C")
    uvicorn.run("app.server:app", host="127.0.0.1", port=8750, log_level="warning")
