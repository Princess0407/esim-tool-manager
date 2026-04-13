import shutil
import subprocess
import platform
import json
import os
import logging
from pathlib import Path
from datetime import datetime

CONFIG_PATH = Path.home() / ".esim_tool_manager" / "config.json"
LOG_PATH    = Path.home() / ".esim_tool_manager" / "manager.log"

CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("esim_tool_manager")


def log(msg: str, level: str = "info"):
    """Write to log file and return the message for display."""
    getattr(logger, level)(msg)
    return msg

def detect_os() -> dict:
    """Detect the current OS and available package manager."""
    system = platform.system()
    distro = ""
    pkg_manager = "unknown"

    if system == "Linux":
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME"):
                        distro = line.split("=")[1].strip().strip('"')
                        break
        except FileNotFoundError:
            distro = "Linux"

        if shutil.which("apt"):
            pkg_manager = "apt"
        elif shutil.which("dnf"):
            pkg_manager = "dnf"
        elif shutil.which("pacman"):
            pkg_manager = "pacman"

    elif system == "Darwin":
        distro = f"macOS {platform.mac_ver()[0]}"
        pkg_manager = "brew" if shutil.which("brew") else "unknown"

    elif system == "Windows":
        distro = f"Windows {platform.version()}"
        if shutil.which("winget"):
            pkg_manager = "winget"
        elif shutil.which("choco"):
            pkg_manager = "choco"

    log(f"OS detected: {distro} · package manager: {pkg_manager}")
    return {
        "system":      system,
        "distro":      distro,
        "pkg_manager": pkg_manager,
        "python":      platform.python_version(),
        "arch":        platform.machine(),
    }

TOOLS = {
 
    "KiCad": {
        "cmd":     "kicad",
        "version": "--version",
        "latest":  "9.0.1",
        "apt":     "kicad",
        "brew":    "kicad",
        "winget":  "KiCad.KiCad",
        "desc":    "Schematic editor & PCB layout (eSim front-end)",
        "esim_role": (
            "Primary schematic capture tool. eSim wraps KiCad's Eeschema "
            "for circuit drawing and component placement. PCB layout is handled "
            "by KiCad's Pcbnew module directly within the eSim workflow."
        ),
        "esim_component": "Schematic + PCB",
    },

    "Ngspice": {
        "cmd":     "ngspice",
        "version": "--version",
        "latest":  "42",
        "apt":     "ngspice",
        "brew":    "ngspice",
        "winget":  "ngspice",
        "desc":    "SPICE simulation engine (eSim core simulator)",
        "esim_role": (
            "Core circuit simulation backend. eSim converts KiCad schematics "
            "to SPICE netlists and invokes Ngspice for all analog simulations — "
            "transient, AC, DC sweep, and operating point analyses."
        ),
        "esim_component": "Circuit Simulation",
    },

    "GHDL": {
        "cmd":     "ghdl",
        "version": "--version",
        "latest":  "4.1.0",
        "apt":     "ghdl",
        "brew":    "ghdl",
        "winget":  "ghdl",
        "desc":    "VHDL simulator — used by eSim's NgVeri for mixed-signal",
        "esim_role": (
            "Enables VHDL-based digital simulation in eSim's NgVeri module. "
            "GHDL compiles VHDL descriptions into shared libraries that are "
            "co-simulated with analog circuits via Ngspice's XSPICE interface."
        ),
        "esim_component": "HDL Simulation (NgVeri)",
    },

    "Verilator": {
        "cmd":     "verilator",
        "version": "--version",
        "latest":  "5.024",
        "apt":     "verilator",
        "brew":    "verilator",
        "winget":  "verilator",
        "desc":    "Verilog/SystemVerilog compiler — eSim NgVeri digital side",
        "esim_role": (
            "Compiles Verilog and SystemVerilog models for use in eSim's NgVeri "
            "mixed-signal simulation framework. Works alongside GHDL to enable "
            "digital HDL blocks to be co-simulated with analog SPICE netlists."
        ),
        "esim_component": "HDL Simulation (NgVeri)",
    },

    "OpenModelica": {
        "cmd":     "omc",
        "version": "--version",
        "latest":  "1.24.0",
        "apt":     "openmodelica",
        "brew":    "openmodelica",
        "winget":  "OpenModelica.OpenModelica",
        "desc":    "System-level modeling — eSim multi-domain simulation",
        "esim_role": (
            "Provides system-level and multi-domain modeling capability within eSim. "
            "Used for control system design, thermal analysis, and higher-abstraction "
            "modeling that complements Ngspice's circuit-level simulations."
        ),
        "esim_component": "System Modeling",
    },
}

