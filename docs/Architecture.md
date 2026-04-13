# Design Document — eSim Tool Manager

> Architecture, module breakdown, and component interaction for the eSim Automated Tool Manager.
> eSim Summer Fellowship 2026 — Task 5

---

## 1. Introduction

eSim is an open-source EDA platform developed by FOSSEE at IIT Bombay. It integrates KiCad for schematic capture and PCB layout, Ngspice for SPICE simulation, GHDL and Verilator for HDL-based mixed-signal work via NgVeri, and OpenModelica for system-level modelling.

Anyone who has set up eSim from scratch knows how fragmented the process is. The wrong Ngspice version silently breaks simulation. A KiCad mismatch breaks the schematic-to-netlist pipeline. A missing `libffi-dev` causes a cryptic build failure. This tool manager exists to solve that automating the entire lifecycle of eSim's external tools.

---

## 2. Design Goals

Before writing code, five principles were agreed upon:

- **Separation of concerns** — backend logic must be completely independent of the UI layer
- **Minimal dependencies** — only `rich` and `customtkinter` as third-party packages; everything else uses the Python standard library
- **eSim-specific intelligence** — the tool knows which versions of each tool are required by each eSim release, not just whether they're installed
- **Graceful failure** — if an install fails, a binary is missing, or a version cannot be parsed, the tool logs it and continues
- **Portable by design** — the same codebase auto-detects apt, brew, winget, dnf, and pacman without user configuration

---

## 3. Overall Architecture

The project is six Python files. Each has one clear responsibility.

```
main.py  →  cli.py  or  gui.py
              both depend on  →  core.py  +  theme.py
health_report.py  →  core.py  +  theme.py
```

The user always enters through `main.py`. Depending on CLI flags, execution goes to either `cli.py` (rich terminal) or `gui.py` (customtkinter desktop app). Both are pure presentation layers — they call functions from `core.py` and display results. `health_report.py` similarly calls `core.py` and builds an HTML document. `theme.py` is a passive constants file.

### Module Breakdown

| File | Responsibility | Key exports |
|---|---|---|
| `theme.py` | Catppuccin Mocha palette constants | `Mocha` class with all hex values |
| `core.py` | All backend logic zero UI code | `scan_tools`, `check_dependencies`, `install_tool`, `check_esim_compatibility`, `get_install_command` |
| `gui.py` | customtkinter desktop GUI 6 panels | `App` class, `launch()` |
| `cli.py` | rich terminal interface interactive menu | `run_interactive`, `run_scan`, `run_dep_check`, `run_compat_check` |
| `health_report.py` | HTML health report generator | `generate_report()` |
| `main.py` | Entry point CLI flag dispatcher | `--gui`, `--scan`, `--check`, `--compat`, `--report`, `--install`, `--dry-run` |

---

## 4. Core Module — core.py

Every meaningful operation happens here. The UI files are thin wrappers that call these functions and display results.

### 4.1 OS and Package Manager Detection

`detect_os()` reads `/etc/os-release` on Linux, checks for `apt`, `dnf`, `pacman` in order; on macOS checks for `brew`; on Windows for `winget` then `choco`. The result is a dictionary every other function uses to select the right install command.

### 4.2 Tool Definitions

Each of the five managed tools is described in the `TOOLS` dictionary with binary name, version flag, latest known version, package names per package manager, and an eSim-specific role description. Adding a new tool is a single dictionary entry.

### 4.3 Tool Scanner

`scan_tools()` calls `shutil.which()` for each binary, runs it with its version flag, and parses the version string. It compares installed vs latest using tuple comparison. Result is one of: `ok`, `update`, `missing`, or `unknown`. Every result is logged.

### 4.4 Dependency Checker

`check_dependencies()` checks system-level packages (gcc, cmake, libffi-dev, git, etc.) that eSim's tools need. For standard binaries it uses `shutil.which()`; for library packages without a direct binary it calls `dpkg -l`. Each missing dependency includes the exact fix command.

### 4.5 eSim Compatibility Matrix

The `ESIM_COMPATIBILITY` dictionary encodes the supported version range for each tool across all three current eSim releases. `check_esim_compatibility()` evaluates each tool against the matrix and distinguishes `too_old`, `too_new`, and `missing`. Critical tools push the overall verdict to `incompatible`; non-critical tools push it to `warning`.

### 4.6 Installer

`install_tool()` builds the appropriate install command and runs it as a subprocess. The `sudo -n` (non-interactive) approach is used — works when the calling terminal has a cached sudo session, fails immediately with a clear message otherwise. A `callback` parameter means the same function streams output to both CLI and GUI.

### 4.7 Configuration

