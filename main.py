import sys
import argparse

def main():
    parser = argparse.ArgumentParser(
        prog="esim-tm",
        description="eSim Tool Manager — manage eSim dependencies & tools"
    )
    parser.add_argument("--gui",      action="store_true", help="Launch the graphical interface")
    parser.add_argument("--check",    action="store_true", help="Run dependency check and exit")
    parser.add_argument("--scan",     action="store_true", help="Scan installed tools and exit")
    parser.add_argument("--report",   action="store_true", help="Generate HTML health report and open in browser")
    parser.add_argument("--compat",   metavar="VERSION",   help="Check eSim compatibility (e.g. --compat 2.5)")
    parser.add_argument("--install",  metavar="TOOL",      help="Install a specific tool by name")
    parser.add_argument("--dry-run",  action="store_true", help="Show install command without executing it (safe for testing)")
    args = parser.parse_args()

    if args.gui:
        try:
            import customtkinter
        except ImportError:
            print("customtkinter not found. Run: pip install customtkinter")
            sys.exit(1)
        from gui import launch
        launch()

    elif args.report:
        from health_report import generate_report
        path = generate_report(open_browser=True)
        print(f"  Report saved to: {path}")

    elif args.compat:
        from cli import run_compat_check
        run_compat_check(args.compat)

    elif args.check:
        from cli import run_dep_check
        run_dep_check()

    elif args.scan:
        from cli import run_scan
        run_scan()

    elif args.install:
        from cli import run_install
        run_install(args.install, dry_run=getattr(args, "dry_run", False))

    else:
        from cli import run_interactive
        run_interactive()


if __name__ == "__main__":
    main()