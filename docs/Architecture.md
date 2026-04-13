# eSim Tool Manager: Architecture Document

## Table of Contents

1. [Introduction](#introduction)
2. [Design Goals](#design-goals)
3. [Overall Architecture](#overall-architecture)
4. [Architecture Diagram Walkthrough](#architecture-diagram-walkthrough)
5. [Module Breakdown](#module-breakdown)
6. [Core Module — core.py](#core-module--corepy)
7. [Graphical Interface — gui.py](#graphical-interface--guipy)
8. [Terminal Interface — cli.py](#terminal-interface--clipy)
9. [Health Report — health_report.py](#health-report--health_reportpy)
10. [eSim Tool Roles](#esim-tool-roles)
11. [Requirements Coverage](#requirements-coverage)
12. [Component Interaction — Typical Session](#component-interaction--typical-session)
---

## Introduction

eSim is an open-source EDA platform developed by FOSSEE at IIT Bombay. It integrates:

- **KiCad** — schematic capture and PCB layout
- **Ngspice** — SPICE-based circuit simulation
- **GHDL / Verilator** — HDL-based mixed-signal work via NgVeri
- **OpenModelica** — system-level modelling

Anyone who has set up eSim from scratch knows how fragmented the process can be. The wrong Ngspice version silently breaks simulation. A KiCad mismatch breaks the schematic-to-netlist pipeline. A missing `libffi-dev` causes a cryptic build failure.

**This tool manager exists to solve that** automating the entire lifecycle of eSim's external tools, from installation and version checking to compatibility validation and health reporting.

---

## Design Goals

Five principles were established before any code was written:

| # | Principle | Description |
|---|---|---|
| 1 | **Separation of concerns** | Backend logic must be completely independent of the UI layer |
| 2 | **Minimal dependencies** | Only `rich` and `customtkinter` as third-party packages; everything else uses the Python standard library |
| 3 | **eSim-specific intelligence** | The tool knows which versions of each tool are required by each eSim release, not just whether they're installed |
| 4 | **Graceful failure** | If an install fails, a binary is missing, or a version cannot be parsed, the tool logs it and continues |
| 5 | **Portable by design** | The same codebase auto-detects `apt`, `brew`, `winget`, `dnf`, and `pacman` without user configuration |

---

## Overall Architecture

The project is **six Python files**. Each has one clear, well-scoped responsibility.

```
main.py  →  cli.py   or   gui.py
              both depend on  →  core.py  +  theme.py
health_report.py  →  core.py  +  theme.py
```

The user always enters through `main.py`. Depending on CLI flags, execution routes to either `cli.py` (rich terminal) or `gui.py` (customtkinter desktop app). Both are **pure presentation layers** they call functions from `core.py` and display results. `health_report.py` similarly calls `core.py` and builds an HTML document. `theme.py` is a passive constants file shared by all layers.

---

## Architecture Diagram Walkthrough

The diagram below describes the full data and control flow through the system.

```
                          ┌────────┐
                          │  User  │
                          └───┬────┘
                              │
                         ┌────▼─────┐
                         │  main.py │
                         │ Entry pt │
                         │ & flags  │
                         └──┬──┬──┬─┘
                  --gui ──┘  │  └── --report
                             │ (default)
            ┌────────────────┼──────────────────┐
            │                │                  │
       ┌────▼────┐     ┌─────▼──────┐    ┌──────▼────────┐
       │  gui.py │     │   cli.py   │    │health_report.py│
       │  ctktr  │     │  rich TUI  │    │ HTML Generator │
       └────┬────┘     └─────┬──────┘    └──────┬─────────┘
            │                │                  │
            └────────┬───────┴──────────────────┘
                     │
          ┌──────────┴─────────┐
          │                    │
     ┌────▼─────┐        ┌─────▼──────┐
     │ core.py  │        │  theme.py  │
     │ Backend  │        │ Catppuccin │
     │  Logic   │        │   Mocha    │
     └────┬─────┘        └────────────┘
          │
   ┌──────┴──────────────────────────────────────────┐
   │                                                  │
   ▼           ▼             ▼           ▼            ▼
detect_os  scan_tools  check_deps  check_compat  install_tool
OS + pkg   Version     System      eSim version  apt/brew/
manager    detection   deps        matrix        winget/dnf/
                                                 pacman
   │                                                  │
   └──────────────────────┬───────────────────────────┘
                          │
              ┌───────────▼────────────┐
              │  ~/.esim_tool_manager/ │
              │  ├── manager.log       │
              │  ├── config.json       │
              │  └── health_report.html│
              └────────────────────────┘
```

### How the diagram maps to execution

**Entry point (`main.py`)** sits at the top, receiving CLI flags from the user. Three flags drive three different execution paths:

- `--gui` → routes to `gui.py`, spawning the desktop application
- `--report` → routes directly to `health_report.py`, generating and opening an HTML file
- default / `--scan` / `--check` / `--compat` → routes to `cli.py`, the rich terminal interface

**Presentation layer (`gui.py`, `cli.py`, `health_report.py`)** all three modules sit at the same level in the hierarchy. None of them contain business logic. They are display wrappers only.

**Logic and theming layer (`core.py`, `theme.py`)** every presentation module feeds into both `core.py` (for data) and `theme.py` (for colours). This is where the strict separation of concerns is enforced; no UI code appears in either file.

**`core.py` functions** six distinct subsystems fan out from core:

| Function | What it does |
|---|---|
| `detect_os()` | Identifies OS and selects the appropriate package manager |
| `scan_tools()` | Detects installed tools and their versions |
| `check_dependencies()` | Validates system-level build prerequisites |
| `check_esim_compatibility()` | Evaluates tools against the eSim version matrix |
| `install_tool()` | Runs package manager install commands as subprocesses |
| `load_config()` / `save_config()` | Reads and writes JSON configuration |

**Persistent storage (`~/.esim_tool_manager/`)** all six functions converge on a single directory for their outputs: a log file, a config file, and the HTML health report.

---

## Module Breakdown

| File | Responsibility | Key exports |
|---|---|---|
| `theme.py` | Catppuccin Mocha palette constants | `Mocha` class with all hex values |
| `core.py` | All backend logic zero UI code | `scan_tools`, `check_dependencies`, `install_tool`, `check_esim_compatibility`, `get_install_command` |
| `gui.py` | customtkinter desktop GUI, 6 panels | `App` class, `launch()` |
| `cli.py` | rich terminal interface, interactive menu | `run_interactive`, `run_scan`, `run_dep_check`, `run_compat_check` |
| `health_report.py` | HTML health report generator | `generate_report()` |
| `main.py` | Entry point & CLI flag dispatcher | `--gui`, `--scan`, `--check`, `--compat`, `--report`, `--install`, `--dry-run` |

---

## Core Modul core.py

Every meaningful operation happens here. The UI files are thin wrappers that call these functions and display results.

### OS and Package Manager Detection

`detect_os()` reads `/etc/os-release` on Linux, checks for `apt`, `dnf`, `pacman` in order; on macOS checks for `brew`; on Windows checks for `winget` then `choco`. The result is a dictionary that every other function uses to select the correct install command.

### Tool Definitions

Each of the five managed tools is described in the `TOOLS` dictionary with:

- Binary name and version flag
- Latest known version
- Package names per package manager
- An eSim-specific role description

Adding a new tool is a **single dictionary entry**.

### Tool Scanner

`scan_tools()` calls `shutil.which()` for each binary, runs it with its version flag, and parses the version string. It compares installed vs. latest using tuple comparison. Results are one of:

| Status | Meaning |
|---|---|
| `ok` | Installed, at latest known version |
| `update` | Installed, but a newer version exists |
| `missing` | Binary not found on PATH |
| `unknown` | Found, but version string could not be parsed |

Every result is logged.

### Dependency Checker

`check_dependencies()` checks system-level packages (`gcc`, `cmake`, `libffi-dev`, `git`, etc.) that eSim's tools require. For standard binaries it uses `shutil.which()`; for library packages without a direct binary it calls `dpkg -l`. Each missing dependency includes the **exact fix command**.

### eSim Compatibility Matrix

The `ESIM_COMPATIBILITY` dictionary encodes the supported version range for each tool across all three current eSim releases. `check_esim_compatibility()` evaluates each tool against the matrix and distinguishes:

- `too_old` — installed version is below the minimum required
- `too_new` — installed version is above the tested maximum
- `missing` — tool is not installed at all

Critical tools push the overall verdict to `incompatible`; non-critical tools push it to `warning`.

### Installer

`install_tool()` builds the appropriate install command and runs it as a subprocess. A `sudo -n` (non-interactive) approach is used — works when the calling terminal has a cached sudo session, fails immediately with a clear message otherwise. A `callback` parameter means the **same function streams output to both CLI and GUI** without duplication.

### Configuration

`load_config()` and `save_config()` read/write JSON at `~/.esim_tool_manager/config.json`. Created from defaults on first run.

---

## Graphical Interface — gui.py

Built with `customtkinter`, fully themed with Catppuccin Mocha colours from `theme.py`.

### Panels

| Panel | Contents |
|---|---|
| **Dashboard** | Stat cards (total, up to date, updates, missing), system info table, recent log tail |
| **Tools** | Scrollable list with version, status badge, path, and Install / Update / Info button |
| **Dependencies** | Colour-coded present/absent table with fix commands |
| **Compat** | Radio buttons for eSim version, full compatibility table, Health Report button |
| **Config** | Form fields and toggles; Save button writes to disk |
| **Log** | Full scrollable log file view |

### Threading

All slow operations run in **daemon threads**. Results are pushed back to the main thread via `after()` — the standard safe tkinter pattern. This ensures the UI never freezes during a scan or install.

### Install Progress Dialog

Clicking Install opens a modal with:

- An indeterminate progress bar
- A live status label
- A scrolling output textbox streaming subprocess output line by line

On completion, the bar turns green (success) or red (failure) and a Close button appears.

---

## Terminal Interface: cli.py

Uses `rich` for tables, panels, coloured text, and spinners. Catppuccin Mocha colours are applied via `rich.Style` objects sourced from `theme.py`. The interface presents an interactive numbered menu, and all functions are also **importable** for the non-interactive CLI flags defined in `main.py`.

---

## Health Report: health_report.py

`generate_report()` collects data from `core.py`, builds a **self-contained HTML document** using Python f-strings, writes to `~/.esim_tool_manager/health_report.html`, and opens it in the default browser.

No external stylesheets or JavaScript — fully portable as a single file. The report can be triggered from the CLI, the GUI's Compat panel, or directly via `python3 main.py --report`.

---

## eSim Tool Roles

| Tool | eSim Component | Role | Criticality |
|---|---|---|---|
| **KiCad** | Schematic + PCB | Primary front-end — Eeschema + Pcbnew | Critical |
| **Ngspice** | Circuit Simulation | Core SPICE engine — receives netlists from KiCad | Critical |
| **GHDL** | HDL Simulation (NgVeri) | Compiles VHDL for co-simulation via XSPICE | Required for NgVeri |
| **Verilator** | HDL Simulation (NgVeri) | Compiles Verilog / SystemVerilog for NgVeri | Required for NgVeri |
| **OpenModelica** | System Modeling | Multi-domain modelling complement to Ngspice | Optional |

KiCad and Ngspice are critical in every eSim version. GHDL and Verilator are required only for NgVeri mixed-signal work. OpenModelica is optional for system-level extensions.

---

## Requirements Coverage

| Requirement | Implementation |
|---|---|
| **Req 1** — Tool Installation | `install_tool()` in `core.py` using apt / brew / winget / dnf / pacman |
| **Req 2** — Update System | Version comparison in `scan_tools()` flags outdated tools |
| **Req 3** — Configuration | `load_config()` / `save_config()` with JSON at `~/.esim_tool_manager/config.json` |
| **Req 4** — Dependency Checker | `check_dependencies()` with `shutil.which` and `dpkg -l` |
| **Req 5** — User Interface | customtkinter GUI + rich terminal UI + persistent log |
| **Req 6** — Cross-platform | `detect_os()` auto-selects apt / brew / winget / dnf / pacman |

---

## Component Interaction — Typical Session

A typical user session running the GUI flows through the following steps:

```
1.  python3 main.py --gui
        └─→ main.py calls gui.launch()

2.  App window appears
        └─→ _startup_scan() starts two daemon threads

3.  Daemon threads call:
        └─→ detect_os()              (core.py)
        └─→ scan_tools()             (core.py)
        └─→ check_dependencies()     (core.py)

4.  Results pushed to main thread via after()
        └─→ Dashboard and Tools panels populate

5.  User selects eSim 2.5 in Compat panel → clicks Check
        └─→ check_esim_compatibility() runs

6.  User clicks Health Report
        └─→ generate_report() builds HTML, opens browser

7.  User clicks Install on a missing tool
        └─→ Progress dialog opens
        └─→ install_tool() streams output line by line

8.  Throughout all steps
        └─→ Every action written to manager.log by log() in core.py
```
