import webbrowser
import platform
from pathlib import Path
from datetime import datetime

from core import (
    detect_os, scan_tools, check_dependencies,
    check_esim_compatibility, ESIM_COMPATIBILITY,
    ESIM_RECOMMENDED, read_log, LOG_PATH, get_esim_roles
)
from theme import Mocha

REPORT_DIR  = Path.home() / ".esim_tool_manager"
REPORT_PATH = REPORT_DIR / "health_report.html"


VERDICT_COLOR = {
    "ok":           Mocha.GREEN,
    "warning":      Mocha.YELLOW,
    "incompatible": Mocha.RED,
    "missing":      Mocha.RED,
    "too_old":      Mocha.RED,
    "too_new":      Mocha.YELLOW,
    "compatible":   Mocha.GREEN,
}

VERDICT_LABEL = {
    "ok":           "✓  Compatible",
    "warning":      "⚠  Warning",
    "incompatible": "✗  Incompatible",
    "missing":      "✗  Missing",
    "too_old":      "✗  Too old",
    "too_new":      "⚠  Too new",
    "compatible":   "✓  Compatible",
}

OVERALL_BG = {
    "compatible":   "#1e3a2e",
    "warning":      "#3a2e1a",
    "incompatible": "#3a1e2a",
}

def _badge(text: str, color: str, bg: str = "#313244") -> str:
    return (
        f'<span style="background:{bg};color:{color};'
        f'padding:2px 10px;border-radius:20px;font-size:12px;'
        f'font-weight:700;letter-spacing:0.04em;font-family:monospace">'
        f'{text}</span>'
    )


def _pill_verdict(verdict: str) -> str:
    color = VERDICT_COLOR.get(verdict, Mocha.MUTED)
    label = VERDICT_LABEL.get(verdict, verdict)
    bg_map = {
        "ok": "#1e3a2e", "compatible": "#1e3a2e",
        "warning": "#3a2e1a", "too_new": "#3a2e1a",
        "incompatible": "#3a1e2a", "missing": "#3a1e2a", "too_old": "#3a1e2a",
    }
    bg = bg_map.get(verdict, "#313244")
    return _badge(label, color, bg)


def _tool_rows(compat_tools: list) -> str:
    rows = ""
    for t in compat_tools:
        crit = "●" if t["critical"] else "○"
        crit_color = Mocha.RED if t["critical"] else Mocha.OVERLAY0
        rows += f"""
        <tr>
          <td style="padding:10px 14px;color:{Mocha.TEXT};font-weight:600">{t['tool']}</td>
          <td style="padding:10px 14px;color:{Mocha.TEAL};font-family:monospace">{t['installed']}</td>
          <td style="padding:10px 14px;color:{Mocha.OVERLAY0};font-family:monospace">{t['min']} – {t['max']}</td>
          <td style="padding:10px 14px">{_pill_verdict(t['verdict'])}</td>
          <td style="padding:10px 14px;color:{Mocha.SUBTEXT0};font-size:13px">{t['note']}</td>
          <td style="padding:10px 14px;color:{crit_color};font-size:14px" title="{'Critical' if t['critical'] else 'Optional'}">{crit}</td>
        </tr>"""
    return rows


def _dep_rows(deps: list) -> str:
    rows = ""
    for d in deps:
        status = "present" if d["present"] else "absent"
        color  = Mocha.GREEN if d["present"] else Mocha.RED
        label  = "✓  Installed" if d["present"] else "✗  Missing"
        bg     = "#1e3a2e" if d["present"] else "#3a1e2a"
        fix    = "" if d["present"] else f'<code style="color:{Mocha.PEACH};font-size:12px">{d["fix"]}</code>'
        rows += f"""
        <tr>
          <td style="padding:10px 14px;color:{Mocha.TEXT};font-family:monospace">{d['name']}</td>
          <td style="padding:10px 14px">{_badge(label, color, bg)}</td>
          <td style="padding:10px 14px">{fix}</td>
        </tr>"""
    return rows


