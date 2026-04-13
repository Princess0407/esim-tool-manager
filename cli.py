import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner
from rich.columns import Columns
from rich import box

from theme import Mocha
from core import (
    detect_os, scan_tools, check_dependencies,
    install_tool, load_config, read_log,
    check_esim_compatibility, ESIM_COMPATIBILITY, ESIM_RECOMMENDED
)

console = Console()

def ctp(color: str) -> str:
    """Return a rich markup color string for Catppuccin Mocha."""
    palette = {
        "text":      Mocha.TEXT,
        "subtext":   Mocha.SUBTEXT0,
        "muted":     Mocha.OVERLAY0,
        "mauve":     Mocha.MAUVE,
        "lavender":  Mocha.LAVENDER,
        "blue":      Mocha.BLUE,
        "teal":      Mocha.TEAL,
        "green":     Mocha.GREEN,
        "yellow":    Mocha.YELLOW,
        "peach":     Mocha.PEACH,
        "red":       Mocha.RED,
        "maroon":    Mocha.MAROON,
        "surface":   Mocha.SURFACE0,
        "base":      Mocha.BASE,
    }
    return palette.get(color, color)


def status_style(status: str):
    """Return (symbol, color) for a tool/dep status."""
    return {
        "ok":      ("✓ ok",      ctp("green")),
        "update":  ("↑ update",  ctp("yellow")),
        "missing": ("✗ missing", ctp("red")),
        "unknown": ("? unknown", ctp("muted")),
        "present": ("✓",         ctp("green")),
        "absent":  ("✗",         ctp("red")),
    }.get(status, (status, ctp("muted")))


BANNER = f"""[{ctp('mauve')} bold]
  ███████╗███████╗██╗███╗   ███╗    
  ██╔════╝██╔════╝██║████╗ ████║       
  █████╗  ███████╗██║██╔████╔██║       
  ██╔══╝  ╚════██║██║██║╚██╔╝██║       
  ███████╗███████║██║██║ ╚═╝ ██║       
  ╚══════╝╚══════╝╚═╝╚═╝     ╚═╝    [/]
[{ctp('lavender')}]  eSim Tool Manager[/]  [{ctp('muted')}]v1.0.0  ·  Automated EDA Tool Management[/]"""


def print_banner(os_info: dict):
    console.print(BANNER)
    console.print(
        f"  [{ctp('muted')}]OS:[/] [{ctp('teal')}]{os_info.get('distro','—')}[/]  "
        f"[{ctp('muted')}]Python:[/] [{ctp('teal')}]{os_info.get('python','—')}[/]  "
        f"[{ctp('muted')}]pkg:[/] [{ctp('teal')}]{os_info.get('pkg_manager','—')}[/]"
    )
    console.rule(style=Style(color=Mocha.SURFACE1))

# Tools
def print_tools_table(tools: list):
    table = Table(
        box=box.SIMPLE_HEAD,
        border_style=Style(color=Mocha.SURFACE1),
        header_style=Style(color=Mocha.OVERLAY0, bold=True),
        show_edge=False,
        padding=(0, 1),
    )
    table.add_column("Tool",    style=Style(color=Mocha.TEXT, bold=True), width=16)
    table.add_column("Version", style=Style(color=Mocha.TEAL), width=10)
    table.add_column("Latest",  style=Style(color=Mocha.OVERLAY0), width=10)
    table.add_column("Status",  width=14)
    table.add_column("Path",    style=Style(color=Mocha.OVERLAY0))

    for t in tools:
        sym, col = status_style(t["status"])
        path = t["path"] if len(t["path"]) < 40 else "…" + t["path"][-38:]
        table.add_row(
            t["name"],
            t["version"],
            t["latest"],
            Text(sym, style=Style(color=col, bold=True)),
            path,
        )

    console.print(Panel(table, title=f"[{ctp('yellow')} bold] Installed Tools[/]",
                        border_style=Style(color=Mocha.SURFACE0), padding=(0, 1)))

def print_deps_table(deps: list):
    table = Table(
        box=box.SIMPLE_HEAD,
        border_style=Style(color=Mocha.SURFACE1),
        header_style=Style(color=Mocha.OVERLAY0, bold=True),
        show_edge=False,
        padding=(0, 1),
    )
    table.add_column("Dependency", style=Style(color=Mocha.TEXT, bold=True), width=18)
    table.add_column("Status", width=10)
    table.add_column("Fix command", style=Style(color=Mocha.PEACH))

    for d in deps:
        sym, col = status_style("present" if d["present"] else "absent")
        table.add_row(
            d["name"],
            Text(sym, style=Style(color=col, bold=True)),
            "" if d["present"] else d["fix"],
        )

    console.print(Panel(table, title=f"[{ctp('yellow')} bold] Dependency Check[/]",
                        border_style=Style(color=Mocha.SURFACE0), padding=(0, 1)))

