# eSim Tool Manager

> Automated installation, dependency checking, configuration, and management of eSim's external tools — with a Catppuccin Mocha themed terminal UI and GUI.

---

## Features

| Requirement | Coverage |
|---|---|
| **Req 1** — Tool Installation Management | Install Ngspice, KiCad, GHDL, OpenModelica, Verilator via system package manager |
| **Req 3** — Configuration Handling | JSON config, path management, env-aware |
| **Req 4** — Dependency Checker | Checks all build deps, reports missing with fix commands |
| **Req 5** — User Interface + Logging | Rich terminal UI + customtkinter GUI + persistent log file |
| **Req 6** — Cross-platform | Auto-detects apt / brew / winget / dnf / pacman |

---

## Install (one-liner)

```bash
curl -sSL https://raw.githubusercontent.com/Princess0407/esim-tool-manager/main/install.sh | bash
```

---

## Manual Install

```bash
git clone https://github.com/Princess0407/esim-tool-manager
cd esim-tool-manager
pip install -r requirements.txt --break-system-packages
```

---

## Usage

### Terminal UI (default)
```bash
python3 main.py
esim-tm
```

### GUI (Catppuccin Mocha dashboard)
```bash
python3 main.py --gui
# or:
esim-tm --gui
```

### Quick commands
```bash
esim-tm --scan       # Scan and print installed tools
esim-tm --check      # Run dependency check
esim-tm --install Ngspice   # Install a specific tool
```

---

## Project Structure

```
esim_tool_manager/
├── main.py          # Entry point — CLI flags, dispatches to gui or cli
├── gui.py           # customtkinter GUI — all panels and widgets
├── cli.py           # rich terminal interface — menus and tables
├── core.py          # Backend — scanner, installer, dep checker, logger, config
├── theme.py         # Catppuccin Mocha palette constants
├── requirements.txt # Python dependencies
├── install.sh       # One-liner installer for end users
└── README.md        # This file
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `customtkinter` | Modern dark-themed GUI widgets |
| `rich` | Beautiful terminal tables, panels, spinners |

Both are installed automatically by `install.sh`.

---

## Config file

Stored at `~/.esim_tool_manager/config.json`:

```json
{
  "theme": "mocha",
  "auto_update": false,
  "log_level": "info",
  "esim_path": "/home/user/eSim",
  "check_on_start": true
}
```

---

## Log file

All actions are logged to `~/.esim_tool_manager/manager.log`:

```
2026-04-04 10:12:01  [INFO]   Tool Manager started
2026-04-04 10:12:02  [INFO]   Tool scan: Ngspice → ok (40.1)
2026-04-04 10:12:02  [INFO]   Tool scan: KiCad → update (8.0.3)
2026-04-04 10:12:02  [INFO]   Dep check: gcc → ok
2026-04-04 10:12:02  [INFO]   Dep check: libffi-dev → missing
```

---

## Supported Tools

| Tool | Description |
|---|---|
| Ngspice | SPICE circuit simulator (core eSim engine) |
| KiCad | PCB design suite |
| GHDL | VHDL simulator |
| OpenModelica | Modelica-based simulation |
| Verilator | Verilog/SystemVerilog simulator |

---

## Supported Package Managers

| OS | Package Manager |
|---|---|
| Debian / Ubuntu | `apt` |
| Fedora / RHEL | `dnf` |
| Arch Linux | `pacman` |
| macOS | `brew` (Homebrew) |
| Windows | `winget` or `choco` |

---

## License

MIT License — developed as part of eSim Summer Fellowship 2026 Task 5.
