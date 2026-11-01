"""Runs the commands of the guide, as a reader would type them, and checks what they show.

The commands come from README.md itself: each code block to run has a marker just before it,
an HTML comment that GitHub does not show:

    <!-- ci linux stage=cli check="devcontainer --version" expect="0.89.0" -->

- `linux` (or `macos`, `windows`): the version of the guide the block belongs to;
- `stage=`: the blocks of one stage run in order, in one shell, like one terminal;
- `check="..."`: a command the text asks the reader to type after the block ("What you should see");
- `expect="..."`: a text that the output of the block (and of its check) must contain.

One change is made to the commands, and only this one (SUBSTITUTIONS below): the guide opens the
workshop kit, and says "for a workshop or a guide, change the name of the repository"; CI_REPO does
that, so that the same blocks open each repository of the workflow.

The blocks run in CI_WORKDIR (default: a new temporary folder), never in the home folder.
Never run the stage `delete` on your own computer: it deletes the container of the repository, and
every version of the image of the workshops.

Usage (the same CI_WORKDIR for every stage, so that `inside` finds what `open` downloaded):
    export CI_WORKDIR=$(mktemp -d)
    CI_REPO=yal-opencode-guide python3 ci/run_guide.py --os linux --stage open
    CI_REPO=yal-opencode-guide python3 ci/run_guide.py --os linux --stage inside
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
REPO = os.environ.get("CI_REPO", "yal-workshop-kit")
SUBSTITUTIONS = [
    # The same steps for each repository that uses the image of the workshops.
    ("yal-workshop-kit", REPO),
]
MARKER = re.compile(r"^\s*<!--\s*ci\s+(.*?)\s*-->\s*$")
FENCE = re.compile(r"^(\s*)```(\w+)\s*$")


def blocks(os_name, stage):
    """The marked blocks of README.md for this system and stage, in the order of the guide."""
    lines = README.read_text(encoding="utf-8").split("\n")
    found = []
    for i, line in enumerate(lines):
        m = MARKER.match(line)
        if not m or i + 1 >= len(lines):
            continue
        spec = m.group(1)
        systems = spec.split()[0].split(",")
        if os_name not in systems or f"stage={stage}" not in spec.split():
            continue
        fence = FENCE.match(lines[i + 1])
        if not fence:
            sys.exit(f"README.md line {i + 1}: a ci marker must be just before a code block")
        indent = fence.group(1)
        body, j = [], i + 2
        while not lines[j].strip().startswith("```"):
            body.append(lines[j][len(indent):] if lines[j].startswith(indent) else lines[j])
            j += 1
        code = "\n".join(body)
        # The same substitutions in the commands, the checks and the expected texts.
        for old, new in SUBSTITUTIONS:
            code = code.replace(old, new)
            spec = spec.replace(old, new)
        found.append({
            "line": i + 2,
            "code": code,
            "checks": re.findall(r'check="([^"]*)"', spec),
            "expects": re.findall(r'expect="([^"]*)"', spec),
        })
    return found


def bash_script(found, out_dir):
    """One bash script: each block in a function, so that cd, export and source stay for the next one."""
    # A command that fails stops everything, as a reader would stop at an error.
    parts = ["set -eE -o pipefail", "trap 'echo \"::error::failed: $BASH_COMMAND\"' ERR"]
    for n, b in enumerate(found):
        out = out_dir / f"{n}.txt"
        checks = "\n".join(b["checks"])
        parts.append(f"block_{n}() {{\n{b['code']}\n}}")
        parts.append(f"check_{n}() {{\n{checks or ':'}\n}}")
        parts.append(
            f'echo "::group::README.md line {b["line"]}"\n'
            # When a command fails, set -e leaves at once: show the output of the block before.
            f"trap 'rc=$?; cat {out}; echo \"::endgroup::\"; "
            f"echo \"::error::README.md line {b['line']}: exit code $rc\"' EXIT\n"
            # A file, not a pipe: `devcontainer up` leaves a `docker run` that keeps a pipe open.
            f"block_{n} > {out} 2>&1 < /dev/null\n"
            f"check_{n} >> {out} 2>&1 < /dev/null\n"
            f'trap - EXIT; cat {out}; echo "::endgroup::"')
    return "\n\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--os", required=True, choices=["linux", "macos", "windows"])
    parser.add_argument("--stage", required=True)
    parser.add_argument("--print", action="store_true", help="show the script, do not run it")
    args = parser.parse_args()
    found = blocks(args.os, args.stage)
    if not found:
        sys.exit(f"no block marked for {args.os}, stage {args.stage}")
    if args.os == "windows":
        sys.exit("windows: not written yet")
    out_dir = Path(tempfile.mkdtemp(prefix="guide-"))
    script = out_dir / "guide.sh"
    script.write_text(bash_script(found, out_dir), encoding="utf-8")
    if args.print:
        print(script.read_text(encoding="utf-8"))
        return
    work = Path(os.environ.get("CI_WORKDIR") or tempfile.mkdtemp(prefix="work-"))
    work.mkdir(parents=True, exist_ok=True)
    print(f"{len(found)} blocks of README.md, stage {args.stage}, repository {REPO}, in {work}", flush=True)
    # A login shell, as a new terminal: it reads the profile that the installers change.
    rc = subprocess.run(["bash", "-l", str(script)], cwd=work).returncode
    if rc != 0:
        sys.exit(rc)
    failed = []
    for n, b in enumerate(found):
        text = (out_dir / f"{n}.txt").read_text(encoding="utf-8", errors="replace")
        for want in b["expects"]:
            if want not in text:
                failed.append(f'README.md line {b["line"]}: "{want}" not in the output')
    for f in failed:
        print(f"::error::{f}")
    if failed:
        sys.exit(1)
    print(f"stage {args.stage}: every block ran and showed what the guide says")


if __name__ == "__main__":
    main()
