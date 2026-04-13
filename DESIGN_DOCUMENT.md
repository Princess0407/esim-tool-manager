## Design Document

# **1\. Introduction**

eSim is an open-source EDA platform developed by the FOSSEE team at IIT Bombay. It brings together several external tools accessible from one place. KiCad for schematic capture and PCB layout, Ngspice for SPICE simulation, GHDL and Verilator for HDL-based mixed-signal work via NgVeri, and OpenModelica for system-level modelling. Each of these tools has its own installation procedure, version requirements, and configuration needs.

Anyone who has tried setting up eSim from scratch on a fresh system will know how fragmented this process can be. You hunt for the right Ngspice build, discover your KiCad version is incompatible, miss a shared library, and end up spending an afternoon on setup rather than on actual circuit work. That is the problem that this tool manager is trying to solve.

The eSim Tool Manager automates the entire lifecycle of these external tools: detecting what is already installed, checking whether installed versions are compatible with a specific eSim release, identifying missing system dependencies, and installing or updating tools with a single action. It provides both a terminal interface for users comfortable on the command line and a full graphical dashboard for everyone else, and it also generates HTML health report that captures the state of the system at a glance for deeper insights.

# **2\. Design Goals**

Before writing a single line of code, a few principles were agreed on to guide every decision:

- the backend logic should be entirely independent of the UI. Whether someone uses the terminal or the GUI, the same functions run underneath.
- No unnecessary dependencies: the tool should work with only two third-party packages rich for terminal rendering and customtkinter for the GUI. Everything else uses the Python standard library.
- Unlike a generic package manager wrapper, this tool knows exactly which versions of each external tool are required by each eSim release. That knowledge is baked in, not looked up at runtime.
- In case an install fails, if a binary is missing, if a version cannot be parsed, the tool will log it, report it clearly, and continue rather than crash.
- Portable by design: the same codebase detects and adapts to apt on Debian/Ubuntu, brew on macOS, and winget or choco on Windows without the user doing anything.

# **3\. Overall Architecture**

The project is split into six Python files. Each file has one clear responsibility and does not reach into another file's domain unnecessarily. The flowchart below shows how they relate:

**main.py → cli.py or gui.py**

_both depend on → core.py + theme.py_

_health_report.py → core.py + theme.py_

The user always enters through main.py. Depending on the flags passed, execution goes to either the rich terminal interface (cli.py) or the customtkinter graphical interface (gui.py). Both of these are pure presentation layers; they call functions from core.py and simply display the results.The health_report.py module similarly calls core.py to gather data and then builds an HTML document from it. theme.py is a passive constants file to theme the terminal/GUI alike. It holds every Catppuccin(I prefer it) Mocha colour value and is imported wherever a colour is needed.

## **3.1 Module Breakdown**

| **File**         | **Responsibility**                         | **Key exports**                                                                     |
| ---------------- | ------------------------------------------ | ----------------------------------------------------------------------------------- |
| theme.py         | Catppuccin Mocha palette constants         | Mocha class with all hex values                                                     |
| core.py          | All backend logic                          | scan_tools, check_deps, install_tool, check_esim_compatibility, get_install_command |
| gui.py           | customtkinter desktop GUI (6 panels)       | App class, launch()                                                                 |
| cli.py           | rich terminal interface (interactive menu) | run_interactive, run_scan, run_dep_check, run_compat_check                          |
| health_report.py | HTML health report generator               | generate_report()                                                                   |
| main.py          | Entry point into CLI                       | \--gui, --scan, --check, --compat, --report, --install, --dry-run                   |

# **4\. Core Module: core.py**

This is the most important file in the project. Every meaningful operation be it; scanning, checking, installing, configuring; happens here. The UI files are basically thin wrappers that call these functions and display the results.

## **4.1 OS and Package Manager Detection**

The detect_os() function reads /etc/os-release on Linux to get a human-readable distribution name, then checks for the presence of apt, dnf, and pacman in that order to identify the package manager. On macOS it checks for brew; on Windows for winget then choco. The result is a dictionary that every other function uses to know what commands to run.

