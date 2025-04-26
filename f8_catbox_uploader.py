import os
import sys
import logging
from datetime import datetime

import tkinter as tk
from PIL import ImageGrab
import requests
import pyperclip
import keyboard

# ─── Configuration ──────────────────────────────────────────────────────────
CATBOX_API = "https://catbox.moe/user/api.php"
TMP_DIR = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
os.makedirs(TMP_DIR, exist_ok=True)
LOG_FILE = os.path.join(TMP_DIR, "f8_catbox.log")

# ─── Logger Setup ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ─── Auto Startup Registration ───────────────────────────────────────────────────────────────
def add_to_startup():
    """
    Adds a shortcut for this script in the Windows Startup folder to launch at login.
    Requires pywin32 (`pip install pywin32`).
    """
    if os.name != 'nt':
        return
    try:
        import win32com.client
        startup_dir = os.path.join(os.getenv('APPDATA'),
                                   'Microsoft\\Windows\\Start Menu\\Programs\\Startup')
        script = os.path.abspath(__file__)
        # Use pythonw.exe for silent launch
        pythonw = sys.executable.replace('python.exe', 'pythonw.exe')
        link_path = os.path.join(startup_dir, 'F8 Catbox Uploader.lnk')
        if not os.path.exists(link_path):
            shell = win32com.client.Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(link_path)
            shortcut.Targetpath = pythonw
            shortcut.Arguments = f'"{script}"'
            shortcut.WorkingDirectory = os.path.dirname(script)
            shortcut.IconLocation = script
            shortcut.save()
            logger.info(f'Created startup shortcut: {link_path}')
    except Exception:
        logger.exception('Failed to add to startup')

# ─── Snipping Tool ───────────────────────────────────────────────────────────
class SnippingTool:
    def __init__(self):
        self.start_x = self.start_y = self.end_x = self.end_y = 0
        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-alpha', 0.3)
        self.root.config(cursor='cross')
        self.canvas = tk.Canvas(self.root, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.rect = None

        self.root.bind("<ButtonPress-1>", self.on_button_press)
        self.root.bind("<B1-Motion>", self.on_move_press)
        self.root.bind("<ButtonRelease-1>", self.on_button_release)
        self.root.mainloop()

    def on_button_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=2
        )

    def on_move_press(self, event):
        curX, curY = event.x, event.y
        self.canvas.coords(self.rect, self.start_x, self.start_y, curX, curY)

    def on_button_release(self, event):
        self.end_x, self.end_y = event.x, event.y
        self.root.destroy()

# ─── Core Functionality ─────────────────────────────────────────────────────
def take_snip() -> str:
    """Let the user snip a region, save it, and return the filepath."""
    tool = SnippingTool()
    x1 = min(tool.start_x, tool.end_x)
    y1 = min(tool.start_y, tool.end_y)
    x2 = max(tool.start_x, tool.end_x)
    y2 = max(tool.start_y, tool.end_y)

    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"snip_{timestamp}.png"
    path = os.path.join(TMP_DIR, filename)
    img.save(path)
    logger.info(f"Region snipped and saved to {path}")
    return path


def upload_to_catbox(filepath: str) -> str:
    """Upload the given file to Catbox and return the URL."""
    with open(filepath, "rb") as f:
        files = {"fileToUpload": f}
        data = {"reqtype": "fileupload"}
        resp = requests.post(CATBOX_API, data=data, files=files, timeout=30)
    if not resp.ok or not resp.text.startswith("http"):
        raise RuntimeError(f"Upload failed ({resp.status_code}): {resp.text}")
    logger.info(f"Upload successful: {resp.text}")
    return resp.text.strip()


def on_hotkey():
    """Callback: snip, upload, copy URL, and cleanup."""
    path = None
    try:
        path = take_snip()
        url = upload_to_catbox(path)
        pyperclip.copy(url)
        logger.info("Link copied to clipboard.")
    except Exception:
        logger.exception("Error during snip+upload:")
    finally:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                logger.info(f"Temporary file deleted: {path}")
            except Exception:
                logger.exception("Could not delete temp file")

# ─── Entry Point ─────────────────────────────────────────────────────────────
def main():
    # Register script to run at startup
    add_to_startup()
    
    logger.info("✅ f8_catbox_uploader.py is running—waiting for F8 to snip & upload, F4 to exit.")
    keyboard.add_hotkey("F8", on_hotkey)
    keyboard.wait("F4")
    logger.info("F4 pressed—exiting.")

if __name__ == "__main__":
    main()