def print_menu():
    items = [
        ("[1]", "Check dependencies"),
        ("[2]", "Scan installed tools"),
        ("[3]", "Install a tool"),
        ("[4]", "eSim compatibility check"),
        ("[5]", "Generate health report  (opens in browser)"),
        ("[6]", "View configuration"),
        ("[7]", "View action log"),
        ("[q]", "Quit"),
    ]
    console.print()
    for num, label in items:
        num_styled = f"[{ctp('mauve')} bold]{num}[/]"
        lbl_styled = f"[{ctp('text')}]{label}[/]"
        console.print(f"  {num_styled}  {lbl_styled}")
    console.print()

def run_scan():
    with console.status(f"[{ctp('lavender')}]Scanning tools…[/]", spinner="dots"):
        tools = scan_tools()
    print_tools_table(tools)
    return tools


def run_dep_check():
    with console.status(f"[{ctp('lavender')}]Checking dependencies…[/]", spinner="dots"):
        deps = check_dependencies()
    print_deps_table(deps)
    return deps


def run_install(tool_name: str, dry_run: bool = False):
    """Install a tool — asks for confirmation first, then streams output."""
    from core import get_install_command
    os_info = detect_os()
    pkg_mgr = os_info.get("pkg_manager", "apt")
    cmd     = get_install_command(tool_name, pkg_mgr)

    if not cmd:
        console.print(f"\n  [{ctp('red')}]✗ No install mapping for '{tool_name}' on '{pkg_mgr}'.[/]\n")
        return

    cmd_str = " ".join(cmd)

    console.print(f"\n  [{ctp('lavender')} bold]Install  {tool_name}[/]")
    console.print(f"  [{ctp('muted')}]This will run:[/]  [{ctp('peach')}]{cmd_str}[/]")
    if dry_run:
        console.print(f"  [{ctp('yellow')}][dry-run] Skipping actual execution.[/]\n")
        return

    console.print()
    confirm = Prompt.ask(
        f"  [{ctp('green')}]→[/] Proceed?",
        choices=["y", "n"],
        default="n",
        console=console,
    )

    if confirm != "y":
        console.print(f"  [{ctp('muted')}]Cancelled.[/]\n")
        return

    console.print()

    def stream(line):
        console.print(f"  [{ctp('muted')}]{line}[/]")

    ok = install_tool(tool_name, pkg_mgr, callback=stream)

    if ok:
        console.print(f"\n  [{ctp('green')} bold]✓[/] [{ctp('text')}]{tool_name} installed successfully.[/]\n")
    else:
        console.print(f"\n  [{ctp('red')} bold]✗[/] [{ctp('text')}]Installation failed. Check log for details.[/]\n")


def run_config():
    cfg = load_config()
    table = Table(box=box.SIMPLE_HEAD, show_edge=False,
                  border_style=Style(color=Mocha.SURFACE1),
                  header_style=Style(color=Mocha.OVERLAY0, bold=True))
    table.add_column("Key",   style=Style(color=Mocha.SUBTEXT0), width=22)
    table.add_column("Value", style=Style(color=Mocha.TEAL))
    for k, v in cfg.items():
        table.add_row(k, str(v))
    console.print(Panel(table, title=f"[{ctp('yellow')} bold] Configuration[/]",
                        border_style=Style(color=Mocha.SURFACE0)))


def run_log():
    lines = read_log(50)
    content = Text()
    for line in lines:
        if "[ERROR]" in line:
            content.append(line + "\n", style=Style(color=Mocha.RED))
        elif "[WARNING]" in line:
            content.append(line + "\n", style=Style(color=Mocha.YELLOW))
        elif "[INFO]" in line:
            content.append(line + "\n", style=Style(color=Mocha.SUBTEXT0))
        else:
            content.append(line + "\n", style=Style(color=Mocha.OVERLAY0))
    console.print(Panel(content, title=f"[{ctp('yellow')} bold] Action Log[/]",
                        border_style=Style(color=Mocha.SURFACE0)))

