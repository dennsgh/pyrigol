from frontend.app import run_application, signal_handler
import signal
import sys

# Rest of the code...

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    try:
        run_application()
    except KeyboardInterrupt:
        print("Exit signal detected.")