import os
import signal
import subprocess
import sys
from datetime import datetime, UTC
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 4 or sys.argv[2] != "--":
        print("usage: service_runner.py <log_file> -- <command...>", file=sys.stderr)
        return 2

    log_path = Path(sys.argv[1])
    command = sys.argv[3:]
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=os.environ.copy(),
        )

        def forward_signal(signum: int, _frame: object) -> None:
            if process.poll() is None:
                process.send_signal(signum)

        signal.signal(signal.SIGTERM, forward_signal)
        signal.signal(signal.SIGINT, forward_signal)

        assert process.stdout is not None
        for line in process.stdout:
            stamp = datetime.now(UTC).isoformat()
            message = f"{stamp} {line}"
            sys.stdout.write(message)
            sys.stdout.flush()
            log_file.write(message)
            log_file.flush()

        return process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