def _tool_scan_rows(tools: list) -> str:
    rows = ""
    for t in tools:
        color = {
            "ok":      Mocha.GREEN,
            "update":  Mocha.YELLOW,
            "missing": Mocha.RED,
            "unknown": Mocha.OVERLAY0,
        }.get(t["status"], Mocha.OVERLAY0)

        label = {
            "ok":      "✓  Up to date",
            "update":  "↑  Update available",
            "missing": "✗  Not installed",
            "unknown": "?  Unknown",
        }.get(t["status"], t["status"])

        bg = {
            "ok":      "#1e3a2e",
            "update":  "#3a2e1a",
            "missing": "#3a1e2a",
            "unknown": "#313244",
        }.get(t["status"], "#313244")

        component = t.get("esim_component", "—")
        comp_color = {
            "Schematic + PCB":       Mocha.BLUE,
            "Circuit Simulation":    Mocha.MAUVE,
            "HDL Simulation (NgVeri)": Mocha.TEAL,
            "System Modeling":       Mocha.PEACH,
        }.get(component, Mocha.OVERLAY0)

        rows += f"""
        <tr>
          <td style="padding:10px 14px;color:{Mocha.TEXT};font-weight:600">{t['name']}</td>
          <td style="padding:10px 14px">
            <span style="background:{Mocha.SURFACE0};color:{comp_color};
                  padding:2px 8px;border-radius:6px;font-size:11px;
                  font-family:monospace;font-weight:600">{component}</span>
          </td>
          <td style="padding:10px 14px;color:{Mocha.SUBTEXT0};font-size:13px">{t['desc']}</td>
          <td style="padding:10px 14px;color:{Mocha.TEAL};font-family:monospace">{t['version']}</td>
          <td style="padding:10px 14px;color:{Mocha.OVERLAY0};font-family:monospace">{t['latest']}</td>
          <td style="padding:10px 14px">{_badge(label, color, bg)}</td>
          <td style="padding:10px 14px;color:{Mocha.OVERLAY0};font-size:12px;font-family:monospace">{t['path']}</td>
        </tr>"""
    return rows


def _compat_section(esim_ver: str, report: dict) -> str:
    overall_color = VERDICT_COLOR.get(report["overall"], Mocha.MUTED)
    overall_label = VERDICT_LABEL.get(report["overall"], report["overall"])
    overall_bg    = OVERALL_BG.get(report["overall"], "#313244")

    py_color = Mocha.GREEN if report["python_ok"] else Mocha.RED
    py_label = "✓  Compatible" if report["python_ok"] else "✗  Too old"
    py_bg    = "#1e3a2e" if report["python_ok"] else "#3a1e2a"

    return f"""
    <div style="margin-bottom:32px">
      <div style="display:flex;align-items:center;gap:16px;margin-bottom:16px">
        <h2 style="color:{Mocha.LAVENDER};font-family:monospace;font-size:18px;margin:0">
          eSim v{esim_ver}
        </h2>
        <span style="background:{overall_bg};color:{overall_color};
              padding:4px 14px;border-radius:20px;font-size:13px;
              font-weight:700;font-family:monospace">{overall_label}</span>
        <span style="color:{Mocha.OVERLAY0};font-size:13px">{report['description']}</span>
      </div>

      <div style="background:{Mocha.SURFACE0};border-radius:8px;
                  padding:10px 16px;margin-bottom:16px;font-size:13px;
                  color:{Mocha.SUBTEXT0};font-family:monospace">
        {report['os_notes']}
      </div>

      <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">
        <div style="background:{Mocha.MANTLE};border-radius:8px;padding:10px 18px">
          <div style="color:{Mocha.OVERLAY0};font-size:11px;font-family:monospace;
                      text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px">Python required</div>
          <code style="color:{Mocha.TEAL};font-size:14px">&gt;= {report['python_min']}</code>
        </div>
        <div style="background:{Mocha.MANTLE};border-radius:8px;padding:10px 18px">
          <div style="color:{Mocha.OVERLAY0};font-size:11px;font-family:monospace;
                      text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px">Python installed</div>
          <code style="color:{py_color};font-size:14px">{report['python_inst']}</code>
          &nbsp;{_badge(py_label, py_color, py_bg)}
        </div>
      </div>

      <table style="width:100%;border-collapse:collapse;background:{Mocha.MANTLE};border-radius:10px;overflow:hidden">
        <thead>
          <tr style="border-bottom:1px solid {Mocha.SURFACE1}">
            <th style="padding:10px 14px;text-align:left;color:{Mocha.OVERLAY0};font-size:11px;
                       font-family:monospace;text-transform:uppercase;letter-spacing:0.06em">Tool</th>
            <th style="padding:10px 14px;text-align:left;color:{Mocha.OVERLAY0};font-size:11px;
                       font-family:monospace;text-transform:uppercase;letter-spacing:0.06em">Installed</th>
            <th style="padding:10px 14px;text-align:left;color:{Mocha.OVERLAY0};font-size:11px;
                       font-family:monospace;text-transform:uppercase;letter-spacing:0.06em">Supported range</th>
            <th style="padding:10px 14px;text-align:left;color:{Mocha.OVERLAY0};font-size:11px;
                       font-family:monospace;text-transform:uppercase;letter-spacing:0.06em">Status</th>
            <th style="padding:10px 14px;text-align:left;color:{Mocha.OVERLAY0};font-size:11px;
                       font-family:monospace;text-transform:uppercase;letter-spacing:0.06em">Note</th>
            <th style="padding:10px 14px;text-align:left;color:{Mocha.OVERLAY0};font-size:11px;
                       font-family:monospace;text-transform:uppercase;letter-spacing:0.06em"
                title="● Critical  ○ Optional">Crit</th>
          </tr>
        </thead>
        <tbody style="border-collapse:collapse">
          {_tool_rows(report['tools'])}
        </tbody>
      </table>
    </div>"""