def print_compat_table(report: dict):
    """Print a rich-formatted eSim compatibility report."""
    esim_ver = report["esim_version"]
    overall  = report["overall"]

    overall_color = {
        "compatible":   ctp("green"),
        "warning":      ctp("yellow"),
        "incompatible": ctp("red"),
    }.get(overall, ctp("muted"))

    overall_label = {
        "compatible":   "✓ Compatible",
        "warning":      "⚠ Warnings present",
        "incompatible": "✗ Incompatible",
    }.get(overall, overall)

    console.print(
        f"\n  [{ctp('lavender')} bold]eSim v{esim_ver}[/]  "
        f"[{overall_color} bold]{overall_label}[/]  "
        f"[{ctp('muted')}]{report['description']}[/]"
    )

    py_ok    = report["python_ok"]
    py_color = ctp("green") if py_ok else ctp("red")
    console.print(
        f"  [{ctp('muted')}]Python required:[/] [{ctp('teal')}]>= {report['python_min']}[/]  "
        f"[{ctp('muted')}]installed:[/] [{py_color}]{report['python_inst']}[/]"
    )
    console.print()

    table = Table(
        box=box.SIMPLE_HEAD,
        border_style=Style(color=Mocha.SURFACE1),
        header_style=Style(color=Mocha.OVERLAY0, bold=True),
        show_edge=False,
        padding=(0, 1),
    )
    table.add_column("Tool",      style=Style(color=Mocha.TEXT, bold=True), width=16)
    table.add_column("Installed", style=Style(color=Mocha.TEAL), width=10)
    table.add_column("Range",     style=Style(color=Mocha.OVERLAY0), width=14)
    table.add_column("Status",    width=20)
    table.add_column("Note",      style=Style(color=Mocha.SUBTEXT0))
    table.add_column("Crit",      width=6)

    verdict_style = {
        "ok":           (Mocha.GREEN,  "✓ ok"),
        "warning":      (Mocha.YELLOW, "⚠ warning"),
        "incompatible": (Mocha.RED,    "✗ incompatible"),
        "missing":      (Mocha.RED,    "✗ missing"),
        "too_old":      (Mocha.RED,    "✗ too old"),
        "too_new":      (Mocha.YELLOW, "⚠ too new"),
    }

    for t in report["tools"]:
        col, sym = verdict_style.get(t["verdict"], (Mocha.MUTED, t["verdict"]))
        crit_sym = Text("●", style=Style(color=Mocha.RED)) if t["critical"] else Text("○", style=Style(color=Mocha.OVERLAY0))
        table.add_row(
            t["tool"],
            t["installed"],
            f"{t['min']} – {t['max']}",
            Text(sym, style=Style(color=col, bold=True)),
            t["note"],
            crit_sym,
        )

    console.print(Panel(
        table,
        title=f"[{ctp('yellow')} bold] eSim v{esim_ver} — Tool Compatibility[/]",
        border_style=Style(color=Mocha.SURFACE0),
        padding=(0, 1),
    ))


def run_compat_check(esim_version: str = None):
    """Run eSim compatibility check for a specific or all versions."""
    if esim_version and esim_version not in ESIM_COMPATIBILITY:
        console.print(f"  [{ctp('red')}]Unknown eSim version: {esim_version}[/]")
        console.print(f"  [{ctp('muted')}]Known versions: {', '.join(ESIM_COMPATIBILITY.keys())}[/]")
        return

    with console.status(f"[{ctp('lavender')}]Scanning tools for compatibility check…[/]", spinner="dots"):
        tools = scan_tools()

    versions = [esim_version] if esim_version else list(ESIM_COMPATIBILITY.keys())
    for ver in versions:
        report = check_esim_compatibility(ver, tools)
        print_compat_table(report)


def run_health_report():
    """Generate and open the HTML health report."""
    console.print(f"\n  [{ctp('lavender')}]Generating health report…[/]")
    from health_report import generate_report
    path = generate_report(open_browser=True)
    console.print(f"  [{ctp('green')} bold]✓[/] [{ctp('text')}]Report saved → [{ctp('teal')}]{path}[/][/]")
    console.print(f"  [{ctp('muted')}]Opening in your browser…[/]\n")

def run_interactive():
    console.clear()
    os_info = detect_os()
    print_banner(os_info)
    with console.status(f"[{ctp('lavender')}]Scanning tools…[/]", spinner="dots"):
        tools = scan_tools()
    print_tools_table(tools)

    while True:
        print_menu()
        choice = Prompt.ask(
            f"  [{ctp('green')}]→[/] Enter choice",
            console=console,
            default="1",
        ).strip().lower()

        console.print()

        if choice == "1":
            run_dep_check()

        elif choice == "2":
            tools = run_scan()

        elif choice == "3":
            tool_names = [t["name"] for t in tools]
            console.print(f"  [{ctp('muted')}]Available tools:[/] [{ctp('text')}]{', '.join(tool_names)}[/]")
            name = Prompt.ask(f"  [{ctp('green')}]→[/] Tool name", console=console).strip()
            if name in tool_names:
                run_install(name)
            else:
                console.print(f"  [{ctp('red')}]Unknown tool: {name}[/]")

        elif choice == "4":
            versions = list(ESIM_COMPATIBILITY.keys())
            console.print(f"  [{ctp('muted')}]Known eSim versions:[/] [{ctp('text')}]{', '.join(versions)}[/]")
            ver = Prompt.ask(
                f"  [{ctp('green')}]→[/] eSim version (or 'all')",
                console=console,
                default=ESIM_RECOMMENDED,
            ).strip()
            run_compat_check(None if ver == "all" else ver)

        elif choice == "5":
            run_health_report()

        elif choice == "6":
            run_config()

        elif choice == "7":
            run_log()

        elif choice in ("q", "quit", "exit"):
            console.print(f"\n  [{ctp('mauve')}]Goodbye!![/]\n")
            sys.exit(0)

        else:
            console.print(f"  [{ctp('red')}]Unknown option. Try 1–7 or q.[/]")

        console.rule(style=Style(color=Mocha.SURFACE0))