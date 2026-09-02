# -*- coding: utf-8 -*-
"""工作面板：伪桌面启动器。桌宠/Live2D -> 展开工作区 -> 点击图标打开程序/文件夹。"""
import sys
import os

os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--allow-file-access-from-files")

# PyInstaller extracts bundled data below sys._MEIPASS.  Keeping resource files
# separate from writable user settings makes the same build work both from
# source and as a frozen application.
APP_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(APP_DIR, "web")

import re
import json
import math
import time
import ctypes
import subprocess
import winreg
from ctypes import wintypes

from PyQt6.QtCore import Qt, QSize, QSizeF, QFileInfo, QRectF, QTimer, QEvent, QUrl, QEventLoop
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QPainterPath, QAction, QActionGroup, QPixmap, QImage, QIcon, QCursor,
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
    QToolButton, QMenu, QFileIconProvider, QFileDialog, QMessageBox, QSizePolicy,
    QDialog, QPushButton, QListWidget, QListWidgetItem, QSlider, QWidgetAction,
    QGraphicsScene, QGraphicsView, QFrame,
)

try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink
    VIDEO_OK = True
except Exception:
    VIDEO_OK = False

VIDEO_ITEM_OK = False
if VIDEO_OK:
    try:
        from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem
        VIDEO_ITEM_OK = True
    except Exception:
        pass

WEB_OK = False
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    if os.path.exists(os.path.join(WEB_DIR, "pet.html")):
        WEB_OK = True
except Exception:
    pass

CONFIG_DIR = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), ".workspace_panel")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

COLUMNS = 4
ICON_SIZE = 44
BTN_WIDTH = 88
TRIGGER_SIZE = 58
PET_W = 340
PET_H = 480
PET_MIN_H = 120
PET_WHEEL_STEP = 20
FILE_ATTRIBUTE_HIDDEN = 0x2
VIDEO_EXTS = (".mp4", ".webm", ".m4v", ".mkv")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif")


def is_video_path(p):
    return p.lower().endswith(VIDEO_EXTS)


def find_we_workshop_dirs():
    dirs = []
    seen = set()

    def add(p):
        if p and os.path.isdir(p):
            k = os.path.normcase(os.path.abspath(p))
            if k not in seen:
                seen.add(k)
                dirs.append(k)

    roots = []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            sp, _ = winreg.QueryValueEx(k, "SteamPath")
            roots.append(sp)
    except OSError:
        pass
    for r in list(roots):
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        try:
            with open(vdf, encoding="utf-8") as f:
                for m in re.finditer(r'"path"\s+"([^"]+)"', f.read()):
                    roots.append(m.group(1).replace("\\\\", "\\"))
        except OSError:
            pass
    for r in roots:
        add(os.path.join(r, "steamapps", "workshop", "content", "431960"))
    return dirs


def list_we_wallpapers():
    items = []
    for d in find_we_workshop_dirs():
        try:
            subs = os.listdir(d)
        except OSError:
            continue
        for sub in subs:
            folder = os.path.join(d, sub)
            if not os.path.isdir(folder):
                continue
            pj = os.path.join(folder, "project.json")
            title = sub
            if os.path.exists(pj):
                try:
                    with open(pj, encoding="utf-8") as f:
                        obj = json.load(f)
                    t = obj.get("title")
                    if isinstance(t, str) and t.strip():
                        title = t.strip()
                except Exception:
                    pass
            video = None
            try:
                for f2 in os.listdir(folder):
                    if is_video_path(f2) and os.path.isfile(os.path.join(folder, f2)):
                        video = os.path.join(folder, f2)
                        break
            except OSError:
                pass
            preview = os.path.join(folder, "preview.gif")
            items.append({
                "title": title,
                "video": video,
                "preview": preview if os.path.exists(preview) else None,
            })
    items.sort(key=lambda x: x["title"].lower())
    return items

PANEL_SS = """
QLabel { color:#f2f2f7; font:12pt "Microsoft YaHei UI"; font-weight:600; }
QLabel#hint  { color:rgba(255,255,255,110); font:8pt "Microsoft YaHei UI"; font-weight:400; }
QLabel#empty { color:rgba(255,255,255,150); font:10pt "Microsoft YaHei UI"; font-weight:400; }
QToolButton#close { background:transparent; color:rgba(255,255,255,160);
                    border:none; font:10pt "Segoe UI"; }
QToolButton#close:hover { color:white; background:rgba(255,255,255,40); border-radius:10px; }
QToolButton[item="true"] { background:transparent; color:#f2f2f7; border-radius:12px;
                           padding:4px 2px 2px; font:9pt "Microsoft YaHei UI"; }
QToolButton[item="true"]:hover { background:rgba(255,255,255,36); }
"""

MENU_SS = """
QMenu { background:#2c2c31; border:1px solid rgba(255,255,255,32); border-radius:10px;
        color:#f2f2f7; font:9pt "Microsoft YaHei UI"; padding:6px; }
QMenu::item { padding:6px 26px; border-radius:6px; }
QMenu::item:selected { background:rgba(255,255,255,38); }
QMenu::separator { height:1px; background:rgba(255,255,255,26); margin:5px 8px; }
"""

DEFAULTS = {
    "entries": [],
    "trigger_pos": None,
    "close_on_open": True,
    "wallpaper": "",
    "pet_mode": "live2d",
    # Portable defaults mirror the current desktop-pet appearance without
    # copying machine-specific shortcuts, screen coordinates, or wallpaper.
    "pet_h": 180,
    "pet_volume": 17,
    "pet_auto_interval_sec": 180,
}

AUTO_INTERVAL_CHOICES = (
    (0, "关闭"),
    (30, "30 秒"),
    (60, "1 分钟"),
    (180, "3 分钟"),
    (300, "5 分钟"),
    (600, "10 分钟"),
    (900, "15 分钟"),
    (1800, "30 分钟"),
)


def load_cfg():
    d = dict(DEFAULTS)
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            d.update(json.load(f))
    except Exception:
        pass
    return d


def save_cfg():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def public_desktop_root():
    pub = os.environ.get("PUBLIC")
    if not pub:
        return None
    return os.path.normcase(os.path.abspath(os.path.join(pub, "Desktop")))


def needs_admin(path):
    root = public_desktop_root()
    p = os.path.normcase(os.path.abspath(path))
    return bool(root and p.startswith(root + os.sep))


def set_hidden_batch(paths, hidden):
    admin, normal = [], []
    for p in paths:
        (admin if needs_admin(p) else normal).append(p)
    k = ctypes.windll.kernel32
    for p in normal:
        attrs = k.GetFileAttributesW(p)
        if attrs == 0xFFFFFFFF:
            dlog(f"getattrs fail {p}")
            continue
        new = (attrs | FILE_ATTRIBUTE_HIDDEN) if hidden else (attrs & ~FILE_ATTRIBUTE_HIDDEN)
        if not k.SetFileAttributesW(p, new):
            dlog(f"setattrs fail err={ctypes.GetLastError()} {p}")
    if admin:
        flag = "+h" if hidden else "-h"
        args = flag + "".join(f' "{p}"' for p in admin)
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", "attrib.exe", args, None, 0)
        dlog(f"attrib runas rc={rc} {args}")


def desktop_roots():
    roots = []
    up = os.environ.get("USERPROFILE")
    pub = os.environ.get("PUBLIC")
    if up:
        roots.append(os.path.join(up, "Desktop"))
    if pub:
        roots.append(os.path.join(pub, "Desktop"))
    return roots


def is_on_desktop(path):
    p = os.path.normcase(os.path.abspath(path))
    for r in desktop_roots():
        if p.startswith(os.path.normcase(os.path.abspath(r)) + os.sep):
            return True
    return False


def elide(s, n=7):
    return s if len(s) <= n else s[:n] + "…"


def open_in_explorer(path):
    subprocess.Popen(["explorer", f"/select,{path}"])


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def autostart_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, "WorkspacePanel")
        return True
    except OSError:
        return False


def set_autostart(on):
    if on:
        if getattr(sys, "frozen", False):
            # A frozen build is already a windowed executable; passing the
            # bundled panel.py path would create a stale, machine-local arg.
            cmd = f'"{os.path.abspath(sys.executable)}"'
        else:
            exe_dir = os.path.dirname(sys.executable)
            pyw_candidate = os.path.join(exe_dir, "pythonw.exe")
            pyw = pyw_candidate if os.path.exists(pyw_candidate) else sys.executable
            cmd = f'"{pyw}" "{os.path.abspath(__file__)}"'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "WorkspacePanel", 0, winreg.REG_SZ, cmd)
    else:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, "WorkspacePanel")
        except OSError:
            pass
    dlog(f"set_autostart({on}) -> enabled={autostart_enabled()}")


cfg = load_cfg()

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


u32 = ctypes.windll.user32
u32.IsWindowVisible.argtypes = [wintypes.HWND]
u32.IsIconic.argtypes = [wintypes.HWND]
u32.GetForegroundWindow.restype = wintypes.HWND
u32.SetForegroundWindow.argtypes = [wintypes.HWND]
u32.SetForegroundWindow.restype = wintypes.BOOL
u32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
u32.GetWindowLongW.restype = ctypes.c_long
u32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
u32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
u32.MonitorFromPoint.restype = wintypes.HMONITOR
u32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
u32.MonitorFromWindow.restype = wintypes.HMONITOR
u32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
ENUM_PROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
u32.EnumWindows.argtypes = [ENUM_PROC, wintypes.LPARAM]
dwmapi = ctypes.windll.dwmapi
dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]


