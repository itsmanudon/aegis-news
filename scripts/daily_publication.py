"""Small workflow coordinator: no shell evaluation of provider content or artifacts."""

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from aegis.provenance.service import canonical
from aegis.showcase.contracts import DailyExport, parse_export
from aegis.showcase.daily import digest, run
from aegis.showcase.site import audit, build
from aegis.showcase.state import GitHubState, StateError

DIRECTORY = Path(".data/daily")
CANDIDATE = DIRECTORY / "candidate.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("acquire", "build", "prepare", "promote", "summary"))
    action = parser.parse_args().action
    if action == "summary":
        summary = Path(os.environ.get("GITHUB_STEP_SUMMARY", str(DIRECTORY / "summary.md")))
        summary.parent.mkdir(parents=True, exist_ok=True)
        with summary.open("a", encoding="utf-8") as stream:
            stream.write("Static Daily Publication · No Hosted Private Services\n\n")
            report = DIRECTORY / "report.json"
            if report.exists():
                stream.write("```json\n" + report.read_text(encoding="utf-8") + "\n```\n")
            stream.write("A release is successful only after the promotion step passes.\n")
        return
    state = json.loads((DIRECTORY / "state.json").read_bytes())
    if action == "acquire":
        if state["resume"] != "true":
            asyncio.run(
                run(DIRECTORY / "previous.json", CANDIDATE, None, DIRECTORY / "report.json")
            )
        return
    if not CANDIDATE.exists():
        print("No new permitted news; previous validated release retained")
        return
    export = parse_export(CANDIDATE.read_bytes())
    if not isinstance(export, DailyExport):
        raise ValueError("daily candidate must be a signed v2 release")
    if action == "build":
        build(export, Path("apps/showcase/dist"))
        audit(export, Path("apps/showcase/dist"))
    elif action == "prepare":
        store = GitHubState()
        if state["resume"] == "true":
            if store.head() != state["head"] or state["release"] != digest(export):
                raise StateError("prepared state changed; do not deploy")
            head = state["head"]
        else:
            head = store.prepare(export, state["head"])
        (DIRECTORY / "prepared-head.json").write_bytes(canonical({"head": head}))
    else:
        expected = json.loads((DIRECTORY / "prepared-head.json").read_bytes())["head"]
        # Allow CDN propagation; never change state until the production digest agrees.
        for attempt in range(3):
            try:
                GitHubState().promote(digest(export), expected)
                break
            except StateError:
                if attempt == 2:
                    raise
                time.sleep(10)
        print("Live signed release verified and durable public state promoted")


if __name__ == "__main__":
    main()