This single function is what makes the tool cross-platform. The rest of the code simply uses the pkg_manager value it returns.

## **4.2 Tool Definitions**

Each of the five managed tools is described in a TOOLS dictionary. An entry looks like this:
```
"Ngspice": {

"cmd": "ngspice", # binary to look up via shutil.which

"version": "--version", # flag to get the version string

"latest": "42", # current known stable release

"apt": "ngspice", # package name on Debian/Ubuntu

"brew": "ngspice", # package name on macOS

"winget": "ngspice", # package name on Windows

"desc": "SPICE simulation engine (eSim core simulator)",

"esim_role": "...", # full explanation of role within eSim

"esim_component": "Circuit Simulation"

}
```

Keeping all of this in one place means adding support for a new tool is a single dictionary entry

## **4.3 Tool Scanner**

scan_tools() iterates over every entry in TOOLS. For each one it calls shutil.which() to find the binary, then runs the binary with its version flag and parses the output to extract the version string. It then compares the installed version against the known latest using a simple tuple comparison of the first two version number components. The result is one of four statuses: ok, update, missing, or unknown. Every result is logged to the persistent log file.

## **4.4 Dependency Checker**

check_dependencies() works similarly but against a separate DEPENDENCIES dictionary that lists the system-level packages eSim's tools need at build or runtime things like gcc, cmake, libffi-dev, and git. For standard binaries it uses shutil.which(); for library packages that do not have a direct binary, it calls dpkg -l and checks for the ii prefix that indicates a cleanly installed package. Each missing dependency includes the exact apt install command needed to fix it.

## **4.5 eSim Compatibility Matrix**

The ESIM_COMPATIBILITY dictionary encodes the supported version range for each tool across all three current eSim releases:

| **Tool**     | **eSim 2.3** | **eSim 2.4** | **eSim 2.5** | **Critical** |
| ------------ | ------------ | ------------ | ------------ | ------------ |
| Ngspice      | 36 - 38      | 38 - 40      | 40 - 42      | Yes          |
| KiCad        | 5.1 - 6.0    | 6.0 - 7.0    | 8.0 - 9.0    | Yes          |
| GHDL         | 1.0 - 2.0    | 2.0 - 3.0    | 3.0 - 4.1    | No           |
| Verilator    | 4.2          | 4.2 - 5.0    | 5.0 - 5.024  | Yes (2.4+)   |
| OpenModelica | 1.18 - 1.20  | 1.20 - 1.22  | 1.22 - 1.24  | No           |

The check_esim_compatibility() function takes a target eSim version and the list of scanned tools, then evaluates each tool against the matrix. It distinguishes between three compatibility problems: too_old (installed version below minimum), too_new (above tested maximum may work but untested), and missing. Critical tools those whose absence makes eSim non-functional push the overall verdict to incompatible. Non-critical tools push it only to warning. Python version is also checked against the minimum required by the target eSim release.

## **4.6 Installer**

install_tool() builds the appropriate install command from the TOOLS dictionary and the detected package manager, then runs it as a subprocess. On Linux with apt, the command uses sudo. To avoid the GUI hanging silently while waiting for a password prompt that can never appear, the tool uses sudo -n (non-interactive mode). If the user ran the GUI from a terminal that already has a cached sudo session, the install proceeds immediately and streams every line of output back through a callback function. If the session is not cached, sudo -n exits immediately with a non-zero return code, and the output box shows a clear message asking the **user to open a terminal,** **run sudo echo to cache the session**, and try again.

The callback pattern means the same install_tool() function works for both the CLI (where it prints each line to the terminal) and the GUI (where it appends each line to the live output textbox in the progress dialog). To save the user from uneceaasry clueless waiting session.

## **4.7 Configuration**

load_config() and save_config() read and write a JSON file at ~/.esim_tool_manager/config.json. If the file does not exist on first run, it is created from a set of defaults. The Config panel in the GUI writes back to this file whenever the user clicks Save. Settings include the path to the eSim installation, the log level, and toggles for auto-update and startup checks.

# **5\. Graphical Interface - gui.py**

