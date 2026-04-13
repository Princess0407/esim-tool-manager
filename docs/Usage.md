# Usage Guide — eSim Tool Manager

## First Run Workflow

```bash
# 1. Check what's installed and what's broken
python3 main.py --scan

# 2. Check system dependencies
python3 main.py --check

# 3. Validate against your target eSim version
python3 main.py --compat 2.5

# 4. Generate a full health report
python3 main.py --report

# 5. Install anything missing (cache sudo first)
sudo echo "sudo ready" && python3 main.py --gui
```

## Using the GUI

```bash
# Launch the graphical dashboard
python3 main.py --gui
```

In the GUI:
- **Dashboard** — overview of your system at a glance
- **Tools** — click Install on any missing tool, Update on outdated ones
- **Dependencies** — see what system packages are missing and how to fix them
- **Compat** — select eSim 2.3 / 2.4 / 2.5, click Check, see exactly what needs fixing
- **Config** — edit settings, toggle auto-check on startup
- **Log** — full history of every action

## Safe Testing (no installs)

```bash
# See what would happen without doing anything
python3 main.py --install Ngspice --dry-run
python3 main.py --install KiCad --dry-run
```

## Scripting / CI

```bash
# Scan and exit — useful in scripts
python3 main.py --scan
python3 main.py --check
python3 main.py --compat 2.5

# Generate report silently and check the file
python3 main.py --report
cat ~/.esim_tool_manager/health_report.html
```

## Install with sudo cached

```bash
# Cache sudo password, then launch GUI for installs
sudo echo "cached" && python3 main.py --gui
```

## View logs

```bash
cat ~/.esim_tool_manager/manager.log
# or inside the tool:
python3 main.py
# → select [7] View action log
```