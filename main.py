import sys


def main() -> None:
    args = sys.argv[1:]

    if args and args[0] == "uninstall":
        from uninstall import run
        raise SystemExit(run(args[1:]))

    if args and args[0] in ("--version", "-V"):
        from config import APP_VERSION
        print(f"Vesper-Agent {APP_VERSION}")
        return

    from tui import VesperAgentApp

    continue_last = "-c" in args or "--continue" in args
    # mouse=True agar roda mouse bisa scroll chat.
    # Untuk memblok teks, tahan Shift saat drag mouse, lalu Ctrl+C.
    VesperAgentApp(continue_last=continue_last).run(mouse=True)


if __name__ == "__main__":
    main()