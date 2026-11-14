"""Simple opt-in, serial local scheduling; intended for cron/systemd timers."""
import argparse
import subprocess
import sys
from pathlib import Path

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--urls-file", type=Path, required=True)
    p.add_argument("--allow-domain", action="append", required=True)
    p.add_argument("--knowledge-id", required=True)
    args=p.parse_args(argv)
    command=[sys.executable, "-m", "ingest.cli", "--urls-file", str(args.urls_file),
             "--knowledge-id", args.knowledge_id]
    for domain in args.allow_domain:
        command.extend(["--allow-domain", domain])
    # The caller (e.g. cron) controls cadence. Never create background tasks implicitly.
    return subprocess.call(command)

if __name__=="__main__":
    sys.exit(main())
