"""List and create Open WebUI knowledge bases without importing content."""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence

from .webui import WebUI, WebUIError


def run(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--webui-url", default="http://127.0.0.1:3000")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="Print accessible bases as JSON (IDs and names)")
    create = commands.add_parser("create", help="Create a knowledge base")
    create.add_argument("--name", required=True)
    create.add_argument("--description", default="")
    args = parser.parse_args(argv)
    try:
        with WebUI(args.webui_url, os.getenv("OPEN_WEBUI_API_KEY", "")) as api:
            result = (api.list_knowledge() if args.command == "list" else
                      api.create_knowledge(args.name, args.description))
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, WebUIError) as exc:
        print(f"Knowledge operation failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(run())
