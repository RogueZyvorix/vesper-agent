import sys

from tui import VesperAgentApp


def main() -> None:
    continue_last = "-c" in sys.argv or "--continue" in sys.argv
    # mouse=True agar roda mouse bisa scroll chat.
    # Untuk memblok teks, tahan Shift saat drag mouse, lalu Ctrl+C.
    VesperAgentApp(continue_last=continue_last).run(mouse=True)


if __name__ == "__main__":
    main()