def _role_card(role: dict) -> str:
    comp_color = {
        "Schematic + PCB":         Mocha.BLUE,
        "Circuit Simulation":      Mocha.MAUVE,
        "HDL Simulation (NgVeri)": Mocha.TEAL,
        "System Modeling":         Mocha.PEACH,
    }.get(role["component"], Mocha.OVERLAY0)

    return f"""
    <div style="background:{Mocha.SURFACE0};border-radius:10px;padding:16px">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
        <span style="font-size:15px;font-weight:700;color:{Mocha.TEXT};
                     font-family:monospace">{role['name']}</span>
        <span style="background:{Mocha.MANTLE};color:{comp_color};
                     padding:2px 8px;border-radius:6px;font-size:11px;
                     font-family:monospace;font-weight:600">{role['component']}</span>
      </div>
      <p style="color:{Mocha.SUBTEXT0};font-size:13px;line-height:1.6;margin:0">
        {role['role']}
      </p>
    </div>"""


def build_html(os_info: dict, tools: list, deps: list,
               compat_reports: dict, log_lines: list) -> str:
    """Assemble the full HTML report string."""

    now       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total     = len(tools)
    ok        = sum(1 for t in tools if t["status"] == "ok")
    updates   = sum(1 for t in tools if t["status"] == "update")
    missing   = sum(1 for t in tools if t["status"] == "missing")
    dep_ok    = sum(1 for d in deps if d["present"])
    dep_miss  = sum(1 for d in deps if not d["present"])

    stat_cards = f"""
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:32px">
        {_stat_card("Tools found",      str(total),   Mocha.LAVENDER)}
        {_stat_card("Up to date",       str(ok),      Mocha.GREEN)}
        {_stat_card("Updates available",str(updates),  Mocha.YELLOW if updates else Mocha.GREEN)}
        {_stat_card("Missing tools",    str(missing),  Mocha.RED if missing else Mocha.GREEN)}
      </div>"""

    compat_html = ""
    for ver, report in compat_reports.items():
        compat_html += _compat_section(ver, report)

    log_html = "\n".join(
        f'<div style="color:{_log_color(l)};padding:1px 0;font-size:12px">{l}</div>'
        for l in log_lines[-40:]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>eSim Tool Manager — Health Report</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: {Mocha.BASE};
      color: {Mocha.TEXT};
      font-family: 'Segoe UI', system-ui, sans-serif;
      font-size: 15px;
      line-height: 1.6;
      padding: 0;
    }}
    a {{ color: {Mocha.BLUE}; }}
    table {{ border-collapse: collapse; }}
    tbody tr {{ border-bottom: 1px solid {Mocha.SURFACE0}; }}
    tbody tr:last-child {{ border-bottom: none; }}
    code {{ font-family: 'Courier New', monospace; }}
    h1 {{ color: {Mocha.TEXT}; }}
    h2 {{ color: {Mocha.LAVENDER}; }}
    h3 {{ color: {Mocha.YELLOW}; font-family: monospace; font-size: 11px;
          text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 14px; }}
    .section {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 0 32px 40px;
    }}
    .card {{
      background: {Mocha.MANTLE};
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
    }}
  </style>
</head>
<body>

<!-- Header -->
<div style="background:{Mocha.MANTLE};border-bottom:1px solid {Mocha.SURFACE0};
            padding:24px 32px;margin-bottom:0">
  <div style="max-width:1100px;margin:0 auto;display:flex;
              align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
    <div style="display:flex;align-items:center;gap:14px">
      <div style="background:{Mocha.MAUVE};border-radius:10px;width:42px;height:42px;
                  display:flex;align-items:center;justify-content:center;
                  font-weight:700;color:{Mocha.CRUST};font-family:monospace;font-size:15px">eT</div>
      <div>
        <div style="font-size:20px;font-weight:700;color:{Mocha.TEXT};
                    font-family:monospace">eSim Tool Manager</div>
        <div style="font-size:13px;color:{Mocha.OVERLAY0}">System Health Report · {now}</div>
      </div>
    </div>
    <div style="text-align:right">
      <div style="color:{Mocha.SUBTEXT0};font-size:13px;font-family:monospace">
        {os_info.get('distro','—')}
      </div>
      <div style="color:{Mocha.OVERLAY0};font-size:12px;font-family:monospace">
        Python {os_info.get('python','—')} · {os_info.get('arch','—')} · pkg: {os_info.get('pkg_manager','—')}
      </div>
    </div>
  </div>
