"""
vibeCopy - a friendly dark-mode GUI for Windows robocopy.

Single-file app: Python 3.8+ (tested on 3.11), standard library only.
Double-click vibeCopy.pyw to start it (no console window).
Nothing is saved: profiles live in this file, and changes last until the app is closed.
Instructions: see HELP_URL below.
"""

import codecs
import collections
import ctypes
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from tkinter import filedialog, ttk

APP_NAME = "vibeCopy"
APP_VERSION = "3.0"
HELP_URL = "https://github.com/petandk/Vibe-Coding/blob/main/vibeCopy/README.md"   # the instructions
IS_WIN = sys.platform == "win32"
DEFAULT_LOG = os.path.join(os.path.expanduser("~"), "Documents", "vibeCopy logs", "robocopy.log")


# =============================================================================
# Palette  -  "Forest & Coral"
# =============================================================================

C = dict(
    bg="#0E1311",          # window background (near-black green)
    card="#151C19",        # cards
    raised="#1D2622",      # info boxes, stat tiles, buttons
    field="#0F1613",       # inputs, log
    hover="#26312C",
    border="#26322D",
    border_hi="#3A4A43",
    text="#E8EFEA",
    soft="#C3CFC8",        # normal log text
    muted="#91A49B",
    faint="#5A6A63",
    white="#FFFFFF",
    accent="#FF7A59",      # coral
    accent_hover="#FF9474",
    accent_press="#E5603E",
    on_accent="#1E0F0A",
    sel="#4A2C22",
    mint="#3DD9A4",        # progress / success
    amber="#F4BF4F",       # warnings
    danger="#FF5C7A",
    danger_bg="#3A1D24",
)


# =============================================================================
# Actions (WHAT happens to your files) - always chosen by the user
# =============================================================================

ACTIONS = [
    ("copy", "Copy", "Copy new and changed files. Nothing is ever deleted."),
    ("update", "Update", "Copy new and changed files, but never overwrite a file that is newer in the "
                         "destination (/XO). Good for refreshing a backup."),
    ("mirror", "Mirror ⚠", "Make the destination an exact copy of the source (/MIR). DELETES files in the "
                           "destination that aren't in the source."),
    ("move", "Move ⚠", "Copy, then DELETE the files from the source (/MOVE)."),
]
ACTION_TEXT = {k: (title, desc) for k, title, desc in ACTIONS}
DANGER_ACTIONS = ("mirror", "move")


# =============================================================================
# Speed profiles (HOW to copy fast) - recommended automatically after the scan
# Edit these to change the built-in defaults. Changes made in the app are temporary.
# =============================================================================

PROFILE_DEFAULTS = dict(threads=8, unbuffered=False, restartable=False, fft=False,
                        skip_junctions=True, retries=2, wait=2)

PROFILES = [
    dict(name="Everyday", set=dict(threads=8),
         use="A normal folder: documents, or a few hundred files of any size.",
         why="There's not much to optimize. 8 parallel threads are quick without overloading the disks.",
         watch="Nothing special. This is the safe default."),
    dict(name="Many small files", set=dict(threads=64),
         use="Photo libraries, source code, mail archives: thousands to millions of small files.",
         why="With tiny files, most of the time goes to opening, creating and closing files, not to moving "
             "data. 64 parallel threads hide that overhead and keep the disks busy.",
         watch="On a hard disk (HDD), too many threads make the disk head jump around. vibeCopy lowers "
               "the thread count automatically when it detects one."),
    dict(name="Mixed sizes", set=dict(threads=16),
         use="User folders and project folders: a mix of documents, photos and videos.",
         why="16 threads is enough parallelism for the small files, without the big ones fighting "
             "over the disk.",
         watch="Nothing special."),
    dict(name="Few big files", set=dict(threads=1, unbuffered=True),
         use="ISOs, virtual machine disks, movies, backup archives: a handful of files of several GB each.",
         why="Unbuffered I/O (/J) skips the Windows RAM cache. That's faster for huge files and keeps your PC "
             "responsive. Copying one file at a time gives a smooth live % and ETA.",
         watch="/J makes small files slower, so this profile isn't meant for mixed folders."),
    dict(name="Many big files", set=dict(threads=8, unbuffered=True),
         use="Video projects, RAW footage, game libraries: lots of large files.",
         why="8 large files are copied in parallel with unbuffered I/O, without filling your RAM with cache.",
         watch="Progress moves in steps, because robocopy only reports a file once it's finished."),
    dict(name="Network / NAS", set=dict(threads=16, restartable=True, fft=True, retries=5, wait=5),
         use="Copying to or from a NAS, a server share (\\\\server\\share) or a mapped network drive.",
         why="Restartable mode (/Z) resumes a file after a network drop instead of starting it over. "
             "/FFT tolerates the 2-second timestamps of many NAS devices, so files aren't copied again "
             "every time. More retries help on unreliable Wi-Fi.",
         watch="/Z adds a bit of overhead on local disks."),
    dict(name="USB / external drive", set=dict(threads=4, retries=3, wait=3),
         use="Copying to or from a USB stick, a USB hard disk or an SD card.",
         why="USB drives, especially sticks and portable hard disks, get slower with many parallel "
             "writes, so 4 threads is the sweet spot. Fewer retries waste less time if the drive is unplugged.",
         watch="Unplug the drive only after vibeCopy says Done. Cheap USB sticks are slow with small "
               "files whatever the settings."),
]
PROFILE_BY_NAME = {p["name"]: p for p in PROFILES}

FIELD_DEFAULTS = dict(
    src="", dst="", files="*.*", xf="", xd="", action="copy", subdirs=True,
    dir_times=True, copy_perms=False, backup=False, dry_run=False,
    log=False, log_path=DEFAULT_LOG, verbose=False, when_done="Do nothing",
)
ALL_DEFAULTS = {**FIELD_DEFAULTS, **PROFILE_DEFAULTS}
WHEN_DONE = ("Do nothing", "Sleep", "Shut down")

SMALL, BIG, FAT32_MAX = 1 << 20, 100 << 20, 4 * (1 << 30) - 1

GUIDE_RULES = [
    ("Automatic", "After you choose the folders, vibeCopy scans what needs copying, checks your drives, "
                  "and picks a profile for you. You can always choose another one."),
    ("Size", "Most files under ~1 MB → “Many small files”.  Most of the data in files over "
             "~100 MB → “Few big files” or “Many big files”."),
    ("Count", "Fewer than ~1,000 files → “Everyday”, unless they're big files."),
    ("Drives", "Network → “Network / NAS”.  USB stick, USB disk or SD card → “USB / external drive”.  "
               "Hard disks (HDD) automatically get fewer threads."),
    ("Action", "Copy, Update, Mirror and Move are chosen separately. The profile only decides HOW FAST, "
               "never WHAT happens to your files."),
]

SCHEDULE_STEPS = [
    "Open the Start menu, type “Task Scheduler” and open it.",
    "On the right, click “Create Basic Task…”. Give it a name, e.g. “Nightly photo backup”.",
    "Trigger: choose when it runs, e.g. Daily at 02:00, Weekly, or “When I log on”.",
    "Action: “Start a program”, then Browse… and pick your .bat file. Click Finish.",
    "Optional: open the task's Properties and tick “Run whether user is logged on or not”, so it also runs "
    "when you're signed out.",
]
SCHEDULE_TIPS = [
    "Tick “Write log file” (Speed profile → Fine-tune) before saving the .bat, so every scheduled run leaves a log.",
    "Scheduled tasks don't see mapped network drives (Z:) when you're signed out: use \\\\server\\share paths instead.",
    "The .bat returns 0 when robocopy succeeded, so Task Scheduler's “Last Run Result” shows 0x0 for a good run.",
    "Backup mode (/B) needs “Run with highest privileges” in the task's Properties.",
]

TIPS = dict(
    files="Which files to copy. Wildcards, separated by spaces: *.jpg *.png\nLeave *.* for everything.",
    xf="Files to skip (/XF). Wildcards or names, separated by spaces: *.tmp ~$* Thumbs.db",
    xd="Folders to skip (/XD). Names or full paths, separated by spaces: node_modules .git \"My Temp\"",
    subdirs="/E: include all subfolders (even empty ones). Off = only the files directly in the source folder.",
    threads="/MT: how many files are copied at the same time.\n"
            "1 = classic mode with live % inside each file (best for a few huge files).\n"
            "Higher = faster for many files, but progress moves in steps.",
    retries="/R: how many times to retry a file that fails (e.g. it's locked).\n"
            "Robocopy's own default is 1,000,000, which looks like a freeze.",
    wait="/W: seconds to wait between retries (robocopy's default is 30).",
    restartable="/Z: if the copy is interrupted, the file resumes where it stopped.\n"
                "Great for networks, a bit slower on local disks.",
    unbuffered="/J: unbuffered I/O. Skips the RAM cache. Much better for huge files, worse for small ones.",
    backup="/B: backup mode. Copies files even if your account has no permission to read them.\n"
           "Needs the app to run as Administrator.",
    skip_junctions="/XJ: skip junction points (folder shortcuts). Avoids endless loops "
                   "in folders like your user profile.",
    fft="/FFT: assume FAT timestamps (2-second precision). Stops NAS devices and USB sticks from "
        "having files copied again every time.",
    dir_times="/DCOPY:DAT: also copy folder timestamps (otherwise folders get today's date).",
    copy_perms="/COPY:DATS: also copy NTFS permissions (who can access each file).",
    dry_run="/L: list only. Shows what WOULD be copied or deleted, without touching anything.",
    log="Also save the full output to a log file (each run is appended, as UTF-8 text).",
    verbose="Show every copied file in the log below (can be a lot of lines).",
    when_done="What to do when the copy finishes. Sleep and Shut down wait 60 seconds first, "
              "so you can cancel.",
    save_bat="Save this exact copy as a .bat file. Double-click it to run it again, "
             "or schedule it with Windows Task Scheduler (e.g. a nightly backup).",
    rescan="Scan again (e.g. if files changed on disk since the last scan).",
    swap="Swap source and destination.",
    src="The folder to copy FROM. Type or paste a path, click Browse…, or drag a folder from Explorer.\n"
        "Drop a file to copy only that file (its folder becomes the source).",
    dst="The folder to copy TO. Type or paste a path, click Browse…, or drag a folder from Explorer.\n"
        "It's created if it doesn't exist yet.",
    reset="Undo your changes and go back to this profile's values (including the drive tuning).",
)


# =============================================================================
# Command builder
# =============================================================================

def split_patterns(text):
    """'*.jpg "my file.txt";*.png' -> ['*.jpg', 'my file.txt', '*.png']"""
    return [a or b for a, b in re.findall(r'"([^"]*)"|([^\s;]+)', text or "")]


def norm_path(p):
    p = (p or "").strip().strip('"').strip()
    if not p:
        return ""
    if re.fullmatch(r"[A-Za-z]:", p):
        return p + "\\"
    return os.path.normpath(p)


def build_args(o, scan=False):
    """Robocopy argument list. With scan=True: the list-only scan, which contains only the options
    that change WHICH files are copied (so it can also serve as the scan's cache key)."""
    args = ["robocopy", norm_path(o["src"]) or "<source>", norm_path(o["dst"]) or "<destination>"]
    files = split_patterns(o["files"])
    if files and files != ["*.*"]:
        args += files

    action = o["action"]
    if action == "mirror":
        args.append("/MIR")
    elif action == "move" and not scan:
        args += ["/E", "/MOVE"] if o["subdirs"] else ["/MOV"]
    elif o["subdirs"]:
        args.append("/E")
    if action == "update":
        args.append("/XO")

    if scan:
        if o["skip_junctions"]:
            args.append("/XJ")
        xf, xd = split_patterns(o["xf"]), split_patterns(o["xd"])
        if xf:
            args += ["/XF", *xf]
        if xd:
            args += ["/XD", *xd]
        return args + ["/L", "/BYTES", "/NDL", "/NJH", "/NJS", "/NP", "/R:0", "/W:0"]

    if o["threads"] > 1:
        args.append(f"/MT:{o['threads']}")
    if o["restartable"] and o["backup"]:
        args.append("/ZB")
    elif o["restartable"]:
        args.append("/Z")
    elif o["backup"]:
        args.append("/B")
    if o["unbuffered"]:
        args.append("/J")
    if o["skip_junctions"]:
        args.append("/XJ")
    if o["fft"]:
        args.append("/FFT")
    if o["dir_times"]:
        args.append("/DCOPY:DAT")
    if o["copy_perms"]:
        args.append("/COPY:DATS")
    xf, xd = split_patterns(o["xf"]), split_patterns(o["xd"])
    if xf:
        args += ["/XF", *xf]
    if xd:
        args += ["/XD", *xd]
    args += [f"/R:{o['retries']}", f"/W:{o['wait']}"]
    if o["dry_run"]:
        args.append("/L")
    args.append("/BYTES")
    if o["log"] and o["log_path"].strip():
        args += [f"/LOG+:{norm_path(o['log_path'])}", "/TEE"]
    return args


def run_args(args, temp_log):
    """What vibeCopy actually runs: the same command, but logging to a fresh Unicode file it can read
    (/UNILOG+ writes plain codepage text when the file is new: a robocopy quirk)."""
    keep = [a for a in args if not a.upper().startswith(("/LOG", "/UNILOG")) and a.upper() != "/TEE"]
    return keep + [f"/UNILOG:{temp_log}"]


def new_temp_log():
    return os.path.join(tempfile.gettempdir(), f"vibeCopy-{os.getpid()}-{int(time.time() * 1000)}.log")


def cleanup_temp_logs():
    """Remove temp logs left behind by a vibeCopy that was killed (older than 12 hours)."""
    try:
        folder, cutoff = tempfile.gettempdir(), time.time() - 12 * 3600
        for name in os.listdir(folder):
            if name.startswith("vibeCopy-") and name.endswith(".log"):
                path = os.path.join(folder, name)
                try:
                    if os.path.getmtime(path) < cutoff:
                        os.remove(path)
                except OSError:
                    pass
    except OSError:
        pass


CMD_SPECIAL = set("&|<>^()")


def cmd_quote(arg):
    """Quote one argument for cmd.exe (.bat files, pasting into a console). list2cmdline only quotes
    arguments with spaces, so a folder like R&D would be split by cmd at the '&'."""
    q = subprocess.list2cmdline([arg]) if arg else '""'
    if not q.startswith('"') and any(c in CMD_SPECIAL for c in arg):
        trailing = len(arg) - len(arg.rstrip("\\"))       # C:\R&D\ -> "C:\R&D\\" (a lone \" would escape the quote)
        q = '"' + arg + "\\" * trailing + '"'
    return q


def cmd_line(args):
    return " ".join(cmd_quote(a) for a in args)


def is_full_path(path):
    """C:\\... or \\\\server\\share. A relative path would silently point next to wherever vibeCopy was started."""
    p = norm_path(path)
    return p.startswith("\\\\") or bool(re.match(r"[A-Za-z]:\\", p))


def bad_patterns(o):
    """Filter entries starting with '/' would reach robocopy as options (e.g. /PURGE)."""
    return [x for key in ("files", "xf", "xd") for x in split_patterns(o[key]) if x.startswith("/")]


def risky_mirror_target(dst):
    """'a whole drive' / 'a personal folder' when mirroring into it would wipe unrelated files, else None."""
    p = norm_path(dst)
    if re.fullmatch(r"[A-Za-z]:\\?", p) or (p.startswith("\\\\") and len(p.strip("\\").split("\\")) <= 2):
        return "a whole drive"
    home = os.path.expanduser("~")
    for q in [home] + [os.path.join(home, n) for n in ("Desktop", "Documents", "Downloads", "Pictures",
                                                       "Music", "Videos", "OneDrive")]:
        if os.path.normcase(os.path.abspath(p)) == os.path.normcase(os.path.abspath(q)):
            return "a personal folder"
    return None


def profile_flags(v):
    flags = [f"/MT:{v['threads']}" if v["threads"] > 1 else "1 thread"]
    flags += [f for key, f in (("unbuffered", "/J"), ("restartable", "/Z"), ("fft", "/FFT"),
                               ("skip_junctions", "/XJ")) if v[key]]
    return " ".join(flags + [f"/R:{v['retries']}", f"/W:{v['wait']}"])


def is_inside(child, parent):
    c = os.path.normcase(os.path.abspath(child))
    p = os.path.normcase(os.path.abspath(parent)).rstrip("\\/") + os.sep
    return c.startswith(p)


def same_path(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def validate(o):
    """Returns (errors, warnings) as lists of strings."""
    errors, warnings = [], []
    src, dst = norm_path(o["src"]), norm_path(o["dst"])
    if not src:
        errors.append("Choose a source folder.")
    elif not is_full_path(src):
        errors.append("Use a full path for the source, like C:\\Photos or \\\\server\\share.")
    elif folder_exists(src) is False:               # network paths are checked by the scan
        errors.append(f"Source folder not found:\n{src}")
    if not dst:
        errors.append("Choose a destination folder.")
    elif not is_full_path(dst):
        errors.append("Use a full path for the destination, like D:\\Backup or \\\\server\\share.")
    bad = bad_patterns(o)
    if bad:
        errors.append(f"The filter entry “{bad[0]}” starts with “/”, so robocopy would read it as an option. "
                      f"Remove it from the Filters (step 1).")
    if src and dst and is_full_path(src) and is_full_path(dst):
        if same_path(src, dst):
            errors.append("Source and destination are the same folder.")
        elif is_inside(dst, src) and (o["subdirs"] or o["action"] == "mirror"):
            errors.append("The destination is inside the source folder. Robocopy would copy "
                          "the copy into itself over and over.")
        elif is_inside(src, dst) and o["action"] == "mirror":
            errors.append("The source is inside the destination. Mirroring would delete "
                          "the source folder itself.")
    if o["backup"] and not is_admin():
        errors.append("Backup mode (/B) needs vibeCopy to run as Administrator.\n"
                      "Untick it, or restart the app with “Run as administrator”.")
    if o["log"] and not o["log_path"].strip():
        errors.append("Choose a log file, or untick “Write log file”.")
    if o["unbuffered"] and o["threads"] > 32:
        warnings.append("Unbuffered I/O (/J) with many threads is usually slower for small files.")
    if o["copy_perms"] and not is_admin():
        warnings.append("Copying permissions may fail for some files without Administrator rights.")
    return errors, warnings


def explain_rc(rc, cancelled=False, dry_run=False):
    """Robocopy exit code is a bitmask. Returns (headline, detail, color)."""
    if cancelled:
        return "Stopped", "You stopped the copy. Run it again to continue: files that are already copied are skipped.", C["amber"]
    if rc is None:
        return "Failed", "Robocopy didn't run.", C["danger"]
    if rc >= 16:
        return "Failed", ("Serious error: robocopy couldn't do the job (bad path, no access, "
                          "or an invalid option). See the log for details."), C["danger"]
    parts = []
    if rc == 0:
        parts.append("Nothing to copy: the destination is already up to date.")
    if rc & 1:
        parts.append("Files would be copied." if dry_run else "Files were copied.")
    if rc & 2:
        parts.append("The destination has extra files that aren't in the source.")
    if rc & 4:
        parts.append("Some mismatched files or folders were found.")
    if rc & 8:
        parts.append("Some files could NOT be copied (see the red lines in the log).")
        return "Finished with errors", " ".join(parts), C["amber"]
    return ("Dry run finished" if dry_run else "Done"), " ".join(parts), C["mint"]


# =============================================================================
# Drive detection (no admin rights needed)
# =============================================================================

_drive_cache = {}


def _kernel32():
    from ctypes import wintypes as w
    k = ctypes.windll.kernel32
    if not getattr(k, "_vc_ready", False):
        k.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE]
        k.CreateFileW.restype = w.HANDLE
        k.DeviceIoControl.argtypes = [w.HANDLE, w.DWORD, w.LPVOID, w.DWORD, w.LPVOID, w.DWORD,
                                      ctypes.POINTER(w.DWORD), w.LPVOID]
        k.DeviceIoControl.restype = w.BOOL
        k.CloseHandle.argtypes = [w.HANDLE]
        k.GetVolumeInformationW.argtypes = [w.LPCWSTR, w.LPWSTR, w.DWORD, w.LPVOID, w.LPVOID,
                                            w.LPVOID, w.LPWSTR, w.DWORD]
        k._vc_ready = True
    return k