DEPENDENCIES = {
    "python3":    {"apt": "python3",     "brew": "python",     "winget": "Python.Python.3"},
    "pip3":       {"apt": "python3-pip", "brew": "python",     "winget": "Python.Python.3"},
    "gcc":        {"apt": "gcc",         "brew": "gcc",        "winget": "GnuWin32.GCC"},
    "cmake":      {"apt": "cmake",       "brew": "cmake",      "winget": "Kitware.CMake"},
    "make":       {"apt": "make",        "brew": "make",       "winget": "GnuWin32.Make"},
    "git":        {"apt": "git",         "brew": "git",        "winget": "Git.Git"},
    "libffi-dev": {"apt": "libffi-dev",  "brew": "libffi",     "winget": "libffi"},
    "libglu1":    {"apt": "libglu1-mesa","brew": "mesa",       "winget": "mesa"},
}


ESIM_COMPATIBILITY = {
    "2.3": {
        "release":     "2022",
        "description": "Stable release — widely used in FOSSEE workshops",
        "requires": {
            "Ngspice":       {"min": "36",   "max": "38",   "critical": True},
            "KiCad":         {"min": "5.1",  "max": "6.0",  "critical": True},
            "GHDL":          {"min": "1.0",  "max": "2.0",  "critical": False},
            "OpenModelica":  {"min": "1.18", "max": "1.20", "critical": False},
            "Verilator":     {"min": "4.2",  "max": "4.2",  "critical": False},
        },
        "python_min": "3.8",
        "os_notes": "Best supported on Ubuntu 20.04 / 22.04",
    },
    "2.4": {
        "release":     "2023",
        "description": "Adds NgVeri for Verilog mixed-signal support",
        "requires": {
            "Ngspice":       {"min": "38",   "max": "40",   "critical": True},
            "KiCad":         {"min": "6.0",  "max": "7.0",  "critical": True},
            "GHDL":          {"min": "2.0",  "max": "3.0",  "critical": False},
            "OpenModelica":  {"min": "1.20", "max": "1.22", "critical": False},
            "Verilator":     {"min": "4.2",  "max": "5.0",  "critical": True},
        },
        "python_min": "3.9",
        "os_notes": "Supported on Ubuntu 22.04. Partial support on Debian 11.",
    },
    "2.5": {
        "release":     "2024",
        "description": "Latest release — improved PCB workflow, KiCad 8 support",
        "requires": {
            "Ngspice":       {"min": "40",   "max": "42",   "critical": True},
            "KiCad":         {"min": "8.0",  "max": "9.0",  "critical": True},
            "GHDL":          {"min": "3.0",  "max": "4.1",  "critical": False},
            "OpenModelica":  {"min": "1.22", "max": "1.24", "critical": False},
            "Verilator":     {"min": "5.0",  "max": "5.024","critical": True},
        },
        "python_min": "3.10",
        "os_notes": "Ubuntu 24.04 recommended. Known issues on Ubuntu 25.04 (see Task 4).",
    },
}

# stable release version of esim(recommeneded for new users)
ESIM_RECOMMENDED = "2.5"


def parse_version(v: str) -> tuple:
    """Convert '40.1' → (40, 1). Handles single-digit versions like '42' → (42, 0)."""
    try:
        parts = v.strip().split(".")
        return tuple(int(x) for x in parts[:2])
    except Exception:
        return (0, 0)


