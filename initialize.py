import threading
import subprocess
import signal
import sys
import os
import time

def run_flask():
    os.system("flask run")

def run_osu_server():
    os.system("python server.py")

def shutdown(signum, frame):
    os._exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)

    flask_thread = threading.Thread(target=run_flask)
    osu_thread = threading.Thread(target=run_osu_server)

    flask_thread.start()
    osu_thread.start()

    while True:
        time.sleep(1)