def _query_device(letter):
    """(seek_penalty, bus_type, disk_number) for a drive letter; None where unknown."""
    from ctypes import wintypes as w

    class Query(ctypes.Structure):
        _fields_ = [("PropertyId", w.DWORD), ("QueryType", w.DWORD), ("Extra", ctypes.c_byte * 4)]

    class Seek(ctypes.Structure):
        _fields_ = [("Version", w.DWORD), ("Size", w.DWORD), ("IncursSeekPenalty", ctypes.c_bool)]

    class Desc(ctypes.Structure):
        _fields_ = [("Version", w.DWORD), ("Size", w.DWORD), ("DeviceType", ctypes.c_byte),
                    ("DeviceTypeModifier", ctypes.c_byte), ("RemovableMedia", ctypes.c_bool),
                    ("CommandQueueing", ctypes.c_bool), ("VendorIdOffset", w.DWORD),
                    ("ProductIdOffset", w.DWORD), ("ProductRevisionOffset", w.DWORD),
                    ("SerialNumberOffset", w.DWORD), ("BusType", ctypes.c_int),
                    ("RawPropertiesLength", w.DWORD), ("Raw", ctypes.c_byte * 512)]

    class Extent(ctypes.Structure):
        _fields_ = [("Disk", w.DWORD), ("Start", ctypes.c_longlong), ("Length", ctypes.c_longlong)]

    class Extents(ctypes.Structure):
        _fields_ = [("Count", w.DWORD), ("Pad", w.DWORD), ("Ext", Extent * 8)]

    k = _kernel32()
    h = k.CreateFileW("\\\\.\\" + letter + ":", 0, 3, None, 3, 0, None)
    if not h or h == (1 << 64) - 1 or h == (1 << 32) - 1:
        return None, None, None
    seek = bus = disk = None
    try:
        ret = w.DWORD()
        q, s = Query(7, 0), Seek()                   # StorageDeviceSeekPenaltyProperty
        if k.DeviceIoControl(h, 0x2D1400, ctypes.byref(q), ctypes.sizeof(q), ctypes.byref(s),
                             ctypes.sizeof(s), ctypes.byref(ret), None):
            seek = bool(s.IncursSeekPenalty)
        q, d = Query(0, 0), Desc()                   # StorageDeviceProperty -> BusType
        if k.DeviceIoControl(h, 0x2D1400, ctypes.byref(q), ctypes.sizeof(q), ctypes.byref(d),
                             ctypes.sizeof(d), ctypes.byref(ret), None):
            bus = d.BusType
        e = Extents()                                # IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS
        if k.DeviceIoControl(h, 0x560000, None, 0, ctypes.byref(e), ctypes.sizeof(e),
                             ctypes.byref(ret), None) and e.Count:
            disk = e.Ext[0].Disk
    finally:
        k.CloseHandle(h)
    return seek, bus, disk


def drive_info(path):
    """dict(root, kind, fs, hdd, bus, disk) - kind: network/usb/removable/fixed/optical/unknown."""
    p = norm_path(path)
    if not p:
        return None
    if p.startswith("\\\\"):
        parts = p.lstrip("\\").split("\\")
        return dict(root="\\\\" + "\\".join(parts[:2]), kind="network", fs=None, hdd=None, bus=None, disk=None)
    m = re.match(r"([A-Za-z]):", p)
    if not m or not IS_WIN:
        return None
    letter = m.group(1).upper()
    cached = _drive_cache.get(letter)
    if cached and time.time() - cached[0] < 60:
        return cached[1]
    info = dict(root=letter + ":", kind="unknown", fs=None, hdd=None, bus=None, disk=None)
    try:
        k = _kernel32()
        dt = k.GetDriveTypeW(letter + ":\\")
        info["kind"] = {2: "removable", 3: "fixed", 4: "network", 5: "optical"}.get(dt, "unknown")
        if dt != 4:                                  # don't touch possibly-offline network drives
            fs = ctypes.create_unicode_buffer(64)
            if k.GetVolumeInformationW(letter + ":\\", None, 0, None, None, None, fs, 64):
                info["fs"] = fs.value or None
            if dt in (2, 3):
                info["hdd"], info["bus"], info["disk"] = _query_device(letter)
                if info["bus"] == 7:
                    info["kind"] = "usb"
    except Exception:
        pass
    _drive_cache[letter] = (time.time(), info)
    return info


_drive_pending = set()


def drive_info_nowait(path, on_ready):
    """Cached drive info for the UI thread: never blocks. A missing/old entry is looked up in a background
    thread (opening a sleeping USB/hard disk can take seconds), then on_ready() is called from that thread."""
    p = norm_path(path)
    m = re.match(r"([A-Za-z]):", p)
    if not m:
        return drive_info(p)                         # UNC paths: instant, no device access
    letter = m.group(1).upper()
    cached = _drive_cache.get(letter)
    if (not cached or time.time() - cached[0] >= 60) and letter not in _drive_pending:
        _drive_pending.add(letter)

        def work():
            try:
                _drive_cache.pop(letter, None)
                drive_info(p)
            finally:
                _drive_pending.discard(letter)
                on_ready()
        threading.Thread(target=work, daemon=True).start()
    return cached[1] if cached else None


def describe_drive(i):
    if not i:
        return "?"
    return f"{i['root']} {drive_kind(i)}" + (f", {i['fs']}" if i["fs"] else "")


def drive_kind(i):
    kind = i["kind"]
    if kind == "network":
        what = "network drive"
    elif kind == "usb":
        what = "USB hard disk" if i["hdd"] else "USB drive"
    elif kind == "removable":
        what = "removable drive"
    elif kind == "optical":
        what = "optical drive"
    elif i["hdd"]:
        what = "hard disk (HDD)"
    elif i["bus"] == 17:
        what = "NVMe SSD"
    elif i["hdd"] is False:
        what = "SSD"
    else:
        what = "local disk"
    return what


def free_space(path):
    p = norm_path(path)
    while p:
        if os.path.isdir(p):
            try:
                return shutil.disk_usage(p).free
            except OSError:
                return None
        parent = os.path.dirname(p)
        if parent == p:
            return None
        p = parent
    return None


def is_network_path(path):
    """True for \\\\server\\share paths and mapped network drives (fast: never touches the network)."""
    p = norm_path(path)
    if p.startswith("\\\\"):
        return True
    m = re.match(r"([A-Za-z]):", p)
    if m and IS_WIN:
        try:
            return ctypes.windll.kernel32.GetDriveTypeW(m.group(1) + ":\\") == 4
        except Exception:
            return False
    return False


def folder_exists(path):
    """True / False, or None for network paths (left to the scan, so the UI never freezes)."""
    p = norm_path(path)
    if not p:
        return False
    if is_network_path(p):
        return None
    return os.path.isdir(p)


# =============================================================================
# Robocopy output parsing, scanner and runner (background threads)
# =============================================================================

RE_SPLIT = re.compile(rb"\r\n|\r|\n")
RE_ITEM = re.compile(r"^\t(?P<cls>\D*?)\s*(?P<num>\d+)\t(?P<name>.+)$")
RE_PCT = re.compile(r"^\s*(\d{1,3}(?:[.,]\d+)?)%\s*$")
RE_ERR = re.compile(r"\s(\S+)\s+(\d+)\s+\(0x[0-9A-Fa-f]{8}\)")
RE_ERR_PATH = re.compile(r"([A-Za-z]:\\.*|\\\\.*)$")          # the path at the end of an ERROR line


def oem_encoding():
    if IS_WIN:
        try:
            enc = f"cp{ctypes.windll.kernel32.GetOEMCP()}"
            "".encode(enc)
            return enc
        except Exception:
            pass
    return "latin-1"


ENC = oem_encoding()


def start_robocopy(args):
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW if IS_WIN else 0)


def read_lines(proc, handler, lock):
    """Feed robocopy's output to handler(line), split on \\r and \\n (progress uses bare \\r)."""
    out, buf = proc.stdout, b""
    while True:
        chunk = out.read1(65536)
        if not chunk:
            break
        buf += chunk
        parts = RE_SPLIT.split(buf)
        buf = parts.pop()
        with lock:
            for part in parts:
                if part:
                    handler(part.decode(ENC, "replace"))
    if buf:
        with lock:
            handler(buf.decode(ENC, "replace"))
    return proc.wait()


class Scanner(threading.Thread):
    """The one-time scan: drive detection + robocopy /L. Gives the totals for the ETA, the size mix
    for the recommendation, the extras a mirror would delete, and free space."""

    def __init__(self, args, src, dst):
        super().__init__(daemon=True)
        self.args, self.src, self.dst = args, src, dst
        self.lock = threading.Lock()
        self.proc = None
        self.src_info = self.dst_info = self.free = None
        self.n = self.bytes = self.small_n = self.mid_n = self.big_n = self.big_bytes = 0
        self.extras = self.over4g = self.max_size = 0
        self.extras_names = []          # first 1,000 files a mirror would delete
        self.other = []
        self.rc = self.error = None
        self.cancelled = self.done = False
        self.t_start, self.t_done = time.time(), None

    @property
    def ok(self):
        return self.done and not self.cancelled and self.error is None and self.rc is not None and self.rc < 16

    def cancel(self):
        self.cancelled = True
        p = self.proc
        if p and p.poll() is None:
            try:
                p.kill()
            except OSError:
                pass

    def run(self):
        try:
            self.src_info = drive_info(self.src)
            self.dst_info = drive_info(self.dst)
            for info, what in ((self.src_info, "source"), (self.dst_info, "destination")):
                if info and info["kind"] == "network" and not os.path.isdir(info["root"] + "\\"):
                    self.error = (f"The {what} drive {info['root']} isn't reachable. It looks like a "
                                  f"disconnected network drive: open it in Explorer to reconnect, then Rescan.")
                    return
            if self.cancelled:
                return
            self.proc = start_robocopy(self.args)
            if self.cancelled:
                self.cancel()
            self.rc = read_lines(self.proc, self._on_line, self.lock)
            self.free = free_space(self.dst)
        except Exception as e:
            self.error = repr(e)
        finally:
            self.t_done = time.time()
            self.done = True

    def _on_line(self, line):
        m = RE_ITEM.match(line)
        if m and not m["name"].endswith("\\"):
            if m["cls"].strip().startswith("*"):     # *EXTRA: only in the destination
                self.extras += 1
                if len(self.extras_names) < 1000:
                    self.extras_names.append(m["name"])
                return
            size = int(m["num"])
            self.n += 1
            self.bytes += size
            self.max_size = max(self.max_size, size)
            if size > FAT32_MAX:
                self.over4g += 1
            if size < SMALL:
                self.small_n += 1
            elif size >= BIG:
                self.big_n += 1
                self.big_bytes += size
            else:
                self.mid_n += 1
        elif line.strip() and len(self.other) < 40:
            self.other.append(line.strip())


def recommend(sc):
    """Pick a profile from the scan and the drives, then tune it for the hardware.
    Returns (name, values, reasons, tuning)."""
    s, d = sc.src_info, sc.dst_info
    drives = [x for x in (s, d) if x]
    kinds = {x["kind"] for x in drives}
    big_share = sc.big_bytes / sc.bytes if sc.bytes else 0.0
    reasons, tuning = [], []

    if "network" in kinds:
        name = "Network / NAS"
        reasons.append(" and ".join(x["root"] for x in drives if x["kind"] == "network") + " is on the network.")
    elif kinds & {"usb", "removable"}:
        name = "USB / external drive"
        reasons.append(" ".join(f"{x['root']} is a {drive_kind(x)}." for x in drives
                                if x["kind"] in ("usb", "removable")))
    elif sc.n == 0:
        name = "Everyday"
        reasons.append("Nothing needs copying.")
    elif big_share >= 0.7 and sc.n - sc.big_n < 200:
        name = "Few big files" if sc.big_n <= 8 else "Many big files"
        reasons.append(f"{big_share:.0%} of the data is in {sc.big_n:,} file{'s' if sc.big_n != 1 else ''} "
                       f"of 100 MB or more.")
    elif big_share >= 0.7:                       # big files AND lots of small ones: /J or 1 thread would crawl
        name = "Mixed sizes"
        reasons.append(f"{big_share:.0%} of the data is in {sc.big_n:,} big file{'s' if sc.big_n != 1 else ''}, "
                       f"but there are also {sc.n - sc.big_n:,} smaller files: parallel copies keep both moving.")
    elif sc.n < 1000:
        name = "Everyday"
        reasons.append(f"Only {sc.n:,} files to copy.")
    elif sc.small_n / sc.n >= 0.8:
        name = "Many small files"
        reasons.append(f"{sc.n:,} files to copy, {sc.small_n / sc.n:.0%} of them under 1 MB.")
    else:
        name = "Mixed sizes"
        reasons.append(f"{sc.n:,} files of mixed sizes.")

    values = {**PROFILE_DEFAULTS, **PROFILE_BY_NAME[name]["set"]}
    hdd_roots = sorted({x["root"] for x in drives if x["hdd"]})
    same_hdd = bool(s and d and s["hdd"] and s["disk"] is not None and s["disk"] == d["disk"])
    if same_hdd:
        cap = 2 if name == "Many big files" else 4
        if values["threads"] > cap:
            values["threads"] = cap
            tuning.append(f"Source and destination are on the same hard disk: threads lowered to {cap}, "
                          f"because the disk head has to jump between reading and writing.")
    elif hdd_roots:
        cap = 2 if name == "Many big files" else 8
        if values["threads"] > cap:
            values["threads"] = cap
            tuning.append(f"{' and '.join(hdd_roots)} {'are hard disks' if len(hdd_roots) > 1 else 'is a hard disk'}"
                          f": threads lowered to {cap}, because parallel copies make the disk head jump around.")
    if d and (d["fs"] or "").upper() in ("FAT32", "FAT", "EXFAT") and not values["fft"]:
        values["fft"] = True
        tuning.append(f"{d['root']} uses {d['fs']}: /FFT added, so its coarse timestamps don't make files "
                      f"get copied again every time.")
    if name == "USB / external drive" and big_share >= 0.7 and not values["unbuffered"]:
        values["unbuffered"] = True
        tuning.append("Mostly big files: unbuffered I/O (/J) added.")
    return name, values, reasons, tuning


class RoboJob(threading.Thread):
    """Runs the real robocopy and parses its output as it's written.
    The output is read from robocopy's /UNILOG file, not from stdout: piped output loses every character
    outside the console codepage (Japanese, emoji…), while the Unicode log keeps them."""

    def __init__(self, args, totals, dry_run, verbose, user_log=None):
        super().__init__(daemon=True)
        self.log_path = new_temp_log()
        self.args = run_args(args, self.log_path)
        self.shown_args = args
        self.dry_run, self.verbose, self.user_log = dry_run, verbose, user_log
        self.lock = threading.Lock()
        self.q = queue.Queue()
        self.proc = None
        self.total_files, self.total_bytes = totals if totals else (None, None)
        self.done_files = self.done_bytes = 0
        self.cur = None            # (name, size)
        self.cur_pct = 0.0
        self.cur_failed = False
        self.cur_dir = ""
        self.failed = set()
        self.fail_info = {}        # full path -> reason
        self._last_fail = None
        self.err_next = False
        self.rc = None
        self.cancelled = False
        self.finished = False
        self.hidden_lines = 0      # "Show every file" lines skipped because the view fell behind
        self.t_start = time.time()

    def stop(self):
        self.cancelled = True
        p = self.proc
        if p and p.poll() is None:
            try:
                p.kill()
            except OSError:
                pass

    def snapshot(self):
        with self.lock:
            partial = 0
            if self.cur and not self.cur_failed:
                partial = self.cur[1] * self.cur_pct / 100.0
            return dict(
                finished=self.finished, cancelled=self.cancelled, rc=self.rc,
                total_files=self.total_files, total_bytes=self.total_bytes,
                done_files=self.done_files, done_bytes=self.done_bytes + partial,
                current=self.cur[0] if self.cur else "", cur_dir=self.cur_dir, errors=len(self.failed),
            )

    def failed_items(self):
        """[(path, reason)] for the files that could not be copied."""
        with self.lock:
            return sorted((n, self.fail_info.get(n, "")) for n in self.failed)

    def _full(self, name):
        """/MT output has full paths; single-thread output has names relative to the last folder line."""
        return name if (":" in name or name.startswith("\\\\")) else self.cur_dir + name

    def log(self, text, tag="info"):
        if tag == "dim" and self.q.qsize() > 20000:     # per-file lines only; errors and summary always shown
            self.hidden_lines += 1
            return
        self.q.put((text, tag))

    def run(self):
        out = []
        try:
            self.proc = start_robocopy(self.args)
            if self.cancelled:
                self.stop()
            drain = threading.Thread(target=lambda: out.append(self.proc.stdout.read()), daemon=True)
            drain.start()                              # stdout only matters if the log never opens
            got_log = self._follow_log()
            rc = self.proc.wait()
            drain.join(5)
            if not got_log and out and out[0]:         # e.g. an invalid option: robocopy stops before logging
                with self.lock:
                    for part in RE_SPLIT.split(out[0]):
                        if part:
                            self._on_line(part.decode(ENC, "replace"))
            with self.lock:
                if self.cur and not self.cur_failed and self.dry_run:
                    self._commit()
                self.rc = rc
        except Exception as e:  # never die silently
            self.log(f"Internal error: {e!r}", "err")
        finally:
            if self.hidden_lines:
                self.q.put((f"({self.hidden_lines:,} file lines were not shown here to keep up with robocopy. "
                            f"The copy itself is complete; turn on “Write log file” for the full list.)", "dim"))
            self._save_user_log()
            try:
                os.remove(self.log_path)
            except OSError:
                pass
            self.finished = True

    def _save_user_log(self):
        """Append this run to the user's log as UTF-8, streamed in 1 MB pieces (a log of millions of files
        must not be loaded into memory)."""
        if not self.user_log:
            return
        try:
            os.makedirs(os.path.dirname(self.user_log) or ".", exist_ok=True)
            with open(self.user_log, "a", encoding="utf-8", newline="") as out:
                out.write(f"\r\n===== vibeCopy {time.strftime('%Y-%m-%d %H:%M:%S')} =====\r\n"
                          f"{cmd_line(self.shown_args)}\r\n")
                try:
                    src = open(self.log_path, "rb")
                except OSError:
                    out.write("(robocopy wrote no log: see the error in vibeCopy)\r\n")
                    return
                with src:
                    decoder = codecs.getincrementaldecoder("utf-16")(errors="replace")   # eats the BOM
                    while True:
                        chunk = src.read(1 << 20)
                        out.write(decoder.decode(chunk, final=not chunk))
                        if not chunk:
                            break
        except OSError as e:
            self.log(f"Couldn't write the log file: {e}", "warn")

    def _follow_log(self):
        decoder = codecs.getincrementaldecoder("utf-16-le")(errors="replace")
        f, pending, got = None, "", False
        try:
            while True:
                alive = self.proc.poll() is None
                if f is None:
                    try:
                        f = open(self.log_path, "rb")
                    except OSError:
                        f = None
                chunk = f.read() if f else b""
                if chunk:
                    got = True
                    parts = re.split(r"\r\n|\r|\n", pending + decoder.decode(chunk))
                    pending = parts.pop()
                    with self.lock:
                        for part in parts:
                            part = part.lstrip("\ufeff")
                            if part:
                                self._on_line(part)
                elif not alive:
                    break
                else:
                    time.sleep(0.1)
            pending = (pending + decoder.decode(b"", final=True)).lstrip("\ufeff")
            if pending.strip():
                with self.lock:
                    self._on_line(pending)
        finally:
            if f:
                f.close()
        return got

    def _commit(self):
        name, size = self.cur
        self.done_files += 1
        self.done_bytes += size
        full = self._full(name)                         # copied after all (a retry worked)
        self.failed.discard(full)
        self.fail_info.pop(full, None)
        self.cur, self.cur_pct, self.cur_failed = None, 0.0, False

    def _on_line(self, line):
        m = RE_ITEM.match(line)
        if m:
            cls, size, name = m["cls"].strip(), int(m["num"]), m["name"]
            if name.endswith("\\"):                     # directory line
                self.cur_dir = name
                if self.verbose:
                    self.log(f"{cls or 'Dir'}  {name}", "dim")
                return
            if cls.startswith("*"):                     # *EXTRA (deleted by /MIR)
                if self.verbose:
                    self.log(f"{cls}  {name}", "warn")
                return
            if self.cur and self.cur[0] != name and not self.cur_failed:
                self._commit()                          # missed a 100% line: count it anyway
            if not (self.cur and self.cur[0] == name):  # (same name again = a retry)
                self.cur_failed = False
            self.cur, self.cur_pct = (name, size), 0.0
            if self.verbose:
                self.log(f"{cls}  {fmt_bytes(size)}  {name}", "dim")
            if self.dry_run:                            # /L prints no % lines
                self._commit()
            return

        m = RE_PCT.match(line)
        if m:
            pct = float(m.group(1).replace(",", "."))
            if self.cur:
                if pct >= 100:
                    self._commit()
                else:
                    self.cur_pct = pct
            return

        m = RE_ERR.search(line)
        if m:
            # the ERROR line names the file itself; with /MT the "current file" can be another one
            mp = RE_ERR_PATH.search(line[m.end():].strip())
            key = mp.group(1) if mp else (self._full(self.cur[0]) if self.cur else line[m.end():].strip())
            self.failed.add(key)
            self.fail_info.setdefault(key, f"Error {m.group(2)}")
            self._last_fail = key
            self.cur_failed = True
            self.err_next = True
            self.log(line.strip(), "err")
            return
        if self.err_next:                               # the message under an ERROR line
            self.err_next = False
            if line.strip():
                if self._last_fail in self.failed:
                    self.fail_info[self._last_fail] = line.strip()
                self.log("    " + line.strip(), "err")
                return

        text = line.rstrip()
        if not text.strip():
            return
        if set(text.strip()) <= set("-"):
            self.log(text.strip(), "dim")
        elif text.lstrip().upper().startswith("ERROR"):   # not the summary header's "ERROR" column
            self.log(text, "err")
        else:
            self.log(text, "info")