The GUI is built with customtkinter, which wraps tkinter with a modern dark-mode rendering layer. The entire window is themed with the Catppuccin Mocha colour palette defined in theme.py, giving it a consistent visual identity.

## **5.1 Layout**

The window is divided into a fixed width sidebar on the left and a main content area on the right. The sidebar contains the navigation buttons and a small system info label at the bottom. The top of the main area has a thin bar that shows the current page title and a live status message. Below that is the content area, which swaps between six panels using pack/pack_forget.

## **5.2 Panels**

- Dashboard: shows four stat cards (total tools, up to date, updates available, missing), a system information table, and a tail of the recent log.
- Tools: a scrollable list of all managed tools with their version, latest version, status badge, installation path, and an action button that changes to Install, Update, or Info depending on status.
- Dependencies: a scrollable list of all system dependencies with a colour-coded present/absent badge and the fix command for anything missing.
- Compat: radio buttons to select a target eSim version, a full compatibility breakdown table, and a Health Report button.
- Config: form fields and toggle switches for all user settings, with a Save button that writes to disk.
- Log: a scrollable view of the full contents of the persistent log file, with a Refresh button.

## **5.3 Threading**

All potentially slow operations tool scanning, dependency checking, and installation run in daemon threads so the GUI never freezes. Results are pushed back to the main thread using the after() method, which is the standard safe way to update tkinter widgets from a background thread.

## **5.4 Install Progress Dialog**

Clicking Install opens a modal dialog containing a command preview, an indeterminate progress bar that animates while the install runs, a live status label showing the most recent output line, and a scrollable textbox receiving the full streamed output. When the install completes, the progress bar switches to determinate mode and turns green or red, the status label updates, and a Close button becomes active. The dashboard then automatically rescans.

# **6\. Terminal Interface - cli.py**

The terminal interface uses the rich library to render tables, panels, coloured text, and progress spinners. It uses the same Catppuccin Mocha colours as the GUI, applied via rich Style objects constructed from the hex values in theme.py.

The interface presents an interactive numbered menu. Each option calls one of the public functions run_scan(), run_dep_check(), run_compat_check(), run_install(), run_config(), run_log(), or run_health_report(). All of these functions are also importable and callable directly, which is how main.py implements the non-interactive command-line flags like --scan and --check.

The tool table uses rich's Table class with SIMPLE_HEAD box style. Statuses are rendered as coloured Text objects rather than plain strings, so the terminal output uses colour semantically green for ok, yellow for update available, red for missing rather than just decoratively color coding.

# **7\. Health Report - health_report.py**

The generate_report() function collects data by calling detect_os(), scan_tools(), check_dependencies(), check_esim_compatibility() for all three known eSim versions, and read_log(). It then builds a self-contained HTML document using Python f-strings and writes it to ~/.esim_tool_manager/health_report.html, opening it in the default browser automatically.

The report is fully self-contained no external stylesheets or JavaScript. It uses the Catppuccin Mocha colour values inline so it looks consistent regardless of the browser or OS. It contains five sections: a stat card grid, an eSim component roles card grid explaining why each tool exists, the full compatibility matrix for all three eSim versions, the tool scan results table, and a tail of the log file.

This report is designed to be shareable. A user who wants to ask for help diagnosing their eSim setup can send the HTML file and the recipient gets a complete, readable picture of the system without needing to install anything.

# **8\. eSim Tool Roles**

Understanding why each tool is managed - not just that it needs to be installed - informed a lot of decisions about version ranges, criticality flags, and the descriptions shown in the UI. The table below summarises the official role of each tool within the eSim ecosystem:

| **Tool**     | **eSim Component**      | **Role within eSim**                                                                                       |
| ------------ | ----------------------- | ---------------------------------------------------------------------------------------------------------- |
| KiCad        | Schematic + PCB         | Primary front-end. Eeschema handles circuit drawing; Pcbnew handles PCB layout.                            |
| Ngspice      | Circuit Simulation      | Core engine. eSim converts KiCad schematics to SPICE netlists and invokes Ngspice for all analog analyses. |
| GHDL         | HDL Simulation (NgVeri) | Compiles VHDL descriptions into shared libraries co-simulated with Ngspice via XSPICE.                     |
| Verilator    | HDL Simulation (NgVeri) | Compiles Verilog/SystemVerilog into C++ linked into Ngspice for mixed-signal simulation.                   |
| OpenModelica | System Modeling         | Multi-domain modeling for control systems and thermal analysis, complementing Ngspice circuit-level work.  |

