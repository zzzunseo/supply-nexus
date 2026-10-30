"""Start the local app independently of the launching terminal on Windows."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
import webbrowser
from urllib.request import urlopen


def healthy(url):
    try:
        with urlopen(url + '/_stcore/health', timeout=2) as response:
            return response.status == 200 and response.read().strip() == b'ok'
    except (OSError, TimeoutError):
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8701)
    parser.add_argument('--log-dir', type=Path)
    parser.add_argument('--open', action='store_true', help='Open the browser after the server is ready')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    root = Path(__file__).resolve().parent
    logs = args.log_dir or root / 'work'
    logs.mkdir(parents=True, exist_ok=True)
    url = f'http://127.0.0.1:{args.port}'
    if healthy(url):
        print(f'App is already running: {url}')
        if args.open:webbrowser.open(url)
        return
    command = [sys.executable, '-m', 'streamlit', 'run', str(root / 'app.py'),
               '--server.address', '127.0.0.1', '--server.port', str(args.port),
               '--server.headless', 'true']
    flags = 0
    if os.name == 'nt':
        flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                 | subprocess.CREATE_BREAKAWAY_FROM_JOB)
    with (logs / 'supply-server.log').open('ab') as output:
        process = subprocess.Popen(command, cwd=root, stdin=subprocess.DEVNULL,
                                   stdout=output, stderr=subprocess.STDOUT,
                                   creationflags=flags, close_fds=True)
    (logs / 'supply-server.pid').write_text(str(process.pid), encoding='ascii')
    for _ in range(30):
        if healthy(url):
            print(f'App is ready: {url} (PID {process.pid})')
            if args.open:webbrowser.open(url)
            return
        if process.poll() is not None:
            raise RuntimeError(f'Server exited. See {logs / "supply-server.log"}')
        time.sleep(1)
    raise RuntimeError(f'Server did not become ready. See {logs / "supply-server.log"}')


if __name__ == '__main__':
    main()