class Meter:
    """Speed over a sliding time window."""

    def __init__(self, window=10.0):
        self.window = window
        self.samples = collections.deque()

    def add(self, t, b, f):
        self.samples.append((t, b, f))
        while len(self.samples) > 2 and self.samples[0][0] < t - self.window:
            self.samples.popleft()

    def rate(self):
        if len(self.samples) < 2:
            return None, None
        t0, b0, f0 = self.samples[0]
        t1, b1, f1 = self.samples[-1]
        if t1 - t0 < 1.0:
            return None, None
        return (b1 - b0) / (t1 - t0), (f1 - f0) / (t1 - t0)


def fmt_bytes(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def fmt_dur(s):
    s = int(max(0, s))
    h, rest = divmod(s, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_ago(t):
    s = time.time() - t
    if s < 45:
        return "just now"
    if s < 3600:
        return f"{int(s // 60) or 1} min ago"
    return f"{int(s // 3600)} h ago"


def elide(text, n=90):
    return text if len(text) <= n else "…" + text[-(n - 1):]


def elide_px(text, font, max_px):
    """Shorten from the left (keeping the file name) until it fits in max_px pixels."""
    if max_px <= 20 or font.measure(text) <= max_px:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi) // 2
        if font.measure("…" + text[mid:]) <= max_px:
            hi = mid
        else:
            lo = mid + 1
    return "…" + text[lo:]


# =============================================================================
# Windows helpers
# =============================================================================

def enable_dpi_awareness():
    if IS_WIN:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("vibeCopy.app")
        except Exception:
            pass


def work_area():
    """Size of the desktop minus the taskbar, or None."""
    if not IS_WIN:
        return None
    try:
        from ctypes import wintypes
        rc = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rc), 0)  # SPI_GETWORKAREA
        return rc.right - rc.left, rc.bottom - rc.top
    except Exception:
        return None


def hwnd_of(win):
    try:
        return ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
    except Exception:
        return None


def dark_titlebar(win):
    """Dark title bar on Windows 10/11, tinted with the window background on Windows 11."""
    if not IS_WIN:
        return
    try:
        win.update_idletasks()
        hwnd = hwnd_of(win)
        dwm = ctypes.windll.dwmapi
        on = ctypes.c_int(1)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(on), 4)  # DWMWA_USE_IMMERSIVE_DARK_MODE
        r, g, b = (int(C["bg"][i:i + 2], 16) for i in (1, 3, 5))
        color = ctypes.c_int(r | (g << 8) | (b << 16))
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), 4)  # DWMWA_CAPTION_COLOR
    except Exception:
        pass


def keep_awake(on):
    """Stop Windows from sleeping while a copy runs (ES_CONTINUOUS | ES_SYSTEM_REQUIRED)."""
    if IS_WIN:
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | (0x00000001 if on else 0))
        except Exception:
            pass


def flash_taskbar(win):
    if not IS_WIN:
        return
    try:
        from ctypes import wintypes as w

        class FlashInfo(ctypes.Structure):
            _fields_ = [("cbSize", w.UINT), ("hwnd", w.HWND), ("dwFlags", w.DWORD),
                        ("uCount", w.UINT), ("dwTimeout", w.DWORD)]

        info = FlashInfo(ctypes.sizeof(FlashInfo), hwnd_of(win), 3 | 12, 0, 0)  # FLASHW_ALL | TIMERNOFG
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
    except Exception:
        pass


def power_action(what):
    if what == "Sleep":
        ctypes.windll.powrprof.SetSuspendState(False, False, False)
    elif what == "Shut down":
        subprocess.run(["shutdown", "/s", "/t", "0"], creationflags=subprocess.CREATE_NO_WINDOW)


class FileDrop:
    """Accept files and folders dragged from Explorer (WM_DROPFILES), with ctypes only.
    The window procedure must not call Tk (it runs inside Tk's own event dispatch), so drops are only
    queued here and the app picks them up from `pending` on its next tick."""

    def __init__(self, win):
        from ctypes import wintypes as w
        u, sh = ctypes.windll.user32, ctypes.windll.shell32
        proc_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
        u.SetWindowLongPtrW.restype = ctypes.c_void_p
        u.SetWindowLongPtrW.argtypes = [w.HWND, ctypes.c_int, ctypes.c_void_p]
        u.CallWindowProcW.restype = ctypes.c_ssize_t
        u.CallWindowProcW.argtypes = [ctypes.c_void_p, w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        u.ChangeWindowMessageFilterEx.argtypes = [w.HWND, w.UINT, w.DWORD, ctypes.c_void_p]
        sh.DragQueryFileW.argtypes = [w.HANDLE, w.UINT, w.LPWSTR, w.UINT]
        sh.DragQueryFileW.restype = w.UINT
        sh.DragFinish.argtypes = [w.HANDLE]
        sh.DragAcceptFiles.argtypes = [w.HWND, w.BOOL]
        self.old = {}
        self.pending = collections.deque()

        def proc(hwnd, msg, wparam, lparam):
            if msg == 0x0233:                                   # WM_DROPFILES
                paths = []
                try:
                    for i in range(sh.DragQueryFileW(wparam, 0xFFFFFFFF, None, 0)):
                        n = sh.DragQueryFileW(wparam, i, None, 0)
                        buf = ctypes.create_unicode_buffer(n + 1)
                        sh.DragQueryFileW(wparam, i, buf, n + 1)
                        paths.append(buf.value)
                finally:
                    sh.DragFinish(wparam)
                if paths:
                    self.pending.append(paths)
                return 0
            return u.CallWindowProcW(self.old[hwnd], hwnd, msg, wparam, lparam)

        self.proc = proc_type(proc)                             # keep a reference: Windows calls it
        for hwnd in (win.winfo_id(), u.GetParent(win.winfo_id())):
            if hwnd and hwnd not in self.old:
                sh.DragAcceptFiles(hwnd, True)
                for msg in (0x0233, 0x004A, 0x0049):            # let drops through when running as admin
                    u.ChangeWindowMessageFilterEx(hwnd, msg, 1, None)
                self.old[hwnd] = u.SetWindowLongPtrW(hwnd, -4, ctypes.cast(self.proc, ctypes.c_void_p))


class TaskbarProgress:
    """Progress on the taskbar button (ITaskbarList3 through plain ctypes COM)."""
    NONE, BUSY, NORMAL, ERROR, PAUSED = 0, 1, 2, 4, 8

    def __init__(self, win):
        self.ptr = None
        try:
            from ctypes import wintypes as w

            class GUID(ctypes.Structure):
                _fields_ = [("a", w.DWORD), ("b", w.WORD), ("c", w.WORD), ("d", ctypes.c_ubyte * 8)]

            ole = ctypes.windll.ole32
            ole.CoInitialize(None)
            clsid, iid = GUID(), GUID()
            ole.CLSIDFromString("{56FDF344-FD6D-11d0-958A-006097C9A090}", ctypes.byref(clsid))
            ole.CLSIDFromString("{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}", ctypes.byref(iid))
            ptr = ctypes.c_void_p()
            if ole.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(ptr)) != 0:
                return
            vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
            hr = ctypes.HRESULT
            self._init = ctypes.WINFUNCTYPE(hr, ctypes.c_void_p)(vtbl[3])
            self._value = ctypes.WINFUNCTYPE(hr, ctypes.c_void_p, w.HWND, ctypes.c_ulonglong,
                                             ctypes.c_ulonglong)(vtbl[9])
            self._state = ctypes.WINFUNCTYPE(hr, ctypes.c_void_p, w.HWND, ctypes.c_int)(vtbl[10])
            self._init(ptr)
            self.ptr, self.hwnd = ptr, hwnd_of(win)
        except Exception:
            self.ptr = None

    def set(self, state, fraction=None):
        if not self.ptr:
            return
        try:
            self._state(self.ptr, self.hwnd, state)
            if fraction is not None:
                self._value(self.ptr, self.hwnd, int(max(0.0, min(1.0, fraction)) * 1000), 1000)
        except Exception:
            pass


# =============================================================================
# GUI drawing helpers
# =============================================================================

def make_icon(root):
    n = 32
    img = tk.PhotoImage(width=n, height=n)
    rows = []
    for y in range(n):
        row = []
        for x in range(n):
            dy = abs(y - 15.5)
            on = False
            for x0 in (5, 14):
                d = (x - x0) - (9 - dy)
                if dy <= 9 and 0 <= d < 4.5:
                    on = True
            row.append(C["on_accent"] if on else C["accent"])
        rows.append("{" + " ".join(row) + "}")
    img.put(" ".join(rows))
    return img


def _rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))