KiCad and Ngspice are marked critical in every eSim version because without them the core schematic to simulation workflow cannot function at all. GHDL, Verilator, and OpenModelica are optional in the sense that basic analog simulation still works without them, but NgVeri mixed-signal simulation requires both GHDL and Verilator.

# **9\. Requirements Coverage**

| **Requirement**           | **Status** | **Implementation**                                                                           |
| ------------------------- | ---------- | -------------------------------------------------------------------------------------------- |
| Req 1: Tool Installation  | Covered    | install_tool() in core.py uses apt/brew/winget/dnf/pacman with sudo-n fallback               |
| Req 2: Update System      | Partial    | Version comparison in scan_tools() flags outdated tools; install re-runs to update           |
| Req 3: Configuration      | Covered    | load_config()/save_config() with JSON at ~/.esim_tool_manager/config.json                    |
| Req 4: Dependency Checker | Covered    | check_dependencies() uses shutil.which and dpkg -l for library packages                      |
| Req 5: User Interface     | Covered    | Full customtkinter GUI + rich terminal UI + persistent log file                              |
| Req 6: Cross-platform     | Covered    | detect_os() auto-selects apt/brew/winget; tested on Linux; architecture supports Mac/Windows |

# **10\. Component Interaction(By User)**

The following describes a typical user session to illustrate how the components work together at runtime:

- The user runs python3 main.py --gui. main.py parses the flag and calls gui.launch().
- The App window appears. Its \_\_init\_\_method calls after(200, self.\_startup_scan) so the scan starts after the window is drawn.
- \_startup_scan() starts two daemon threads: one calls detect_os() and scan_tools() from core.py; the other calls check_dependencies().
- As each thread finishes, it schedules UI updates on the main thread using after(). The Dashboard stat cards update, the Tools panel populates its scrollable list, and the Dependencies panel fills in.
- The user navigates to the Compat panel and selects eSim 2.5. They click Check. A new daemon thread calls check_esim_compatibility('2.5', self.tools) from core.py and renders the result table.
- The user clicks Health Report. generate_report() in health_report.py calls core.py functions, builds the HTML string, writes it to disk, and opens the browser. The status bar updates.
- The user sees Ngspice is missing. They click Install. The progress dialog opens, a daemon thread runs install_tool() from core.py with a callback that appends each output line to the dialog's textbox. When done, run_scan() is called again to refresh the Tools panel.
- Every action throughout the session is written to ~/.esim_tool_manager/manager.log by the log() function in core.py.

# **11\. Configuration and Logging**

## **11.1 Config file**

Stored at ~/.esim_tool_manager/config.json. Created on first run with defaults. Fields:

- theme: colour theme name (currently mocha only)
- auto_update: boolean check for updates on startup
- log_level: info / debug / warning
- esim_path: path to eSim installation directory
- check_on_start: boolean run dependency check on startup

## **11.2 Log file**

Stored at ~/.esim_tool_manager/manager.log. Every call to the log() function in core.py appends a timestamped line. Format:

2026-04-13 10:12:01 \[INFO\] Tool scan: Ngspice → ok (40.1)

2026-04-13 10:12:02 \[WARNING\] KiCad update available: 9.0.1

2026-04-13 10:12:03 \[ERROR\] Install failed for OpenModelica

The log is readable in the Log panel of the GUI, in the terminal via menu option 7, and in the health report's log section.

# **12\. Installation and Execution**

## **12.1 Dependencies**

- Python 3.10 or later
- customtkinter (pip install customtkinter)
- rich (pip install rich)

On Debian/Ubuntu: pip install customtkinter rich --break-system-packages