`load_config()` and `save_config()` read/write JSON at `~/.esim_tool_manager/config.json`. Created from defaults on first run.

---

## 5. Graphical Interface — gui.py

Built with `customtkinter`, fully themed with Catppuccin Mocha from `theme.py`.

### Panels

- **Dashboard** — stat cards (total, up to date, updates, missing), system info table, recent log tail
- **Tools** — scrollable list with version, status badge, path, and Install/Update/Info button
- **Dependencies** — colour-coded present/absent table with fix commands
- **Compat** — radio buttons for eSim version, full compatibility table, Health Report button
- **Config** — form fields and toggles, Save button writes to disk
- **Log** — full scrollable log file view

### Threading

All slow operations run in daemon threads. Results are pushed back to the main thread via `after()` — the standard safe tkinter pattern.

### Install Progress Dialog

Clicking Install opens a modal with an indeterminate progress bar, live status label, and scrolling output textbox. On completion the bar turns green or red and a Close button appears.

---

## 6. Terminal Interface — cli.py

Uses `rich` for tables, panels, coloured text, and spinners. Same Catppuccin Mocha colours applied via `rich.Style` objects from `theme.py`. Interactive numbered menu; all functions are also importable for the non-interactive CLI flags in `main.py`.

---

## 7. Health Report — health_report.py

`generate_report()` collects data from `core.py`, builds a self-contained HTML document using Python f-strings, writes to `~/.esim_tool_manager/health_report.html`, and opens the browser. No external stylesheets or JavaScript — fully portable as a single file.

---

## 8. eSim Tool Roles

| Tool | eSim Component | Role |
|---|---|---|
| KiCad | Schematic + PCB | Primary front-end — Eeschema + Pcbnew |
| Ngspice | Circuit Simulation | Core SPICE engine — receives netlists from KiCad |
| GHDL | HDL Simulation (NgVeri) | Compiles VHDL for co-simulation via XSPICE |
| Verilator | HDL Simulation (NgVeri) | Compiles Verilog/SystemVerilog for NgVeri |
| OpenModelica | System Modeling | Multi-domain modeling complement to Ngspice |

KiCad and Ngspice are critical in every eSim version. GHDL and Verilator are required for NgVeri mixed-signal work. OpenModelica is optional for system-level extensions.

---

## 9. Requirements Coverage

| Requirement | Implementation |
|---|---|
| Req 1 — Tool Installation | `install_tool()` in `core.py` using apt/brew/winget/dnf/pacman |
| Req 2 — Update System | Version comparison in `scan_tools()` flags outdated tools |
| Req 3 — Configuration | `load_config()`/`save_config()` with JSON at `~/.esim_tool_manager/config.json` |
| Req 4 — Dependency Checker | `check_dependencies()` with `shutil.which` and `dpkg -l` |
| Req 5 — User Interface | customtkinter GUI + rich terminal UI + persistent log |
| Req 6 — Cross-platform | `detect_os()` auto-selects apt/brew/winget/dnf/pacman |

---

## 10. Component Interaction [Typical Session]

1. User runs `python3 main.py --gui` → `main.py` calls `gui.launch()`
2. App window appears, `_startup_scan()` starts two daemon threads
3. Threads call `detect_os()`, `scan_tools()`, `check_dependencies()` from `core.py`
4. Results pushed to main thread via `after()` — Dashboard and Tools panels update
5. User selects eSim 2.5 in Compat panel, clicks Check → `check_esim_compatibility()` runs
6. User clicks Health Report → `generate_report()` builds HTML, opens browser
7. User clicks Install on a missing tool → progress dialog opens, `install_tool()` streams output line by line
8. Every action throughout is written to `manager.log` by `log()` in `core.py`

---

## 11. Key Design Decisions

**customtkinter over PyQt** — single pip install, wraps built-in tkinter, no C extensions, minimum friction on a fresh Debian system.

**rich for terminal UI** — no native code dependencies, identical rendering on Linux/macOS/Windows, colour applied via Style objects tied to `theme.py`.

**Catppuccin Mocha** — accessibility-considered contrast ratios, single source of truth in `theme.py` ensures GUI and CLI share identical colours.

**Offline compatibility matrix** — querying a live API would require internet access, add latency, and create failure points. eSim version ranges are stable and documented; embedding them means the tool works fully offline.

**Separate health_report.py** — the HTML report is a standalone deliverable. Keeping it separate means it can be called from CLI, GUI, or directly, without polluting either UI module.

---

## 12. Possible Extensions

- Live version lookups from GitHub releases to keep the matrix current
- Update All button with sequential install and combined progress view
- Python package dependency tracking (PySpice, etc.)
- Polkit integration for GUI password prompts without cached sudo
- Scan history to compare system state over time