def _seg_dist(px_, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px_ - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return ((px_ - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5


def indicator_image(kind, size, gap, border, fill, mark, bg=None):
    """Anti-aliased checkbox ('check') or radio ('radio') image, drawn with 4x4 supersampling.
    The image is `gap` pixels wider than tall, so the label text doesn't touch the box."""
    bg, border, fill = _rgb(bg or C["card"]), _rgb(border), _rgb(fill)
    mark = _rgb(mark) if mark else None
    bw = 0.10  # border width, relative to size

    def paint(x, y):  # x, y in 0..1 over the indicator square
        if x > 1:
            return bg
        if kind == "radio":
            d = ((x - 0.5) ** 2 + (y - 0.5) ** 2) ** 0.5 - 0.46
            if d > 0:
                return bg
            if mark:
                return mark if ((x - 0.5) ** 2 + (y - 0.5) ** 2) ** 0.5 < 0.19 else fill
            return border if d > -bw else fill
        qx, qy = abs(x - 0.5) - 0.46 + 0.24, abs(y - 0.5) - 0.46 + 0.24
        d = (max(qx, 0) ** 2 + max(qy, 0) ** 2) ** 0.5 + min(max(qx, qy), 0) - 0.24
        if d > 0:
            return bg
        if mark and min(_seg_dist(x, y, 0.26, 0.52, 0.43, 0.69),
                        _seg_dist(x, y, 0.43, 0.69, 0.75, 0.34)) < 0.075:
            return mark
        return border if d > -bw else fill

    w, ss = size + gap, 4
    img = tk.PhotoImage(width=w, height=size)
    rows = []
    for y in range(size):
        row = []
        for x in range(w):
            r = g = b = 0
            for sy in range(ss):
                for sx in range(ss):
                    c = paint((x + (sx + 0.5) / ss) / size, (y + (sy + 0.5) / ss) / size)
                    r, g, b = r + c[0], g + c[1], b + c[2]
            n = ss * ss
            row.append(f"#{r // n:02x}{g // n:02x}{b // n:02x}")
        rows.append("{" + " ".join(row) + "}")
    img.put(" ".join(rows))
    return img


class Tooltip:
    _by_widget = {}

    @classmethod
    def update(cls, widget, text):
        tip = cls._by_widget.get(str(widget))
        if tip:
            tip.text = text

    def __init__(self, widget, text, app):
        self.widget, self.text, self.app = widget, text, app
        Tooltip._by_widget[str(widget)] = self
        self.tip = self.job = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _=None):
        self._cancel()
        self.job = self.widget.after(450, self._show)

    def _cancel(self):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None

    def _show(self):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + self.app.px(12)
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + self.app.px(6)
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.configure(bg=C["border_hi"])
        tk.Label(tw, text=self.text, justify="left", bg=C["raised"], fg=C["text"],
                 font=self.app.f["small"], wraplength=self.app.px(380),
                 padx=self.app.px(10), pady=self.app.px(7)).pack(padx=1, pady=1)
        tw.wm_geometry(f"+{x}+{y}")

    def _hide(self, _=None):
        self._cancel()
        if self.tip:
            self.tip.destroy()
            self.tip = None


# =============================================================================
# Main application
# =============================================================================

class Section:
    """One collapsible step of the accordion: a clickable header (number, title, summary, state) + a body."""

    def __init__(self, app, parent, index, title):
        self.app, self.index, self.title = app, index, title
        px, f = app.px, app.f
        self.is_open = False
        self.summary_text, self.state = "", None
        self.frame = tk.Frame(parent, bg=C["card"], highlightthickness=1,
                              highlightbackground=C["border"], highlightcolor=C["accent"])
        self.head = tk.Frame(self.frame, bg=C["card"], cursor="hand2", takefocus=1)
        self.head.pack(fill="x")
        self.bar = tk.Frame(self.head, bg=C["card"], width=px(3))
        self.bar.pack(side="left", fill="y")
        size = px(26)
        self.badge = tk.Canvas(self.head, width=size, height=size, bg=C["card"], highlightthickness=0)
        self.badge.pack(side="left", padx=(px(12), px(10)), pady=px(11))
        self._oval = self.badge.create_oval(1, 1, size - 1, size - 1, fill=C["raised"], outline="")
        self._num = self.badge.create_text(size // 2, size // 2, text=str(index), fill=C["muted"], font=f["bold"])
        self.title_lbl = tk.Label(self.head, text=title, bg=C["card"], fg=C["text"], font=f["h3"])
        self.title_lbl.pack(side="left")
        self.chev = tk.Label(self.head, text="▸", bg=C["card"], fg=C["muted"], font=f["h3"])
        self.chev.pack(side="right", padx=(px(6), px(14)))
        self.state_lbl = tk.Label(self.head, text="", bg=C["card"], fg=C["mint"], font=f["bold"])
        self.state_lbl.pack(side="right")
        self.summary = tk.Label(self.head, text="", bg=C["card"], fg=C["muted"], font=f["base"], anchor="w")
        self.summary.pack(side="left", fill="x", expand=True, padx=(px(14), px(8)))
        self.body = tk.Frame(self.frame, bg=C["card"])

        for w in (self.head, self.bar, self.badge, self.title_lbl, self.chev, self.state_lbl, self.summary):
            w.bind("<Button-1>", lambda _: app.toggle_section(self.index))
            w.bind("<Enter>", lambda _: self._hover(True))
            w.bind("<Leave>", lambda _: self._hover(False))
        self.head.bind("<Return>", lambda _: app.toggle_section(self.index))
        self.head.bind("<space>", lambda _: app.toggle_section(self.index))
        self.head.bind("<FocusIn>", lambda _: self.frame.configure(highlightbackground=C["accent"]))
        self.head.bind("<FocusOut>", lambda _: self.frame.configure(highlightbackground=C["border"]))
        self.head.bind("<Configure>", lambda _: self._fit_summary())

    def _hover(self, on):
        bg = C["raised"] if on and not self.is_open else C["card"]
        for w in (self.head, self.badge, self.title_lbl, self.chev, self.state_lbl, self.summary):
            w.configure(bg=bg)
        if not self.is_open:
            self.bar.configure(bg=bg)

    def set_open(self, is_open):
        self.is_open = is_open
        px = self.app.px
        if is_open:
            self.body.pack(fill="both", expand=True, padx=(px(18), px(18)), pady=(0, px(16)))
        else:
            self.body.pack_forget()
        self.chev.configure(text="▾" if is_open else "▸", fg=C["accent"] if is_open else C["muted"])
        self.bar.configure(bg=C["accent"] if is_open else C["card"])
        self.badge.itemconfigure(self._oval, fill=C["accent"] if is_open else C["raised"])
        self.badge.itemconfigure(self._num, fill=C["on_accent"] if is_open else C["muted"])
        self._hover(False)

    def set_summary(self, text, state=None):
        """state: None, 'ok' (✓), 'warn' / 'danger' (⚠), 'busy' (…)."""
        if (text, state) == (self.summary_text, self.state):
            return
        self.summary_text, self.state = text, state
        icon, color = {"ok": ("✓", C["mint"]), "warn": ("⚠", C["amber"]), "danger": ("⚠", C["danger"]),
                       "busy": ("…", C["muted"])}.get(state, ("", C["muted"]))
        self.state_lbl.configure(text=icon, fg=color)
        self.summary.configure(fg=C["danger"] if state == "danger" else C["muted"])
        self._fit_summary()

    def _fit_summary(self):
        width = self.summary.winfo_width()
        if width > 20:
            self.summary.configure(text=elide_px(self.summary_text, self.app.f["base"], width - 4))
        else:
            self.summary.configure(text=self.summary_text)


class App:
    def __init__(self):
        enable_dpi_awareness()
        cleanup_temp_logs()
        self.root = root = tk.Tk()
        root.withdraw()
        root.report_callback_exception = self._on_error
        self.scale = root.winfo_fpixels("1i") / 96.0
        self._init_fonts()
        self._init_style()
        root.title(APP_NAME)
        root.configure(bg=C["bg"])
        self.icon = make_icon(root)
        root.iconphoto(True, self.icon)

        self.job = None
        self.job_opts = None
        self.last_job = None
        self.meter = Meter()
        self._eta_smooth = None
        self._last_args = []
        self._applying = False
        self._refresh_pending = False
        self._ready = False
        self._tick_id = self._refresh_id = self._scan_after = None
        self._typing = False
        self._filters_open = False
        self._drop_filter = None         # (source folder, Files value) set by dropping files as the source
        self._drives_changed = False     # set by background drive lookups -> refresh on the next tick
        self._errors_shown = set()
        self._shown = {}                 # last values shown in the run bar (see _put)

        # profile state (nothing is saved: all of this lives only while the app is open)
        self.profile = PROFILES[0]["name"]
        self.base_values = {**PROFILE_DEFAULTS, **PROFILES[0]["set"]}
        self.applied_tuning = []
        self.touched = False             # user picked/edited the profile -> don't auto-apply
        self.recommended = None          # (name, values, reasons, tuning) from the last scan
        self._folders = None

        # scan state
        self.scan = None
        self.scan_key = None
        self._scan_done_seen = True
        self._scan_skipped = False
        self._pending_run = False

        self.v = {}
        for k, d in ALL_DEFAULTS.items():
            var = tk.BooleanVar() if isinstance(d, bool) else tk.IntVar() if isinstance(d, int) else tk.StringVar()
            var.set(d)
            var.trace_add("write", lambda *_: self._schedule_refresh())
            self.v[k] = var
        for k, val in self.base_values.items():
            self.v[k].set(val)

        self._build()
        self.combo.set(self.profile)
        self._place_window()
        self._show_tab("about")
        self.open_section(1)
        self._ready = True
        self._refresh()

        root.protocol("WM_DELETE_WINDOW", self._on_close)
        root.bind("<Control-Return>", lambda _: self.start())
        root.bind("<Escape>", lambda _: self.stop() if (self.job or self._pending_run) else None)
        for i in range(1, 6):
            root.bind(f"<Control-Key-{i}>", lambda _, n=i: self.open_section(n))
        root.bind_all("<MouseWheel>", self._on_wheel, add="+")
        dark_titlebar(root)
        root.deiconify()
        root.update_idletasks()
        self.taskbar = TaskbarProgress(root) if IS_WIN else None
        self.dropper = None
        if IS_WIN:
            try:
                self.dropper = FileDrop(root)
            except Exception:
                self.dropper = None
        self._tick_id = root.after(200, self._tick)

    # -- setup --------------------------------------------------------------
    def px(self, n):
        return int(round(n * self.scale))

    def _init_fonts(self):
        fams = set(tkfont.families(self.root))

        def pick(*names):
            return next((n for n in names if n in fams), "TkDefaultFont")

        ui = pick("Segoe UI Variable Text", "Segoe UI", "Helvetica", "Arial")
        disp = pick("Segoe UI Variable Display", "Segoe UI Semibold", ui)
        mono = pick("Cascadia Mono", "Cascadia Code", "Consolas", "Courier New")
        self.f = dict(
            base=tkfont.Font(family=ui, size=10),
            small=tkfont.Font(family=ui, size=9),
            bold=tkfont.Font(family=ui, size=10, weight="bold"),
            caps=tkfont.Font(family=ui, size=8, weight="bold"),
            title=tkfont.Font(family=disp, size=16, weight="bold"),
            h2=tkfont.Font(family=disp, size=14, weight="bold"),
            h3=tkfont.Font(family=disp, size=11, weight="bold"),
            value=tkfont.Font(family=disp, size=12, weight="bold"),
            mono=tkfont.Font(family=mono, size=9),
            mono_b=tkfont.Font(family=mono, size=9, weight="bold"),
            link=tkfont.Font(family=ui, size=9, underline=True),
        )
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
            try:
                tkfont.nametofont(name).configure(family=ui, size=10)
            except tk.TclError:
                pass

    def _init_style(self):
        px, f, r = self.px, self.f, self.root
        st = ttk.Style(r)
        st.theme_use("clam")
        st.configure(".", background=C["card"], foreground=C["text"], fieldbackground=C["field"],
                     bordercolor=C["border"], lightcolor=C["border"], darkcolor=C["border"],
                     troughcolor=C["raised"], selectbackground=C["sel"], selectforeground=C["text"],
                     insertcolor=C["accent"], focuscolor=C["card"], arrowcolor=C["muted"], font=f["base"])

        for s in ("TEntry", "TCombobox", "TSpinbox"):
            st.configure(s, fieldbackground=C["field"], foreground=C["text"], bordercolor=C["border"],
                         lightcolor=C["field"], darkcolor=C["field"], insertcolor=C["accent"],
                         padding=(px(8), px(5)))
            st.map(s, bordercolor=[("focus", C["accent"]), ("hover", C["border_hi"])],
                   lightcolor=[("focus", C["field"])],
                   fieldbackground=[("disabled", C["card"]), ("readonly", C["field"])],
                   foreground=[("disabled", C["faint"])])
        st.configure("Drop.TEntry", bordercolor=C["mint"], lightcolor=C["mint"], darkcolor=C["mint"])
        st.configure("Bad.TEntry", bordercolor=C["danger"])
        st.configure("TCombobox", background=C["raised"], arrowcolor=C["text"], arrowsize=px(12))
        st.map("TCombobox", background=[("active", C["hover"]), ("pressed", C["hover"])],
               selectbackground=[("readonly", C["field"])], selectforeground=[("readonly", C["text"])],
               arrowcolor=[("active", C["accent"])])
        st.configure("TSpinbox", background=C["raised"], arrowcolor=C["text"], arrowsize=px(10))
        st.map("TSpinbox", background=[("active", C["hover"])], arrowcolor=[("active", C["accent"])])
        r.option_add("*TCombobox*Listbox.background", C["raised"])
        r.option_add("*TCombobox*Listbox.foreground", C["text"])
        r.option_add("*TCombobox*Listbox.selectBackground", C["accent"])
        r.option_add("*TCombobox*Listbox.selectForeground", C["on_accent"])
        r.option_add("*TCombobox*Listbox.font", f["base"])
        r.option_add("*TCombobox*Listbox.borderWidth", 0)
        r.option_add("*TCombobox*Listbox.relief", "flat")
        st.configure("ComboboxPopdownFrame", background=C["raised"], bordercolor=C["border_hi"],
                     lightcolor=C["raised"], darkcolor=C["raised"], relief="solid", borderwidth=1)

        # custom anti-aliased checkbox / radio indicators
        self._ind = {}
        size, gap = px(17), px(9)
        for kind in ("check", "radio"):
            for state, (border, fill, mark) in dict(
                    off=(C["border_hi"], C["field"], None), hover=(C["accent"], C["field"], None),
                    dis=(C["border"], C["card"], None), on=(C["accent"], C["accent"], C["on_accent"]),
                    on_hover=(C["accent_hover"], C["accent_hover"], C["on_accent"]),
                    on_dis=(C["border_hi"], C["border_hi"], C["card"])).items():
                self._ind[kind, state] = indicator_image(kind, size, gap, border, fill, mark)
        for s, el, kind in (("TCheckbutton", "Checkbutton", "check"), ("TRadiobutton", "Radiobutton", "radio")):
            i = lambda state, k=kind: self._ind[k, state]
            st.element_create(f"vc.{el}.indicator", "image", i("off"),
                              ("disabled", "selected", i("on_dis")), ("disabled", i("dis")),
                              ("active", "selected", i("on_hover")), ("selected", i("on")),
                              ("active", i("hover")), sticky="w")
            st.layout(s, [(f"{el}.padding", {"sticky": "nswe", "children": [
                (f"vc.{el}.indicator", {"side": "left", "sticky": ""}),
                (f"{el}.label", {"side": "left", "sticky": "nswe"})]})])
            st.configure(s, background=C["card"], foreground=C["text"], padding=(0, px(3)))
            st.map(s, background=[("active", C["card"])],
                   foreground=[("disabled", C["faint"]), ("active", C["white"])])

        st.layout("TButton", [("Button.border", {"sticky": "nswe", "border": "1", "children": [
            ("Button.padding", {"sticky": "nswe", "children": [("Button.label", {"sticky": "nswe"})]})]})])
        st.configure("TButton", background=C["raised"], foreground=C["text"], bordercolor=C["border"],
                     lightcolor=C["raised"], darkcolor=C["raised"], padding=(px(12), px(6)),
                     focusthickness=0, relief="flat")
        st.map("TButton",
               background=[("disabled", C["card"]), ("pressed", C["border"]), ("active", C["hover"])],
               lightcolor=[("disabled", C["card"]), ("pressed", C["border"]), ("active", C["hover"])],
               darkcolor=[("disabled", C["card"]), ("pressed", C["border"]), ("active", C["hover"])],
               bordercolor=[("disabled", C["border"]), ("focus", C["accent"]), ("active", C["border_hi"])],
               foreground=[("disabled", C["faint"])])
        st.configure("Accent.TButton", background=C["accent"], foreground=C["on_accent"],
                     bordercolor=C["accent"], lightcolor=C["accent"], darkcolor=C["accent"],
                     font=f["bold"], padding=(px(22), px(9)))
        st.map("Accent.TButton",
               background=[("disabled", C["raised"]), ("pressed", C["accent_press"]), ("active", C["accent_hover"])],
               lightcolor=[("disabled", C["raised"]), ("pressed", C["accent_press"]), ("active", C["accent_hover"])],
               darkcolor=[("disabled", C["raised"]), ("pressed", C["accent_press"]), ("active", C["accent_hover"])],
               bordercolor=[("disabled", C["border"]), ("focus", C["white"]), ("pressed", C["accent_press"]),
                            ("active", C["accent_hover"])],
               foreground=[("disabled", C["faint"])])
        st.configure("Danger.TButton", background=C["raised"], foreground=C["danger"],
                     bordercolor=C["border"], font=f["bold"], padding=(px(18), px(9)))
        st.map("Danger.TButton",
               background=[("disabled", C["card"]), ("pressed", C["danger_bg"]), ("active", C["danger_bg"])],
               lightcolor=[("disabled", C["card"]), ("active", C["danger_bg"])],
               darkcolor=[("disabled", C["card"]), ("active", C["danger_bg"])],
               bordercolor=[("disabled", C["border"]), ("active", C["danger"])],
               foreground=[("disabled", C["faint"])])
        st.configure("Ghost.TButton", background=C["card"], foreground=C["muted"], bordercolor=C["card"],
                     lightcolor=C["card"], darkcolor=C["card"], padding=(px(8), px(4)))
        st.map("Ghost.TButton",
               background=[("disabled", C["card"]), ("active", C["raised"])],
               lightcolor=[("active", C["raised"])], darkcolor=[("active", C["raised"])],
               bordercolor=[("focus", C["border_hi"]), ("active", C["raised"])],
               foreground=[("disabled", C["faint"]), ("active", C["accent"])])
        st.configure("Mint.TButton", background=C["mint"], foreground="#06231A", bordercolor=C["mint"],
                     lightcolor=C["mint"], darkcolor=C["mint"], font=f["bold"], padding=(px(16), px(7)))
        st.map("Mint.TButton",
               background=[("pressed", "#2BBF8C"), ("active", "#63E6B9")],
               lightcolor=[("pressed", "#2BBF8C"), ("active", "#63E6B9")],
               darkcolor=[("pressed", "#2BBF8C"), ("active", "#63E6B9")],
               bordercolor=[("focus", C["white"]), ("pressed", "#2BBF8C"), ("active", "#63E6B9")])
        st.configure("Next.TButton", background=C["raised"], foreground=C["text"], bordercolor=C["border"],
                     lightcolor=C["raised"], darkcolor=C["raised"], font=f["bold"], padding=(px(14), px(5)))
        st.map("Next.TButton", background=[("active", C["hover"])], foreground=[("active", C["accent"])],
               lightcolor=[("active", C["hover"])], darkcolor=[("active", C["hover"])],
               bordercolor=[("focus", C["accent"]), ("active", C["border_hi"])])

        st.configure("Horizontal.TScale", background=C["accent"], troughcolor=C["raised"],
                     bordercolor=C["card"], lightcolor=C["accent"], darkcolor=C["accent"], gripcount=0)
        st.map("Horizontal.TScale", background=[("active", C["accent_hover"])])
        st.configure("Mint.Horizontal.TProgressbar", background=C["mint"], troughcolor=C["raised"],
                     bordercolor=C["raised"], lightcolor=C["mint"], darkcolor=C["mint"], thickness=px(10))
        st.configure("Vertical.TScrollbar", background=C["raised"], troughcolor=C["bg"],
                     bordercolor=C["bg"], lightcolor=C["raised"], darkcolor=C["raised"],
                     arrowcolor=C["muted"], gripcount=0, arrowsize=px(12))
        st.map("Vertical.TScrollbar", background=[("active", C["hover"])])

    # -- small widget factories ---------------------------------------------
    def label(self, parent, text="", fg=None, font=None, bg=None, **kw):
        return tk.Label(parent, text=text, fg=fg or C["text"], bg=bg or C["card"],
                        font=font or self.f["base"], **kw)

    def link(self, parent, text, command, fg=None, bg=None, font=None):
        color = fg or C["accent"]
        lbl = tk.Label(parent, text=text, fg=color, bg=bg or C["card"], font=font or self.f["link"],
                       cursor="hand2")
        lbl.bind("<Button-1>", lambda _: command())
        lbl.bind("<Enter>", lambda _: lbl.configure(fg=C["accent_hover"]))
        lbl.bind("<Leave>", lambda _: lbl.configure(fg=color))
        return lbl

    def tip(self, widget, key_or_text):
        Tooltip(widget, TIPS.get(key_or_text, key_or_text), self)

    def check(self, parent, text, key):
        w = ttk.Checkbutton(parent, text=text, variable=self.v[key])
        self.tip(w, key)
        return w

    def wrap_on_resize(self, container, *labels, margin=4):
        container.bind("<Configure>", lambda e: [l.configure(wraplength=max(self.px(120), e.width - self.px(margin)))
                                                 for l in labels], add="+")

    def next_button(self, section, target, text):
        row = tk.Frame(section.body, bg=C["card"])
        row.pack(fill="x", side="bottom", pady=(self.px(14), 0))
        ttk.Button(row, text=text, style="Next.TButton",
                   command=lambda: self.open_section(target)).pack(side="right")
        return row

    # -- layout -------------------------------------------------------------
    def _build(self):
        px, root = self.px, self.root
        outer = tk.Frame(root, bg=C["bg"])
        outer.pack(fill="both", expand=True)

        head = tk.Frame(outer, bg=C["bg"])
        head.pack(fill="x", padx=px(18), pady=(px(10), px(8)))
        logo = tk.Canvas(head, width=px(28), height=px(28), bg=C["bg"], highlightthickness=0)
        logo.create_oval(2, 2, px(28) - 2, px(28) - 2, fill=C["accent"], outline="")
        logo.create_text(px(14), px(14) - 1, text="»", fill=C["on_accent"], font=self.f["h3"])
        logo.pack(side="left", padx=(0, px(10)))
        tk.Label(head, text="vibeCopy", bg=C["bg"], fg=C["text"], font=self.f["title"]).pack(side="left")
        tk.Label(head, text="robocopy, without the guesswork", bg=C["bg"], fg=C["muted"],
                 font=self.f["base"]).pack(side="left", padx=(px(12), 0), pady=(px(4), 0))

        foot = tk.Frame(outer, bg=C["bg"])
        foot.pack(side="bottom", fill="x", padx=px(18), pady=(px(6), px(8)))
        tk.Label(foot, text="Nothing is saved: your changes last until you close vibeCopy.", bg=C["bg"],
                 fg=C["faint"], font=self.f["small"]).pack(side="left")
        self.link(foot, "Help & instructions ↗", self.open_help, bg=C["bg"]).pack(side="right")
        tk.Label(foot, text=f"vibeCopy {APP_VERSION}  ·", bg=C["bg"], fg=C["faint"],
                 font=self.f["small"]).pack(side="right", padx=(0, px(6)))

        self._build_runbar(outer)

        # scrollable column with the accordion
        mid = tk.Frame(outer, bg=C["bg"])
        mid.pack(fill="both", expand=True, padx=(px(18), px(6)))
        self.canvas = tk.Canvas(mid, bg=C["bg"], highlightthickness=0, bd=0, yscrollincrement=px(24))
        self.vsb = ttk.Scrollbar(mid, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.column = tk.Frame(self.canvas, bg=C["bg"])
        self._col_id = self.canvas.create_window(0, 0, window=self.column, anchor="nw")
        self.column.bind("<Configure>", lambda _: self._update_scroll())
        self.canvas.bind("<Configure>", lambda e: (self.canvas.itemconfigure(self._col_id, width=e.width),
                                                   self._update_scroll()))

        self.sections = {}
        for i, title in enumerate(("Folders", "Action", "Speed profile", "Review", "Log"), 1):
            sec = Section(self, self.column, i, title)
            sec.frame.pack(fill="x", pady=(0, px(8)), padx=(0, px(12)))
            self.sections[i] = sec
        self._build_folders(self.sections[1])
        self._build_action(self.sections[2])
        self._build_profile(self.sections[3])
        self._build_review(self.sections[4])
        self._build_log(self.sections[5])

    def _update_scroll(self):
        self.canvas.configure(scrollregion=(0, 0, self.column.winfo_reqwidth(), self.column.winfo_reqheight()))
        need = self.column.winfo_reqheight() > self.canvas.winfo_height() + 1
        if need and not self.vsb.winfo_ismapped():
            self.vsb.pack(side="right", fill="y")
        elif not need and self.vsb.winfo_ismapped():
            self.vsb.pack_forget()
            self.canvas.yview_moveto(0)

    def _on_wheel(self, event):
        w = self.root.winfo_containing(event.x_root, event.y_root)
        if w is None or w.winfo_toplevel() is not self.root:
            return
        if w is self.log_txt or isinstance(w, tk.Listbox):      # the log scrolls by itself
            return
        if not self.vsb.winfo_ismapped():
            return
        p = w
        while p is not None and p is not self.canvas:
            p = p.master
        if p is self.canvas:
            self.canvas.yview_scroll(int(-event.delta / 120) * 3, "units")

    def toggle_section(self, n):
        sec = self.sections[n]
        if sec.is_open:
            sec.set_open(False)
            self.root.after_idle(self._update_scroll)
        else:
            self.open_section(n)

    def open_section(self, n):
        for i, sec in self.sections.items():
            if sec.is_open != (i == n):
                sec.set_open(i == n)
        self.root.after_idle(lambda: self._scroll_to(self.sections[n]))
        if n == 5:
            self.root.after_idle(lambda: self.log_txt.see("end"))

    def _scroll_to(self, sec):
        self.root.update_idletasks()
        self._update_scroll()
        total = max(1, self.column.winfo_reqheight())
        view = self.canvas.winfo_height()
        top = sec.frame.winfo_y()
        bottom = top + sec.frame.winfo_reqheight()
        y0, y1 = self.canvas.yview()
        if top < y0 * total or bottom > y1 * total:
            self.canvas.yview_moveto(max(0, min(top, bottom - view)) / total)

    # 1 · Folders ----------------------------------------------------------------
    def _build_folders(self, sec):
        px, b = self.px, sec.body
        hint = tk.Frame(b, bg=C["card"])
        hint.pack(fill="x", pady=(0, px(8)))
        self.label(hint, "⤓", fg=C["accent"], font=self.f["h3"]).pack(side="left")
        self.label(hint, "Type or paste a path, click Browse…, or drag a folder from Explorer onto this window.",
                   fg=C["muted"], font=self.f["small"]).pack(side="left", padx=(px(6), 0))

        self.path_entry, self.path_status, self.path_zone = {}, {}, {}
        for key, title in (("src", "Source"), ("dst", "Destination")):
            zone = tk.Frame(b, bg=C["card"])
            zone.pack(fill="x", pady=(px(4), 0))
            row = tk.Frame(zone, bg=C["card"])
            row.pack(fill="x")
            lbl = self.label(row, title, fg=C["muted"], width=11, anchor="w")
            lbl.pack(side="left")
            self.tip(lbl, key)
            e = ttk.Entry(row, textvariable=self.v[key], font=self.f["base"])
            e.pack(side="left", fill="x", expand=True)
            e.bind("<Key>", lambda _: setattr(self, "_typing", True))
            e.bind("<Return>", lambda _: self._path_done())
            e.bind("<FocusOut>", lambda _: self._path_done())
            ttk.Button(row, text="Browse…", command=lambda k=key: self.browse(k)).pack(side="left", padx=(px(8), 0))
            st = self.label(zone, "", fg=C["faint"], font=self.f["small"], anchor="w")
            st.pack(fill="x", padx=(self.f["base"].measure("0") * 11 + px(2), 0), pady=(px(2), 0))
            self.path_entry[key], self.path_status[key], self.path_zone[key] = e, st, zone
            if key == "src":
                swap_row = tk.Frame(b, bg=C["card"])
                swap_row.pack(fill="x")
                sw = ttk.Button(swap_row, text="⇅  Swap", style="Ghost.TButton", command=self.swap_paths)
                sw.pack(side="right")
                self.tip(sw, "swap")

        frow = tk.Frame(b, bg=C["card"])
        frow.pack(fill="x", pady=(px(10), 0))
        self.filters_lnk = self.link(frow, "▸ Filters", self.toggle_filters, font=self.f["bold"])
        self.filters_lnk.pack(side="left")
        self.filters_sum = self.label(frow, "", fg=C["faint"], font=self.f["small"])
        self.filters_sum.pack(side="left", padx=(px(10), 0))
        self.filters = tk.Frame(b, bg=C["card"])
        for i, (title, key) in enumerate((("FILES", "files"), ("EXCLUDE FILES", "xf"),
                                          ("EXCLUDE FOLDERS", "xd"))):
            lbl = self.label(self.filters, title, fg=C["muted"], font=self.f["caps"], anchor="w")
            lbl.grid(row=0, column=i, sticky="w", padx=(0 if i == 0 else px(10), 0))
            e = ttk.Entry(self.filters, textvariable=self.v[key], font=self.f["base"])
            e.grid(row=1, column=i, sticky="ew", padx=(0 if i == 0 else px(10), 0), pady=(px(3), 0))
            self.tip(e, key)
            self.tip(lbl, key)
        self.filters.columnconfigure((0, 1, 2), weight=1, uniform="flt")
        self.next_button(sec, 2, "Next: Action  ›")

    def toggle_filters(self, force=None):
        self._filters_open = (not self._filters_open) if force is None else force
        if self._filters_open:
            self.filters.pack(fill="x", pady=(self.px(6), 0), after=self.filters_lnk.master)
        else:
            self.filters.pack_forget()
        self.filters_lnk.configure(text=("▾" if self._filters_open else "▸") + " Filters")
        self.root.after_idle(self._update_scroll)

    def _path_done(self):
        """Enter / leaving a path field: scan right away instead of waiting for the typing pause."""
        self._typing = False
        if self._scan_after:
            o = self.collect()
            self._schedule_scan(o, self._scan_key(o), delay=0)

    # 2 · Action ------------------------------------------------------------------
    def _build_action(self, sec):
        px, b = self.px, sec.body
        row = tk.Frame(b, bg=C["card"])
        row.pack(fill="x")
        seg = tk.Frame(row, bg=C["border"])
        seg.pack(side="left")
        self.seg = {}
        for i, (key, title, desc) in enumerate(ACTIONS):
            lbl = tk.Label(seg, text=title, bg=C["raised"], fg=C["text"], font=self.f["bold"],
                           padx=px(15), pady=px(6), cursor="hand2", takefocus=1)
            lbl.pack(side="left", padx=(0 if i == 0 else 1, 0), pady=1)
            lbl.bind("<Button-1>", lambda _, k=key: self.v["action"].set(k))
            lbl.bind("<Return>", lambda _, k=key: self.v["action"].set(k))
            lbl.bind("<space>", lambda _, k=key: self.v["action"].set(k))
            lbl.bind("<Enter>", lambda _, k=key: self._render_action(hover=k))
            lbl.bind("<Leave>", lambda _: self._render_action())
            lbl.bind("<FocusIn>", lambda _, k=key: self._render_action(hover=k))
            lbl.bind("<FocusOut>", lambda _: self._render_action())
            self.tip(lbl, desc)
            self.seg[key] = lbl
        self.subdirs_cb = self.check(row, "Include subfolders", "subdirs")
        self.subdirs_cb.pack(side="right")
        self.action_desc = self.label(b, "", fg=C["muted"], anchor="w", justify="left")
        self.action_desc.pack(fill="x", pady=(px(8), 0))
        self.wrap_on_resize(b, self.action_desc)
        self.next_button(sec, 3, "Next: Speed profile  ›")

    # 3 · Speed profile -------------------------------------------------------------
    def _build_profile(self, sec):
        px, b = self.px, sec.body
        row = tk.Frame(b, bg=C["card"])
        row.pack(fill="x")
        self.combo = ttk.Combobox(row, state="readonly", width=22, font=self.f["bold"],
                                  values=[p["name"] for p in PROFILES])
        self.combo.pack(side="left")
        self.combo.bind("<<ComboboxSelected>>", lambda _: self.apply_profile(self.combo.get(), manual=True))
        self.status_lbl = self.label(row, "", font=self.f["small"])
        self.status_lbl.pack(side="left", padx=(px(10), 0))
        self.reset_btn = ttk.Button(row, text="↺  Reset", style="Ghost.TButton", command=self.reset_profile)
        self.reset_btn.pack(side="right")
        self.tip(self.reset_btn, "reset")
        ttk.Button(row, text="?  Which one?", style="Ghost.TButton", command=self.show_guide).pack(side="right")

        tabs = tk.Frame(b, bg=C["card"])
        tabs.pack(fill="x", pady=(px(12), 0))
        self.tab_btns = {}
        for key, title in (("about", "About this profile"), ("tune", "Fine-tune")):
            f = tk.Frame(tabs, bg=C["card"])
            f.pack(side="left", padx=(0, px(20)))
            lbl = tk.Label(f, text=title, bg=C["card"], fg=C["muted"], font=self.f["bold"], cursor="hand2",
                           takefocus=1)
            lbl.pack()
            bar = tk.Frame(f, bg=C["card"], height=px(2))
            bar.pack(fill="x", pady=(px(4), 0))
            for ev in ("<Button-1>", "<Return>", "<space>"):
                lbl.bind(ev, lambda _, k=key: self._show_tab(k))
            self.tab_btns[key] = (lbl, bar)
        tk.Frame(b, bg=C["border"], height=1).pack(fill="x")

        about = tk.Frame(b, bg=C["card"])
        info = tk.Frame(about, bg=C["raised"])
        info.pack(fill="x")
        self.info_bar = tk.Frame(info, bg=C["accent"], width=px(3))
        self.info_bar.pack(side="left", fill="y")
        inner = tk.Frame(info, bg=C["raised"])
        inner.pack(side="left", fill="both", expand=True, padx=px(14), pady=px(10))
        self.info_flags = tk.Label(inner, bg=C["raised"], fg=C["accent"], font=self.f["mono"],
                                   anchor="w", justify="left")
        self.info_flags.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, px(6)))
        self.info_rows = {}
        rows = (("use", "USE IT WHEN"), ("why", "WHY"), ("watch", "WATCH OUT"), ("tuned", "TUNED FOR\nYOUR DRIVES"))
        for i, (key, title) in enumerate(rows, 1):
            head = tk.Label(inner, text=title, bg=C["raised"], fg=C["muted"], font=self.f["caps"],
                            anchor="nw", justify="left", width=12)
            head.grid(row=i, column=0, sticky="nw", pady=(px(3), px(3)))
            val = tk.Label(inner, bg=C["raised"], fg=C["mint"] if key == "tuned" else C["text"],
                           font=self.f["base"], anchor="w", justify="left", wraplength=px(380))
            val.grid(row=i, column=1, sticky="w", pady=(px(1), px(3)))
            self.info_rows[key] = (head, val)
        inner.columnconfigure(1, weight=1)
        inner.bind("<Configure>", lambda e: [v.configure(wraplength=max(px(160), e.width - px(115)))
                                             for _, v in self.info_rows.values()])

        tune = tk.Frame(b, bg=C["card"])
        r2 = tk.Frame(tune, bg=C["card"])
        r2.pack(fill="x")
        lbl = self.label(r2, "Threads", fg=C["muted"], width=8, anchor="w")
        lbl.pack(side="left")
        self.tip(lbl, "threads")
        self.scale_w = ttk.Scale(r2, from_=1, to=128, orient="horizontal",
                                 command=lambda val: self.v["threads"].set(int(round(float(val)))))
        self.scale_w.pack(side="left", fill="x", expand=True)
        self.tip(self.scale_w, "threads")
        self.threads_lbl = self.label(r2, "", fg=C["accent"], font=self.f["value"], width=4, anchor="e")
        self.threads_lbl.pack(side="left", padx=(px(8), 0))
        self.threads_desc = self.label(tune, "", fg=C["faint"], font=self.f["small"], anchor="w")
        self.threads_desc.pack(fill="x", padx=(self.f["base"].measure("0") * 8, 0))

        r3 = tk.Frame(tune, bg=C["card"])
        r3.pack(fill="x", pady=(px(8), px(2)))
        for title, key, hi, unit in (("Retries", "retries", 999, ""), ("Wait", "wait", 3600, "seconds")):
            lbl = self.label(r3, title, fg=C["muted"], width=8 if key == "retries" else 0, anchor="w")
            lbl.pack(side="left", padx=(0 if key == "retries" else px(18), px(6) if key == "wait" else 0))
            sp = ttk.Spinbox(r3, from_=0, to=hi, width=5, textvariable=self.v[key], font=self.f["base"])
            sp.pack(side="left")
            self.tip(sp, key)
            self.tip(lbl, key)
            if unit:
                self.label(r3, unit, fg=C["faint"], font=self.f["small"]).pack(side="left", padx=(px(6), 0))

        grid = tk.Frame(tune, bg=C["card"])
        grid.pack(fill="x", pady=(px(8), 0))
        for i, (text, key) in enumerate((("Restartable  /Z", "restartable"), ("Unbuffered I/O  /J", "unbuffered"),
                                         ("Skip junctions  /XJ", "skip_junctions"), ("NAS timestamps  /FFT", "fft"))):
            self.check(grid, text, key).grid(row=i // 2, column=i % 2, sticky="w", padx=(0, px(16)))
        grid.columnconfigure((0, 1), weight=1, uniform="chk")

        self.label(tune, "GENERAL  (not part of the profile)", fg=C["muted"], font=self.f["caps"],
                   anchor="w").pack(fill="x", pady=(px(10), px(2)))
        grid2 = tk.Frame(tune, bg=C["card"])
        grid2.pack(fill="x")
        for i, (text, key) in enumerate((("Keep folder dates  /DCOPY:DAT", "dir_times"),
                                         ("Copy NTFS permissions", "copy_perms"),
                                         ("Backup mode  /B  (admin)", "backup"), ("Dry run, list only  /L", "dry_run"))):
            self.check(grid2, text, key).grid(row=i // 2, column=i % 2, sticky="w", padx=(0, px(16)))
        grid2.columnconfigure((0, 1), weight=1, uniform="chk")
        r4 = tk.Frame(tune, bg=C["card"])
        r4.pack(fill="x", pady=(px(6), 0))
        self.check(r4, "Write log file", "log").pack(side="left")
        self.log_entry = ttk.Entry(r4, textvariable=self.v["log_path"], font=self.f["small"])
        self.log_entry.pack(side="left", fill="x", expand=True, padx=(px(10), px(6)))
        self.log_btn = ttk.Button(r4, text="…", width=3, command=self.browse_log)
        self.log_btn.pack(side="left")

        self.tab_frames = {"about": about, "tune": tune}
        self.next_button(sec, 4, "Next: Review  ›")

    def _show_tab(self, key):
        for k, frame in self.tab_frames.items():
            lbl, bar = self.tab_btns[k]
            if k == key:
                frame.pack(fill="both", expand=True, pady=(self.px(12), 0))
                lbl.configure(fg=C["text"])
                bar.configure(bg=C["accent"])
            else:
                frame.pack_forget()
                lbl.configure(fg=C["muted"])
                bar.configure(bg=C["card"])
        self.root.after_idle(self._update_scroll)

    # 4 · Review --------------------------------------------------------------------
    def _build_review(self, sec):
        px, b = self.px, sec.body
        top = tk.Frame(b, bg=C["card"])
        top.pack(fill="x")
        self.scan_main = self.label(top, "", font=self.f["value"], anchor="w", justify="left")
        self.scan_main.pack(side="left", fill="x", expand=True)
        self.rescan_lnk = self.link(top, "Rescan", self.rescan)
        self.rescan_lnk.pack(side="right")
        self.tip(self.rescan_lnk, "rescan")
        self.scan_age = self.label(top, "", fg=C["faint"], font=self.f["small"])
        self.scan_age.pack(side="right", padx=(0, px(8)))
        self.scan_mix = self.label(b, "", fg=C["muted"], font=self.f["small"], anchor="w", justify="left")
        self.scan_mix.pack(fill="x", pady=(px(2), 0))
        self.scan_drives = self.label(b, "", fg=C["muted"], font=self.f["small"], anchor="w", justify="left")
        self.scan_drives.pack(fill="x")
        rec = tk.Frame(b, bg=C["card"])
        rec.pack(fill="x", pady=(px(6), 0))
        self.scan_rec = self.label(rec, "", fg=C["mint"], anchor="w", justify="left")
        self.scan_rec.pack(side="left", fill="x", expand=True)
        self.apply_lnk = self.link(rec, "Apply", self.apply_recommended)
        warn = tk.Frame(b, bg=C["card"])
        warn.pack(fill="x", pady=(px(4), 0))
        self.scan_warn = self.label(warn, "", fg=C["amber"], anchor="w", justify="left")
        self.scan_warn.pack(side="left", fill="x", expand=True)
        self.extras_lnk = self.link(warn, "Show files", self.show_extras)
        self.wrap_on_resize(b, self.scan_main, self.scan_mix, self.scan_drives)
        rec.bind("<Configure>", lambda e: self.scan_rec.configure(wraplength=max(px(120), e.width - px(70))))
        warn.bind("<Configure>", lambda e: self.scan_warn.configure(wraplength=max(px(120), e.width - px(90))))

        head = tk.Frame(b, bg=C["card"])
        head.pack(fill="x", pady=(px(14), px(4)))
        self.label(head, "COMMAND", fg=C["muted"], font=self.f["caps"]).pack(side="left")
        self.copied_lbl = self.label(head, "", fg=C["mint"], font=self.f["small"])
        self.copied_lbl.pack(side="right", padx=(0, px(8)))
        ttk.Button(head, text="Copy", style="Ghost.TButton", command=self.copy_command).pack(side="right")
        box = tk.Frame(b, bg=C["field"], highlightthickness=1, highlightbackground=C["border"])
        box.pack(fill="x")
        self.cmd_txt = tk.Text(box, height=3, wrap="word", bg=C["field"], fg=C["soft"], bd=0,
                               font=self.f["mono"], padx=px(10), pady=px(8), highlightthickness=0,
                               insertbackground=C["accent"], selectbackground=C["sel"], cursor="arrow")
        self.cmd_txt.pack(fill="x")
        for tag, color in (("exe", C["text"]), ("path", C["mint"]), ("ph", C["faint"]), ("sw", C["accent"]),
                           ("danger", C["danger"]), ("arg", C["amber"])):
            self.cmd_txt.tag_configure(tag, foreground=color)
        self.cmd_txt.tag_configure("exe", font=self.f["mono_b"])
        self.cmd_txt.tag_configure("danger", font=self.f["mono_b"])
        self.cmd_txt.configure(state="disabled")
        self.cmd_txt.bind("<Configure>", lambda _: self._fit_command())
        self.label(b, "vibeCopy adds a temporary /UNILOG file when it runs this, so file names in any language "
                      "show correctly.", fg=C["faint"], font=self.f["small"], anchor="w",
                   justify="left").pack(fill="x", pady=(px(4), 0))

        # "Reuse this copy anytime": Save .bat gets a box of its own (it's a feature, not a detail)
        raised = C["raised"]
        reuse = tk.Frame(b, bg=raised)
        reuse.pack(fill="x", pady=(px(14), 0))
        self.reuse_box = reuse
        tk.Frame(reuse, bg=C["mint"], width=px(3)).pack(side="left", fill="y")
        inner = tk.Frame(reuse, bg=raised)
        inner.pack(side="left", fill="both", expand=True, padx=px(14), pady=px(12))
        tk.Label(inner, text="Reuse this copy anytime", bg=raised, fg=C["text"], font=self.f["h3"],
                 anchor="w").pack(fill="x")
        txt = tk.Label(inner, text="Save it as a .bat file. Double-click the file to run exactly this copy again, "
                                   "or let Windows run it on a schedule (every night, every Monday…) with Task "
                                   "Scheduler. vibeCopy doesn't even need to be open.",
                       bg=raised, fg=C["soft"], anchor="w", justify="left")
        txt.pack(fill="x", pady=(px(4), 0))
        inner.bind("<Configure>", lambda e: txt.configure(wraplength=max(px(160), e.width - px(4))), add="+")
        row = tk.Frame(inner, bg=raised)
        row.pack(fill="x", pady=(px(10), 0))
        bb = ttk.Button(row, text="⤓   Save as .bat…", style="Mint.TButton", command=self.save_bat)
        bb.pack(side="left")
        self.tip(bb, "save_bat")
        self.link(row, "How to schedule it", self.show_schedule_help, bg=raised).pack(side="left", padx=(px(14), 0))
        self.bat_saved = tk.Label(row, text="", bg=raised, fg=C["mint"], font=self.f["small"])
        self.bat_saved.pack(side="left", padx=(px(14), 0))
        self.bat_show = self.link(row, "Show in folder", self._show_saved_bat, bg=raised)
        self._saved_bat = None
        self.label(b, "All set? Press  ►  Run  below  (Ctrl+Enter).", fg=C["muted"], anchor="w").pack(
            fill="x", pady=(px(12), 0))

    def _fit_command(self):
        try:
            lines = self.cmd_txt.count("1.0", "end", "displaylines")[0]
        except (tk.TclError, TypeError):
            return
        lines = min(6, max(2, lines))
        if int(self.cmd_txt.cget("height")) != lines:
            self.cmd_txt.configure(height=lines)

    # 5 · Log -----------------------------------------------------------------------
    def _build_log(self, sec):
        px, b = self.px, sec.body
        bar = tk.Frame(b, bg=C["card"])
        bar.pack(fill="x", pady=(0, px(6)))
        self.check(bar, "Show every file", "verbose").pack(side="left")
        self.failed_lnk = self.link(bar, "", self.show_failed, fg=C["danger"])
        box = tk.Frame(b, bg=C["field"], highlightthickness=1, highlightbackground=C["border"])
        box.pack(fill="both", expand=True)
        self.log_txt = tk.Text(box, wrap="none", bg=C["field"], fg=C["soft"], bd=0, height=14,
                               font=self.f["mono"], padx=px(10), pady=px(8), highlightthickness=0,
                               selectbackground=C["sel"], insertbackground=C["accent"])
        sb = ttk.Scrollbar(box, orient="vertical", command=self.log_txt.yview)
        self.log_txt.configure(yscrollcommand=sb.set, state="disabled")
        sb.pack(side="right", fill="y")
        self.log_txt.pack(side="left", fill="both", expand=True)
        for tag, color in (("info", C["soft"]), ("dim", C["faint"]), ("ok", C["mint"]),
                           ("warn", C["amber"]), ("err", C["danger"]), ("cmd", C["accent"])):
            self.log_txt.tag_configure(tag, foreground=color)

    # Run bar (always visible) --------------------------------------------------------
    def _build_runbar(self, parent):
        px = self.px
        wrap = tk.Frame(parent, bg=C["bg"])
        wrap.pack(side="bottom", fill="x", padx=px(18))
        bar = tk.Frame(wrap, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        bar.pack(fill="x")
        self.runbar = bar
        tk.Frame(bar, bg=C["accent"], height=px(2)).pack(fill="x")
        body = tk.Frame(bar, bg=C["card"])
        body.pack(fill="x", padx=px(16), pady=(px(12), px(12)))

        r1 = tk.Frame(body, bg=C["card"])
        r1.pack(fill="x")
        self.run_btn = ttk.Button(r1, text="►   Run", style="Accent.TButton", command=self.start)
        self.run_btn.pack(side="left")
        self.stop_btn = ttk.Button(r1, text="■   Stop", style="Danger.TButton", command=self.stop,
                                   state="disabled")
        self.stop_btn.pack(side="left", padx=(px(8), 0))
        mid = tk.Frame(r1, bg=C["card"])
        mid.pack(side="left", fill="x", expand=True, padx=(px(16), 0))
        top = tk.Frame(mid, bg=C["card"])
        top.pack(fill="x")
        self.phase_lbl = self.label(top, "Ready", font=self.f["h2"])
        self.phase_lbl.pack(side="left")
        self.pct_lbl = self.label(top, "", fg=C["mint"], font=self.f["h2"])
        self.pct_lbl.pack(side="right")
        self.pbar = ttk.Progressbar(mid, style="Mint.Horizontal.TProgressbar", maximum=1000)
        self.pbar.pack(fill="x", pady=(px(4), 0))

        r2 = tk.Frame(body, bg=C["card"])
        r2.pack(fill="x", pady=(px(10), 0))
        self.stat = {}
        cells = (("speed", "SPEED", 3), ("eta", "TIME LEFT", 2), ("elapsed", "ELAPSED", 2),
                 ("files", "FILES", 3), ("data", "DATA", 4), ("errors", "FAILED", 2))
        for i, (key, title, weight) in enumerate(cells):
            cell = tk.Frame(r2, bg=C["card"])
            cell.grid(row=0, column=i, sticky="w")
            tk.Label(cell, text=title, bg=C["card"], fg=C["muted"], font=self.f["caps"]).pack(anchor="w")
            val = tk.Label(cell, text="—", bg=C["card"], fg=C["text"], font=self.f["value"])
            val.pack(anchor="w")
            self.stat[key] = val
            r2.columnconfigure(i, weight=weight, uniform="stats")
        self.stat["errors"].bind("<Button-1>", lambda _: self.show_failed())

        r3 = tk.Frame(body, bg=C["card"])
        r3.pack(fill="x", pady=(px(8), 0))
        self.detail_lbl = self.label(r3, "", fg=C["muted"], font=self.f["small"], anchor="w")
        self.detail_lbl.pack(side="left", fill="x", expand=True)
        self.open_btn = ttk.Button(r3, text="Open destination", style="Ghost.TButton",
                                   command=self.open_destination)
        self.open_btn.pack(side="right")
        cb = ttk.Combobox(r3, state="readonly", width=11, values=WHEN_DONE, textvariable=self.v["when_done"],
                          font=self.f["small"])
        cb.pack(side="right", padx=(px(6), px(10)))
        self.tip(cb, "when_done")
        lbl = self.label(r3, "When done", fg=C["muted"], font=self.f["small"])
        lbl.pack(side="right")
        self.tip(lbl, "when_done")
        self._detail_text = ""
        self.tip(self.detail_lbl, "")
        self.detail_lbl.bind("<Configure>", lambda _: self._fit_detail())

    def set_detail(self, text, fg=None, path=False):
        """Status line under the stats. Paths are shortened from the left (keeps the file name),
        sentences from the right."""
        if (text, fg, path) == (self._detail_text, getattr(self, "_detail_fg", None), getattr(self, "_detail_path", None)):
            return                                      # unchanged: skip the text measuring and redraw
        self._detail_fg = fg
        self._detail_text, self._detail_path = text, path
        self.detail_lbl.configure(fg=fg or C["muted"])
        self._fit_detail()

    def _fit_detail(self):
        w, text, font = self.detail_lbl.winfo_width() - 4, self._detail_text, self.f["small"]
        if w > 20 and font.measure(text) > w:
            if getattr(self, "_detail_path", False):
                text = elide_px(text, font, w)
            else:
                while text and font.measure(text + "…") > w:
                    text = text[:-1]
                text += "…"
        self.detail_lbl.configure(text=text)
        Tooltip.update(self.detail_lbl, self._detail_text if text != self._detail_text else "")

    def _place_window(self):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        wa_w, wa_h = work_area() or (sw, sh)
        w, h = min(self.px(880), wa_w - self.px(40)), min(self.px(920), wa_h - self.px(70))
        self.root.geometry(f"{w}x{h}+{(wa_w - w) // 2}+{max(0, (wa_h - h - self.px(40)) // 2)}")
        self.root.minsize(min(self.px(640), wa_w), min(self.px(560), wa_h - self.px(40)))

    # -- options / profiles -------------------------------------------------
    def collect(self):
        o = {}
        for k, d in ALL_DEFAULTS.items():
            try:
                val = self.v[k].get()
            except (tk.TclError, ValueError):
                val = d
            if isinstance(d, bool):
                val = bool(val)
            elif isinstance(d, int):
                try:
                    val = max(0, int(float(val)))
                except (TypeError, ValueError):
                    val = d
            o[k] = val
        o["threads"] = min(128, max(1, o["threads"]))
        if o["action"] not in ACTION_TEXT:
            o["action"] = "copy"
        return o

    def apply_profile(self, name, values=None, tuning=(), manual=False):
        if name not in PROFILE_BY_NAME:
            return
        values = dict(values or {**PROFILE_DEFAULTS, **PROFILE_BY_NAME[name]["set"]})
        self._applying = True
        for k, val in values.items():
            self.v[k].set(val)
        self._applying = False
        self.profile = name
        self.base_values = values
        self.applied_tuning = list(tuning)
        self.combo.set(name)
        self.scale_w.set(values["threads"])
        if manual:
            self.touched = True
        self._refresh()

    def apply_recommended(self):
        if self.recommended:
            name, values, _, tuning = self.recommended
            self.apply_profile(name, values, tuning)
            self.touched = False

    def reset_profile(self):
        if self.recommended and self.recommended[0] == self.profile:
            self.apply_recommended()
        else:
            self.apply_profile(self.profile)

    def _show_info(self, o):
        p = PROFILE_BY_NAME[self.profile]
        pv = {k: o[k] for k in PROFILE_DEFAULTS}
        self.info_flags.configure(text=profile_flags(pv))
        for key in ("use", "why", "watch"):
            self.info_rows[key][1].configure(text=p[key])
        self.info_rows["watch"][1].configure(fg=C["amber"])
        head, val = self.info_rows["tuned"]
        if self.applied_tuning:
            val.configure(text="\n".join("•  " + t for t in self.applied_tuning))
            head.grid()
            val.grid()
        else:
            head.grid_remove()
            val.grid_remove()

    # -- folders: typing, browsing, dropping ----------------------------------------
    def browse(self, key):
        current = norm_path(self.v[key].get())
        path = filedialog.askdirectory(parent=self.root, initialdir=current if os.path.isdir(current) else None,
                                       title="Choose the source folder" if key == "src" else "Choose the destination folder")
        if path:
            self._typing = False
            self.v[key].set(os.path.normpath(path))

    def swap_paths(self):
        self._typing = False
        src, dst = self.v["src"].get(), self.v["dst"].get()
        self.v["src"].set(dst)
        self.v["dst"].set(src)

    def on_drop(self, paths):
        """Folders/files dropped from Explorer. Goes to the field under the mouse, else the first empty one."""
        target = None
        try:
            from ctypes import wintypes
            pt = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            w = self.root.winfo_containing(pt.x, pt.y)
        except Exception:
            w = None
        while w is not None:
            for key, zone in self.path_zone.items():
                if w is zone:
                    target = key
            if target:
                break
            w = w.master
        o = self.collect()
        if target is None:
            if not norm_path(o["src"]):
                target = "src"
            elif not norm_path(o["dst"]):
                target = "dst"
            else:
                target = self.choose("Use the dropped item as…", elide(paths[0], 70),
                                     [("Source", "src"), ("Destination", "dst")])
                if not target:
                    return
        first = paths[0]
        self._typing = False
        note = ""
        if os.path.isdir(first) or is_network_path(first) and not os.path.splitext(first)[1]:
            self.v[target].set(os.path.normpath(first))
            if len(paths) > 1:
                note = f"Only the first of the {len(paths)} dropped items was used."
        else:
            folder = os.path.dirname(first)
            self.v[target].set(folder)
            if target == "src":
                names = [os.path.basename(p) for p in paths if os.path.dirname(p) == folder and not os.path.isdir(p)]
                self.v["files"].set(" ".join(f'"{n}"' if " " in n else n for n in names))
                self._drop_filter = (os.path.normcase(norm_path(folder)), self.v["files"].get())
                self.toggle_filters(True)
                note = (f"Dropped {'a file' if len(names) == 1 else f'{len(names)} files'}: only "
                        f"{'it' if len(names) == 1 else 'those'} will be copied (see Filters).")
            else:
                note = "A file was dropped: its folder is used as the destination."
        self.open_section(1)
        e = self.path_entry[target]
        e.configure(style="Drop.TEntry")
        self.root.after(900, lambda: e.configure(style="TEntry"))
        if note:
            self.set_detail(note, C["amber"])

    # -- live refresh -------------------------------------------------------
    def _schedule_refresh(self):
        if self._ready and not self._applying and not self._refresh_pending:
            self._refresh_pending = True
            self._refresh_id = self.root.after_idle(self._refresh)

    def _refresh(self):
        self._refresh_pending = False
        o = self.collect()
        df = self._drop_filter
        if df and os.path.normcase(norm_path(o["src"])) != df[0]:
            # the Files filter came from dropping files; a new source must not silently keep it
            self._drop_filter = None
            if o["files"] == df[1]:
                self.v["files"].set("*.*")
                o = self.collect()
                self.set_detail("The source changed, so the file filter from your earlier drop was cleared.",
                                C["amber"])
        pv = {k: o[k] for k in PROFILE_DEFAULTS}
        modified = pv != self.base_values
        if modified:
            self.touched = True
        folders = (norm_path(o["src"]).lower(), norm_path(o["dst"]).lower())
        if folders != self._folders:                    # new folders = new job: recommend again
            self._folders = folders
            self.touched = modified

        is_rec = bool(self.recommended) and self.recommended[0] == self.profile
        if modified:
            self.status_lbl.configure(text="● modified", fg=C["amber"])
        elif is_rec:
            self.status_lbl.configure(text="★ recommended", fg=C["mint"])
        else:
            self.status_lbl.configure(text="")
        self.reset_btn.configure(state="normal" if modified else "disabled")

        n = o["threads"]
        self.threads_lbl.configure(text=str(n))
        self.threads_desc.configure(text="Off: one file at a time, live % inside each file" if n == 1
                                    else f"{n} files copied in parallel")
        if abs(self.scale_w.get() - n) >= 1:
            self.scale_w.set(n)
        self.subdirs_cb.configure(state="disabled" if o["action"] == "mirror" else "normal")
        state = "normal" if o["log"] else "disabled"
        self.log_entry.configure(state=state)
        self.log_btn.configure(state=state)
        self._render_action()
        self._show_info(o)
        self._render_command(build_args(o))
        self._render_paths(o)

        key = self._scan_key(o)
        if key != self.scan_key and not self.job:      # never scan during a copy: it would steal disk time
            self._scan_skipped = False
            self._schedule_scan(o, key, delay=1200 if self._typing else 250)
        self._render_scan()
        self._update_summaries(o)

    def _render_paths(self, o):
        src, dst = norm_path(o["src"]), norm_path(o["dst"])
        ok_src = folder_exists(src)
        for key, path, exists in (("src", src, ok_src), ("dst", dst, folder_exists(dst))):
            st = self.path_status[key]
            if not path:
                st.configure(text="", fg=C["faint"])
                continue
            if not is_full_path(path):
                st.configure(text="✗  Type a full path, like D:\\Backup or \\\\server\\share", fg=C["danger"])
                continue
            info = drive_info_nowait(path, self._drives_ready) if not is_network_path(path) else dict(
                root=path[:2] if path[1:2] == ":" else "\\\\" + "\\".join(path.lstrip("\\").split("\\")[:2]),
                kind="network", fs=None, hdd=None, bus=None, disk=None)
            where = f"  ·  {describe_drive(info)}" if info else ""
            if exists is None:
                st.configure(text=f"Network location{where}: checked by the scan", fg=C["muted"])
            elif exists:
                st.configure(text=f"✓  Folder found{where}", fg=C["mint"])
            elif key == "src":
                st.configure(text="✗  Folder not found", fg=C["danger"])
            else:
                st.configure(text=f"Will be created{where}", fg=C["muted"])
        if src and dst and ok_src is not False:
            if same_path(src, dst):
                self.path_status["dst"].configure(text="✗  Same folder as the source", fg=C["danger"])
            elif is_inside(dst, src) and (o["subdirs"] or o["action"] == "mirror"):
                self.path_status["dst"].configure(text="✗  Inside the source folder: it would copy into itself",
                                                  fg=C["danger"])
        f = split_patterns(o["files"])
        parts = ["all files" if not f or f == ["*.*"] else " ".join(f[:3]) + (" …" if len(f) > 3 else "")]
        if split_patterns(o["xf"]):
            parts.append(f"skip files: {' '.join(split_patterns(o['xf'])[:3])}")
        if split_patterns(o["xd"]):
            parts.append(f"skip folders: {' '.join(split_patterns(o['xd'])[:3])}")
        bad = bad_patterns(o)
        if bad:
            self.filters_sum.configure(text=f"✗  “{bad[0]}” starts with “/”: robocopy would read it as an option",
                                       fg=C["danger"])
        else:
            self.filters_sum.configure(text="  ·  ".join(parts), fg=C["faint"])

    def _drives_ready(self):
        """Called from a background thread: only set a flag (Tk must be used from its own thread)."""
        self._drives_changed = True

    def _update_summaries(self, o=None):
        o = o or self.collect()
        s = self.sections
        src, dst = norm_path(o["src"]), norm_path(o["dst"])
        if src and dst:
            ok = self.scan_key is not None
            s[1].set_summary(f"{src}   →   {dst}", "ok" if ok else "danger")
        else:
            s[1].set_summary("Choose a source and a destination", "warn" if (src or dst) else None)
        title, desc = ACTION_TEXT[o["action"]]
        short = {"copy": "nothing is deleted", "update": "never overwrites newer files",
                 "mirror": "deletes extras in the destination", "move": "deletes the source files"}[o["action"]]
        s[2].set_summary(f"{title.replace(' ⚠', '')}  ·  {short}",
                         "danger" if o["action"] in DANGER_ACTIONS else "ok")
        pv = {k: o[k] for k in PROFILE_DEFAULTS}
        rec = self.recommended and self.recommended[0] == self.profile and pv == self.recommended[1]
        s[3].set_summary(f"{self.profile}" + ("  ·  ★ recommended" if rec else
                                              "  ·  modified" if pv != self.base_values else ""), "ok")
        sc = self.scan
        if self.scan_key is None:
            s[4].set_summary("Waiting for the folders")
        elif sc is None and self._scan_skipped:
            s[4].set_summary("Scan skipped (no ETA)")
        elif sc is None or not sc.done:
            s[4].set_summary("Scanning…", "busy")
        elif not sc.ok:
            s[4].set_summary("The scan failed", "danger")
        else:
            warns = self._scan_warnings(o, sc)
            text = (f"{sc.n:,} file{'s' if sc.n != 1 else ''}  ·  {fmt_bytes(sc.bytes)} to copy" if sc.n
                    else "Nothing to copy")
            if warns:
                level = "danger" if any(l == "danger" for _, l in warns) else "warn"
                s[4].set_summary(f"{text}  ·  {len(warns)} warning{'s' if len(warns) != 1 else ''}", level)
            else:
                s[4].set_summary(text, "ok")
        if self.job:
            s[5].set_summary("Copy in progress…", "busy")
        elif self.last_job:
            s[5].set_summary(self._last_result, self._last_state)
        else:
            s[5].set_summary("")

    def _render_action(self, hover=None):
        action = self.v["action"].get()
        for key, lbl in self.seg.items():
            if key == action:
                bg = C["danger"] if key in DANGER_ACTIONS else C["accent"]
                lbl.configure(bg=bg, fg=C["on_accent"])
            else:
                lbl.configure(bg=C["hover"] if key == hover else C["raised"], fg=C["text"])
        title, desc = ACTION_TEXT.get(action, ACTION_TEXT["copy"])
        self.action_desc.configure(text=desc, fg=C["danger"] if action in DANGER_ACTIONS else C["muted"])

    def _render_command(self, args):
        self._last_args = args
        t = self.cmd_txt
        t.configure(state="normal")
        t.delete("1.0", "end")
        for i, a in enumerate(args):
            if i == 0:
                tag = "exe"
            elif i in (1, 2):
                tag = "ph" if a.startswith("<") else "path"
            elif a in ("/MIR", "/MOVE", "/MOV"):
                tag = "danger"
            elif a.startswith("/"):
                tag = "sw"
            else:
                tag = "arg"
            t.insert("end", cmd_quote(a), tag)
            t.insert("end", " ")
        t.configure(state="disabled")
        self._fit_command()

    # -- scan -----------------------------------------------------------------
    def _scan_key(self, o):
        src, dst = norm_path(o["src"]), norm_path(o["dst"])
        if not is_full_path(src) or not is_full_path(dst) or bad_patterns(o):
            return None
        if folder_exists(src) is False or same_path(src, dst):
            return None
        if is_inside(dst, src) and (o["subdirs"] or o["action"] == "mirror"):
            return None
        return tuple(build_args(o, scan=True))

    def _schedule_scan(self, o, key, delay=250):
        if self._scan_after:
            self.root.after_cancel(self._scan_after)
            self._scan_after = None
        if self.scan and not self.scan.done:
            self.scan.cancel()
        self.scan, self.scan_key = None, key
        if key is not None:
            src, dst = norm_path(o["src"]), norm_path(o["dst"])
            self._scan_after = self.root.after(delay, lambda: self._start_scan(key, src, dst))

    def _start_scan(self, key, src, dst):
        self._scan_after = None
        if key != self.scan_key:
            return
        self.scan = Scanner(list(key), src, dst)
        self.scan.start()
        self._scan_done_seen = False

    def rescan(self):
        if self.job:
            return
        o = self.collect()
        self._schedule_scan(o, self._scan_key(o), delay=0)
        self._render_scan()

    def _on_scan_done(self):
        sc = self.scan
        if sc.ok and sc.n > 0:                          # nothing to copy = nothing to recommend
            self.recommended = recommend(sc)
            name, values, _, tuning = self.recommended
            if not self.touched:
                self.apply_profile(name, values, tuning)
        else:
            self.recommended = None
        self._refresh()
        if self._pending_run:
            self._pending_run = False
            self.start()

    def _render_scan(self):
        sc, o = self.scan, self.collect()
        self.apply_lnk.pack_forget()
        self.extras_lnk.pack_forget()
        if self.scan_key is None:
            self.scan_main.configure(text="Choose a source folder and a destination first (step 1).", fg=C["muted"])
            for w in (self.scan_mix, self.scan_drives, self.scan_rec, self.scan_age, self.scan_warn):
                w.configure(text="")
            return
        if sc is None and self._scan_skipped:
            self.scan_main.configure(text="Scan skipped for this run (no ETA)", fg=C["muted"])
            for w in (self.scan_mix, self.scan_drives, self.scan_rec, self.scan_age, self.scan_warn):
                w.configure(text="")
            return
        if sc is None or not sc.done:
            n, b = (sc.n, sc.bytes) if sc else (0, 0)
            secs = int(time.time() - sc.t_start) if sc else 0
            self.scan_main.configure(text="Scanning…" + (f"  {secs} s" if secs >= 2 else ""), fg=C["text"])
            hint = ("   ·   Taking long? A network drive may be slow or offline."
                    if secs >= 10 and n == 0 else "")
            self.scan_mix.configure(text=(f"{n:,} files · {fmt_bytes(b)} found so far" + hint) if sc else "")
            for w in (self.scan_drives, self.scan_rec, self.scan_age, self.scan_warn):
                w.configure(text="")
            return
        if not sc.ok:
            self.scan_main.configure(text="The scan failed", fg=C["danger"])
            detail = sc.error or "\n".join(l for l in sc.other if l)[:400] or f"robocopy exit code {sc.rc}"
            self.scan_mix.configure(text=detail)
            for w in (self.scan_drives, self.scan_rec, self.scan_warn):
                w.configure(text="")
            self.scan_age.configure(text=fmt_ago(sc.t_done) + "  ·")
            return

        if sc.n:
            self.scan_main.configure(text=f"{sc.n:,} file{'s' if sc.n != 1 else ''} · {fmt_bytes(sc.bytes)} to copy",
                                     fg=C["text"])
            self.scan_mix.configure(text=f"Under 1 MB: {sc.small_n:,}   ·   1–100 MB: {sc.mid_n:,}   ·   "
                                         f"100 MB+: {sc.big_n:,}   ·   largest {fmt_bytes(sc.max_size)}")
        else:
            self.scan_main.configure(text="Nothing to copy: the destination is already up to date", fg=C["mint"])
            self.scan_mix.configure(text="")
        drives = f"{describe_drive(sc.src_info)}   →   {describe_drive(sc.dst_info)}"
        si, di = sc.src_info, sc.dst_info
        if si and di and si["disk"] is not None and si["disk"] == di["disk"]:
            drives += "   (same physical disk)"
        if sc.free is not None:
            drives += f"   ·   {fmt_bytes(sc.free)} free"
        self.scan_drives.configure(text=drives)
        self.scan_age.configure(text=f"scanned {fmt_ago(sc.t_done)}  ·")

        if self.recommended and sc.n:
            name, _, reasons, _ = self.recommended
            self.scan_rec.configure(text=f"★  Recommended profile: {name}.  " + " ".join(reasons))
            pv = {k: o[k] for k in PROFILE_DEFAULTS}
            if name != self.profile or pv != self.recommended[1]:
                self.apply_lnk.pack(side="right")
        else:
            self.scan_rec.configure(text="")
        if not self.job and not self._pending_run and self.phase_lbl.cget("text") == "Ready":
            self.set_detail("Everything's ready: press Run to start." if sc.n else "Nothing to copy right now.")

        warn = self._scan_warnings(o, sc)
        self.scan_warn.configure(text="\n".join("⚠  " + t for t, _ in warn),
                                 fg=C["danger"] if any(c == "danger" for _, c in warn) else C["amber"])
        if o["action"] == "mirror" and sc.extras:
            self.extras_lnk.pack(side="right", anchor="n")

    def _scan_warnings(self, o, sc):
        """[(text, level)] from the scan, level 'danger' or 'warn'."""
        out = []
        dst_root = sc.dst_info["root"] if sc.dst_info else "the destination"
        if o["action"] == "mirror" and sc.extras:
            out.append((f"Mirror will DELETE {sc.extras:,} file{'s' if sc.extras != 1 else ''} from the "
                        f"destination that aren't in the source.", "danger"))
        risky = risky_mirror_target(o["dst"]) if o["action"] == "mirror" else None
        if risky:
            out.append((f"The destination is {risky}. Mirror deletes EVERYTHING in it that isn't in the source.",
                        "danger"))
        if o["action"] == "move" and sc.n:
            out.append((f"Move will delete {sc.n:,} files from the source after copying them.", "warn"))
        if sc.free is not None and sc.bytes > sc.free:
            out.append((f"Not enough space: {fmt_bytes(sc.bytes)} to copy, only {fmt_bytes(sc.free)} free on "
                        f"{dst_root}. (Files that get overwritten free some space, so it might still fit.)",
                        "danger"))
        elif sc.free is not None and sc.bytes > 0.9 * sc.free:
            out.append((f"Tight on space: {fmt_bytes(sc.bytes)} to copy, {fmt_bytes(sc.free)} free.", "warn"))
        fs = ((sc.dst_info or {}).get("fs") or "").upper()
        if fs in ("FAT32", "FAT") and sc.over4g:
            out.append((f"{sc.over4g:,} file{'s are' if sc.over4g != 1 else ' is'} larger than 4 GB, which "
                        f"{fs} can't store. Copy to an NTFS or exFAT drive instead.", "danger"))
        return out

    # -- misc actions -----------------------------------------------------------
    def browse_log(self):
        cur = self.v["log_path"].get()
        path = filedialog.asksaveasfilename(parent=self.root, title="Log file", defaultextension=".log",
                                            initialdir=os.path.dirname(cur) or None,
                                            initialfile=os.path.basename(cur) or "robocopy.log",
                                            filetypes=[("Log files", "*.log *.txt"), ("All files", "*.*")])
        if path:
            self.v["log_path"].set(os.path.normpath(path))

    def open_destination(self):
        dst = norm_path(self.v["dst"].get())
        if dst and os.path.isdir(dst):
            os.startfile(dst)
        else:
            self.message("Not found", "The destination folder doesn't exist (yet).", C["amber"])

    def open_help(self):
        webbrowser.open(HELP_URL)

    def copy_command(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(cmd_line(self._last_args))
        self._flash_note("Copied to clipboard")

    def _flash_note(self, text):
        self.copied_lbl.configure(text=text)
        self.root.after(2200, lambda: self.copied_lbl.configure(text=""))

    def save_bat(self):
        o = self.collect()
        if not norm_path(o["src"]) or not norm_path(o["dst"]):
            self.message("Save .bat", "Choose the source and destination folders first.", C["amber"])
            return
        errors, _ = validate(o)
        errors = [e for e in errors if "Administrator" not in e]   # /B may be fine for a task run as admin
        if errors:
            self.message("Save .bat", "\n\n".join(errors), C["danger"])
            return
        if o["action"] in DANGER_ACTIONS and not o["dry_run"] and not self.ask(
                "This .bat deletes files",
                f"The action is {ACTION_TEXT[o['action']][0].replace(' ⚠', '')}: "
                + ("every time the .bat runs, files in the destination that aren't in the source are DELETED."
                   if o["action"] == "mirror" else
                   "every time the .bat runs, the copied files are DELETED from the source.")
                + "\n\nThat's usually what you want for a scheduled backup mirror, but double-check the folders."
                  "\n\nSave it anyway?", "Save .bat", danger=True):
            return
        src_name = os.path.basename(norm_path(o["src"]).rstrip("\\")) or "drive"
        path = filedialog.asksaveasfilename(parent=self.root, title="Save as .bat", defaultextension=".bat",
                                            initialfile=f"vibeCopy - {src_name}.bat",
                                            filetypes=[("Batch file", "*.bat"), ("All files", "*.*")])
        if not path:
            return
        cmd = cmd_line(build_args(o)).replace("%", "%%")
        title = ACTION_TEXT[o["action"]][0].replace(" ⚠", "")
        lines = [
            "@echo off",
            f"rem vibeCopy job, created {time.strftime('%Y-%m-%d %H:%M')}",
            f"rem Action: {title}   Profile: {self.profile}",
            "rem Double-click to run it again, or schedule it with Windows Task Scheduler.",
        ]
        if o["action"] in DANGER_ACTIONS:
            lines.append(f"rem WARNING: {title} deletes files every time this runs.")
        lines += [
            cmd,
            "set RC=%ERRORLEVEL%",
            "echo.",
            "if %RC% GEQ 8 (echo Finished with errors - robocopy exit code %RC%) "
            "else (echo Done - robocopy exit code %RC%)",
            "rem Exit codes 0-7 mean success, 8 or higher means some files could not be copied.",
            "if %RC% GEQ 8 exit /b %RC%",
            "exit /b 0",
        ]
        text = "\r\n".join(lines) + "\r\n"
        try:
            data = text.encode(ENC)
        except UnicodeEncodeError:                     # names outside the console codepage
            data = ("@chcp 65001 >nul\r\n" + text).encode("utf-8")
        try:
            with open(path, "wb") as fh:
                fh.write(data)
        except OSError as e:
            self.message("Save .bat", f"Couldn't save the file:\n{e}", C["danger"])
            return
        self._saved_bat = path
        self.bat_saved.configure(text="✓  Saved " + os.path.basename(path))
        self.bat_show.pack(side="left", padx=(self.px(8), 0))

    def _show_saved_bat(self):
        if self._saved_bat and os.path.exists(self._saved_bat):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(self._saved_bat)])

    def show_schedule_help(self):
        px = self.px
        d, body = self._dialog("Run it on a schedule")
        self.label(body, "Run it on a schedule", font=self.f["h2"], anchor="w").pack(fill="x")
        self.label(body, "Windows can run your .bat automatically with Task Scheduler. It takes about a minute:",
                   fg=C["muted"], anchor="w").pack(fill="x", pady=(px(2), px(10)))
        steps = tk.Frame(body, bg=C["raised"])
        steps.pack(fill="x")
        for i, text in enumerate(SCHEDULE_STEPS, 1):
            tk.Label(steps, text=str(i), bg=C["raised"], fg=C["mint"], font=self.f["h3"], width=3,
                     anchor="n").grid(row=i, column=0, sticky="n", padx=(px(8), 0), pady=px(6))
            tk.Label(steps, text=text, bg=C["raised"], fg=C["text"], anchor="w", justify="left",
                     wraplength=px(520)).grid(row=i, column=1, sticky="w", padx=(px(4), px(12)), pady=px(6))
        self.label(body, "TIPS", fg=C["muted"], font=self.f["caps"], anchor="w").pack(fill="x", pady=(px(14), px(4)))
        for tip in SCHEDULE_TIPS:
            self.label(body, "•  " + tip, fg=C["soft"], anchor="w", justify="left",
                       wraplength=px(560)).pack(fill="x", pady=(0, px(4)))
        _, close = self._buttons(body, [("Close", "Accent.TButton", d.destroy)])
        d.bind("<Escape>", lambda _: d.destroy())
        self._show_dialog(d, close)

    # -- run ----------------------------------------------------------------
    def start(self, skip_scan=False):
        if self.job:
            return
        if not shutil.which("robocopy"):
            self.message("robocopy not found", "robocopy.exe wasn't found. It's part of Windows "
                         "(C:\\Windows\\System32).", C["danger"])
            return
        o = self.collect()
        errors, warnings = validate(o)
        if errors:
            self.open_section(1)
            self.message("Can't start yet", "\n\n".join(errors), C["danger"])
            return

        key = self._scan_key(o)
        sc = self.scan
        # before anything gets deleted, the numbers in the confirmation must be fresh (max 5 minutes old)
        stale = bool(sc is not None and sc.done and sc.ok and not o["dry_run"] and o["action"] in DANGER_ACTIONS
                     and time.time() - sc.t_done > 300)
        if skip_scan:                                   # "Run now (no ETA)": don't wait, don't count
            self._pending_run = False
            if self._scan_after:
                self.root.after_cancel(self._scan_after)
                self._scan_after = None
            if sc and not sc.done:
                sc.cancel()
            self.scan, self.scan_key, self._scan_skipped = None, key, True
            sc = None
        elif key != self.scan_key or sc is None or not sc.done or stale:
            if key != self.scan_key or sc is None or stale:   # not started yet, outdated or too old: scan now
                self._schedule_scan(o, key, delay=0)
            self._pending_run = True
            self.phase_lbl.configure(text="Re-checking before deleting…" if stale else "Waiting for the scan…",
                                     fg=C["text"])
            self.set_detail("The copy starts as soon as the scan is done, or press “Run now” to skip it.")
            self.run_btn.configure(text="►   Run now (no ETA)", command=lambda: self.start(skip_scan=True))
            self.stop_btn.configure(state="normal")
            return
        self._reset_run_button()

        scan_ok = sc is not None and sc.ok
        totals = None
        if scan_ok:
            totals = (sc.n, sc.bytes)
            fs = ((sc.dst_info or {}).get("fs") or "").upper()
            if fs in ("FAT32", "FAT") and sc.over4g:
                self.message("Files too big for this drive", self._scan_warnings(o, sc)[-1][0], C["danger"])
                return
            need = sc.n * 400                       # the temp progress log: ~300-400 bytes per file
            try:
                tmp_free = shutil.disk_usage(tempfile.gettempdir()).free
            except OSError:
                tmp_free = None
            if tmp_free is not None and need > tmp_free * 0.5 and not self.ask(
                    "Low space for the progress log",
                    f"vibeCopy follows the copy through a temporary log file. For {sc.n:,} files it needs about "
                    f"{fmt_bytes(need)} in {tempfile.gettempdir()}, where only {fmt_bytes(tmp_free)} is free.\n\n"
                    f"Run anyway?", "Run anyway"):
                return
        elif not skip_scan and not self.ask("The scan failed", "The scan couldn't list the files, so there "
                                            "will be no ETA. Robocopy will probably report the same problem."
                                            "\n\nRun anyway?", "Run anyway"):
            return

        src, dst = norm_path(o["src"]), norm_path(o["dst"])
        if scan_ok and sc.free is not None and sc.bytes > sc.free:
            if not self.ask("Not enough space?",
                            f"{fmt_bytes(sc.bytes)} need to be copied, but only {fmt_bytes(sc.free)} is free "
                            f"on the destination.\n\nFiles that get overwritten free some space, so it "
                            f"might still fit.", "Run anyway"):
                return
        if not o["dry_run"] and o["action"] == "mirror":
            if scan_ok:
                what = (f"The scan found {sc.extras:,} file{'s' if sc.extras != 1 else ''} in\n    {dst}\n"
                        f"that {'are' if sc.extras != 1 else 'is'} not in\n    {src}\n"
                        f"{'They' if sc.extras != 1 else 'It'} will be DELETED.")
            else:
                what = f"Every file in\n    {dst}\nthat is not in\n    {src}\nwill be DELETED."
            if not self.ask("Mirror: files will be deleted",
                            f"Mirror makes the destination an exact copy of the source.\n\n{what}\n\n"
                            f"Tip: tick “Dry run” (Speed profile → Fine-tune) first to see what would happen.",
                            "Mirror and delete", danger=True,
                            extra=("Show files", self.show_extras) if scan_ok and sc.extras else None):
                return
            risky = risky_mirror_target(dst)
            if risky and not self.ask("Are you really sure?",
                                      f"{dst} is {risky}. Mirroring into it deletes EVERYTHING there that "
                                      f"isn't in {src}, including files that have nothing to do with this "
                                      f"copy.\n\nUsually you want a subfolder, like {os.path.join(dst, 'Backup')}.",
                                      "Yes, mirror into it", danger=True):
                return
        elif not o["dry_run"] and o["action"] == "move":
            count = f"{sc.n:,} files" if scan_ok else "Files"
            if not self.ask("Move: source files will be deleted",
                            f"{count} will be copied to\n    {dst}\nand then DELETED from\n    {src}",
                            "Move files", danger=True):
                return
        elif warnings:
            if not self.ask("Heads up", "\n\n".join(warnings), "Run anyway"):
                return

        args = build_args(o)
        self._clear_log()
        self._append_log([(cmd_line(args), "cmd")])
        if totals:
            self._append_log([(f"Scan: {totals[0]:,} files ({fmt_bytes(totals[1])}) to copy. "
                               f"Profile: {self.profile}.", "ok")])
        self.meter = Meter()
        self._eta_smooth = None
        self._shown = {}
        self.job_opts = o
        self.job = RoboJob(args, totals, o["dry_run"], o["verbose"],
                           user_log=norm_path(o["log_path"]) if o["log"] else None)
        self.job.start()
        self.last_job = None
        keep_awake(True)
        if self.taskbar:
            self.taskbar.set(TaskbarProgress.NORMAL if totals else TaskbarProgress.BUSY, 0)
        self.failed_lnk.pack_forget()

        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.phase_lbl.configure(text="Starting…", fg=C["text"])
        self.pct_lbl.configure(text="")
        self.pbar.configure(value=0)
        self.set_detail("Dry run: nothing will be changed." if o["dry_run"] else
                        "Your PC won't go to sleep while the copy runs.")
        for v in self.stat.values():
            v.configure(text="—", fg=C["text"], cursor="")
        self.open_section(5)

    def _reset_run_button(self):
        self.run_btn.configure(text="►   Run", command=self.start)

    def stop(self):
        if self._pending_run:
            self._pending_run = False
            self._reset_run_button()
            self.run_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.phase_lbl.configure(text="Ready", fg=C["text"])
            self.set_detail("")
        elif self.job:
            self.job.stop()
            self.stop_btn.configure(state="disabled")
            self.phase_lbl.configure(text="Stopping…")

    def _tick(self):
        try:
            while self.dropper and self.dropper.pending:
                self.on_drop(self.dropper.pending.popleft())
            if self._drives_changed:
                self._drives_changed = False
                self._schedule_refresh()
            if self.job:
                self._update_job()
            sc = self.scan
            if sc is not None:
                if not sc.done:
                    self._render_scan()
                    self._update_summaries()
                elif not self._scan_done_seen:
                    self._scan_done_seen = True
                    self._on_scan_done()
                elif int(time.time() * 4) % 20 == 0:
                    self._render_scan()              # keeps "scanned N min ago" fresh
        finally:
            self._tick_id = self.root.after(250, self._tick)

    def _update_job(self):
        job = self.job
        lines = []
        limit = None if job.finished else 800          # at the end: take everything at once
        try:
            while limit is None or len(lines) < limit:
                lines.append(job.q.get_nowait())
        except queue.Empty:
            pass
        if len(lines) > 4000:                           # the view keeps the last 4,000 lines anyway
            lines = [(f"… {len(lines) - 4000:,} lines not shown …", "dim")] + lines[-4000:]
        if lines:
            self._append_log(lines)

        s = job.snapshot()
        now = time.time()
        self._put(self.stat["elapsed"], text=fmt_dur(now - job.t_start))
        self._put(self.stat["errors"], text=f"{s['errors']:,}", fg=C["danger"] if s["errors"] else C["text"],
                  cursor="hand2" if s["errors"] else "")
        self._update_copy(s, now)
        if s["finished"] and job.q.empty():
            self._job_done(s)

    def _put(self, widget, **options):
        """configure() only when something changed: during a copy, redrawing identical labels 4 times a
        second is wasted work (speed comes first)."""
        key = str(widget)
        if self._shown.get(key) != options:
            self._shown[key] = options
            widget.configure(**options)

    def _update_copy(self, s, now):
        dry = self.job_opts["dry_run"]
        self._put(self.phase_lbl, text="Listing (dry run)…" if dry else "Copying…")
        tb, tf = s["total_bytes"], s["total_files"]
        db, df = s["done_bytes"], s["done_files"]
        self.meter.add(now, db, df)
        brate, frate = self.meter.rate()
        elapsed = now - self.job.t_start
        avg_b = db / elapsed if elapsed > 1 else None
        speed = brate if brate else avg_b

        self._put(self.stat["speed"], text=f"{fmt_bytes(speed)}/s" if speed else "—")
        self._put(self.stat["files"], text=f"{df:,} / {tf:,}" if tf is not None else f"{df:,}")
        self._put(self.stat["data"], text=f"{fmt_bytes(db)} / {fmt_bytes(tb)}" if tb is not None else fmt_bytes(db))

        if tb is not None and tf is not None:
            if tb > 0:
                frac = min(1.0, db / tb)
            else:
                frac = min(1.0, df / tf) if tf else 1.0
            self._put(self.pbar, value=int(frac * 1000))
            pct = f"{frac:.0%}"
            if self._shown.get("pct") != pct:            # title + taskbar only when the % changes
                self._shown["pct"] = pct
                self.pct_lbl.configure(text=pct)
                self.root.title(f"{pct} · {APP_NAME}")
                if self.taskbar:
                    self.taskbar.set(TaskbarProgress.NORMAL, frac)
            eta = None
            small_files = tf and tb / tf < 256 * 1024
            if small_files and (frate or (df and elapsed > 1)):
                rate = frate or df / elapsed
                eta = (tf - df) / rate if rate > 0 else None
            elif speed and speed > 0:
                eta = max(0.0, tb - db) / speed
            if eta is not None:
                # smooth the jumps so the ETA doesn't flicker; follow drops fast (no "99% · 0:09 left")
                prev = self._eta_smooth
                if prev is None:
                    self._eta_smooth = eta
                elif eta < prev:
                    self._eta_smooth = prev * 0.4 + eta * 0.6
                else:
                    self._eta_smooth = prev * 0.8 + eta * 0.2
                self._put(self.stat["eta"], text=fmt_dur(self._eta_smooth))
            elif elapsed > 2:
                self._put(self.stat["eta"], text="…")
        else:
            self._put(self.pbar, value=0)
            self._put(self.stat["eta"], text="no scan")
            if self._shown.get("pct") != "no scan":
                self._shown["pct"] = "no scan"
                self.root.title(f"Copying… · {APP_NAME}")

        cur = s["current"]
        if cur:
            path = cur if (":" in cur or cur.startswith("\\\\")) else s["cur_dir"] + cur
            self.set_detail(f"{'Listing' if dry else 'Copying'}:  {path}", C["faint"], path=True)

    def _job_done(self, s):
        job, self.job = self.job, None
        self._shown = {}
        self.last_job = job
        keep_awake(False)
        head, detail, color = explain_rc(s["rc"], s["cancelled"], self.job_opts["dry_run"])
        if s["rc"] is not None and s["rc"] < 8 and not s["cancelled"]:
            self.pbar.configure(value=1000)
            self.pct_lbl.configure(text="100%")
        self.phase_lbl.configure(text=head, fg=color)
        code = f"  (robocopy exit code {s['rc']})" if s["rc"] is not None else ""
        if s["errors"]:
            detail += "  Press Run again to retry them."
        self.set_detail(detail + code, C["text"] if color == C["mint"] else color)
        self.stat["eta"].configure(text="—")
        elapsed = max(0.001, time.time() - job.t_start)
        self.stat["elapsed"].configure(text=fmt_dur(elapsed))
        if not s["cancelled"]:
            self.stat["speed"].configure(text=f"{fmt_bytes(s['done_bytes'] / elapsed)}/s avg")
        tag = "ok" if color == C["mint"] else "err" if color == C["danger"] else "warn"
        self._append_log([(f"{head}: {detail}{code}", tag)])
        self._last_result = f"{head}{code}"
        self._last_state = "ok" if color == C["mint"] else "danger" if color == C["danger"] else "warn"
        if s["errors"]:
            self.failed_lnk.configure(text=f"Show the {s['errors']:,} failed file{'s' if s['errors'] != 1 else ''}")
            self.failed_lnk.pack(side="right")
        self.run_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.root.title(f"{head} · {APP_NAME}")
        if self.taskbar:
            if color == C["mint"]:
                self.taskbar.set(TaskbarProgress.NONE)
            else:
                self.taskbar.set(TaskbarProgress.ERROR if color == C["danger"] else TaskbarProgress.PAUSED, 1.0)
        self.root.bell()
        flash_taskbar(self.root)

        # the files on disk changed: scan again so the numbers are current (the profile stays as it is)
        if not self.job_opts["dry_run"]:
            self.scan_key = None
        self._refresh()
        if not s["cancelled"] and self.job_opts["when_done"] in ("Sleep", "Shut down"):
            self._countdown(self.job_opts["when_done"])

    def _countdown(self, what):
        px = self.px
        d = tk.Toplevel(self.root)
        d.title(f"{what} in 60 seconds")
        d.configure(bg=C["card"])
        d.transient(self.root)
        d.resizable(False, False)
        body = tk.Frame(d, bg=C["card"])
        body.pack(fill="both", expand=True, padx=px(22), pady=px(18))
        title = self.label(body, "", font=self.f["h2"], fg=C["amber"], anchor="w")
        title.pack(fill="x")
        self.label(body, "The copy is finished. You chose this in “When done”.", fg=C["soft"],
                   anchor="w").pack(fill="x", pady=(px(6), 0))
        state = {"left": 60, "cancelled": False}

        def cancel():
            state["cancelled"] = True
            d.destroy()

        def now():
            d.destroy()
            power_action(what)

        row = tk.Frame(body, bg=C["card"])
        row.pack(fill="x", pady=(px(18), 0))
        ttk.Button(row, text=f"{what} now", command=now).pack(side="right", padx=(px(8), 0))
        ttk.Button(row, text="Cancel", style="Accent.TButton", command=cancel).pack(side="right")

        def tick():
            if state["cancelled"] or not d.winfo_exists():
                return
            if state["left"] <= 0:
                now()
                return
            title.configure(text=f"{what} in {state['left']} seconds…")
            state["left"] -= 1
            d.after(1000, tick)

        d.protocol("WM_DELETE_WINDOW", cancel)
        tick()
        d.update_idletasks()
        r = self.root
        d.geometry(f"+{r.winfo_rootx() + (r.winfo_width() - d.winfo_reqwidth()) // 2}"
                   f"+{r.winfo_rooty() + (r.winfo_height() - d.winfo_reqheight()) // 3}")
        dark_titlebar(d)
        d.lift()
        d.focus_force()

    # -- log ----------------------------------------------------------------
    def _clear_log(self):
        self.log_txt.configure(state="normal")
        self.log_txt.delete("1.0", "end")
        self.log_txt.configure(state="disabled")

    def _append_log(self, lines):
        t = self.log_txt
        at_bottom = t.yview()[1] >= 0.999
        t.configure(state="normal")
        for text, tag in lines:
            t.insert("end", text + "\n", tag)
        count = int(t.index("end-1c").split(".")[0])
        if count > 5000:
            t.delete("1.0", f"{count - 4000}.0")
        t.configure(state="disabled")
        if at_bottom:
            t.see("end")

    # -- dialogs ------------------------------------------------------------
    def _dialog(self, title):
        d = tk.Toplevel(self.root)
        d.withdraw()
        d.title(title)
        d.configure(bg=C["card"])
        d.transient(self.root)
        d.resizable(False, False)
        body = tk.Frame(d, bg=C["card"])
        body.pack(fill="both", expand=True, padx=self.px(22), pady=self.px(18))
        return d, body

    def _show_dialog(self, d, focus=None):
        d.update_idletasks()
        r = self.root
        x = r.winfo_rootx() + (r.winfo_width() - d.winfo_reqwidth()) // 2
        y = r.winfo_rooty() + (r.winfo_height() - d.winfo_reqheight()) // 3
        d.geometry(f"+{max(0, x)}+{max(0, y)}")
        dark_titlebar(d)
        d.deiconify()
        d.grab_set()
        (focus or d).focus_set()
        d.wait_window()

    def _buttons(self, body, buttons):
        row = tk.Frame(body, bg=C["card"])
        row.pack(fill="x", pady=(self.px(18), 0))
        first = None
        for text, style, cb in reversed(buttons):
            b = ttk.Button(row, text=text, style=style, command=cb)
            b.pack(side="right", padx=(self.px(8), 0))
            first = first or b
        return row, first

    def message(self, title, text, color=None):
        d, body = self._dialog(title)
        self.label(body, title, fg=color or C["text"], font=self.f["h2"], anchor="w").pack(fill="x")
        self.label(body, text, fg=C["soft"], justify="left", anchor="w",
                   wraplength=self.px(460)).pack(fill="x", pady=(self.px(8), 0))
        _, ok = self._buttons(body, [("OK", "Accent.TButton", d.destroy)])
        d.bind("<Return>", lambda _: d.destroy())
        d.bind("<Escape>", lambda _: d.destroy())
        self._show_dialog(d, ok)

    def ask(self, title, text, ok_text="OK", danger=False, extra=None):
        result = [False]
        d, body = self._dialog(title)

        def ok():
            result[0] = True
            d.destroy()

        self.label(body, title, fg=C["danger"] if danger else C["text"], font=self.f["h2"],
                   anchor="w").pack(fill="x")
        self.label(body, text, fg=C["soft"], justify="left", anchor="w",
                   wraplength=self.px(460)).pack(fill="x", pady=(self.px(8), 0))
        row, _ = self._buttons(body, [("Cancel", "TButton", d.destroy),
                                      (ok_text, "Danger.TButton" if danger else "Accent.TButton", ok)])
        if extra:
            ttk.Button(row, text=extra[0], style="Ghost.TButton", command=extra[1]).pack(side="left")
        d.bind("<Escape>", lambda _: d.destroy())
        if not danger:
            d.bind("<Return>", lambda _: ok())
        self._show_dialog(d)
        return result[0]

    def choose(self, title, text, options):
        """Small dialog with one button per (label, value); returns the value or None."""
        result = [None]
        d, body = self._dialog(title)
        self.label(body, title, font=self.f["h2"], anchor="w").pack(fill="x")
        self.label(body, text, fg=C["soft"], justify="left", anchor="w",
                   wraplength=self.px(460)).pack(fill="x", pady=(self.px(8), 0))

        def pick(v):
            result[0] = v
            d.destroy()

        buttons = [("Cancel", "TButton", d.destroy)] + [(lbl, "Accent.TButton", lambda v=v: pick(v))
                                                        for lbl, v in options]
        self._buttons(body, buttons)
        d.bind("<Escape>", lambda _: d.destroy())
        self._show_dialog(d)
        return result[0]

    def list_dialog(self, title, subtitle, rows, color=None):
        """Scrollable list of (text, detail) rows."""
        px = self.px
        d, body = self._dialog(title)
        d.resizable(True, True)
        self.label(body, title, fg=color or C["text"], font=self.f["h2"], anchor="w").pack(fill="x")
        self.label(body, subtitle, fg=C["muted"], anchor="w", justify="left",
                   wraplength=px(600)).pack(fill="x", pady=(px(4), px(8)))
        box = tk.Frame(body, bg=C["field"], highlightthickness=1, highlightbackground=C["border"])
        box.pack(fill="both", expand=True)
        t = tk.Text(box, wrap="none", bg=C["field"], fg=C["soft"], bd=0, width=90, height=18,
                    font=self.f["mono"], padx=px(10), pady=px(8), highlightthickness=0,
                    selectbackground=C["sel"])
        sb = ttk.Scrollbar(box, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        t.pack(side="left", fill="both", expand=True)
        t.tag_configure("detail", foreground=C["faint"])
        for text, detail in rows:
            t.insert("end", text + "\n")
            if detail:
                t.insert("end", "    " + detail + "\n", "detail")
        t.configure(state="disabled")
        _, ok = self._buttons(body, [("Close", "Accent.TButton", d.destroy)])
        d.bind("<Escape>", lambda _: d.destroy())
        self._show_dialog(d, ok)

    def show_extras(self):
        sc = self.scan
        if not sc or not sc.ok or not sc.extras:
            return
        more = f" (showing the first {len(sc.extras_names):,})" if sc.extras > len(sc.extras_names) else ""
        self.list_dialog("Files Mirror would delete",
                         f"{sc.extras:,} file{'s' if sc.extras != 1 else ''} in the destination "
                         f"{'are' if sc.extras != 1 else 'is'} not in the source{more}.",
                         [(n, "") for n in sc.extras_names], C["danger"])

    def show_failed(self):
        job = self.job or self.last_job
        if not job:
            return
        items = job.failed_items()
        if not items:
            return
        self.list_dialog("Files that could not be copied",
                         f"{len(items):,} file{'s' if len(items) != 1 else ''}. Common reasons: the file is open in "
                         f"another program, or your account has no access. Fix it and press Run again: "
                         f"files that already copied are skipped.", items, C["danger"])

    def show_guide(self):
        px = self.px
        d, body = self._dialog("Which profile should I pick?")
        self.label(body, "Which profile should I pick?", font=self.f["h2"], anchor="w").pack(fill="x")
        self.label(body, "Usually you don't have to: the scan picks one for you. Here's how it decides.",
                   fg=C["muted"], anchor="w").pack(fill="x", pady=(px(2), px(10)))
        rules = tk.Frame(body, bg=C["raised"])
        rules.pack(fill="x")
        for i, (head, text) in enumerate(GUIDE_RULES):
            tk.Label(rules, text=head.upper(), bg=C["raised"], fg=C["accent"], font=self.f["caps"],
                     anchor="nw", width=11).grid(row=i, column=0, sticky="nw", padx=(px(12), 0), pady=px(6))
            tk.Label(rules, text=text, bg=C["raised"], fg=C["text"], font=self.f["base"], anchor="w",
                     justify="left", wraplength=px(520)).grid(row=i, column=1, sticky="w",
                                                              padx=(px(4), px(12)), pady=px(6))

        self.label(body, "ALL PROFILES", fg=C["muted"], font=self.f["caps"], anchor="w").pack(
            fill="x", pady=(px(14), px(4)))
        lst = tk.Frame(body, bg=C["card"])
        lst.pack(fill="x")
        for i, p in enumerate(PROFILES):
            name = tk.Label(lst, text=p["name"], bg=C["card"], fg=C["text"], font=self.f["bold"],
                            anchor="w", cursor="hand2")
            name.grid(row=i, column=0, sticky="nw", pady=px(3))
            tk.Label(lst, text=p["use"], bg=C["card"], fg=C["soft"], font=self.f["small"], anchor="w",
                     justify="left", wraplength=px(420)).grid(row=i, column=1, sticky="w",
                                                              padx=(px(14), 0), pady=px(3))

            def pick(_=None, n=p["name"]):
                d.destroy()
                self.apply_profile(n, manual=True)

            name.bind("<Button-1>", pick)
            name.bind("<Enter>", lambda e: e.widget.configure(fg=C["accent"]))
            name.bind("<Leave>", lambda e: e.widget.configure(fg=C["text"]))
        foot = tk.Frame(body, bg=C["card"])
        foot.pack(fill="x", pady=(px(8), 0))
        self.label(foot, "Tip: click a profile name to select it.", fg=C["faint"],
                   font=self.f["small"]).pack(side="left")
        self.link(foot, "Full instructions ↗", self.open_help).pack(side="right")
        _, close = self._buttons(body, [("Close", "Accent.TButton", d.destroy)])
        d.bind("<Escape>", lambda _: d.destroy())
        self._show_dialog(d, close)

    def _on_error(self, exc, val, tb):
        """Tk callback errors would vanish under pythonw (no console): show them once, with copyable details."""
        import traceback
        details = "".join(traceback.format_exception(exc, val, tb))
        key = details.strip().splitlines()[-1] if details.strip() else repr(val)
        if key in self._errors_shown:                   # the same error repeating (e.g. every tick): once is enough
            return
        self._errors_shown.add(key)
        try:
            d, body = self._dialog("Something went wrong")
            self.label(body, "Something went wrong", fg=C["danger"], font=self.f["h2"], anchor="w").pack(fill="x")
            self.label(body, "vibeCopy hit an unexpected error. A copy that is already running keeps going: "
                             "robocopy runs on its own. Please report the details below.", fg=C["soft"],
                       anchor="w", justify="left", wraplength=self.px(520)).pack(fill="x", pady=(self.px(6), self.px(8)))
            t = tk.Text(body, height=10, width=80, bg=C["field"], fg=C["soft"], bd=0, font=self.f["mono"],
                        highlightthickness=1, highlightbackground=C["border"], padx=self.px(8), pady=self.px(6))
            t.insert("1.0", details)
            t.configure(state="disabled")
            t.pack(fill="both", expand=True)

            def copy():
                self.root.clipboard_clear()
                self.root.clipboard_append(details)

            row, _ = self._buttons(body, [("Close", "Accent.TButton", d.destroy)])
            ttk.Button(row, text="Copy details", style="Ghost.TButton", command=copy).pack(side="left")
            d.bind("<Escape>", lambda _: d.destroy())
            self._show_dialog(d)
        except Exception:
            pass

    # -- lifecycle ----------------------------------------------------------
    def _on_close(self):
        if self.job:
            if not self.ask("Copy in progress", "A copy is still running. Stop it and quit?",
                            "Stop and quit", danger=True):
                return
            self.job.stop()
        if self.scan and not self.scan.done:
            self.scan.cancel()
        keep_awake(False)
        if self.taskbar:
            self.taskbar.set(TaskbarProgress.NONE)
        for after_id in (self._tick_id, self._refresh_id, self._scan_after):
            if after_id:
                try:
                    self.root.after_cancel(after_id)
                except tk.TclError:
                    pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    try:
        app = App()
    except Exception:                                   # pythonw has no console: say why it didn't start
        import traceback
        details = traceback.format_exc()
        try:
            from tkinter import messagebox
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("vibeCopy", "vibeCopy couldn't start:\n\n" + details[-1800:])
            r.destroy()
        except Exception:
            pass
        raise
    app.run()


if __name__ == "__main__":
    main()
