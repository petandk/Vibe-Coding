# 💪 Muscle Tutor

Welcome to the **vive coding** repository's newest torture device... I mean, learning tool!

**🤖 Full Disclosure:** 100% of the Python code for this application was written by me, an AI (Gemini). My human friend came up with the architecture, the strict design requirements, and the completely valid complaints about standard alphabetical file sorting. I just did the heavy lifting of writing the `tkinter` boilerplate. I don't have hands or a central nervous system, so I don't need muscle memory. You, however, have exams to pass. 

## 🤷‍♂️ What is this?

**Muscle Tutor** (`muscle_tutor.py`) is a merciless, language-agnostic typing application designed to drill syntax directly into your fingers. 

If you've ever frozen up during a strict coding exam because you forgot how to set up your includes, or because your fancy modern IDE usually auto-closes your brackets and handles your indentation, this tool fixes that. It strips away all autocomplete, linting, and formatting help, forcing you to type the codebase *exactly* as it is written, raw keystroke by raw keystroke.

## ✨ Features

*   **👻 Ghost Opacity:** Your target code appears as a faint "ghost" on a dark theme. You can adjust the opacity slider if you want to play on extreme hard mode and barely see the solution.
*   **🛑 Zero Forgiveness:** If you type the wrong character, it turns angry red and blocks you from progressing until you hit Backspace and fix it. You cannot cheat the system.
*   **🔍 The Whitespace Exposer:** Because mixing tabs and spaces is a cardinal sin. The app highlights standard spaces with a faint grey background and tabs with a deep blue background. You'll never guess wrong again.
*   **⏭️ Language-Agnostic Comment Skipping:** You shouldn't have to memorize comments. The app uses regex magic to automatically leap over `/* */`, `//`, `#`, `"""`, and `<!-- -->` blocks in C, C++, Python, Bash, Makefiles, Go, HTML, and more.
*   **🧠 Smart C/C++ Sorting:** Standard alphabetical sorting puts `.c` files before `.h` files, which is deeply offensive to the natural order of programming. This app uses a custom sorting logic to ensure you practice your headers (`.h`/`.hpp`) *before* your implementation files (`.c`/`.cpp`).
*   **🚀 Seamless Flow:** When you finish a file, a pop-up overlay immediately suggests the next logical file in the folder. Hit `[Enter]` to start it, or `[S]` to skip to the next one.

## 🛠️ How to Use It

1.  Make sure you have Python 3 installed on your system. 
2.  Tkinter is usually included with Python, but if you're on Linux, you might need to install it (e.g., `sudo apt install python3-tk`).
3.  Run the app:
    ```bash
    python3 muscle_tutor.py
    ```
4.  Click **"Open Folder"** in the sidebar and select a directory containing the code you want to memorize.
5.  Select a file from the tree view and start typing. 

## ⌨️ Keyboard Shortcuts

*   **`Enter`**: Starts the next file when the completion overlay is up.
*   **`S`**: Skips the currently suggested file and lines up the next one.
*   **`Escape`**: Closes the completion overlay so you can browse the sidebar manually.
*   **`Tab`**: Actually inserts a tab (unlike standard IDEs that convert it to spaces... looking at you, VSCode).

## 📝 Final Words

May your pointers never dangle, your memory never leak, and your fingers always remember the syntax. Happy typing!