## **12.2 Running the tool**
```bash
python3 main.py # interactive terminal menu

python3 main.py --gui # graphical dashboard

python3 main.py --scan # scan tools, print table, exit

python3 main.py --check # check dependencies, exit

python3 main.py --compat 2.5 # eSim 2.5 compatibility check

python3 main.py --report # generate HTML report, open browser

python3 main.py --install Ngspice # install a specific tool

python3 main.py --dry-run --install KiCad # preview without executing
```

## **12.3 Install note for GUI installs**

The install feature calls sudo under the hood. For the GUI to run installs without hanging, the terminal that launched the GUI should have a cached sudo session. Before launching the GUI, run:

sudo echo ok && python3 main.py --gui

This caches the sudo password for the session duration. All subsequent installs from the GUI will proceed without needing a password prompt.

# **13\. Key Design Decisions**

### **Customtkinter over PyQt or tkinter**

customtkinter is a single pip install that wraps tkinter which ships with Python giving it a modern dark-mode appearance without requiring Qt or any C extensions. For a tool that needs to run on a student's freshly installed Debian system, minimising setup friction matters.

### **rich for the terminal UI**

rich provides tables, panels, coloured output, and spinner animations with no native code dependencies. It works identically on Linux, macOS, and Windows terminals. The result is a terminal experience that looks good rather than like raw print() statements.

### **Catppuccin Mocha over Normal theming**

Catppuccin is a well-documented community colour scheme with accessibility-considered contrast ratios. Mocha's dark base with pastel accents reads well on both high-DPI screens and older monitors. More practically, keeping all colours in theme.py means the visual identity of the GUI and terminal UI stays consistent with a single source of truth.

### **Compatibility matrix rather than live version lookup**

Querying a live API at runtime would require internet access, introduce latency, and create a point of failure. The supported version ranges for eSim 2.3, 2.4, and 2.5 are stable and documented. Embedding them directly means the tool works fully offline which matters on the lab machines where eSim is typically used.

### **Separate health_report.py from the rest of the UI**

The HTML report is a standalone deliverable it can be saved, emailed, and opened without the tool manager being installed. Keeping it in its own module means it can be called from the CLI, the GUI, or directly, and its HTML generation logic does not pollute either UI module.

# **14\. Planned Extensions**

- Live Version Lookups (GitHub API)
Automatically queries the GitHub REST API to detect the latest releases for KiCad and Ngspice, ensuring users always have access to current binaries.
Provides real-time compatibility checks by fetching metadata directly from official tool repositories instead of relying on hardcoded versions.

- Update All Sequential Installer
Implements a threaded task queue to download and install all pending updates sequentially without freezing the user interface.
Includes a unified progress tracker that displays the real-time status and remaining time for the entire batch update cycle.

- Python Package Tracking
Monitors and manages essential eSim-related libraries like PySpice and NumPy to ensure the internal simulation environment is fully functional.
Automatically triggers pip updates for these specific dependencies when version mismatches or missing modules are detected during system scans.

- Polkit Integration for Linux Security
Enhances security by using Polkit (pkexec) to request administrative privileges only during critical installation steps rather than running the entire GUI as root.
Seamlessly integrates with native OS password prompts to provide a professional, secure, and user-friendly experience on Linux systems.

- One-Click Rollback Mechanism
Provides an option to revert tools to previous versions or restore configuration files to a "Last Known Good" state.
Safely manages backup paths to ensure project continuity and minimize downtime if an experimental update introduces bugs.

- Sandboxed Environments (Venv/Conda)
Isolates eSim’s Python dependencies within a dedicated virtual environment to prevent conflicts with the user's system-wide packages.
Automates the creation and maintenance of these isolated spaces to ensure a clean, reproducible simulation environment for every user.

# **15\. Conclusion**

The eSim Tool Manager is a focused solution to a real problem that anyone setting up eSim from scratch encounters. It is not a generic package manager it knows about eSim specifically, including which tools are required by which release version and why. The architecture separates backend logic, terminal presentation, and graphical presentation into distinct modules so that each can be understood, tested, and extended independently.

The combination of a graphical dashboard, a rich terminal interface, an HTML health report, and a cross-platform install system covers all six of the task requirements while remaining simple enough that the entire codebase is readable by anyone with intermediate Python experience.
