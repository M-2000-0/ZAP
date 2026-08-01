# ZPX OS - Operating System Built 100% with ZPX

> An operating system built entirely with the ZPX programming language.
> AI-Native · Lightweight · Fast · Full-Stack · Plug & Play

## Quick Start (Plug & Play)

### One Command to Boot

```bash
# From the ZPX project root:
python -m src run zpx-os/boot.zpx
```

Or use the standalone launcher:

```bash
# Unix/Mac
cd zpx-os && python boot.py

# Windows
cd zpx-os && run.bat
```

### Prerequisites

Only requires ZPX (which you already have):

```bash
pip install zpx-lang
```

## Overview

ZPX OS is a fully self-contained operating system built entirely using
the ZPX programming language. It provides a complete OS experience
with a shell, UI framework, applications, package management, and more.

## Features

- **100% ZPX** - Every line of code written in ZPX
- **AI-Native** - Designed for AI code generation with 30-60% fewer tokens  
- **Lightweight** - Minimal footprint, fast boot time
- **Good UX/UI** - Built-in UI framework with windows, theming, widgets
- **Cross-Language Compatible** - ZPX bridges Python, JS, and SQL
- **Self-Hosting** - The interpreter is written in ZPX itself
- **Package Manager** - Install and manage OS applications
- **Shell** - Full interactive command shell with history
- **File Manager** - Browse and manage files
- **Text Editor** - Built-in text editing
- **Terminal Emulator** - Embedded terminal for command execution
- **Plug & Play** - One command to boot, no configuration needed

## Quick Start

### One Command to Boot

```bash
# From the ZPX project root:
python -m src run zpx-os/boot.zpx
```

Or use the standalone launcher:

```bash
# Unix/Mac
cd zpx-os && python boot.py

# Windows
cd zpx-os && run.bat
```

## Project Structure

```
zpx-os/
├── boot.zpx         OS boot script (entry point)
├── kernel.zpx       Core OS kernel
├── shell.zpx        Interactive shell
├── ui/
│   └── window.zpx   Window management framework
├── apps/
│   ├── filemanager.zpx  File manager
│   ├── settings.zpx     System settings
│   ├── texteditor.zpx   Text editor
│   └── terminal.zpx     Terminal emulator
├── pkg/
│   └── manager.zpx  Package manager
├── std/
│   └── os.zpx       OS standard library
├── drivers/
│   └── basic.zpx    Basic device drivers
├── zpx.json         OS configuration
└── README.md
```

## Quick Start

### Running ZPX OS

```bash
# From the ZPX project directory
cd zpx
python -m src run zpx-os/boot.zpx
```

### Available Shell Commands

| Command | Description |
|---------|-------------|
| `help` | Show all available commands |
| `ls` | List files and directories |
| `cat <file>` | Show file contents |
| `echo <msg>` | Print a message |
| `pwd` | Print working directory |
| `uname` | System information |
| `meminfo` | Memory usage |
| `date` | Current date/time |
| `ps` | List processes |
| `editor` | Open text editor |
| `terminal` | Open terminal emulator |
| `filemgr` | Open file manager |
| `settings` | System settings |
| `pkg list` | List installed packages |
| `pkg install <name>` | Install a package |
| `shutdown` | Shut down ZPX OS |

## Architecture

```
ZPX OS Boot Sequence:
  1. Load kernel module
  2. Register system services
  3. Load device drivers
  4. Initialize shell
  5. User interaction loop
```

## ZPX Language

ZPX uses clean minimal syntax designed for AI code generation:

```zpx
fn greet(name):
  ret "Hello, " + name + "!"

let os_name = "ZPX OS"

if x > 0:
  print("positive")
el:
  print("not positive")

let items = [1, 2, 3]
let user = {"name": "Alice", "age": 30}
```

## System Requirements

- Python 3.10+
- zpx-lang 0.2.0+

## License

MIT - free for commercial use.