</div>

<!-- Overview stats -->
<div class="section" style="padding-top:32px">
  {stat_cards}

  <!-- eSim component roles -->
  <div class="card">
    <h3>eSim Component Roles</h3>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px">
      {"".join(_role_card(r) for r in get_esim_roles())}
    </div>
  </div>

  <!-- eSim Compatibility -->
  <div class="card">
    <h3>eSim Compatibility Matrix</h3>
    {compat_html}
  </div>

  <!-- Tool scan -->
  <div class="card">
    <h3>Installed Tools</h3>
    <table style="width:100%;background:{Mocha.MANTLE};border-radius:10px;overflow:hidden">
      <thead>
        <tr style="border-bottom:1px solid {Mocha.SURFACE1}">
          {"".join(f'<th style="padding:10px 14px;text-align:left;color:{Mocha.OVERLAY0};font-size:11px;font-family:monospace;text-transform:uppercase;letter-spacing:0.06em">{h}</th>' for h in ["Tool","eSim Component","Description","Version","Latest","Status","Path"])}
        </tr>
      </thead>
      <tbody>{_tool_scan_rows(tools)}</tbody>
    </table>
  </div>

  <!-- Dependencies -->
  <div class="card">
    <h3>Dependencies  &nbsp;
      <span style="font-weight:400;color:{Mocha.GREEN}">✓ {dep_ok} installed</span>
      {"&nbsp;" + f'<span style="font-weight:400;color:{Mocha.RED}">✗ {dep_miss} missing</span>' if dep_miss else ""}
    </h3>
    <table style="width:100%;background:{Mocha.MANTLE};border-radius:10px;overflow:hidden">
      <thead>
        <tr style="border-bottom:1px solid {Mocha.SURFACE1}">
          {"".join(f'<th style="padding:10px 14px;text-align:left;color:{Mocha.OVERLAY0};font-size:11px;font-family:monospace;text-transform:uppercase;letter-spacing:0.06em">{h}</th>' for h in ["Dependency","Status","Fix command"])}
        </tr>
      </thead>
      <tbody>{_dep_rows(deps)}</tbody>
    </table>
  </div>

  <!-- Log tail -->
  <div class="card">
    <h3>Recent Log &nbsp;
      <span style="color:{Mocha.OVERLAY0};font-size:11px;font-weight:400">{str(LOG_PATH)}</span>
    </h3>
    <div style="background:{Mocha.BASE};border-radius:8px;padding:16px;
                font-family:monospace;line-height:1.9;max-height:320px;overflow-y:auto">
      {log_html}
    </div>
  </div>

  <div style="text-align:center;color:{Mocha.OVERLAY0};font-size:12px;
              font-family:monospace;padding-bottom:32px">
    Generated by eSim Tool Manager v1.0.0 · Catppuccin Mocha · {now}
  </div>
</div>

</body>
</html>"""


def _stat_card(label: str, value: str, color: str) -> str:
    return f"""
    <div style="background:{Mocha.MANTLE};border-radius:10px;padding:14px 18px">
      <div style="color:{Mocha.OVERLAY0};font-size:11px;font-family:monospace;
                  text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px">{label}</div>
      <div style="font-size:28px;font-weight:700;color:{color};font-family:monospace">{value}</div>
    </div>"""


def _log_color(line: str) -> str:
    if "[ERROR]"   in line: return Mocha.RED
    if "[WARNING]" in line: return Mocha.YELLOW
    if "[INFO]"    in line: return Mocha.SUBTEXT0
    return Mocha.OVERLAY0


def generate_report(open_browser: bool = True) -> Path:
    """
    Run all checks, build the HTML report, save it, and optionally open it.
    Returns the path to the saved report.
    """
    os_info = detect_os()
    tools   = scan_tools()
    deps    = check_dependencies()
    logs    = read_log(100)

    # compatibility check 
    compat_reports = {}
    for ver in ESIM_COMPATIBILITY:
        compat_reports[ver] = check_esim_compatibility(ver, tools)

    html = build_html(os_info, tools, deps, compat_reports, logs)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(html, encoding="utf-8")

    if open_browser:
        webbrowser.open(REPORT_PATH.as_uri())

    return REPORT_PATH