# pip install customtkinker

import customtkinter as ctk
import threading
import subprocess
from datetime import datetime
from pathlib import Path

from theme import Mocha
from core import (
    detect_os, scan_tools, check_dependencies,
    install_tool, load_config, save_config,
    read_log, LOG_PATH
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

FONT_MONO  = (Mocha.FONT_MONO, 13)
FONT_MONO_SM = (Mocha.FONT_MONO, 11)
FONT_MONO_LG = (Mocha.FONT_MONO, 15, "bold")
FONT_UI    = (Mocha.FONT_UI, 13)
FONT_UI_SM = (Mocha.FONT_UI, 11)
FONT_HEADING = (Mocha.FONT_MONO, 11, "bold")


class Badge(ctk.CTkLabel):
    STATUS_MAP = {
        "ok":      (Mocha.OK,   Mocha.OK_BG,   "✓  ok"),
        "update":  (Mocha.WARN, Mocha.WARN_BG,  "↑  update"),
        "missing": (Mocha.RED,  Mocha.ERR_BG,   "✗  missing"),
        "unknown": (Mocha.MUTED,Mocha.SURFACE0,  "?  unknown"),
        "present": (Mocha.OK,   Mocha.OK_BG,    "✓"),
        "absent":  (Mocha.RED,  Mocha.ERR_BG,   "✗"),
    }

    def __init__(self, master, status: str, **kwargs):
        color, bg, label = self.STATUS_MAP.get(status, (Mocha.MUTED, Mocha.SURFACE0, status))
        super().__init__(
            master,
            text=label,
            text_color=color,
            fg_color=bg,
            corner_radius=6,
            font=FONT_MONO_SM,
            padx=8, pady=2,
            **kwargs
        )

class SectionHeader(ctk.CTkLabel):
    def __init__(self, master, text: str, **kwargs):
        super().__init__(
            master,
            text=text.upper(),
            text_color=Mocha.OVERLAY0,
            font=FONT_HEADING,
            anchor="w",
            **kwargs
        )

class Divider(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, height=1, fg_color=Mocha.SURFACE0, **kwargs)
        self.pack(fill="x", pady=(6, 10))


class NavButton(ctk.CTkButton):
    def __init__(self, master, text, icon, command, **kwargs):
        super().__init__(
            master,
            text=f"  {icon}  {text}",
            command=command,
            fg_color="transparent",
            text_color=Mocha.SUBTEXT0,
            hover_color=Mocha.SURFACE0,
            anchor="w",
            font=FONT_MONO,
            height=38,
            corner_radius=8,
            **kwargs
        )
        self._text = text

    def set_active(self, active: bool):
        if active:
            self.configure(fg_color=Mocha.SURFACE0, text_color=Mocha.LAVENDER)
        else:
            self.configure(fg_color="transparent", text_color=Mocha.SUBTEXT0)


class StatCard(ctk.CTkFrame):
    def __init__(self, master, label: str, value: str, color: str = Mocha.LAVENDER, **kwargs):
        super().__init__(master, fg_color=Mocha.MANTLE, corner_radius=10, **kwargs)
        ctk.CTkLabel(self, text=label.upper(), text_color=Mocha.OVERLAY0,
                     font=FONT_HEADING, anchor="w").pack(anchor="w", padx=14, pady=(12, 2))
        self._val_label = ctk.CTkLabel(self, text=value, text_color=color,
                                        font=(Mocha.FONT_MONO, 26, "bold"), anchor="w")
        self._val_label.pack(anchor="w", padx=14, pady=(0, 12))

    def update_value(self, value: str, color: str = None):
        kwargs = {"text": value}
        if color:
            kwargs["text_color"] = color
        self._val_label.configure(**kwargs)


class DashboardPanel(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._build()

    def _build(self):

        ctk.CTkLabel(self, text="Dashboard", text_color=Mocha.TEXT,
                     font=FONT_MONO_LG, anchor="w").pack(fill="x", pady=(0, 16))

        # Stat cards row
        self.stat_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stat_frame.pack(fill="x", pady=(0, 20))
        self.stat_frame.grid_columnconfigure((0,1,2,3), weight=1)

        self.card_total   = StatCard(self.stat_frame, "Tools",     "—", Mocha.LAVENDER)
        self.card_ok      = StatCard(self.stat_frame, "Up to date","—", Mocha.GREEN)
        self.card_updates = StatCard(self.stat_frame, "Updates",   "—", Mocha.YELLOW)
        self.card_missing = StatCard(self.stat_frame, "Missing",   "—", Mocha.RED)

        for i, card in enumerate([self.card_total, self.card_ok, self.card_updates, self.card_missing]):
            card.grid(row=0, column=i, padx=(0, 10) if i < 3 else 0, sticky="ew")

        SectionHeader(self, "System").pack(fill="x", pady=(0, 8))
        self.sys_frame = ctk.CTkFrame(self, fg_color=Mocha.MANTLE, corner_radius=10)
        self.sys_frame.pack(fill="x", pady=(0, 20))

        self.sys_labels = {}
        for key in ["OS", "Python", "Arch", "Package Manager", "Config", "Log"]:
            row = ctk.CTkFrame(self.sys_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(row, text=key, text_color=Mocha.OVERLAY0,
                         font=FONT_MONO_SM, width=140, anchor="w").pack(side="left")
            lbl = ctk.CTkLabel(row, text="—", text_color=Mocha.TEXT,
                               font=FONT_MONO_SM, anchor="w")
            lbl.pack(side="left")
            self.sys_labels[key] = lbl

        SectionHeader(self, "Recent activity").pack(fill="x", pady=(0, 8))
        self.log_box = ctk.CTkTextbox(
            self, height=160, fg_color=Mocha.MANTLE,
            text_color=Mocha.SUBTEXT0, font=FONT_MONO_SM,
            corner_radius=10, border_width=0
        )
        self.log_box.pack(fill="x")
        self.log_box.configure(state="disabled")

    def refresh(self, os_info: dict, tools: list):
        total   = len(tools)
        ok      = sum(1 for t in tools if t["status"] == "ok")
        updates = sum(1 for t in tools if t["status"] == "update")
        missing = sum(1 for t in tools if t["status"] == "missing")

        self.card_total.update_value(str(total))
        self.card_ok.update_value(str(ok))
        self.card_updates.update_value(str(updates), Mocha.YELLOW if updates else Mocha.GREEN)
        self.card_missing.update_value(str(missing), Mocha.RED if missing else Mocha.GREEN)

        self.sys_labels["OS"].configure(text=os_info.get("distro", "—"))
        self.sys_labels["Python"].configure(text=os_info.get("python", "—"))
        self.sys_labels["Arch"].configure(text=os_info.get("arch", "—"))
        self.sys_labels["Package Manager"].configure(text=os_info.get("pkg_manager", "—"))
        self.sys_labels["Config"].configure(text=str(Path.home() / ".esim_tool_manager" / "config.json"))
        self.sys_labels["Log"].configure(text=str(LOG_PATH))

        lines = read_log(20)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        for line in lines[-8:]:
            self.log_box.insert("end", line + "\n")
        self.log_box.configure(state="disabled")
        self.log_box.see("end")


class ToolsPanel(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._rows = []
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text="Tools", text_color=Mocha.TEXT,
                     font=FONT_MONO_LG, anchor="w").pack(side="left")
        ctk.CTkButton(header, text="↺  Refresh", command=self.app.run_scan,
                      fg_color=Mocha.SURFACE0, text_color=Mocha.LAVENDER,
                      hover_color=Mocha.SURFACE1, font=FONT_MONO_SM,
                      corner_radius=8, height=30, width=100).pack(side="right")
        
        col_hdr = ctk.CTkFrame(self, fg_color="transparent")
        col_hdr.pack(fill="x", padx=16, pady=(0, 6))
        for text, width in [("Tool", 140), ("Version", 90), ("Latest", 90), ("Status", 110), ("Path", 0), ("", 90)]:
            ctk.CTkLabel(col_hdr, text=text.upper(), text_color=Mocha.OVERLAY0,
                         font=FONT_HEADING, width=width, anchor="w").pack(side="left")

        Divider(self)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.scroll.pack(fill="both", expand=True)

    def refresh(self, tools: list, pkg_manager: str):
        for w in self.scroll.winfo_children():
            w.destroy()

        for tool in tools:
            row = ctk.CTkFrame(self.scroll, fg_color=Mocha.MANTLE, corner_radius=10)
            row.pack(fill="x", pady=4)

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=10)

            # Name + desc
            name_col = ctk.CTkFrame(inner, fg_color="transparent", width=140)
            name_col.pack(side="left")
            name_col.pack_propagate(False)
            ctk.CTkLabel(name_col, text=tool["name"], text_color=Mocha.TEXT,
                         font=FONT_MONO, anchor="w").pack(anchor="w")
            ctk.CTkLabel(name_col, text=tool["desc"], text_color=Mocha.OVERLAY0,
                         font=FONT_MONO_SM, anchor="w").pack(anchor="w")

            ctk.CTkLabel(inner, text=tool["version"], text_color=Mocha.TEAL,
                         font=FONT_MONO_SM, width=90, anchor="w").pack(side="left")
            ctk.CTkLabel(inner, text=tool["latest"], text_color=Mocha.OVERLAY0,
                         font=FONT_MONO_SM, width=90, anchor="w").pack(side="left")

            Badge(inner, tool["status"]).pack(side="left", padx=(0, 12))

            path_text = tool["path"] if len(tool["path"]) < 28 else "…" + tool["path"][-26:]
            ctk.CTkLabel(inner, text=path_text, text_color=Mocha.OVERLAY0,
                         font=FONT_MONO_SM, anchor="w").pack(side="left", expand=True, fill="x")

            if tool["status"] == "missing":
                btn = ctk.CTkButton(
                    inner, text="Install",
                    command=lambda t=tool["name"]: self.app.install_tool(t),
                    fg_color=Mocha.MAUVE, text_color=Mocha.CRUST,
                    hover_color=Mocha.LAVENDER, font=FONT_MONO_SM,
                    corner_radius=8, height=28, width=80
                )
            elif tool["status"] == "update":
                btn = ctk.CTkButton(
                    inner, text="Update",
                    command=lambda t=tool["name"]: self.app.install_tool(t),
                    fg_color=Mocha.YELLOW, text_color=Mocha.CRUST,
                    hover_color=Mocha.PEACH, font=FONT_MONO_SM,
                    corner_radius=8, height=28, width=80
                )
            else:
                btn = ctk.CTkButton(
                    inner, text="Info",
                    command=lambda t=tool["name"]: self.app.show_tool_info(t),
                    fg_color=Mocha.SURFACE0, text_color=Mocha.SUBTEXT0,
                    hover_color=Mocha.SURFACE1, font=FONT_MONO_SM,
                    corner_radius=8, height=28, width=80
                )
            btn.pack(side="right")


class DepsPanel(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text="Dependencies", text_color=Mocha.TEXT,
                     font=FONT_MONO_LG, anchor="w").pack(side="left")
        ctk.CTkButton(header, text="↺  Check", command=self.app.run_dep_check,
                      fg_color=Mocha.SURFACE0, text_color=Mocha.LAVENDER,
                      hover_color=Mocha.SURFACE1, font=FONT_MONO_SM,
                      corner_radius=8, height=30, width=100).pack(side="right")

        col_hdr = ctk.CTkFrame(self, fg_color="transparent")
        col_hdr.pack(fill="x", padx=16, pady=(0, 6))
        for text, width in [("Dependency", 160), ("Status", 90), ("Fix command", 0)]:
            ctk.CTkLabel(col_hdr, text=text.upper(), text_color=Mocha.OVERLAY0,
                         font=FONT_HEADING, width=width, anchor="w").pack(side="left")

        Divider(self)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.scroll.pack(fill="both", expand=True)

    def refresh(self, deps: list):
        for w in self.scroll.winfo_children():
            w.destroy()

        for dep in deps:
            row = ctk.CTkFrame(self.scroll, fg_color=Mocha.MANTLE, corner_radius=10)
            row.pack(fill="x", pady=4)
            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=10)

            ctk.CTkLabel(inner, text=dep["name"], text_color=Mocha.TEXT,
                         font=FONT_MONO, width=160, anchor="w").pack(side="left")
            Badge(inner, "present" if dep["present"] else "absent").pack(side="left", padx=(0, 16))

            if not dep["present"]:
                ctk.CTkLabel(inner, text=dep["fix"], text_color=Mocha.PEACH,
                             font=FONT_MONO_SM, anchor="w").pack(side="left")
            else:
                ctk.CTkLabel(inner, text="installed", text_color=Mocha.OVERLAY0,
                             font=FONT_MONO_SM, anchor="w").pack(side="left")


class ConfigPanel(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._entries = {}
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Configuration", text_color=Mocha.TEXT,
                     font=FONT_MONO_LG, anchor="w").pack(fill="x", pady=(0, 20))

        cfg = self.app.config
        fields = [
            ("esim_path",    "eSim installation path", cfg.get("esim_path", "")),
            ("log_level",    "Log level (info/debug/warning)", cfg.get("log_level", "info")),
        ]

        for key, label, value in fields:
            frame = ctk.CTkFrame(self, fg_color=Mocha.MANTLE, corner_radius=10)
            frame.pack(fill="x", pady=6)
            ctk.CTkLabel(frame, text=label, text_color=Mocha.SUBTEXT0,
                         font=FONT_MONO_SM, anchor="w").pack(anchor="w", padx=16, pady=(10, 4))
            entry = ctk.CTkEntry(frame, fg_color=Mocha.SURFACE0,
                                 text_color=Mocha.TEXT, border_color=Mocha.SURFACE1,
                                 font=FONT_MONO_SM, height=34)
            entry.insert(0, value)
            entry.pack(fill="x", padx=16, pady=(0, 12))
            self._entries[key] = entry

        toggle_frame = ctk.CTkFrame(self, fg_color=Mocha.MANTLE, corner_radius=10)
        toggle_frame.pack(fill="x", pady=6)

        self._auto_var = ctk.BooleanVar(value=cfg.get("auto_update", False))
        self._start_var = ctk.BooleanVar(value=cfg.get("check_on_start", True))

        for label, var in [
            ("Auto-update tools on startup", self._auto_var),
            ("Check dependencies on startup", self._start_var),
        ]:
            row = ctk.CTkFrame(toggle_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=8)
            ctk.CTkLabel(row, text=label, text_color=Mocha.TEXT,
                         font=FONT_MONO_SM, anchor="w").pack(side="left")
            ctk.CTkSwitch(row, variable=var, text="",
                          progress_color=Mocha.MAUVE,
                          button_color=Mocha.LAVENDER).pack(side="right")

        ctk.CTkButton(self, text="Save configuration",
                      command=self._save,
                      fg_color=Mocha.MAUVE, text_color=Mocha.CRUST,
                      hover_color=Mocha.LAVENDER, font=FONT_MONO,
                      corner_radius=10, height=40).pack(fill="x", pady=(20, 0))

    def _save(self):
        cfg = self.app.config.copy()
        for key, entry in self._entries.items():
            cfg[key] = entry.get()
        cfg["auto_update"]    = self._auto_var.get()
        cfg["check_on_start"] = self._start_var.get()
        save_config(cfg)
        self.app.config = cfg
        self.app.show_toast("Configuration saved!")


class LogPanel(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text="Action Log", text_color=Mocha.TEXT,
                     font=FONT_MONO_LG, anchor="w").pack(side="left")
        ctk.CTkButton(header, text="↺  Refresh", command=self.refresh,
                      fg_color=Mocha.SURFACE0, text_color=Mocha.LAVENDER,
                      hover_color=Mocha.SURFACE1, font=FONT_MONO_SM,
                      corner_radius=8, height=30, width=100).pack(side="right")

        self.log_box = ctk.CTkTextbox(
            self, fg_color=Mocha.MANTLE,
            text_color=Mocha.SUBTEXT0, font=FONT_MONO_SM,
            corner_radius=10, border_width=0, wrap="none"
        )
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

        ctk.CTkLabel(self, text=str(LOG_PATH), text_color=Mocha.OVERLAY0,
                     font=FONT_MONO_SM, anchor="w").pack(anchor="w", pady=(6, 0))

    def refresh(self):
        lines = read_log(200)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        for line in lines:
            self.log_box.insert("end", line + "\n")
        self.log_box.configure(state="disabled")
        self.log_box.see("end")


class CompatPanel(ctk.CTkFrame):
    """eSim-specific compatibility checker panel."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._build()

    def _build(self):
 
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text="eSim Compatibility", text_color=Mocha.TEXT,
                     font=FONT_MONO_LG, anchor="w").pack(side="left")

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")

        ctk.CTkButton(btn_frame, text="↺  Check",
                      command=self._run_check,
                      fg_color=Mocha.SURFACE0, text_color=Mocha.LAVENDER,
                      hover_color=Mocha.SURFACE1, font=FONT_MONO_SM,
                      corner_radius=8, height=30, width=90).pack(side="left", padx=(0, 8))

        ctk.CTkButton(btn_frame, text="⬇  Health Report",
                      command=self._open_report,
                      fg_color=Mocha.MAUVE, text_color=Mocha.CRUST,
                      hover_color=Mocha.LAVENDER, font=FONT_MONO_SM,
                      corner_radius=8, height=30, width=140).pack(side="left")

        sel_frame = ctk.CTkFrame(self, fg_color=Mocha.MANTLE, corner_radius=10)
        sel_frame.pack(fill="x", pady=(0, 16))
        inner = ctk.CTkFrame(sel_frame, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(inner, text="Target eSim version:", text_color=Mocha.SUBTEXT0,
                     font=FONT_MONO_SM).pack(side="left", padx=(0, 12))

        from core import ESIM_COMPATIBILITY, ESIM_RECOMMENDED
        self._ver_var = ctk.StringVar(value=ESIM_RECOMMENDED)
        for ver in ESIM_COMPATIBILITY:
            ctk.CTkRadioButton(
                inner, text=f"v{ver}",
                variable=self._ver_var, value=ver,
                text_color=Mocha.TEXT, font=FONT_MONO_SM,
                fg_color=Mocha.MAUVE, hover_color=Mocha.LAVENDER,
            ).pack(side="left", padx=10)

        self._verdict_frame = ctk.CTkFrame(self, fg_color=Mocha.SURFACE0, corner_radius=10)
        self._verdict_frame.pack(fill="x", pady=(0, 16))
        self._verdict_lbl = ctk.CTkLabel(
            self._verdict_frame,
            text="Select a version and press Check",
            text_color=Mocha.OVERLAY0, font=FONT_MONO,
        )
        self._verdict_lbl.pack(pady=14)

        Divider(self)
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.scroll.pack(fill="both", expand=True)

    def _run_check(self):
        ver = self._ver_var.get()
        self.app._set_status(f"Checking eSim {ver} compatibility…")
        import threading
        threading.Thread(target=self._do_check, args=(ver,), daemon=True).start()

    def _do_check(self, ver: str):
        from core import check_esim_compatibility
        tools  = self.app.tools or []
        report = check_esim_compatibility(ver, tools)
        self.after(0, lambda: self._render(report))

    def _render(self, report: dict):
        overall = report.get("overall", "unknown")
        colors  = {"compatible": Mocha.GREEN, "warning": Mocha.YELLOW,
                   "incompatible": Mocha.RED}
        labels  = {"compatible": "✓  Compatible",
                   "warning":    "⚠  Some warnings — check tool versions",
                   "incompatible": "✗  Incompatible — critical tools missing or wrong version"}
        color = colors.get(overall, Mocha.MUTED)
        label = labels.get(overall, overall)

        self._verdict_frame.configure(
            fg_color={"compatible": Mocha.OK_BG,
                      "warning": Mocha.WARN_BG,
                      "incompatible": Mocha.ERR_BG}.get(overall, Mocha.SURFACE0)
        )
        self._verdict_lbl.configure(text=label, text_color=color)

        for w in self.scroll.winfo_children():
            w.destroy()

        py_row = ctk.CTkFrame(self.scroll, fg_color=Mocha.MANTLE, corner_radius=10)
        py_row.pack(fill="x", pady=4)
        pr = ctk.CTkFrame(py_row, fg_color="transparent")
        pr.pack(fill="x", padx=14, pady=10)
        ctk.CTkLabel(pr, text="Python", text_color=Mocha.TEXT,
                     font=FONT_MONO, width=140, anchor="w").pack(side="left")
        ctk.CTkLabel(pr, text=report["python_inst"], text_color=Mocha.TEAL,
                     font=FONT_MONO_SM, width=90, anchor="w").pack(side="left")
        ctk.CTkLabel(pr, text=f">= {report['python_min']}", text_color=Mocha.OVERLAY0,
                     font=FONT_MONO_SM, width=90, anchor="w").pack(side="left")
        Badge(pr, "ok" if report["python_ok"] else "missing").pack(side="left", padx=(0, 12))
        note = "Compatible" if report["python_ok"] else f"Need Python >= {report['python_min']}"
        ctk.CTkLabel(pr, text=note, text_color=Mocha.SUBTEXT0,
                     font=FONT_MONO_SM, anchor="w").pack(side="left")

        for t in report.get("tools", []):
            row = ctk.CTkFrame(self.scroll, fg_color=Mocha.MANTLE, corner_radius=10)
            row.pack(fill="x", pady=4)
            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=10)

            crit_color = Mocha.RED if t["critical"] else Mocha.OVERLAY0
            ctk.CTkLabel(inner, text="●" if t["critical"] else "○",
                         text_color=crit_color, font=FONT_MONO_SM,
                         width=18, anchor="w").pack(side="left")
            ctk.CTkLabel(inner, text=t["tool"], text_color=Mocha.TEXT,
                         font=FONT_MONO, width=130, anchor="w").pack(side="left")
            ctk.CTkLabel(inner, text=t["installed"], text_color=Mocha.TEAL,
                         font=FONT_MONO_SM, width=90, anchor="w").pack(side="left")
            ctk.CTkLabel(inner, text=f"{t['min']} – {t['max']}",
                         text_color=Mocha.OVERLAY0, font=FONT_MONO_SM,
                         width=100, anchor="w").pack(side="left")
            Badge(inner, t["verdict"] if t["verdict"] in ("ok","missing") else
                  ("update" if t["verdict"] == "too_new" else "missing")).pack(side="left", padx=(0,12))
            ctk.CTkLabel(inner, text=t["note"], text_color=Mocha.SUBTEXT0,
                         font=FONT_MONO_SM, anchor="w").pack(side="left", expand=True, fill="x")

        self.app._set_status(
            f"eSim {report['esim_version']} compat: {overall}"
        )

    def _open_report(self):
        self.app._set_status("Generating health report…")
        import threading
        def run():
            from health_report import generate_report
            path = generate_report(open_browser=True)
            self.after(0, lambda: self.app.show_toast(f"Report saved → {path}"))
        threading.Thread(target=run, daemon=True).start()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("eSim Tool Manager")
        self.geometry("1020x680")
        self.minsize(860, 560)
        self.configure(fg_color=Mocha.BASE)
        self.resizable(True, True)

        self.config   = load_config()
        self.os_info  = {}
        self.tools    = []
        self.deps     = []
        self._active_nav = "Dashboard"

        self._build_layout()
        self._nav_buttons = {}
        self._build_sidebar()
        self._build_panels()
        self._show_panel("Dashboard")

        self.after(200, self._startup_scan)

    def _build_layout(self):
        self.sidebar = ctk.CTkFrame(self, width=200, fg_color=Mocha.MANTLE,
                                     corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.main = ctk.CTkFrame(self, fg_color=Mocha.BASE, corner_radius=0)
        self.main.pack(side="left", fill="both", expand=True)

        self.topbar = ctk.CTkFrame(self.main, height=52, fg_color=Mocha.MANTLE,
                                    corner_radius=0)
        self.topbar.pack(fill="x")
        self.topbar.pack_propagate(False)

        self._page_title = ctk.CTkLabel(
            self.topbar, text="Dashboard",
            text_color=Mocha.TEXT, font=FONT_MONO_LG, anchor="w"
        )
        self._page_title.pack(side="left", padx=24)

        self._status_lbl = ctk.CTkLabel(
            self.topbar, text="Scanning…",
            text_color=Mocha.OVERLAY0, font=FONT_MONO_SM, anchor="e"
        )
        self._status_lbl.pack(side="right", padx=24)
        self.content = ctk.CTkFrame(self.main, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=28, pady=24)

    def _build_sidebar(self):

        logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo.pack(fill="x", padx=16, pady=(20, 24))

        icon = ctk.CTkFrame(logo, width=34, height=34, fg_color=Mocha.MAUVE,
                             corner_radius=8)
        icon.pack(side="left")
        icon.pack_propagate(False)
        ctk.CTkLabel(icon, text="eT", text_color=Mocha.CRUST,
                     font=(Mocha.FONT_MONO, 13, "bold")).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(logo, text=" eSim TM", text_color=Mocha.TEXT,
                     font=(Mocha.FONT_MONO, 14, "bold")).pack(side="left")

        
        nav_items = [
            ("Dashboard",    "◈"),
            ("Tools",        "⚙"),
            ("Dependencies", "⬡"),
            ("Compat",       "⊛"),
            ("Config",       "≡"),
            ("Log",          "⋮"),
        ]
        self._nav_buttons = {}
        for name, icon in nav_items:
            btn = NavButton(self.sidebar, text=name, icon=icon,
                            command=lambda n=name: self._show_panel(n))
            btn.pack(fill="x", padx=10, pady=2)
            self._nav_buttons[name] = btn

        # Bottom info
        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=16, pady=16)
        ctk.CTkFrame(bottom, height=1, fg_color=Mocha.SURFACE0).pack(fill="x", pady=(0, 10))
        self._os_lbl = ctk.CTkLabel(bottom, text="Detecting OS…",
                                     text_color=Mocha.OVERLAY0,
                                     font=FONT_MONO_SM, anchor="w", wraplength=170)
        self._os_lbl.pack(anchor="w")

    def _build_panels(self):
        self._panels = {
            "Dashboard":    DashboardPanel(self.content, self),
            "Tools":        ToolsPanel(self.content, self),
            "Dependencies": DepsPanel(self.content, self),
            "Compat":       CompatPanel(self.content, self),
            "Config":       ConfigPanel(self.content, self),
            "Log":          LogPanel(self.content, self),
        }

    def _show_panel(self, name: str):
        for n, btn in self._nav_buttons.items():
            btn.set_active(n == name)
        for n, panel in self._panels.items():
            if n == name:
                panel.pack(fill="both", expand=True)
            else:
                panel.pack_forget()
        self._page_title.configure(text=name)
        self._active_nav = name

        if name == "Log":
            self._panels["Log"].refresh()

    def _startup_scan(self):
        self.run_scan()
        if self.config.get("check_on_start"):
            self.run_dep_check()

    def run_scan(self):
        self._set_status("Scanning tools…")
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        self.os_info = detect_os()
        self.tools   = scan_tools()
        self.after(0, self._apply_scan)

    def _apply_scan(self):
        self._panels["Dashboard"].refresh(self.os_info, self.tools)
        self._panels["Tools"].refresh(self.tools, self.os_info.get("pkg_manager", "apt"))
        self._os_lbl.configure(
            text=f"{self.os_info.get('distro','—')}\nPython {self.os_info.get('python','—')}"
        )
        self._set_status(f"Last scan: {datetime.now().strftime('%H:%M:%S')}")

    def run_dep_check(self):
        self._set_status("Checking dependencies…")
        threading.Thread(target=self._do_dep_check, daemon=True).start()

    def _do_dep_check(self):
        self.deps = check_dependencies()
        self.after(0, lambda: self._panels["Dependencies"].refresh(self.deps))
        self.after(0, lambda: self._set_status(f"Deps checked: {datetime.now().strftime('%H:%M:%S')}"))

    def install_tool(self, tool_name: str):
        """
        Opens a progress dialog and installs the tool in a background thread.
        Runs via 'sudo -n' (non-interactive) works when sudo is already
        cached from the terminal that launched the GUI. If not cached, falls
        back to opening xterm so the user can type their password there.
        """
        import shutil as _sh
        pkg_mgr = self.os_info.get("pkg_manager", "apt")
        from core import get_install_command, TOOLS

        cmd = get_install_command(tool_name, pkg_mgr)
        if not cmd:
            self._set_status(f"No install mapping for {tool_name}")
            return

        cmd_str = " ".join(cmd)


        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Installing {tool_name}")
        dialog.geometry("600x480")
        dialog.configure(fg_color=Mocha.MANTLE)
        dialog.resizable(False, True)
        dialog.transient(self)
        dialog.update_idletasks()
        dialog.wait_visibility()
        dialog.grab_set()

    
        hdr = ctk.CTkFrame(dialog, fg_color=Mocha.SURFACE0, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(
            hdr, text=f"  Installing  {tool_name}",
            text_color=Mocha.TEXT, font=FONT_MONO_LG, anchor="w",
        ).pack(fill="x", pady=14)


        ctk.CTkLabel(
            dialog, text=f"  {cmd_str}",
            text_color=Mocha.OVERLAY0, font=FONT_MONO_SM, anchor="w",
        ).pack(fill="x", padx=4, pady=(10, 4))

        progress = ctk.CTkProgressBar(
            dialog, mode="indeterminate",
            fg_color=Mocha.SURFACE0, progress_color=Mocha.MAUVE, height=8,
        )
        progress.pack(fill="x", padx=20, pady=(0, 6))
        progress.start()

        status_lbl = ctk.CTkLabel(
            dialog, text="Waiting for package manager…",
            text_color=Mocha.LAVENDER, font=FONT_MONO_SM, anchor="w",
        )
        status_lbl.pack(fill="x", padx=20, pady=(0, 8))

        # Live output textbox
        out_box = ctk.CTkTextbox(
            dialog, fg_color=Mocha.BASE,
            text_color=Mocha.SUBTEXT0, font=FONT_MONO_SM,
            corner_radius=8, border_width=0,
        )
        out_box.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        out_box.configure(state="disabled")

        # Close button — disabled until done
        close_btn = ctk.CTkButton(
            dialog, text="Installing…",
            fg_color=Mocha.SURFACE0, text_color=Mocha.OVERLAY0,
            font=FONT_MONO, corner_radius=8, height=36,
            state="disabled", command=dialog.destroy,
        )
        close_btn.pack(pady=(0, 16))

        def append(line: str):
            def _do():
                out_box.configure(state="normal")
                out_box.insert("end", line + "\n")
                out_box.configure(state="disabled")
                out_box.see("end")
                # Show last meaningful line in status label
                stripped = line.strip()
                if stripped:
                    status_lbl.configure(text=stripped[:90])
            self.after(0, _do)

        def finish(ok: bool):
            def _do():
                progress.stop()
                progress.configure(
                    mode="determinate",
                    progress_color=Mocha.GREEN if ok else Mocha.RED,
                )
                progress.set(1.0)
                status_lbl.configure(
                    text="✓  Done! Tool installed successfully." if ok
                         else "✗  Installation failed see output above.",
                    text_color=Mocha.GREEN if ok else Mocha.RED,
                )
                close_btn.configure(
                    text="Close",
                    state="normal",
                    fg_color=Mocha.MAUVE,
                    text_color=Mocha.CRUST,
                    hover_color=Mocha.LAVENDER,
                )
                self._set_status(
                    f"✓ {tool_name} installed" if ok else f"✗ {tool_name} failed"
                )
                self.run_scan()
            self.after(0, _do)

        def run():
            import subprocess as _sp
            append(f"Running: {cmd_str}")
            append("─" * 52)
            try:
                proc = _sp.Popen(
                    cmd,
                    stdout=_sp.PIPE,
                    stderr=_sp.STDOUT,
                    stdin=_sp.DEVNULL,   
                    text=True,
                )
                for line in proc.stdout:
                    line = line.rstrip()
                    if line:
                        append(line)
                proc.wait()
                ok = proc.returncode == 0
            except Exception as e:
                append(f"Error: {e}")
                ok = False

            append("─" * 52)
            finish(ok)

        threading.Thread(target=run, daemon=True).start()

    def show_tool_info(self, tool_name: str):
        self._set_status(f"Tool: {tool_name} — see Tools panel for details")

    # ── Toast / status ─────────────────────────────────────────────────────────
    def _set_status(self, msg: str):
        self._status_lbl.configure(text=msg)

    def show_toast(self, msg: str):
        self._set_status(msg)
        self.after(3000, lambda: self._set_status("Ready"))


# ── Entry point ────────────────────────────────────────────────────────────────
def launch():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    launch()