def check_esim_compatibility(esim_version: str, tools: list[dict]) -> dict:
    """
    Given a target eSim version and a list of scanned tools,
    check each tool's installed version against the compatibility matrix.
    Returns a detailed compatibility report dict.
    """
    if esim_version not in ESIM_COMPATIBILITY:
        log(f"Unknown eSim version: {esim_version}", "warning")
        return {"error": f"Unknown eSim version: {esim_version}"}

    matrix   = ESIM_COMPATIBILITY[esim_version]
    requires = matrix["requires"]
    results  = []
    overall  = "compatible"   

    for tool in tools:
        name = tool["name"]
        if name not in requires:
            continue

        req     = requires[name]
        min_ver = req["min"]
        max_ver = req["max"]
        critical = req["critical"]

        installed = tool["version"]

        if installed == "—" or installed is None:
            compat  = "missing"
            verdict = "incompatible" if critical else "warning"
            note    = f"Not installed. Required: {min_ver} – {max_ver}"
        else:
            iv  = parse_version(installed)
            mnv = parse_version(min_ver)
            mxv = parse_version(max_ver)

            if iv < mnv:
                compat  = "too_old"
                verdict = "incompatible" if critical else "warning"
                note    = f"v{installed} is below minimum v{min_ver}"
            elif iv > mxv:
                compat  = "too_new"
                verdict = "warning"
                note    = f"v{installed} exceeds tested maximum v{max_ver} — may work but untested"
            else:
                compat  = "ok"
                verdict = "ok"
                note    = f"v{installed} is within supported range {min_ver} – {max_ver}"

        # Bubble up severity to overall
        if verdict == "incompatible":
            overall = "incompatible"
        elif verdict == "warning" and overall != "incompatible":
            overall = "warning"

        log(f"eSim {esim_version} compat: {name} → {compat} ({note})")
        results.append({
            "tool":      name,
            "installed": installed,
            "min":       min_ver,
            "max":       max_ver,
            "compat":    compat,
            "verdict":   verdict,
            "critical":  critical,
            "note":      note,
        })

    py_min  = matrix["python_min"]
    py_inst = platform.python_version()
    py_ok   = parse_version(py_inst) >= parse_version(py_min)
    if not py_ok and overall != "incompatible":
        overall = "warning"

    log(f"eSim {esim_version} overall compatibility: {overall}")
    return {
        "esim_version": esim_version,
        "description":  matrix["description"],
        "os_notes":     matrix["os_notes"],
        "overall":      overall,
        "tools":        results,
        "python_min":   py_min,
        "python_inst":  py_inst,
        "python_ok":    py_ok,
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
def get_installed_version(cmd: str, flag: str) -> str:
    """Run `cmd flag` and extract the first version-like token found."""
    binary = shutil.which(cmd)
    if not binary:
        return None
    try:
        result = subprocess.run(
            [cmd, flag],
            capture_output=True, text=True, timeout=5
        )
        output = (result.stdout + result.stderr).strip()
        # Grab first token that looks like a version number
        for token in output.split():
            if token[0].isdigit() or (len(token) > 1 and token[1].isdigit()):
                return token.rstrip(",")
        return output.split("\n")[0][:30]
    except Exception:
        return "unknown"


def scan_tools() -> list[dict]:
    """Scan system for all defined tools and return their status."""
    results = []
    for name, info in TOOLS.items():
        binary = shutil.which(info["cmd"])
        if binary:
            version = get_installed_version(info["cmd"], info["version"])
            status  = "ok" if version and version != "unknown" else "unknown"
            # Simple version comparison — flag if installed < latest
            try:
                iv = tuple(int(x) for x in version.split(".")[:2])
                lv = tuple(int(x) for x in info["latest"].split(".")[:2])
                if iv < lv:
                    status = "update"
            except Exception:
                pass
        else:
            version = None
            status  = "missing"
            binary  = "—"

        log(f"Tool scan: {name} → {status} ({version or 'not found'})")
        results.append({
            "name":           name,
            "desc":           info["desc"],
            "esim_role":      info.get("esim_role", ""),
            "esim_component": info.get("esim_component", ""),
            "version":        version or "—",
            "latest":         info["latest"],
            "status":         status,
            "path":           binary,
        })
    return results


def get_esim_roles() -> list[dict]:
    """
    Return eSim-specific role information for all managed tools.
    Used in the health report and GUI info panels to explain
    *why* each tool is needed within the eSim ecosystem.
    """
    return [
        {
            "name":      name,
            "component": info.get("esim_component", ""),
            "role":      info.get("esim_role", ""),
            "desc":      info["desc"],
        }
        for name, info in TOOLS.items()
    ]
def check_dependencies() -> list[dict]:
    """Check all required dependencies and return their status."""
    results = []
    for dep, pkg in DEPENDENCIES.items():
        binary  = shutil.which(dep.replace("-dev", "").replace("lib", ""))
        present = binary is not None

        if dep.startswith("lib"):
            try:
                out = subprocess.run(
                    ["dpkg", "-l", dep],
                    capture_output=True, text=True, timeout=3
                )
                present = "ii" in out.stdout
            except Exception:
                present = False

        log(f"Dep check: {dep} → {'ok' if present else 'missing'}")
        results.append({
            "name":    dep,
            "present": present,
            "fix":     f"apt install {pkg.get('apt', dep)}",
        })
    return results

def get_install_command(tool_name: str, pkg_manager: str) -> list[str] | None:
    """
    Return the install command list for a tool on the given package manager.
    Returns None if the tool or package manager is unknown.
    """
    if tool_name not in TOOLS:
        return None
    pkg = TOOLS[tool_name].get(pkg_manager)
    if not pkg:
        return None
    cmd_map = {
        "apt":    ["sudo", "apt", "install", "-y", pkg],
        "brew":   ["brew", "install", pkg],
        "winget": ["winget", "install", "--silent", pkg],
        "dnf":    ["sudo", "dnf", "install", "-y", pkg],
        "pacman": ["sudo", "pacman", "-S", "--noconfirm", pkg],
    }
    return cmd_map.get(pkg_manager)


def install_tool(
    tool_name:   str,
    pkg_manager: str,
    callback=    None,
    dry_run:     bool = False,
) -> bool:
    """
    Install a tool using the system package manager.

    Args:
        tool_name:   Name of the tool (must be a key in TOOLS).
        pkg_manager: One of apt / brew / winget / dnf / pacman.
        callback:    Optional callable(line: str) — called for each output line.
                     Use this to stream live output into the GUI or CLI.
        dry_run:     If True, log and report the command without executing it.
                     Safe for demos and testing.

    Returns:
        True on success, False on failure or dry_run.

    Notes on sudo:
        On Linux with apt/dnf/pacman the command uses sudo. The process
        inherits the terminal's stdin so the user can type their password
        normally when running from the CLI. In GUI mode, sudo may silently
        fail if no password is cached — the callback will receive the error
        output and it will be logged.
    """
    if tool_name not in TOOLS:
        log(f"Install failed: unknown tool '{tool_name}'", "error")
        return False

    cmd = get_install_command(tool_name, pkg_manager)
    if not cmd:
        log(f"No install mapping for '{tool_name}' on '{pkg_manager}'", "warning")
        if callback:
            callback(f"No package mapping found for {tool_name} on {pkg_manager}.")
        return False

    cmd_str = " ".join(cmd)
    log(f"Install requested: {tool_name} via {pkg_manager} → {cmd_str}")

    if dry_run:
        msg = f"[dry-run] Would execute: {cmd_str}"
        log(msg)
        if callback:
            callback(msg)
        return False

    if callback:
        callback(f"Running: {cmd_str}")
        callback("─" * 50)

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=None,
            text=True,
        )
        for line in process.stdout:
            line = line.rstrip()
            if line:
                log(line)
                if callback:
                    callback(line)

        process.wait()
        success = process.returncode == 0
        result  = "succeeded" if success else f"failed (exit {process.returncode})"
        log(f"Install {result} for {tool_name}", "info" if success else "error")

        if callback:
            callback("─" * 50)
            callback(f"{'✓ Installation complete.' if success else '✗ Installation failed — check log for details.'}")

        return success

    except FileNotFoundError:
        msg = f"Package manager '{pkg_manager}' not found on this system."
        log(msg, "error")
        if callback:
            callback(msg)
        return False

    except Exception as e:
        log(f"Install error for {tool_name}: {e}", "error")
        if callback:
            callback(f"Error: {e}")
        return False

DEFAULT_CONFIG = {
    "theme":        "mocha",
    "auto_update":  False,
    "log_level":    "info",
    "esim_path":    str(Path.home() / "eSim"),
    "check_on_start": True,
}


def load_config() -> dict:
    """Load config from disk, falling back to defaults."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                cfg = json.load(f)
            log("Config loaded from disk")
            return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            pass
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    """Persist config to disk."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    log("Config saved")

def read_log(n_lines: int = 100) -> list[str]:
    """Return the last n_lines from the log file."""
    if not LOG_PATH.exists():
        return ["No log file found yet."]
    try:
        with open(LOG_PATH) as f:
            lines = f.readlines()
        return [l.rstrip() for l in lines[-n_lines:]]
    except Exception as e:
        return [f"Could not read log: {e}"]