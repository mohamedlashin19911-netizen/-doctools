# -*- coding: utf-8 -*-
"""إطلاق أدوات المستندات كتطبيق سطح مكتب — نافذة أصلية بدون متصفح."""
import os
import threading
import time
import urllib.request

os.chdir(os.path.dirname(os.path.abspath(__file__)))
URL = "http://127.0.0.1:8750"


def server_running():
    try:
        with urllib.request.urlopen(URL + "/api/health", timeout=1) as r:
            return r.status == 200
    except Exception:
        return False


def start_server():
    import uvicorn
    from app.server import app
    uvicorn.run(app, host="127.0.0.1", port=8750, log_level="error")


def main():
    import webview
    if not server_running():
        threading.Thread(target=start_server, daemon=True).start()
        for _ in range(60):
            if server_running():
                break
            time.sleep(0.2)
    webview.create_window(
        "DocTools", URL + "/",
        width=1280, height=860, min_size=(940, 620),
    )
    webview.start()


if __name__ == "__main__":
    main()
