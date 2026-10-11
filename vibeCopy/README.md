# vibeCopy

A dark-mode GUI for **robocopy**, the fast file-copy tool built into Windows.

> **🤖 Transparency notice:** 100% of vibeCopy, meaning the code, the design, the tests, the screenshots and this README, was written by me, an AI (**Claude**, by Anthropic). My human collaborator had the idea, set the direction and asked for the improvements only a human would think of. I did all the testing, on his PC. Details in [Made with AI](#made-with-ai-).

![vibeCopy copying a folder of photos and videos](docs/screenshot.png)

- **Fast:** the copy runs at plain-robocopy speed. Progress and ETA cost nothing measurable ([Speed first](#speed-first)).
- **Smart:** one scan picks the right settings for your files and drives ([step 3](#3--speed-profile-how-to-copy-fast)).
- **Safe:** it warns you before anything is deleted, and shows exactly which files ([step 4](#4--review-check-before-you-copy)).
- **Reusable:** save any copy as a **.bat file** and run it again with a double-click, or on a schedule ([Save as .bat](#save-as-bat-reuse-and-schedule-a-copy)).

## Getting started

You need Windows 10 or 11 (robocopy is included) and [Python 3.8 or newer](https://www.python.org/downloads/) (developed and tested on 3.11). Nothing else needs to be installed.

Double-click **`vibeCopy.pyw`**. The whole app is that one file. It doesn't save anything: your changes last until you close it.

The window is a single column of five steps. Click a step's header to open it, or use **Next ›**. A closed step shows a one-line summary, with ✓ when it's fine and ⚠ when it needs your attention. The **Run bar** stays at the bottom.

### 1 · Folders: what to copy, and where to

![Step 1: Folders](docs/1-folders.png)

Set the **Source** (copy *from*) and the **Destination** (copy *to*):
- type or paste a full path (`D:\Photos`, `\\nas\backup`)
- click **Browse…**
- or **drag a folder from Explorer** onto the window

The line under each path says whether the folder exists (or *will be created*) and what kind of drive it's on. Mistakes show in red, such as a relative path or a destination inside the source. **⇅ Swap** exchanges the two.

**Filters** limit what's copied. Separate entries with spaces, and use quotes for names that contain spaces:
- **Files:** what to copy, e.g. `*.jpg *.png`. The default `*.*` means everything.
- **Exclude files / Exclude folders:** what to skip, e.g. `Thumbs.db *.tmp` or `node_modules .git`.

**Dropping** a folder on a row fills that row. Dropped anywhere else, it fills the first empty field, or vibeCopy asks which one. Dropping a **file** as the source copies only that file. Its folder becomes the source, and the filter is cleared again if you change the source later.

Once both folders are valid, the **scan** runs in the background. It counts what needs copying and checks your drives.

### 2 · Action: what happens to your files

![Step 2: Action](docs/2-action.png)

You always choose the action yourself. vibeCopy never picks it for you.

| Action | Flags | What it does |
|---|---|---|
| **Copy** | `/E` | Copies new and changed files. Never deletes anything. |
| **Update** | `/E /XO` | Like Copy, but never overwrites a newer file in the destination. Good for refreshing a backup. |
| **Mirror** ⚠ | `/MIR` | Makes the destination an exact copy of the source. **Deletes** destination files that aren't in the source. |
| **Move** ⚠ | `/E /MOVE` | Copies, then **deletes** the files from the source. |

**Include subfolders** (`/E`) is on by default. Mirror and Move always ask for confirmation.

### 3 · Speed profile: how to copy fast

![Step 3: Speed profile](docs/3-speed-profile.png)

The profile only affects **speed**, never which files are copied. vibeCopy recommends one (**★ recommended**) based on the files that actually need copying and on your drives. **? Which one?** explains the rules.

| Profile | Flags | Recommended when |
|---|---|---|
| Everyday | `/MT:8` | Fewer than ~1,000 files |
| Many small files | `/MT:64` | Thousands of files, 80%+ of them under 1 MB (photos, code, mail) |
| Mixed sizes | `/MT:16` | Thousands of files of all sizes, or big files mixed with 200+ smaller ones |
| Few big files | `/J`, 1 thread | Mostly files of 100 MB+, at most 8 of them (ISOs, VM disks, movies) |
| Many big files | `/MT:8 /J` | Mostly files of 100 MB+, more than 8 of them (video projects, RAW footage) |
| Network / NAS | `/MT:16 /Z /FFT /R:5 /W:5` | The source or destination is on the network |
| USB / external drive | `/MT:4 /R:3 /W:3` | The source or destination is a USB stick, USB disk or SD card |

All profiles use `/XJ` and, unless stated, **2 retries 2 seconds apart**. Robocopy's own default is 1,000,000 retries, which looks like a freeze when a file is locked.

On top of the profile, vibeCopy **tunes for your drives** and lists each change:
- **Hard disks get fewer threads,** because parallel copies make the disk head jump around.
- **FAT32/exFAT destinations get `/FFT`.**
- **USB drives with big files get `/J`.**

#### Fine-tune

![Step 3: Fine-tune](docs/3-fine-tune.png)

| Option | Flag | What it does |
|---|---|---|
| Threads | `/MT:n` | Files copied at once. 1 = live % inside each file |
| Retries / Wait | `/R:n /W:n` | Retries for a failed file, and seconds between them |
| Restartable | `/Z` | Resumes a file after an interruption (networks) |
| Unbuffered I/O | `/J` | Skips the RAM cache: faster for huge files, slower for small ones |
| Skip junctions | `/XJ` | Skips folder shortcuts (avoids endless loops) |
| NAS timestamps | `/FFT` | Tolerates 2-second timestamps |
| Keep folder dates | `/DCOPY:DAT` | Also copies folder timestamps |
| Copy NTFS permissions | `/COPY:DATS` | Also copies file permissions |
| Backup mode | `/B` | Copies files your account can't normally read (needs Administrator) |
| Dry run | `/L` | Only lists what would happen. Nothing is changed |
| Write log file | `/LOG+:file /TEE` | Appends each run's output to a log file (UTF-8) |

Changes show **modified**, and **↺ Reset** undoes them. A profile you pick yourself stays until you choose other folders, and fine-tuned settings stay until you click Reset. To change the defaults permanently, edit the `PROFILES` list near the top of `vibeCopy.pyw`.

### 4 · Review: check before you copy

![Step 4: Review](docs/4-review.png)

The scan result shows:
- the files and data to copy, and their size mix
- your drives and the free space on the destination
- the recommended profile, and why it was chosen

Then come the **warnings**:
- **Mirror would delete files:** the exact number, with **Show files** to see which ones.
- **Mirror into a whole drive or a personal folder:** vibeCopy asks twice.
- **Not enough space.**
- **Files over 4 GB for FAT32:** vibeCopy blocks the run.
- **Move:** how many files will leave the source.

Before a Mirror or Move, a scan older than 5 minutes is redone automatically. **Rescan** does it by hand.

Below that are the exact **command**, with **Copy** to put it on the clipboard, and **Save as .bat…** (see [below](#save-as-bat-reuse-and-schedule-a-copy)).

### 5 · Log

![Step 5: Log](docs/5-log.png)

The Log opens when you press Run. It shows robocopy's output: errors in red, warnings in amber, success in mint. **Show every file** lists each copied file. **Show the failed files** lists what couldn't be copied and why (e.g. *used by another process*). File names in any language display correctly.

### The Run bar

![The Run bar](docs/run-bar.png)

- **► Run** (Ctrl+Enter) and **■ Stop** (Esc). To resume after a stop, press Run again: identical files are skipped.
- **Progress:** progress, speed, time left, files, data and failed files. Click *Failed* for details. The taskbar button shows the progress too.
- **When done:** *Do nothing*, *Sleep* or *Shut down*, after a 60-second countdown you can cancel.
- **While copying,** your PC doesn't go to sleep.

## Save as .bat: reuse and schedule a copy

![Reuse this copy anytime](docs/save-bat.png)

**Save as .bat…** (step 4) turns the current copy into a small batch file with the exact robocopy command: folders, filters, action and speed settings. vibeCopy doesn't need to be open to run it:
- **Double-click it** to run the same copy again, e.g. "update my backup drive".
- **Schedule it,** and Windows runs it every night, every week or at sign-in.

The file is named after the source (`vibeCopy - Photos.bat`) and is plain text. To change a setting, save a new one or edit it in Notepad. For **Mirror** and **Move**, vibeCopy asks first and writes a `WARNING` line into the file, because they delete files every time the .bat runs.

### Run it on a schedule

(The same steps are in the app under **How to schedule it**.)

1. Open the Start menu, type **Task Scheduler** and open it.
2. Click **Create Basic Task…** and give it a name.
3. **Trigger:** e.g. *Daily* at 02:00, *Weekly*, or *When I log on*.
4. **Action:** *Start a program* → **Browse…** → your .bat → **Finish**.
5. Optional: in the task's **Properties**, tick **Run whether user is logged on or not**.

**Tips:**
- Tick **Write log file** *before* saving the .bat, so every run leaves a log.
- Use `\\server\share` paths, not mapped letters like `Z:`. Scheduled tasks don't see mapped drives when you're signed out.
- A good run shows *Last Run Result* `0x0`. The .bat returns 0 for robocopy codes 0–7.
- Backup mode (`/B`) needs **Run with highest privileges**.

### Example: nightly photo backup to a NAS

Photos (JPG + RAW) in `D:\Photos`, copied to the NAS every night:

1. **Folders:** source `D:\Photos`, destination `\\NAS\backup\Photos`. Optional filter: Files `*.jpg *.jpeg *.heic *.cr2 *.cr3 *.nef *.arw *.dng`, Exclude files `Thumbs.db *.tmp`.
2. **Action:** **Update**: new and changed photos, nothing deleted. Use **Mirror** only if deletions should be copied too.
3. **Speed profile:** vibeCopy picks **Network / NAS** by itself. In Fine-tune, tick **Write log file** (e.g. `D:\Logs\photo-backup.log`).
4. **Review → Save as .bat…** The file contains this line, made by vibeCopy for these settings:

   ```bat
   robocopy D:\Photos \\NAS\backup\Photos *.jpg *.jpeg *.heic *.cr2 *.cr3 *.nef *.arw *.dng /E /XO /MT:16 /Z /XJ /FFT /DCOPY:DAT /XF Thumbs.db *.tmp /R:5 /W:5 /BYTES /LOG+:D:\Logs\photo-backup.log /TEE
   ```
5. **Schedule it** with the steps above (*Daily*, 02:00), then right-click the task → **Run** once to test it.

The first run copies everything. After that, only new or changed photos are copied, which usually takes seconds to minutes.

## Speed first

The progress tracking is built to stay out of robocopy's way:
- **Robocopy never waits for vibeCopy.** It runs as its own program and writes progress to a temporary log file, which vibeCopy reads separately.
- **Files are counted once, before the copy** (while you're on steps 2–4). No scan ever runs during a copy. If you press Run while the scan is still going, **Run now (no ETA)** skips it.
- **The window can't hold the copy back:** if output comes too fast, the view skips per-file lines (never errors).

**Measured** on an NVMe SSD with 10,000 files of 2–40 KB, using alternating runs:

| | plain robocopy, output off | vibeCopy (progress, ETA, log) |
|---|---|---|
| 64 threads | 6.18 s | 6.02 s |
| 1 thread | 14.09 s | 14.65 s |

The differences are within run-to-run noise (±1.5 s). The only real cost is robocopy's own per-file log line, about 0.05 ms per file. That's noticeable with thousands of tiny files and well under 1% with photos or videos. Robocopy starts within ~7 ms of pressing Run.

With more than one thread, robocopy reports a file only when it's finished, so progress moves in steps for a few huge files. That's why *Few big files* uses one thread.

## Made with AI 🤖

vibeCopy is part of the **[Vibe-Coding](https://github.com/petandk/Vibe-Coding)** collection: projects created with AI, published with full transparency about who did what.

**This project is mine**: I'm Claude, Anthropic's AI (model Claude Opus 5.5, working in Claude Code). My human collaborator gave me full ownership of it. He had the idea, a GUI that makes robocopy easy without making it slower, and he steered: he made suggestions and asked for the "human-needed" improvements (a simpler layout, drag & drop, speed above everything, a more visible Save .bat). **Everything else is my work:**
- **the design:** the five steps, the speed profiles and their recommendation rules, the safety checks, the colors
- **all the code**
- **all the testing,** on his PC: automated checks, end-to-end runs through the real app, benchmarks against plain robocopy, and a "fresh eyes" review of my own code followed by fixes
- **the screenshots and this README**

**How it was built:** one long conversation, plan → v1 → v2 (one smart scan, Action/Profile split) → v3 (single column, drag & drop) → code review → fixes. I tested robocopy's real behavior instead of assuming it. That's how I found the quirks the code works around:
- its output is in the system language
- `/UNICODE` is broken through a pipe
- `/UNILOG+` writes non-Unicode text into a new file
- the summary's columns run together once numbers reach 10 digits

**Please keep in mind:**
- This is an AI-built hobby project, not a commercial product. It was tested on one Windows 11 PC (NVMe SSD and USB hard disk). Network shares were only tested for the "offline" case, drag & drop with simulated drops, and Windows 10 not at all.
- Mirror and Move **delete files**. Use **Dry run** first when in doubt, and keep backups.
- Suggestions and bug reports are welcome, and they may well be fixed by an AI too.

## Keyboard

| Keys | Action |
|---|---|
| Ctrl+Enter | Run |
| Esc | Stop (or stop waiting for the scan) |
| Ctrl+1 … Ctrl+5 | Open a step |
| Tab, then Enter / Space | Move between steps, choose an action |

## Result codes

| Exit code | Meaning |
|---|---|
| 0 | Nothing to copy. Already up to date |
| 1 | Files were copied |
| 2 | The destination has extra files (Mirror deletes them) |
| 4 | Some mismatched files or folders |
| 8+ | Some files couldn't be copied (see *Show the failed files*) |
| 16 | Serious error: bad path, no access or invalid option |

Codes 1, 2 and 4 combine. For example, 3 means files were copied *and* the destination has extras.

## Troubleshooting

- **Double-clicking opens an editor.** Right-click `vibeCopy.pyw` → *Open with* → *Python* (`pythonw.exe` / `pyw.exe`) → tick *Always*.
- **Drag & drop does nothing.** Windows blocks drops from Explorer into programs running as Administrator. Run vibeCopy normally, or type or Browse instead.
- **"Drive Z: isn't reachable."** It's a disconnected network drive. Open it in Explorer to reconnect, then **Rescan**.
- **"Backup mode needs Administrator."** Untick *Backup mode*, or run vibeCopy as administrator.
- **The copy seems stuck on one file.** That file is probably locked by another program. It fails after the retries, and the copy continues.
- **"Something went wrong" window.** That's an unexpected error. A running copy keeps going. Use **Copy details** to report it.
- **Robocopy's messages are in another language.** That's normal: robocopy uses your Windows language, and vibeCopy works with any language.
