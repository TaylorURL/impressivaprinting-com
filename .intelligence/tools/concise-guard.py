#!/usr/bin/env python3
"""Refuses a reply that runs past its word budget.

Length is not thoroughness. A long reply buries the two facts that decide what
happens next under the work that produced them, and the reader has to dig for
them. A budget makes that cost visible at the moment the reply is written rather
than after it is read.

  guard-prompt UserPromptSubmit. State the budget before the reply is written.
  guard-stop   Stop hook. Measure the reply just written; refuse it if it is
               over budget, so it gets written again shorter.
  measure      Report the budget and the count for a transcript, without judging.
  install      Wire the hook into settings.json.

Two budgets, because a question and a report do not owe the same length. A turn
that called no tool is an answer and gets the tight one; a turn that did work
gets the wider one. The refusal fires once per reply: a second pass through the
hook lets the reply stand, so a budget nobody can meet costs one rewrite rather
than a loop.

INTELLIGENCE_CONCISE_OFF=1 disables it. INTELLIGENCE_CONCISE_ANSWER and
INTELLIGENCE_CONCISE_REPORT set the two budgets.
"""
import json
import importlib.util
import os
import re
import sys
from pathlib import Path


def _shared():
    """The shared _lib module, loaded by path.

    Hooks run this tool as a script from arbitrary directories, so the module
    is found beside this file rather than through sys.path, with the installed
    tree as the fallback for a copy executed from elsewhere.
    """
    here = Path(__file__).resolve().parent / "_lib.py"
    path = here if here.is_file() else Path.home() / ".intelligence" / "tools" / "_lib.py"
    spec = importlib.util.spec_from_file_location("intelligence_tools_lib", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# A Stop hook that crashes on a half-synced tree blocks every reply, so a
# missing _lib stands the guard down instead: guard_stop notes it and exits 0.
try:
    _lib = _shared()
    read_transcript = _lib.read_transcript
    final_reply = _lib.final_reply
except Exception:
    _lib = None

ANSWER_BUDGET = int(os.environ.get("INTELLIGENCE_CONCISE_ANSWER", "80"))
REPORT_BUDGET = int(os.environ.get("INTELLIGENCE_CONCISE_REPORT", "150"))

# Openings that spend words before reaching the point.
PREAMBLE = re.compile(
    r"^\s*(?:great|perfect|excellent|sure|certainly|of course|absolutely|"
    r"you'?re (?:right|correct)|good (?:catch|point|question)|"
    r"let me (?:start|begin|first)|i'?ll (?:start|begin)|"
    r"here'?s (?:what|a) )",
    re.I,
)

# Sections that restate work already visible in the transcript.
RECAP = re.compile(
    r"^\s*#{1,4}\s*(?:summary|what (?:i|we) did|recap|overview|"
    r"changes made|what changed|steps taken)\b",
    re.I | re.M,
)


def words(text):
    """The words a reply spends, which is its prose and not its code blocks.

    A file, a diff, or a command reproduced because it was asked for is the
    source's length rather than the writer's, and no budget it is counted
    against can be met without refusing what was asked for.
    """
    return len(re.findall(r"\S+", _lib.prose_only(text) if _lib else text))


def judge(text, used_tool):
    budget = REPORT_BUDGET if used_tool else ANSWER_BUDGET
    count = words(text)
    faults = []
    if count > budget:
        faults.append(f"{count} words against a budget of {budget}")
    if PREAMBLE.search(text):
        faults.append("opens with a preamble instead of the answer")
    if RECAP.search(text):
        faults.append("carries a section recapping work the transcript already shows")
    return budget, count, faults


def guard_stop():
    if os.environ.get("INTELLIGENCE_CONCISE_OFF") == "1":
        sys.exit(0)
    if _lib is None:
        sys.stderr.write("concise-guard: _lib.py unavailable; standing down\n")
        sys.exit(0)
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    # A second pass means the reply has already been sent back once.
    if ev.get("stop_hook_active"):
        sys.exit(0)
    path = ev.get("transcript_path")
    if not path or not Path(path).exists():
        sys.exit(0)

    text, used_tool = final_reply(read_transcript(path))
    if not text.strip():
        sys.exit(0)
    budget, count, faults = judge(text, used_tool)
    if not faults:
        sys.exit(0)

    kind = "report" if used_tool else "answer"
    sys.stderr.write(
        f"\nBLOCKED: this {kind} is longer than it needs to be.\n\n"
        + "".join(f"  {f}\n" for f in faults)
        + "\nWrite it again, under the budget. Lead with the thing that decides what\n"
        "happens next: the answer, the identifiers, the one action still owed.\n"
        "Cut the account of how it was produced; the transcript already holds it.\n"
        "INTELLIGENCE_CONCISE_OFF=1 disables this.\n"
    )
    sys.exit(2)


def measure(path):
    if _lib is None:
        print("concise-guard: _lib.py unavailable; nothing measured", file=sys.stderr)
        return 1
    rows = read_transcript(path)
    text, used_tool = final_reply(rows)
    budget, count, faults = judge(text, used_tool)
    print(f"kind={'report' if used_tool else 'answer'} words={count} budget={budget}")
    for f in faults:
        print(f"  {f}")
    return 1 if faults else 0


def install():
    settings = Path.home() / ".intelligence" / "settings.json"
    try:
        data = json.loads(settings.read_text())
    except Exception:
        return 1
    tool = "~/.intelligence/tools/concise-guard.py"
    wanted = [("Stop", "*", f"{tool} guard-stop"),
              ("UserPromptSubmit", None, f"{tool} guard-prompt"),
              ("SessionStart", "*", f"{tool} install")]
    changed = False
    for event, matcher, command in wanted:
        entries = data.setdefault("hooks", {}).setdefault(event, [])
        if any(command in h.get("command", "")
               for m in entries for h in m.get("hooks", [])):
            continue
        # A guard-hub entry hosts the events it dispatches. SessionStart and
        # UserPromptSubmit are not among them, so those wire directly.
        if event not in ("SessionStart", "UserPromptSubmit") and any(
                "guard-hub.py" in h.get("command", "")
                for m in entries for h in m.get("hooks", [])):
            continue
        block = {"hooks": [{"type": "command", "command": command}]}
        if matcher:
            block["matcher"] = matcher
        entries.append(block)
        changed = True
        print(f"wired {event}[{matcher}]")
    if changed:
        settings.write_text(json.dumps(data, indent=2) + "\n")
    return 0


def guard_prompt():
    """UserPromptSubmit. State the budget before the reply is written.

    Measuring at Stop costs a whole reply: the turn is written, refused, and
    written again, and the second one is paid for in full. Across a fortnight of
    transcripts this refusal fired 139 times in 20 sessions without the habit
    moving, because a rule that arrives after the work is a rule the work never
    saw. The budget is cheap to state and expensive to discover, so it is stated
    at the top of the turn and the Stop hook stays as the backstop rather than
    the teacher.
    """
    if os.environ.get("INTELLIGENCE_CONCISE_OFF") == "1":
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext":
            "Reply budget: %d words if this turn calls no tool, %d if it does, "
            "counting prose and not fenced blocks, and at most 3 sentences of "
            "prose. Lead with the thing that decides what happens next. No "
            "preamble, no recap of work already visible above, no summary "
            "heading. Close with one line per thing asked, each naming "
            "something checkable -- a path, a repo, a URL, a pull request, a "
            "command -- rather than an adjective."
            % (ANSWER_BUDGET, REPORT_BUDGET),
    }}))
    return 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "guard-stop"
    if mode == "guard-stop":
        guard_stop()
    elif mode == "guard-prompt":
        sys.exit(guard_prompt())
    elif mode == "measure":
        sys.exit(measure(sys.argv[2] if len(sys.argv) > 2 else ""))
    elif mode == "install":
        sys.exit(install())
    # An unrecognised verb exits as a refusal rather than a pass, so a caller
    # probing this guard by a name it does not carry cannot read the silent
    # exit as the guard reporting itself wired.
    print("unknown verb: %s" % mode, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
