import sys
import threading

from gui import ValorantYoinkerGUI
from app_backend import ValorantRankYoinker


def main():
    app = ValorantYoinkerGUI()

    def init_backend():
        backend = ValorantRankYoinker(status_callback=app.log_message)
        app.after(0, lambda: app.attach_backend(backend))

    threading.Thread(target=init_backend, daemon=True).start()

    app.mainloop()
    print("Application closed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