def desktop_covered(widget, panel, w, h):
    pt = wintypes.POINT(widget.x() + w // 2, widget.y() + h // 2)
    mon = u32.MonitorFromPoint(pt, 2)
    if not mon:
        return False
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    if not u32.GetMonitorInfoW(mon, ctypes.byref(mi)):
        return False
    work = mi.rcWork
    own = {int(widget.winId()), int(panel.winId())}
    # Only the foreground window can currently cover the pet.  The old
    # EnumWindows implementation also counted maximized windows sitting in the
    # background, which could leave both launch surfaces hidden indefinitely.
    hwnd = u32.GetForegroundWindow()
    if not hwnd or int(hwnd) in own:
        return False
    if not u32.IsWindowVisible(hwnd) or u32.IsIconic(hwnd):
        return False
    if u32.GetWindowLongW(hwnd, -20) & 0x80:
        return False
    cloaked = ctypes.c_uint(0)
    if dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), 4) == 0 and cloaked.value:
        return False
    if u32.MonitorFromWindow(hwnd, 2) != mon:
        return False
    r = wintypes.RECT()
    if not u32.GetWindowRect(hwnd, ctypes.byref(r)):
        return False
    return (r.left <= work.left + 2 and r.top <= work.top + 2
            and r.right >= work.right - 2 and r.bottom >= work.bottom - 2)

DEBUG_LOG = os.path.join(CONFIG_DIR, "debug.log")
DEBUG_LOG_MAX_BYTES = 2 * 1024 * 1024


def dlog(msg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.exists(DEBUG_LOG) and os.path.getsize(DEBUG_LOG) >= DEBUG_LOG_MAX_BYTES:
            old_log = DEBUG_LOG + ".old"
            try:
                if os.path.exists(old_log):
                    os.remove(old_log)
                os.replace(DEBUG_LOG, old_log)
            except OSError:
                pass
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + msg + "\n")
    except Exception:
        pass


dlog("module load")


