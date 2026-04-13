# Features of eSim Tool Manager

## Tool Scanner
- Detects all 5 eSim-managed tools: KiCad, Ngspice, GHDL, Verilator, OpenModelica
- Uses `shutil.which()` for binary detection no hardcoded paths
- Parses version string from CLI output, compares against known latest
- Status: `ok` | `update` | `missing` | `unknown`

## eSim Compatibility Matrix
- Unique feature: validates tools against specific eSim version requirements
- Covers eSim 2.3, 2.4, and 2.5 with exact min/max version ranges
- Distinguishes `too_old`, `too_new`, and `missing`
- Marks tools as critical (core workflow) vs optional (NgVeri/OpenModelica)
- Python version check against eSim minimum requirements
- Overall verdict: `compatible` | `warning` | `incompatible`

## Dependency Checker
- Checks: python3, pip3, gcc, cmake, make, git, libffi-dev, libglu1
- Uses `dpkg -l` for library packages without a direct binary
- Shows exact fix command for each missing dependency

## Tool Installer
- Builds install command from tool registry + detected package manager
- Streams output line-by-line to callback (CLI prints / GUI scrolls)
- `sudo -n` (non-interactive): works when sudo is cached, fails fast when not
- `--dry-run` flag: prints command without executing safe for testing
- Supported: apt, brew, winget, dnf, pacman

## Graphical Dashboard (GUI)
- 6 panels: Dashboard, Tools, Dependencies, Compat, Config, Log
- Stat cards with live counts (total / ok / updates / missing)
- Scrollable tool rows with Install/Update/Info action buttons
- Install progress dialog: animated bar + live output + status label
- Config panel with form fields and toggle switches
- All operations run in daemon threads; UI never freezes

## Rich Terminal UI (CLI)
- Catppuccin Mocha colours via `rich.Style` objects
- Tool and dependency tables with `rich.Table`
- Spinner animations during scans (`rich.Console.status`)
- Interactive numbered menu with `rich.Prompt`
- All public functions importable for scripting

## HTML Health Report
- Triggered by `--report` flag or GUI button
- Self-contained HTML no external CSS or JS
- Sections: stat cards, eSim component roles, compatibility matrix, tool scan, deps, log tail
- Saved to `~/.esim_tool_manager/health_report.html`
- Opens in default browser automatically
- Shareable as a single file

## Logging
- Every action written to `~/.esim_tool_manager/manager.log`
- Format: `YYYY-MM-DD HH:MM:SS  [LEVEL]   message`
- Levels: INFO, WARNING, ERROR
- Viewable in GUI Log panel, CLI menu option 7, or health report

## Configuration
- JSON config at `~/.esim_tool_manager/config.json`
- Created from defaults on first run
- Editable via GUI Config panel or direct file edit
- Fields: theme, auto_update, log_level, esim_path, check_on_start

## Cross-platform Detection
- `detect_os()` reads `/etc/os-release` on Linux for distro name
- Package manager priority: apt → dnf → pacman on Linux
- macOS: checks for brew
- Windows: checks for winget then choco
- All install commands built dynamically from detection result