class WallpaperPickerDialog(QDialog):
    def __init__(self, parent, items):
        super().__init__(parent)
        self.setWindowTitle("Wallpaper Engine 壁纸库")
        self.resize(680, 540)
        self.chosen = None
        self.browse_requested = False
        self.setStyleSheet(
            "QDialog { background:#26262b; font:10pt 'Microsoft YaHei UI'; }"
            "QLabel { color:rgba(255,255,255,130); font:9pt 'Microsoft YaHei UI'; }"
            "QListWidget { background:transparent; border:1px solid rgba(255,255,255,26);"
            " border-radius:10px; color:#f2f2f7; outline:0; }"
            "QListWidget::item { padding:6px; border-radius:8px; }"
            "QListWidget::item:selected { background:rgba(255,255,255,36); }"
            "QPushButton { background:#3a3a41; color:#f2f2f7; border:none;"
            " border-radius:8px; padding:7px 16px; }"
            "QPushButton:hover { background:#4a4a52; }"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        self.listw = QListWidget(self)
        self.listw.setIconSize(QSize(96, 54))
        lay.addWidget(self.listw, stretch=1)
        lay.addWidget(QLabel("仅支持视频类型的壁纸；双击直接应用"))
        row = QHBoxLayout()
        row.addStretch()
        btn_browse = QPushButton("浏览文件夹…", self)
        btn_browse.clicked.connect(self._browse)
        btn_ok = QPushButton("使用", self)
        btn_ok.clicked.connect(self._apply)
        btn_cancel = QPushButton("取消", self)
        btn_cancel.clicked.connect(self.reject)
        row.addWidget(btn_browse)
        row.addWidget(btn_ok)
        row.addWidget(btn_cancel)
        lay.addLayout(row)
        self.items = items
        for it in items:
            label = it["title"] + ("  ✓" if it["video"] else "  （场景/网页，不支持）")
            lwi = QListWidgetItem(label)
            if it["preview"]:
                lwi.setIcon(QIcon(it["preview"]))
            lwi.setSizeHint(QSize(0, 64))
            self.listw.addItem(lwi)
        self.listw.itemDoubleClicked.connect(lambda _: self._apply())

    def _current(self):
        row = self.listw.currentRow()
        if 0 <= row < len(self.items):
            return self.items[row]
        return None

    def _apply(self):
        it = self._current()
        if it and it["video"]:
            self.chosen = it["video"]
            self.accept()

    def _browse(self):
        self.browse_requested = True
        self.reject()


class Panel(QWidget):
    def __init__(self, trigger):
        super().__init__()
        self.trigger = trigger
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.setStyleSheet(PANEL_SS)
        self._maximized = False
        self._normal_geom = None

        # Let Qt Multimedia present video frames directly.  The previous
        # QVideoSink -> QImage -> QPainter path copied every decoded frame to
        # CPU memory and scaled it there, which made 4K wallpapers stutter.
        self._video_view = None
        self._video_scene = None
        self._video_item = None
        self._video_dim = None
        if VIDEO_ITEM_OK:
            # QVideoWidget uses a native video surface on Windows and can cover
            # sibling widgets regardless of QWidget stacking order.  A graphics
            # video item keeps the video in the normal widget composition path,
            # so launcher icons and header controls remain visible above it.
            self._video_view = QGraphicsView(self)
            self._video_view.setFrameShape(QFrame.Shape.NoFrame)
            self._video_view.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self._video_view.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self._video_view.setInteractive(False)
            self._video_view.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
            )
            self._video_scene = QGraphicsScene(self._video_view)
            self._video_view.setScene(self._video_scene)
            self._video_item = QGraphicsVideoItem()
            self._video_item.setAspectRatioMode(
                Qt.AspectRatioMode.KeepAspectRatioByExpanding
            )
            self._video_scene.addItem(self._video_item)
            self._video_view.hide()
            self._video_dim = QWidget(self)
            self._video_dim.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
            )
            self._video_dim.setStyleSheet("background: rgba(15, 15, 18, 150);")
            self._video_dim.hide()

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 12)
        root.setSpacing(6)
        self.root_layout = root

        head = QHBoxLayout()
        title = QLabel("工作区")
        max_btn = QToolButton()
        max_btn.setObjectName("close")
        max_btn.setText("⛶")
        max_btn.setToolTip("最大化工作区（Esc 还原）")
        max_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        max_btn.clicked.connect(self.toggle_maximize)
        close_btn = QToolButton()
        close_btn.setObjectName("close")
        close_btn.setText("✕")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.hide)
        head.addWidget(title)
        head.addStretch()
        head.addWidget(max_btn)
        head.addWidget(close_btn)
        root.addLayout(head)

        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setSpacing(2)
        root.addWidget(self.grid_host)

        self.items_host = QWidget()
        self.items_host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.items_host.hide()
        root.addWidget(self.items_host)

        self._item_btns = []
        self._press_info = {}
        self._dragging_item = False

        self.empty = QLabel("把程序 / 文件夹拖到这里\n桌面上的项目拖入后会自动隐藏")
        self.empty.setObjectName("empty")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.empty)

        self.hint = QLabel("拖入添加 · 右键图标管理 · Esc 收起")
        self.hint.setObjectName("hint")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.hint)

        self._wallpaper = QPixmap()
        self._wp_scaled = None
        self._wp_size = None
        self._video_source = None
        self._vf_image = None
        self._sink_connected = False
        self.sink = None
        self.player = None
        if VIDEO_OK:
            self.player = QMediaPlayer(self)
            audio = QAudioOutput(self)
            audio.setMuted(True)
            self.player.setAudioOutput(audio)
            self.player.setLoops(QMediaPlayer.Loops.Infinite)
            self.player.errorOccurred.connect(
                lambda err, msg: dlog(f"player error {err}: {msg}")
            )
            self.player.playbackStateChanged.connect(
                lambda s: dlog(f"playback state {s}")
            )
            if self._video_item is not None:
                self.player.setVideoOutput(self._video_item)
                dlog("video output backend=graphics-video-item")
            else:
                # Compatibility fallback for environments that do not ship
                # QtMultimediaWidgets.  It is slower, but keeps video support.
                self.sink = QVideoSink(self)
                self.player.setVideoSink(self.sink)
                self.sink.videoFrameChanged.connect(self._on_video_frame)
                self._sink_connected = True
                dlog("video output backend=cpu-painter-fallback")
            self._first_frame_logged = False
        self.rebuild()
        self._load_wallpaper()

    def _layout_video_layers(self):
        if self._video_view is None:
            return
        self._video_view.setGeometry(self.rect())
        self._video_scene.setSceneRect(QRectF(self.rect()))
        self._video_item.setSize(QSizeF(self.size()))
        self._video_dim.setGeometry(self.rect())
        self._video_view.lower()
        self._video_dim.raise_()
        for widget in self.children():
            if (
                isinstance(widget, QWidget)
                and widget is not self._video_view
                and widget is not self._video_dim
            ):
                widget.raise_()

    def _on_video_frame(self, frame):
        img = frame.toImage()
        if not img.isNull():
            self._vf_image = img
            if not self._first_frame_logged:
                self._first_frame_logged = True
                dlog(f"first frame {img.width()}x{img.height()}")
            self.update()

    def _load_wallpaper(self):
        wp = cfg.get("wallpaper") or ""
        if wp and os.path.exists(wp) and not is_video_path(wp):
            pix = QPixmap(wp)
            self._wallpaper = pix if not pix.isNull() else QPixmap()
        else:
            self._wallpaper = QPixmap()
        self._wp_scaled = None
        self._video_source = None
        self._apply_wallpaper()

    def _apply_wallpaper(self):
        wp = cfg.get("wallpaper") or ""
        use_video = (
            VIDEO_OK
            and self.player is not None
            and wp
            and is_video_path(wp)
            and os.path.exists(wp)
        )
        if use_video and self._maximized:
            if self._video_source != wp:
                self._video_source = wp
                self.player.setSource(QUrl.fromLocalFile(wp))
            if self._video_view is not None:
                self._video_view.show()
                self._video_dim.show()
                self._layout_video_layers()
            self.player.play()
            dlog(f"video play, source={wp}")
        else:
            if self.player:
                self.player.stop()
            if self._video_view is not None:
                self._video_view.hide()
                self._video_dim.hide()
            self._vf_image = None
        self.update()

    def _scaled_wallpaper(self):
        if self._wallpaper.isNull():
            return None
        size = (self.width(), self.height())
        if self._wp_scaled is None or self._wp_size != size:
            self._wp_scaled = self._wallpaper.scaled(
                self.width() + 2,
                self.height() + 2,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._wp_size = size
        return self._wp_scaled

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._maximized:
            wp = self._scaled_wallpaper()
            img = self._vf_image
            if wp is not None:
                x = (self.width() - wp.width()) // 2
                y = (self.height() - wp.height()) // 2
                p.drawPixmap(x, y, wp)
                p.fillRect(self.rect(), QColor(15, 15, 18, 150))
            elif self._video_view is not None and self._video_view.isVisible():
                # The child video surface and dim layer paint after their
                # parent; only provide a neutral background before first frame.
                p.fillRect(self.rect(), QColor(30, 30, 34, 255))
            elif img is not None and img.width() and img.height():
                iw, ih = img.width(), img.height()
                scale = max(self.width() / iw, self.height() / ih)
                w, h = int(iw * scale) + 2, int(ih * scale) + 2
                x, y = (self.width() - w) // 2, (self.height() - h) // 2
                p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                p.drawImage(QRectF(x, y, w, h), img)
                p.fillRect(self.rect(), QColor(15, 15, 18, 150))
            else:
                p.fillRect(self.rect(), QColor(30, 30, 34, 255))
            return
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 22, 22)
        p.fillPath(path, QColor(30, 30, 34, 228))
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.drawPath(path)

    def rebuild(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for c in list(self.items_host.children()):
            if isinstance(c, QWidget):
                c.deleteLater()
        self._item_btns = []
        entries = cfg["entries"]
        self.empty.setVisible(not entries)
        self.hint.setVisible(bool(entries))
        big = self._maximized
        icon_size = 64 if big else ICON_SIZE
        btn_width = 104 if big else BTN_WIDTH
        if big:
            self.root_layout.setContentsMargins(40, 28, 40, 28)
        else:
            self.root_layout.setContentsMargins(14, 10, 14, 12)
        self.grid_host.setVisible(not big)
        self.items_host.setVisible(big)
        provider = QFileIconProvider()
        for i, e in enumerate(entries):
            b = QToolButton(self.items_host if big else self.grid_host)
            b.setProperty("item", True)
            b.setText(elide(e["name"], 6 if big else 7))
            b.setToolTip(e["path"])
            b.setIcon(provider.icon(QFileInfo(e["path"])))
            b.setIconSize(QSize(icon_size, icon_size))
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.setMinimumWidth(btn_width)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, p=e["path"]: self.open_path(p))
            b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            b.customContextMenuRequested.connect(
                lambda pos, p=e["path"], btn=b: self.item_menu(btn, p, pos)
            )
            if big:
                b.setFixedSize(84, 96)
                b.installEventFilter(self)
                self._item_btns.append(b)
            else:
                self.grid.addWidget(b, i // COLUMNS, i % COLUMNS)
        if not self._maximized:
            self.adjustSize()
        else:
            QTimer.singleShot(0, self._layout_items)
            QTimer.singleShot(120, self._layout_items)

    def _layout_items(self):
        if not self._maximized:
            return
        host = self.items_host
        W = max(host.width(), 120)
        H = max(host.height(), 120)
        dlog(
            f"layout host={host.width()}x{host.height()} visible={host.isVisible()} "
            f"btns={len(self._item_btns)} entries={len(cfg['entries'])}"
        )
        cw, ch = 112, 116
        cols = max(W // cw, 1)
        rows = max(H // ch, 1)
        used = set()
        for e, b in zip(cfg["entries"], self._item_btns):
            pos = e.get("pos")
            if isinstance(pos, list) and len(pos) == 2 and all(isinstance(v, int) for v in pos):
                x = min(max(0, pos[0]), max(W - b.width(), 0))
                y = min(max(0, pos[1]), max(H - b.height(), 0))
                used.add((x // cw, y // ch))
            else:
                x = y = None
                for ci in range(cols):
                    for ri in range(rows):
                        if (ci, ri) not in used:
                            used.add((ci, ri))
                            x, y = ci * cw, ri * ch
                            break
                    if x is not None:
                        break
                if x is None:
                    x, y = 0, max(H - b.height() - 10, 0)
            b.move(x, y)
            b.setVisible(True)

    def eventFilter(self, obj, ev):
        if (
            self._maximized
            and isinstance(obj, QToolButton)
            and obj.parent() is self.items_host
        ):
            t = ev.type()
            if t == QEvent.Type.MouseButtonPress and ev.button() == Qt.MouseButton.LeftButton:
                self._press_info[obj] = (ev.globalPosition().toPoint(), obj.pos())
                self._dragging_item = False
                obj.raise_()
                return False
            if t == QEvent.Type.MouseMove and obj in self._press_info:
                press_g, orig = self._press_info[obj]
                g = ev.globalPosition().toPoint()
                d = g - press_g
                if not self._dragging_item and d.manhattanLength() > 5:
                    self._dragging_item = True
                if self._dragging_item:
                    host = self.items_host
                    x = max(0, min(orig.x() + d.x(), host.width() - obj.width()))
                    y = max(0, min(orig.y() + d.y(), host.height() - obj.height()))
                    obj.move(x, y)
                    return True
                return False
            if t == QEvent.Type.MouseButtonRelease and obj in self._press_info:
                dragged = self._dragging_item
                self._press_info.pop(obj, None)
                self._dragging_item = False
                if dragged:
                    pos = obj.pos()
                    for e in cfg["entries"]:
                        if e["path"].lower() == obj.toolTip().lower():
                            e["pos"] = [pos.x(), pos.y()]
                            save_cfg()
                            break
                    return True
                return False
        return super().eventFilter(obj, ev)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._layout_video_layers()
        if self._maximized:
            self._layout_items()

    def _apply_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if not self._maximized:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def _queue_trigger_visibility_update(self):
        trigger = self.trigger
        if trigger is not None and hasattr(trigger, "_update_visibility"):
            QTimer.singleShot(0, trigger._update_visibility)

    def toggle_maximize(self):
        if not self._maximized:
            self._normal_geom = self.geometry()
            self._maximized = True
            self._apply_flags()
            self.setGeometry(self.screen().availableGeometry())
        else:
            self._maximized = False
            self._apply_flags()
            if self._normal_geom:
                self.setGeometry(self._normal_geom)
        self.rebuild()
        self._apply_wallpaper()
        self.raise_()
        self.activateWindow()
        self._queue_trigger_visibility_update()

    def hide(self):
        if self._maximized:
            self._maximized = False
            self._apply_flags()
        self._apply_wallpaper()
        super().hide()
        self._queue_trigger_visibility_update()

    def popup(self):
        self.rebuild()
        self.adjustSize()
        g = self.trigger.geometry()
        sg = QApplication.primaryScreen().availableGeometry()
        x, y = g.right() + 14, g.top() - 10
        if x + self.width() > sg.right() - 8:
            x = g.left() - self.width() - 14
        if x < sg.left() + 8:
            x = sg.left() + 8
        if y + self.height() > sg.bottom() - 8:
            y = sg.bottom() - self.height() - 8
        if y < sg.top() + 8:
            y = sg.top() + 8
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

    def open_path(self, path):
        try:
            os.startfile(path)
        except OSError as ex:
            QMessageBox.warning(self, "工作面板", f"无法打开：\n{path}\n\n{ex}")
            return
        if cfg["close_on_open"]:
            self.hide()

    def add_entry(self, path, admin_hides=None):
        path = os.path.normpath(path)
        if any(e["path"].lower() == path.lower() for e in cfg["entries"]):
            return False
        name = os.path.basename(path)
        if name.lower().endswith(".lnk"):
            name = os.path.splitext(name)[0]
        hidden = is_on_desktop(path)
        if hidden:
            if admin_hides is not None and needs_admin(path):
                admin_hides.append(path)
            else:
                set_hidden_batch([path], True)
        cfg["entries"].append({"path": path, "name": name, "hidden_by_us": hidden})
        save_cfg()
        self.rebuild()
        return True

    def restore_entry(self, path):
        for e in cfg["entries"]:
            if e["path"].lower() == path.lower():
                if e.get("hidden_by_us") and os.path.exists(e["path"]):
                    set_hidden_batch([e["path"]], False)
                e["hidden_by_us"] = False
                save_cfg()
                self.rebuild()
                return

    def hide_entry(self, path):
        for e in cfg["entries"]:
            if e["path"].lower() == path.lower():
                set_hidden_batch([path], True)
                e["hidden_by_us"] = True
                save_cfg()
                self.rebuild()
                return

    def remove_entry(self, path):
        self.restore_entry(path)
        cfg["entries"] = [e for e in cfg["entries"] if e["path"].lower() != path.lower()]
        save_cfg()
        self.rebuild()

    def restore_all(self):
        paths = [
            e["path"]
            for e in cfg["entries"]
            if e.get("hidden_by_us") and os.path.exists(e["path"])
        ]
        set_hidden_batch(paths, False)
        for e in cfg["entries"]:
            e["hidden_by_us"] = False
        save_cfg()
        self.rebuild()
        return len(paths)

    def item_menu(self, btn, path, pos):
        entry = next((e for e in cfg["entries"] if e["path"].lower() == path.lower()), None)
        m = QMenu()
        m.setStyleSheet(MENU_SS)
        a_open = QAction("打开", m)
        a_open.triggered.connect(lambda: self.open_path(path))
        a_loc = QAction("打开所在文件夹", m)
        a_loc.triggered.connect(lambda: open_in_explorer(path))
        a_hide = QAction("在桌面隐藏本体", m)
        a_hide.setEnabled(is_on_desktop(path) and not (entry and entry.get("hidden_by_us")))
        a_hide.triggered.connect(lambda: self.hide_entry(path))
        a_rest = QAction("恢复到桌面显示", m)
        a_rest.setEnabled(bool(entry and entry.get("hidden_by_us")))
        a_rest.triggered.connect(lambda: self.restore_entry(path))
        a_rm = QAction("从面板移除（并恢复桌面显示）", m)
        a_rm.triggered.connect(lambda: self.remove_entry(path))
        m.addAction(a_open)
        m.addAction(a_loc)
        m.addSeparator()
        m.addAction(a_hide)
        m.addAction(a_rest)
        m.addAction(a_rm)
        m.exec(btn.mapToGlobal(pos))

    def dragEnterEvent(self, e):
        dlog("panel dragEnter formats=" + ",".join(e.mimeData().formats()))
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            e.accept()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            e.accept()

    def dropEvent(self, e):
        dlog("panel drop")
        admin_hides = []
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            dlog("  url=" + str(u.toString()) + " local=" + str(p))
            if p and os.path.exists(p):
                self.add_entry(p, admin_hides)
        if admin_hides:
            set_hidden_batch(admin_hides, True)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            if self._maximized:
                self.toggle_maximize()
            else:
                self.hide()

    def contextMenuEvent(self, e):
        m = QMenu()
        m.setStyleSheet(MENU_SS)
        a_add = QAction("添加文件…", m)
        a_add.triggered.connect(self.pick_file)
        a_dir = QAction("添加文件夹…", m)
        a_dir.triggered.connect(self.pick_dir)
        a_wp = QAction("设置最大化壁纸…（图片/视频）", m)
        a_wp.triggered.connect(self.pick_wallpaper)
        a_we = QAction("Wallpaper Engine 壁纸库…", m)
        a_we.triggered.connect(self.pick_we_wallpaper)
        m.addAction(a_add)
        m.addAction(a_dir)
        m.addSeparator()
        m.addAction(a_wp)
        m.addAction(a_we)
        if cfg.get("wallpaper"):
            a_wpc = QAction("清除最大化壁纸", m)
            a_wpc.triggered.connect(self.clear_wallpaper)
            m.addAction(a_wpc)
        m.exec(e.globalPos())

    def pick_wallpaper(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "选择壁纸", "",
            "壁纸 (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.mp4 *.webm *.m4v *.mkv)",
        )
        if p:
            cfg["wallpaper"] = p
            save_cfg()
            self._load_wallpaper()

    def pick_we_wallpaper(self):
        if not VIDEO_OK:
            QMessageBox.information(self, "工作面板", "视频壁纸支持未安装（缺少 PyQt6-Multimedia）。")
            return
        items = list_we_wallpapers()
        if not items:
            QMessageBox.information(
                self, "工作面板",
                "未找到 Wallpaper Engine 的创意工坊壁纸，可手动选择壁纸文件夹。",
            )
            self._browse_we_folder()
            return
        dlg = WallpaperPickerDialog(self, items)
        dlg.exec()
        if dlg.chosen:
            cfg["wallpaper"] = dlg.chosen
            save_cfg()
            self._load_wallpaper()
        elif dlg.browse_requested:
            self._browse_we_folder()

    def _browse_we_folder(self):
        d = QFileDialog.getExistingDirectory(self, "选择 Wallpaper Engine 壁纸文件夹")
        if not d:
            return
        found = None
        for f in os.listdir(d):
            if is_video_path(f) and os.path.isfile(os.path.join(d, f)):
                found = os.path.join(d, f)
                break
        if not found:
            QMessageBox.information(
                self, "工作面板", "该文件夹里没有视频文件（可能是场景/网页壁纸），暂不支持。"
            )
            return
        cfg["wallpaper"] = found
        save_cfg()
        self._load_wallpaper()

    def clear_wallpaper(self):
        cfg["wallpaper"] = ""
        save_cfg()
        self._load_wallpaper()
        self.update()

    def pick_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "选择文件或程序")
        if p:
            self.add_entry(p)

    def pick_dir(self):
        p = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if p:
            self.add_entry(p)


class Trigger(QWidget):
    def __init__(self):
        super().__init__()
        self.panel = None
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.setFixedSize(TRIGGER_SIZE, TRIGGER_SIZE)
        self.setToolTip("工作面板：点击展开（可拖动位置，可右键）")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._offset = None
        self._dragged = False
        self._hover = False
        self._force_visible_until = 0.0

        pos = cfg.get("trigger_pos")
        sg = QApplication.primaryScreen().availableGeometry()
        if pos:
            x = max(sg.left(), min(pos[0], sg.right() - TRIGGER_SIZE))
            y = max(sg.top(), min(pos[1], sg.bottom() - TRIGGER_SIZE))
            self.move(x, y)
        else:
            self.move(sg.right() - TRIGGER_SIZE - 14, sg.top() + sg.height() // 2 - TRIGGER_SIZE // 2)
        self.show()

        self._cover_timer = QTimer(self)
        self._cover_timer.setInterval(1000)
        self._cover_timer.timeout.connect(self._update_visibility)
        self._cover_timer.start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        r = TRIGGER_SIZE / 2 - 1
        path.addEllipse(1, 1, r * 2, r * 2)
        bg = QColor(255, 255, 255, 46) if self._hover else QColor(30, 30, 34, 215)
        p.fillPath(path, bg)
        p.setPen(QPen(QColor(255, 255, 255, 60 if self._hover else 34), 1))
        p.drawPath(path)
        p.setPen(QColor(245, 245, 247))
        f = p.font()
        f.setFamily("Segoe UI Emoji")
        f.setPixelSize(24)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "🗂")

    def enterEvent(self, _):
        self._hover = True
        self.update()

    def leaveEvent(self, _):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._offset = e.globalPosition().toPoint() - self.pos()
            self._dragged = False

    def mouseMoveEvent(self, e):
        if self._offset is not None:
            g = e.globalPosition().toPoint()
            d = g - (self.pos() + self._offset)
            if d.manhattanLength() > 5:
                self._dragged = True
            if self._dragged:
                sg = QApplication.primaryScreen().availableGeometry()
                nx = max(sg.left(), min(g.x() - self._offset.x(), sg.right() + 1 - TRIGGER_SIZE))
                ny = max(sg.top(), min(g.y() - self._offset.y(), sg.bottom() + 1 - TRIGGER_SIZE))
                self.move(nx, ny)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self._dragged:
                cfg["trigger_pos"] = [self.x(), self.y()]
                save_cfg()
            else:
                self.toggle_panel()
        self._offset = None

    def toggle_panel(self):
        if self.panel.isVisible():
            self.panel.hide()
        else:
            self.panel.popup()

    def contextMenuEvent(self, e):
        m = QMenu()
        m.setStyleSheet(MENU_SS)
        a_open = QAction("打开工作区", m)
        a_open.triggered.connect(self.toggle_panel)
        if WEB_OK:
            a_pet = QAction("切换为流萤桌宠", m)
            a_pet.triggered.connect(lambda: switch_pet_mode("live2d"))
        a_collapse = QAction("点击图标后收起", m)
        a_collapse.setCheckable(True)
        a_collapse.setChecked(cfg["close_on_open"])
        a_collapse.toggled.connect(self._set_close_on_open)
        a_auto = QAction("开机自启", m)
        a_auto.setCheckable(True)
        a_auto.setChecked(autostart_enabled())
        a_auto.toggled.connect(self._set_autostart)
        a_restore = QAction("全部恢复到桌面", m)
        a_restore.triggered.connect(self._restore_all)
        m.addAction(a_open)
        if WEB_OK:
            m.addAction(a_pet)
        m.addSeparator()
        m.addAction(a_collapse)
        m.addAction(a_auto)
        m.addSeparator()
        m.addAction(a_restore)
        m.addSeparator()
        a_quit = QAction("退出", m)
        a_quit.triggered.connect(QApplication.instance().quit)
        m.addAction(a_quit)
        m.exec(e.globalPos())

    def _set_close_on_open(self, on):
        cfg["close_on_open"] = on
        save_cfg()

    def _set_autostart(self, on):
        set_autostart(on)

    def _restore_all(self):
        n = self.panel.restore_all()
        QMessageBox.information(self, "工作面板", f"已恢复 {n} 个项目到桌面显示。")

    def _update_visibility(self):
        if time.monotonic() < self._force_visible_until:
            if not self.isVisible():
                self.show()
            return
        covered = self.panel._maximized or self._desktop_covered()
        if covered and self.isVisible():
            self.hide()
        elif not covered and not self.isVisible():
            self.show()

    def _desktop_covered(self):
        return desktop_covered(self, self.panel, TRIGGER_SIZE, TRIGGER_SIZE)

    def dragEnterEvent(self, e):
        dlog("trigger dragEnter formats=" + ",".join(e.mimeData().formats()))
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            e.accept()

    def dropEvent(self, e):
        dlog("trigger drop")
        admin_hides = []
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p and os.path.exists(p):
                self.panel.add_entry(p, admin_hides)
        if admin_hides:
            set_hidden_batch(admin_hides, True)
        self.panel.popup()


_app_state = {}


def wake_existing_ui():
    """Idempotently reveal the already-running instance."""
    trigger = _app_state.get("trigger")
    panel = _app_state.get("panel")
    if trigger is None or panel is None:
        return
    trigger._force_visible_until = time.monotonic() + 6.0
    if hasattr(trigger, "_set_runtime_suspended"):
        trigger._set_runtime_suspended(False)
    trigger.show()
    trigger.raise_()
    if panel.isVisible():
        panel.show()
        panel.raise_()
        panel.activateWindow()
    else:
        panel.popup()
    try:
        u32.SetForegroundWindow(int(panel.winId()))
    except Exception:
        pass
    dlog("wake event handled")


def switch_pet_mode(mode):
    panel = _app_state.get("panel")
    old = _app_state.get("trigger")
    if not panel or not old:
        return
    try:
        new = Live2DPet() if (WEB_OK and mode == "live2d") else Trigger()
    except Exception as ex:
        dlog(f"pet mode switch failed: {ex}")
        return
    cfg["pet_mode"] = mode
    save_cfg()
    new.panel = panel
    panel.trigger = new
    _app_state["trigger"] = new
    old.hide()
    if hasattr(old, "_destroy_pet_runtime"):
        old._destroy_pet_runtime()
        QTimer.singleShot(180, old.deleteLater)
    else:
        old.deleteLater()


if WEB_OK:

    class PetLogPage(QWebEnginePage):
        def javaScriptConsoleMessage(self, level, message, line, source):
            dlog(f"petjs {str(message)[:200]}")

    class Live2DPet(QWidget):
        def __init__(self):
            super().__init__()
            self.panel = None
            self._web_ready = False
            self._runtime_suspended = False
            self._destroying = False
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.Tool
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.NoDropShadowWindowHint
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setAcceptDrops(True)
            self.resize(PET_W, PET_H)
            self.setToolTip("流萤：单击随机互动并打开/收起工作区；拖动移动；右键设置")

            # Keep Chromium as a child of a lightweight transparent top-level
            # container.  During drag the child is replaced by a static frame,
            # so the WebGL surface itself never moves and cannot flash.
            self._web = QWebEngineView(self)
            self._web.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self._web.setGeometry(self.rect())
            self._web.setPage(PetLogPage(self._web))
            self._web.page().setBackgroundColor(QColor(0, 0, 0, 0))
            s = self._web.settings()
            s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            s.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
            self._web.loadFinished.connect(self._web_loaded)
            self._web.load(QUrl.fromLocalFile(os.path.join(WEB_DIR, "pet.html")))
            self._web.show()

            self._press = None
            self._press_local = None
            self._dragged = False
            self._was_covered = False
            self._aspect = None
            self._press_logged = False
            self._force_visible_until = 0.0
            self._pending_drag_pos = None
            self._drag_render_paused = False
            self._system_move = False
            self._system_move_save_pending = False
            self._snapshot_active = False
            self._cached_snapshot = QPixmap()
            self._extra_manifest = self._load_extra_manifest()

            self._snapshot = QLabel(self)
            self._snapshot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._snapshot.setStyleSheet("background: transparent;")
            self._snapshot.setGeometry(self.rect())
            self._snapshot.hide()

            self._overlay = QWidget(self)
            self._overlay.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
            self._overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            self._overlay.setStyleSheet("background: transparent;")
            self._overlay.setAcceptDrops(True)
            self._overlay.setMouseTracking(True)
            self._overlay.setCursor(Qt.CursorShape.PointingHandCursor)
            self._overlay.setGeometry(self.rect())
            self._overlay.installEventFilter(self)
            self._overlay.show()
            self._overlay.raise_()

            sg = QApplication.primaryScreen().availableGeometry()
            pos = cfg.get("trigger_pos")
            if pos:
                x = max(sg.left(), min(pos[0], sg.right() + 1 - PET_W))
                y = max(sg.top(), min(pos[1], sg.bottom() + 1 - PET_H))
                self.move(x, y)
            else:
                self.move(sg.right() + 1 - PET_W - 24, sg.bottom() + 1 - PET_H)
            self.show()

            self._aspect_timer = QTimer(self)
            self._aspect_timer.setInterval(300)
            self._aspect_timer.timeout.connect(self._poll_aspect)
            self._aspect_timer.start()

            self._cover_timer = QTimer(self)
            self._cover_timer.setInterval(1000)
            self._cover_timer.timeout.connect(self._update_visibility)
            self._cover_timer.start()

            self._focus_timer = QTimer(self)
            self._focus_timer.setInterval(200)
            self._focus_timer.timeout.connect(self._focus_tick)
            self._focus_timer.start()

            # Coalesce high-frequency mouse moves to the display refresh rate.
            # Moving a transparent WebEngine window for every raw mouse event
            # makes Chromium/DWM repeatedly rebuild the surface and visibly flash.
            self._drag_move_timer = QTimer(self)
            self._drag_move_timer.setInterval(16)
            self._drag_move_timer.timeout.connect(self._flush_drag_move)

            self._system_move_save_timer = QTimer(self)
            self._system_move_save_timer.setSingleShot(True)
            self._system_move_save_timer.setInterval(300)
            self._system_move_save_timer.timeout.connect(self._finish_system_move)

            self._snapshot_cleanup_timer = QTimer(self)
            self._snapshot_cleanup_timer.setSingleShot(True)
            self._snapshot_cleanup_timer.setInterval(200)
            self._snapshot_cleanup_timer.timeout.connect(self._complete_snapshot_handoff)

            self._snapshot_prime_timer = QTimer(self)
            self._snapshot_prime_timer.setSingleShot(True)
            self._snapshot_prime_timer.setInterval(500)
            self._snapshot_prime_timer.timeout.connect(self._prime_snapshot_cache)

        def page(self):
            return self._web.page()

        @staticmethod
        def _load_extra_manifest():
            path = os.path.join(WEB_DIR, "extras", "manifest.json")
            try:
                with open(path, encoding="utf-8") as stream:
                    data = json.load(stream)
                if int(data.get("version", 0)) == 1:
                    return data
            except Exception as ex:
                dlog(f"pet extras manifest error: {ex}")
            return {}

        def _pet_call(self, function_name, *args):
            if self._destroying:
                return
            name = json.dumps(str(function_name), ensure_ascii=False)
            argv = ",".join(json.dumps(arg, ensure_ascii=False) for arg in args)
            self.page().runJavaScript(
                f"if (typeof window[{name}] === 'function') window[{name}]({argv})"
            )

        def _destroy_pet_runtime(self):
            if self._destroying:
                return
            self._destroying = True
            self._runtime_suspended = True
            for name in (
                "_cover_timer", "_focus_timer", "_aspect_timer", "_drag_move_timer",
                "_system_move_save_timer", "_snapshot_cleanup_timer", "_snapshot_prime_timer",
            ):
                timer = getattr(self, name, None)
                if timer is not None:
                    timer.stop()
            self._press = None
            self._press_local = None
            self._pending_drag_pos = None
            self._system_move = False
            try:
                page = self.page()
                page.setAudioMuted(True)
                page.setLifecycleState(QWebEnginePage.LifecycleState.Active)
                page.runJavaScript(
                    "if (typeof window.petDestroy === 'function') window.petDestroy()"
                )
            except Exception:
                pass

        def _play_model_motion(self, index, expression=None):
            self._pet_call("petPlayMotion", int(index), expression, "manual")

        def _play_model_expression(self, index):
            self._pet_call("petPlayExpression", int(index))

        def _play_extra_action(self, key):
            self._pet_call("petPlayAction", str(key), {"loop": False, "source": "manual"})

        def _show_extra_bubble(self, category, mood):
            self._pet_call(
                "petShowBubble", str(category), str(mood), 3400, {"source": "manual"}
            )

        def _play_extra_voice(self, voice_id):
            self._pet_call("petPlayVoice", str(voice_id), {"source": "manual"})

        def _stop_extra_interaction(self):
            self._pet_call("petStopInteraction")

        def _web_loaded(self, ok):
            # loadFinished(False) still means the renderer has completed a
            # navigation (usually to an error page), so it can still be frozen.
            self._web_ready = True
            dlog(f"pet page loaded ok={bool(ok)}")
            if not ok:
                dlog("pet page load reported failure")
            if self._destroying:
                try:
                    self.page().setAudioMuted(True)
                    self.page().runJavaScript(
                        "if (typeof window.petDestroy === 'function') window.petDestroy()"
                    )
                except Exception:
                    pass
                return
            self._raise_input_overlay()
            self._apply_pet_volume(cfg.get("pet_volume", 50), persist=False)
            self._apply_pet_auto_interval(
                cfg.get("pet_auto_interval_sec", 300), persist=False
            )
            self._sync_runtime_state()
            self._snapshot_prime_timer.start()

        def _apply_pet_volume(self, value, persist=True):
            try:
                value = max(0, min(100, int(value)))
            except (TypeError, ValueError):
                value = 50
            cfg["pet_volume"] = value
            self.page().runJavaScript(
                "if (typeof window.petSetVolume === 'function') "
                f"window.petSetVolume({value / 100.0:.2f})"
            )
            if persist:
                save_cfg()

        def _apply_pet_auto_interval(self, seconds, persist=True):
            allowed = {value for value, _label in AUTO_INTERVAL_CHOICES}
            try:
                seconds = int(seconds)
            except (TypeError, ValueError):
                seconds = 300
            if seconds not in allowed:
                seconds = 300
            cfg["pet_auto_interval_sec"] = seconds
            self._pet_call("petSetAutoInterval", seconds)
            if persist:
                save_cfg()

        def _sync_runtime_state(self):
            page = self.page()
            suspended = self._runtime_suspended or self._destroying
            state = "true" if suspended else "false"
            script = (
                "if (typeof window.petSetSuspended === 'function') "
                f"window.petSetSuspended({state})"
            )
            if suspended:
                try:
                    page.setAudioMuted(True)
                except Exception:
                    pass
                if not self._web_ready:
                    return

                def freeze_page(_result=None):
                    try:
                        if (self._runtime_suspended or self._destroying) and not self.isVisible():
                            page.setLifecycleState(QWebEnginePage.LifecycleState.Frozen)
                    except Exception:
                        pass

                try:
                    page.runJavaScript(script, freeze_page)
                    QTimer.singleShot(150, freeze_page)
                except Exception:
                    freeze_page()
            else:
                try:
                    page.setLifecycleState(QWebEnginePage.LifecycleState.Active)
                except Exception:
                    pass
                if not self._web_ready:
                    try:
                        page.setAudioMuted(False)
                    except Exception:
                        pass
                    return

                def unmute_page(_result=None):
                    if not self._runtime_suspended:
                        try:
                            page.setAudioMuted(False)
                        except Exception:
                            pass

                try:
                    page.runJavaScript(script, unmute_page)
                except Exception:
                    unmute_page()

        def _set_runtime_suspended(self, suspended):
            suspended = bool(suspended)
            if self._destroying and not suspended:
                return
            changed = self._runtime_suspended != suspended
            if not changed:
                return
            self._runtime_suspended = suspended
            if hasattr(self, "_focus_timer"):
                if suspended:
                    self._focus_timer.stop()
                elif not self._focus_timer.isActive():
                    self._focus_timer.start()
            if hasattr(self, "_aspect_timer"):
                if suspended:
                    self._aspect_timer.stop()
                elif self._aspect is None and not self._aspect_timer.isActive():
                    self._aspect_timer.start()
            self._sync_runtime_state()
            dlog("pet runtime " + ("suspended" if suspended else "resumed"))

        def _poll_aspect(self):
            def cb(r):
                if r and "/" in str(r):
                    try:
                        w, h = str(r).split("/")
                        self._aspect = float(w) / float(h)
                        dlog(f"pet aspect {self._aspect:.6f}")
                        self._aspect_timer.stop()
                        self._apply_size()
                    except Exception:
                        pass

            self.page().runJavaScript(
                "typeof window.petAspect === 'function' ? window.petAspect() : ''",
                cb,
            )

        def _apply_size(self):
            if not self._aspect:
                return
            screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
            sg = screen.availableGeometry()
            h = int(max(PET_MIN_H, min(int(cfg.get("pet_h", 480)), sg.height())))
            w = int(h * self._aspect)
            if w > sg.width():
                w = sg.width()
                h = int(w / self._aspect)
            self.setFixedSize(w, h)
            self._cached_snapshot = QPixmap()
            x = min(self.x(), sg.right() + 1 - w)
            y = min(self.y(), sg.bottom() + 1 - h)
            self.move(max(sg.left(), x), max(sg.top(), y))
            if hasattr(self, "_snapshot_prime_timer") and not self._destroying:
                self._snapshot_prime_timer.start()

        def _focus_tick(self):
            if not self.isVisible() or self._press is not None or self._system_move:
                return
            g = QCursor.pos()
            nx = (g.x() - self.x()) / max(1, self.width())
            ny = (g.y() - self.y()) / max(1, self.height())
            self.page().runJavaScript(
                f"if (typeof window.petFocus === 'function') window.petFocus({nx:.3f}, {ny:.3f})"
            )

        def _update_visibility(self):
            if self._destroying:
                return
            if self._press is not None or self._system_move:
                return
            covered = self.panel._maximized or desktop_covered(
                self, self.panel, self.width(), self.height()
            )
            if covered:
                try:
                    self.page().setAudioMuted(True)
                except Exception:
                    pass
                if self.isVisible():
                    self._was_covered = True
                    self.hide()
                self._set_runtime_suspended(True)
                return
            if time.monotonic() < self._force_visible_until:
                self._set_runtime_suspended(False)
                if not self.isVisible():
                    self.show()
                    self._raise_input_overlay()
                return
            self._set_runtime_suspended(False)
            if not self.isVisible():
                self.show()
                self._raise_input_overlay()

        def react(self, local_pos=None):
            if self._destroying or self._runtime_suspended or not self._web_ready:
                return
            if self.panel is not None and self.panel._maximized:
                return
            self._pet_call("petRandomExtra", "click")

        def toggle_panel(self):
            if self.panel.isVisible():
                self.panel.hide()
            else:
                self.panel.popup()

        def _press_at(self, e):
            if e.button() == Qt.MouseButton.LeftButton:
                if self._snapshot_cleanup_timer.isActive() or self._snapshot.isVisible():
                    self._complete_snapshot_handoff()
                self._press = e.globalPosition().toPoint() - self.pos()
                self._press_local = e.position().toPoint()
                self._dragged = False
                self._pending_drag_pos = None
                self._system_move = False

        def _move_at(self, e):
            if self._press is not None:
                g = e.globalPosition().toPoint()
                d = g - (self.pos() + self._press)
                if d.manhattanLength() > 6:
                    if not self._dragged:
                        self._dragged = True
                        snapshot_ok = self._begin_drag_snapshot()
                        if not snapshot_ok:
                            self._set_drag_render_paused(True)
                        # Let Windows/DWM move the layered WebEngine window as
                        # one compositor surface.  At this point Chromium is
                        # hidden behind a static frame, so only a raster window
                        # is being moved.
                        try:
                            wh = self.windowHandle()
                            self._system_move = bool(wh and wh.startSystemMove())
                        except Exception:
                            self._system_move = False
                        if self._system_move:
                            # Windows takes over mouse capture and may consume
                            # the matching release event.  moveEvent + a quiet
                            # timer below finalize and persist the operation.
                            self._press = None
                            self._system_move_save_pending = True
                            self._system_move_save_timer.start()
                if self._dragged and not self._system_move:
                    screen = QApplication.screenAt(g) or QApplication.primaryScreen()
                    sg = screen.availableGeometry()
                    nx = max(sg.left(), min(g.x() - self._press.x(), sg.right() + 1 - self.width()))
                    ny = max(sg.top(), min(g.y() - self._press.y(), sg.bottom() + 1 - self.height()))
                    self._pending_drag_pos = (nx, ny)
                    if not self._drag_move_timer.isActive():
                        self._drag_move_timer.start()

        def _flush_drag_move(self):
            if self._pending_drag_pos is not None:
                pos = self._pending_drag_pos
                self._pending_drag_pos = None
                self.move(pos[0], pos[1])

        def _set_drag_render_paused(self, paused):
            if self._drag_render_paused == paused:
                return
            self._drag_render_paused = paused
            self.page().runJavaScript(
                "if (typeof window.petSetDragging === 'function') "
                f"window.petSetDragging({'true' if paused else 'false'})"
            )

        @staticmethod
        def _snapshot_has_content(pix):
            if pix is None or pix.isNull():
                return False
            image = pix.toImage()
            sx = max(1, image.width() // 24)
            sy = max(1, image.height() // 24)
            for y in range(0, image.height(), sy):
                for x in range(0, image.width(), sx):
                    if image.pixelColor(x, y).alpha() > 4:
                        return True
            return False

        def _fallback_drag_snapshot(self):
            source = QPixmap(os.path.join(
                WEB_DIR, "extras", "actions", "Standby", "0.png"
            ))
            if source.isNull():
                return QPixmap()
            result = QPixmap(self.size())
            result.fill(Qt.GlobalColor.transparent)
            scaled = source.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter = QPainter(result)
            painter.drawPixmap(
                (result.width() - scaled.width()) // 2,
                result.height() - scaled.height(),
                scaled,
            )
            painter.end()
            return result

        def _prime_snapshot_cache(self):
            if self._destroying or not self._web_ready or not self.isVisible():
                return
            pix = self._web.grab()
            if self._snapshot_has_content(pix):
                self._cached_snapshot = pix.copy()
                dlog("drag snapshot cache primed")

        def _begin_drag_snapshot(self):
            self._snapshot_cleanup_timer.stop()
            self._snapshot_prime_timer.stop()
            self._set_drag_render_paused(True)
            pix = self._web.grab()
            if self._snapshot_has_content(pix):
                self._cached_snapshot = pix.copy()
            elif not self._cached_snapshot.isNull():
                pix = self._cached_snapshot.scaled(
                    self.size(),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                dlog("drag snapshot using cached frame")
            else:
                pix = self._fallback_drag_snapshot()
                dlog("drag snapshot using 2d fallback")
            if pix.isNull():
                # Hiding the accelerated child is still preferable to moving a
                # live transparent WebEngine surface, which is the flash path.
                pix = QPixmap(self.size())
                pix.fill(Qt.GlobalColor.transparent)

            self._snapshot.setGeometry(self.rect())
            self._snapshot.setPixmap(pix)
            self._snapshot.show()
            self._snapshot.raise_()
            self._overlay.raise_()
            QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
            self._web.hide()
            self._snapshot_active = True
            dlog("drag snapshot active")
            return True

        def _end_drag_visual(self):
            if self._destroying:
                return
            self._set_drag_render_paused(False)
            if not self._snapshot_active:
                self._web.show()
                self._raise_input_overlay()
                return
            # Keep the frozen frame above Chromium briefly while its first
            # frame is presented at the new location.
            self._web.show()
            self._snapshot.raise_()
            self._overlay.raise_()
            self._snapshot_cleanup_timer.start()

        def _complete_snapshot_handoff(self):
            self._snapshot_cleanup_timer.stop()
            self._snapshot.hide()
            self._snapshot.clear()
            self._snapshot_active = False
            if self._destroying:
                self._web.hide()
                return
            self._web.show()
            self._raise_input_overlay()
            self._snapshot_prime_timer.start()

        def _finish_system_move(self):
            if QApplication.mouseButtons() & Qt.MouseButton.LeftButton:
                self._system_move_save_timer.start()
                return
            if self._system_move_save_pending:
                cfg["trigger_pos"] = [self.x(), self.y()]
                save_cfg()
                self._system_move_save_pending = False
            self._system_move = False
            self._dragged = False
            self._press_local = None
            self._force_visible_until = time.monotonic() + 1.0
            self._end_drag_visual()

        def _release_at(self, e):
            if e.button() == Qt.MouseButton.LeftButton:
                if self._press is None and not self._dragged:
                    return
                if self._dragged:
                    self._flush_drag_move()
                    self._drag_move_timer.stop()
                    cfg["trigger_pos"] = [self.x(), self.y()]
                    save_cfg()
                    self._system_move_save_pending = False
                    self._system_move_save_timer.stop()
                    self._end_drag_visual()
                else:
                    self.react(self._press_local)
                    self.toggle_panel()
                self._press = None
                self._press_local = None
                self._pending_drag_pos = None
                self._system_move = False
                self._dragged = False

        def _wheel_at(self, e):
            d = e.angleDelta().y()
            if d:
                screen = QApplication.screenAt(e.globalPosition().toPoint()) or QApplication.primaryScreen()
                max_h = min(1000, screen.availableGeometry().height())
                h = int(max(
                    PET_MIN_H,
                    min(self.height() + (PET_WHEEL_STEP if d > 0 else -PET_WHEEL_STEP), max_h),
                ))
                cfg["pet_h"] = h
                save_cfg()
                self._apply_size()

        def _drop_at(self, e):
            admin_hides = []
            for u in e.mimeData().urls():
                p = u.toLocalFile()
                if p and os.path.exists(p):
                    self.panel.add_entry(p, admin_hides)
            if admin_hides:
                set_hidden_batch(admin_hides, True)
            self.panel.popup()

        def _raise_input_overlay(self):
            self._web.setGeometry(self.rect())
            self._snapshot.setGeometry(self.rect())
            if self._snapshot_active or self._snapshot.isVisible():
                self._snapshot.raise_()
            self._overlay.setGeometry(self.rect())
            self._overlay.show()
            self._overlay.raise_()

        def eventFilter(self, obj, ev):
            t = ev.type()
            if t == QEvent.Type.MouseButtonPress:
                if ev.button() != Qt.MouseButton.LeftButton:
                    return False
                if not self._press_logged:
                    self._press_logged = True
                    try:
                        dlog(f"input press via {obj.metaObject().className()}")
                    except Exception:
                        dlog("input press")
                self._press_at(ev)
                return True
            if t == QEvent.Type.MouseMove:
                if self._press is not None:
                    self._move_at(ev)
                    return True
                return False
            if t == QEvent.Type.MouseButtonRelease:
                if ev.button() != Qt.MouseButton.LeftButton:
                    return False
                self._release_at(ev)
                return True
            if t == QEvent.Type.Wheel:
                self._wheel_at(ev)
                return True
            if t == QEvent.Type.ContextMenu:
                self._open_menu(ev.globalPos())
                return True
            if t == QEvent.Type.DragEnter or t == QEvent.Type.DragMove:
                if ev.mimeData().hasUrls():
                    ev.acceptProposedAction()
                return True
            if t == QEvent.Type.Drop:
                self._drop_at(ev)
                return True
            return super().eventFilter(obj, ev)

        def resizeEvent(self, e):
            super().resizeEvent(e)
            if hasattr(self, "_overlay"):
                self._raise_input_overlay()

        def moveEvent(self, e):
            super().moveEvent(e)
            if getattr(self, "_system_move", False) and hasattr(self, "_system_move_save_timer"):
                self._system_move_save_pending = True
                self._system_move_save_timer.start()

        def mousePressEvent(self, e):
            self._press_at(e)

        def mouseMoveEvent(self, e):
            self._move_at(e)

        def mouseReleaseEvent(self, e):
            self._release_at(e)

        def wheelEvent(self, e):
            self._wheel_at(e)

        def contextMenuEvent(self, e):
            self._open_menu(e.globalPos())

        def _open_menu(self, gpos):
            m = QMenu()
            m.setStyleSheet(MENU_SS)
            a_open = QAction("打开工作区", m)
            a_open.triggered.connect(self.toggle_panel)
            a_ball = QAction("切换为悬浮球", m)
            a_ball.triggered.connect(lambda: switch_pet_mode("ball"))

            def styled_menu(title, parent):
                menu = QMenu(title, parent)
                menu.setStyleSheet(MENU_SS)
                return menu

            extras = self._extra_manifest
            extras_available = bool(extras)

            action_menu = styled_menu("她的动作", m)
            for item in extras.get("modelMotions", []):
                action = QAction(str(item.get("label", item.get("id"))), action_menu)
                index = int(item.get("id", 0))
                expression = item.get("expression")
                action.triggered.connect(
                    lambda _checked=False, i=index, ex=expression: self._play_model_motion(i, ex)
                )
                action_menu.addAction(action)
            sprite_menu = styled_menu("二维动作", action_menu)
            for key, item in extras.get("actions", {}).items():
                action = QAction(str(item.get("label", key)), sprite_menu)
                action.triggered.connect(
                    lambda _checked=False, action_key=key: self._play_extra_action(action_key)
                )
                sprite_menu.addAction(action)
            if action_menu.actions():
                action_menu.addSeparator()
            action_menu.addMenu(sprite_menu)
            action_menu.setEnabled(extras_available)

            expression_menu = styled_menu("她的表情", m)
            for item in extras.get("modelExpressions", []):
                action = QAction(str(item.get("label", item.get("id"))), expression_menu)
                index = int(item.get("id", 0))
                action.triggered.connect(
                    lambda _checked=False, i=index: self._play_model_expression(i)
                )
                expression_menu.addAction(action)
            if expression_menu.actions():
                expression_menu.addSeparator()
            stickers_menu = styled_menu("表情贴纸", expression_menu)
            for category, group in extras.get("bubbles", {}).items():
                category_menu = styled_menu(str(group.get("label", category)), stickers_menu)
                for mood, item in group.get("items", {}).items():
                    label = str(item.get("label", mood))
                    variants = len(item.get("files", []))
                    if variants > 1:
                        label += f"（{variants}张随机）"
                    action = QAction(label, category_menu)
                    action.triggered.connect(
                        lambda _checked=False, c=category, md=mood: self._show_extra_bubble(c, md)
                    )
                    category_menu.addAction(action)
                stickers_menu.addMenu(category_menu)
            expression_menu.addMenu(stickers_menu)
            expression_menu.setEnabled(extras_available)

            voice_menu = styled_menu("她的语音", m)
            if hasattr(voice_menu, "setToolTipsVisible"):
                voice_menu.setToolTipsVisible(True)
            for _group_id, group in extras.get("voices", {}).items():
                group_menu = styled_menu(str(group.get("label", "语音")), voice_menu)
                if hasattr(group_menu, "setToolTipsVisible"):
                    group_menu.setToolTipsVisible(True)
                for item in group.get("items", []):
                    voice_id = str(item.get("id", ""))
                    full_label = str(item.get("label", voice_id))
                    short_label = full_label if len(full_label) <= 20 else full_label[:20] + "…"
                    action = QAction(short_label, group_menu)
                    action.setToolTip(full_label)
                    action.triggered.connect(
                        lambda _checked=False, vid=voice_id: self._play_extra_voice(vid)
                    )
                    group_menu.addAction(action)
                voice_menu.addMenu(group_menu)
            voice_menu.setEnabled(extras_available)

            a_stop_interaction = QAction("停止当前互动", m)
            a_stop_interaction.triggered.connect(self._stop_extra_interaction)
            a_stop_interaction.setEnabled(extras_available)

            allowed_intervals = {value for value, _label in AUTO_INTERVAL_CHOICES}
            try:
                current_interval = int(cfg.get("pet_auto_interval_sec", 300))
            except (TypeError, ValueError):
                current_interval = 300
            if current_interval not in allowed_intervals:
                current_interval = 300
            auto_interval_menu = styled_menu("自动抽取间隔", m)
            auto_interval_menu.setToolTip("未被最大化窗口覆盖时，随机抽取动作、贴纸或语音")
            interval_group = QActionGroup(auto_interval_menu)
            interval_group.setExclusive(True)
            for seconds, label in AUTO_INTERVAL_CHOICES:
                action = QAction(label, auto_interval_menu)
                action.setCheckable(True)
                action.setChecked(seconds == current_interval)
                action.triggered.connect(
                    lambda _checked=False, sec=seconds: self._apply_pet_auto_interval(sec)
                )
                interval_group.addAction(action)
                auto_interval_menu.addAction(action)

            try:
                initial_volume = max(0, min(100, int(cfg.get("pet_volume", 50))))
            except (TypeError, ValueError):
                initial_volume = 50
            volume_widget = QWidget(m)
            volume_widget.setMinimumWidth(220)
            volume_layout = QVBoxLayout(volume_widget)
            volume_layout.setContentsMargins(12, 5, 12, 7)
            volume_layout.setSpacing(4)
            volume_header = QHBoxLayout()
            volume_title = QLabel("她的音量", volume_widget)
            volume_value = QLabel(f"{initial_volume}%", volume_widget)
            volume_title.setStyleSheet("color:#f2f2f7; font:9pt 'Microsoft YaHei UI';")
            volume_value.setStyleSheet("color:rgba(255,255,255,150); font:9pt 'Segoe UI';")
            volume_header.addWidget(volume_title)
            volume_header.addStretch(1)
            volume_header.addWidget(volume_value)
            volume_layout.addLayout(volume_header)
            volume_slider = QSlider(Qt.Orientation.Horizontal, volume_widget)
            volume_slider.setRange(0, 100)
            volume_slider.setSingleStep(1)
            volume_slider.setPageStep(10)
            volume_slider.setValue(initial_volume)
            volume_slider.setToolTip("流萤动作与语音音量；0% 为静音")
            volume_slider.setStyleSheet(
                "QSlider::groove:horizontal { height:4px; border-radius:2px; "
                "background:rgba(255,255,255,45); }"
                "QSlider::sub-page:horizontal { border-radius:2px; background:#7fc8ff; }"
                "QSlider::handle:horizontal { width:14px; margin:-5px 0; border-radius:7px; "
                "background:#f7fbff; }"
            )
            volume_layout.addWidget(volume_slider)

            def preview_volume(value):
                volume_value.setText(f"{value}%")
                self._apply_pet_volume(value, persist=False)

            volume_slider.valueChanged.connect(preview_volume)
            a_volume = QWidgetAction(m)
            a_volume.setDefaultWidget(volume_widget)
            a_collapse = QAction("点击图标后收起", m)
            a_collapse.setCheckable(True)
            a_collapse.setChecked(cfg["close_on_open"])
            a_collapse.toggled.connect(self._set_close_on_open)
            a_auto = QAction("开机自启", m)
            a_auto.setCheckable(True)
            a_auto.setChecked(autostart_enabled())
            a_auto.toggled.connect(set_autostart)
            a_restore = QAction("全部恢复到桌面", m)
            a_restore.triggered.connect(self._restore_all)
            a_quit = QAction("退出", m)
            a_quit.triggered.connect(self._quit_application)
            m.addAction(a_open)
            m.addAction(a_ball)
            m.addSeparator()
            m.addMenu(action_menu)
            m.addMenu(expression_menu)
            m.addMenu(voice_menu)
            m.addAction(a_stop_interaction)
            m.addMenu(auto_interval_menu)
            m.addSeparator()
            m.addAction(a_volume)
            m.addSeparator()
            m.addAction(a_collapse)
            m.addAction(a_auto)
            m.addSeparator()
            m.addAction(a_restore)
            m.addSeparator()
            m.addAction(a_quit)
            m.exec(gpos)
            if volume_slider.value() != initial_volume:
                save_cfg()

        def _quit_application(self):
            self._destroy_pet_runtime()
            QTimer.singleShot(100, QApplication.instance().quit)

        def _set_close_on_open(self, on):
            cfg["close_on_open"] = on
            save_cfg()

        def _restore_all(self):
            n = self.panel.restore_all()
            QMessageBox.information(self, "工作面板", f"已恢复 {n} 个项目到桌面显示。")

        def dragEnterEvent(self, e):
            if e.mimeData().hasUrls():
                e.acceptProposedAction()

        def dropEvent(self, e):
            admin_hides = []
            for u in e.mimeData().urls():
                p = u.toLocalFile()
                if p and os.path.exists(p):
                    self.panel.add_entry(p, admin_hides)
            if admin_hides:
                set_hidden_batch(admin_hides, True)
            self.panel.popup()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    dlog(f"start pid={os.getpid()} admin={bool(ctypes.windll.shell32.IsUserAnAdmin())}")

    k32 = ctypes.windll.kernel32
    k32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    k32.CreateEventW.restype = wintypes.HANDLE
    k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    k32.CreateMutexW.restype = wintypes.HANDLE
    k32.SetEvent.argtypes = [wintypes.HANDLE]
    k32.SetEvent.restype = wintypes.BOOL
    k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.WaitForSingleObject.restype = wintypes.DWORD
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL

    # The optional namespace is useful for release smoke tests; normal users
    # leave it unset and retain strict single-instance behavior.
    instance_tag = re.sub(
        r"[^A-Za-z0-9_-]", "", os.environ.get("DESKPET_INSTANCE_TAG", "")
    )[:32]

    # All instances open the same auto-reset event before taking the mutex.
    # A secondary launch can therefore wake the primary even during startup.
    wake_event = k32.CreateEventW(
        None, False, False, "Local\\WorkspacePanel_WakeEvent_v1" + instance_tag
    )
    mutex = k32.CreateMutexW(None, False, "WorkspacePanel_SingleInstance" + instance_tag)
    already_running = k32.GetLastError() == 183
    if already_running:
        try:
            ctypes.windll.user32.AllowSetForegroundWindow(0xFFFFFFFF)
        except Exception:
            pass
        if wake_event:
            k32.SetEvent(wake_event)
            k32.CloseHandle(wake_event)
        if mutex:
            k32.CloseHandle(mutex)
        dlog("already running, wake requested")
        sys.exit(0)

    import traceback

    def _hook(t, v, tb):
        dlog("EXC " + "".join(traceback.format_exception(t, v, tb)).replace("\n", " | "))

    sys.excepthook = _hook
    try:
        import faulthandler
        faulthandler.enable(
            open(os.path.join(CONFIG_DIR, "crash.log"), "a", encoding="utf-8")
        )
    except Exception:
        pass
    if WEB_OK and cfg.get("pet_mode") == "live2d":
        trigger = Live2DPet()
    else:
        trigger = Trigger()
    panel = Panel(trigger)
    trigger.panel = panel
    _app_state["trigger"] = trigger
    _app_state["panel"] = panel

    def cleanup_current_pet():
        current = _app_state.get("trigger")
        if current is not None and hasattr(current, "_destroy_pet_runtime"):
            current._destroy_pet_runtime()

    app.aboutToQuit.connect(cleanup_current_pet)

    # Automated packaging tests can request a clean self-exit without adding a
    # user-facing command-line option or changing normal runtime behavior.
    try:
        smoke_exit_ms = int(os.environ.get("DESKPET_SMOKE_EXIT_MS", "0"))
    except ValueError:
        smoke_exit_ms = 0
    if smoke_exit_ms > 0:
        QTimer.singleShot(max(1000, smoke_exit_ms), app.quit)

    wake_timer = QTimer(app)
    wake_timer.setInterval(100)

    def poll_wake_event():
        if wake_event and k32.WaitForSingleObject(wake_event, 0) == 0:
            wake_existing_ui()

    wake_timer.timeout.connect(poll_wake_event)
    wake_timer.start()
    _app_state["wake_timer"] = wake_timer
    _app_state["wake_event"] = wake_event
    _app_state["mutex"] = mutex

    try:
        rc = app.exec()
    finally:
        if wake_event:
            k32.CloseHandle(wake_event)
        if mutex:
            k32.CloseHandle(mutex)
    sys.exit(rc)


if __name__ == "__main__":
    main()
