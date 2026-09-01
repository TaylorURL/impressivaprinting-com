#!/usr/bin/env python3
"""What archive.py has to get right for a chat to close on an honest answer.

The tool stands between a chat and its own ending, so both of its failures are
silent. A sweep that misses work lets the one process that knew about it end,
and a harvest that misses a lesson lets the same correction be given again next
week. Neither leaves a mark anywhere, which is why the cases here are mostly
about what the reader must not overlook rather than about what it reports.

Three of them exist because the shapes are easy to miss. A refusal reaches a
transcript three different ways and only one of them is a system row; a hook and
a finished agent both speak through user rows that read like a person objecting;
and fresh work is invisible to any reading that waits a day before it counts.

Every fixture is a temporary directory with the state root, the transcript root
and the session store pinned to it, so no run here can see or move the live
ledger. The roots are also what tells the hand-off and the close they are being
exercised rather than used, and what comes off the environment of anything they
start, so the pinning is the reason nothing here reaches a live session. The
listing of running sessions is answered by a stand-in on the path and the call
that sends a signal is stood in for as well, because a pid in front of this
suite belongs to the machine.

  archive-cases.py     run them
"""

import contextlib
import importlib.util
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "archive.py")

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append("%s: got %r, want %r" % (label, got, want))


def contains(label, haystack, needle):
    if needle not in haystack:
        FAILURES.append("%s: %r missing from the output" % (label, needle))


def load(state, transcripts, sessions):
    os.environ["INTELLIGENCE_STATE_DIR"] = str(state)
    os.environ["INTELLIGENCE_TRANSCRIPTS"] = str(transcripts)
    os.environ["INTELLIGENCE_SESSION_STORE"] = str(sessions)
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@contextlib.contextmanager
def mock_env(values):
    """The process environment as given, put back however the block ends."""
    held = dict(os.environ)
    os.environ.clear()
    os.environ.update(values)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(held)


def transcript(root, session, rows):
    """One session file, written where the tool looks for it."""
    folder = root / "-fixture"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("%s.jsonl" % session)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def registered(root, folder, name, record):
    """One record of the app's own, written where the tool looks for it.

    The store holds a record two directories down under a name of its own, and
    a record given as text is one the reader cannot parse.
    """
    where = root / folder / "sessions"
    where.mkdir(parents=True, exist_ok=True)
    path = where / ("local_%s.json" % name)
    path.write_text(record if isinstance(record, str) else json.dumps(record))
    return path


def said(text):
    return {"type": "user", "origin": {"kind": "human"},
            "message": {"role": "user", "content": text}}


def typed(text):
    """One turn carrying a command as the harness writes it down."""
    return {"type": "user", "origin": {"kind": "human"},
            "message": {"role": "user",
                        "content": [{"type": "text", "text": text}]}}


def denied(text):
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "is_error": True, "content": text}]}}


def feedback(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def wrote(text):
    """One reply, which is what a stop hook refuses and what replaces one."""
    return {"type": "assistant",
            "message": {"content": [{"type": "text", "text": text}]}}


def called(name, given):
    """One tool call, which is the trace a reading has that work was done."""
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": name, "input": given}]}}


def worked_in(root):
    """One turn stamped with a working directory, which is how scope is found."""
    return {"type": "assistant", "cwd": str(root),
            "message": {"content": [{"type": "text", "text": "Working."}]}}


def checkout(root):
    """A checkout with one commit behind it, holding one changed file."""
    root.mkdir(parents=True, exist_ok=True)
    for args in (["init", "-q", "-b", "develop"],
                 ["config", "user.email", "cases@example.invalid"],
                 ["config", "user.name", "Cases"]):
        subprocess.run(["git", "-C", str(root)] + args, capture_output=True)
    (root / "widget.py").write_text("value = 1\n")
    subprocess.run(["git", "-C", str(root), "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "first"],
                   capture_output=True)
    (root / "widget.py").write_text("value = 2\n")
    return root


def summary(text):
    return {"type": "system", "subtype": "stop_hook_summary",
            "hookErrors": [text], "hookInfos": []}


def ran(mod, argv, state, transcripts, extra=None):
    env = dict(os.environ)
    env["INTELLIGENCE_STATE_DIR"] = str(state)
    env["INTELLIGENCE_TRANSCRIPTS"] = str(transcripts)
    env.pop("INTELLIGENCE_TEST_TARGET", None)
    env.update(extra or {})
    return subprocess.run([sys.executable, str(TARGET)] + argv,
                          capture_output=True, text=True, env=env, timeout=300)


def main():
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        state = tmp / "state"
        scripts = tmp / "projects"
        scripts.mkdir()
        store = tmp / "sessions"
        store.mkdir()
        mod = load(state, scripts, store)

        # --------------------------------------------------- the three refusals
        session = "aaaaaaaa-0000-0000-0000-000000000001"
        transcript(scripts, session, [
            denied("BLOCKED: this survey belongs to an agent."),
            denied("BLOCKED: this survey belongs to an agent."),
            feedback("Stop hook feedback: BLOCKED: the reply is the wrong shape."),
            feedback("Stop hook feedback: BLOCKED: the reply is the wrong shape."),
            summary("BLOCKED: a document states a count the setup disagrees with."),
            summary("BLOCKED: a document states a count the setup disagrees with."),
        ])
        found = mod.candidates(session)
        check("every shape a refusal takes is read", len(found), 3)
        check("a refusal wants context rather than a gate",
              {c["wants"] for c in found}, {"context"})

        # A denial arrives as an errored tool result, which carries no prose at
        # all through the ordinary text path. Reading only system rows sees one
        # refusal in six and calls the chat clean.
        check("a denied call is not mistaken for a clean run",
              any("survey belongs" in c["example"] for c in found), True)

        # ------------------------------------------------------- what a person said
        session = "aaaaaaaa-0000-0000-0000-000000000002"
        transcript(scripts, session, [
            said("stop adding the vendored bundle to the commit"),
            said("never add the vendored bundle to the commit again"),
        ])
        found = mod.candidates(session)
        check("a repeated correction is raised", len(found), 1)
        check("a correction wants a mechanism", found[0]["wants"], "a mechanism")

        # The gate's own refusal is not a lesson. Counting it means a chat
        # blocked twice raises a candidate whose only cause was the block, and
        # the next attempt is refused over it, with no ending reachable.
        session = "aaaaaaaa-0000-0000-0000-00000000000a"
        transcript(scripts, session, [
            denied("BLOCKED: the chat is still holding something."),
            denied("BLOCKED: the chat is still holding something."),
        ])
        check("a chat the gate blocked twice can still reach an ending",
              mod.candidates(session), [])

        # ------------------------------------------- who is allowed to correct
        session = "aaaaaaaa-0000-0000-0000-000000000003"
        transcript(scripts, session, [
            dict(said("stop adding the vendored bundle to the commit"),
                 origin={"kind": "task-notification"}),
            dict(said("never add the vendored bundle to the commit again"),
                 origin={"kind": "task-notification"}),
            feedback("Stop hook feedback: never commit the vendored bundle again"),
            feedback("Stop hook feedback: never commit the vendored bundle again"),
        ])
        found = mod.candidates(session)
        check("an agent report is not filed as a correction",
              [c for c in found if c["kind"] == "correction"], [])

        # ------------------------------------------------------------- the floor
        session = "aaaaaaaa-0000-0000-0000-000000000004"
        transcript(scripts, session, [said("stop adding the vendored bundle to the commit")])
        check("one telling is an incident, not a lesson",
              mod.candidates(session), [])

        # ---------------------------------------------------------- the ranking
        session = "aaaaaaaa-0000-0000-0000-000000000005"
        transcript(scripts, session, [
            denied("BLOCKED: this survey belongs to an agent."),
            denied("BLOCKED: this survey belongs to an agent."),
            denied("BLOCKED: this survey belongs to an agent."),
            said("stop adding the vendored bundle to the commit"),
            said("never add the vendored bundle to the commit again"),
        ])
        found = mod.candidates(session)
        check("what nobody enforces outranks what already refused",
              found[0]["kind"], "correction")

        # --------------------------------------------------------- once settled
        mark = found[0]["id"]
        done = ran(mod, ["settle", mark, "--as", "built", "--note", "a hook"],
                   state, scripts)
        check("settling a candidate succeeds", done.returncode, 0)
        check("a settled candidate stops being raised",
              [c["id"] for c in mod.candidates(session)].count(mark), 0)
        check("settling without a note is refused",
              ran(mod, ["settle", "x", "--as", "built"], state, scripts).returncode, 2)

        # --------------------------------------------------------- fresh work
        repo = tmp / "repo"
        repo.mkdir()
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_CONFIG_SYSTEM=os.devnull)
        for args in (["init", "-q", "-b", "main"],
                     ["config", "user.email", "fixture@example.invalid"],
                     ["config", "user.name", "Fixture"]):
            subprocess.run(["git", "-C", str(repo)] + args, env=env, check=True,
                           capture_output=True)
        (repo / "note.txt").write_text("held\n")
        # Work made minutes ago is exactly what a chat closing now abandons, and
        # every drift reading on this machine waits a day before it counts.
        check("work made this minute is held", mod.tree_findings(repo),
              ["1 uncommitted change(s)"])

        # ------------------------------------------------------- the footprint
        rows = [{"cwd": "/Users/fixture/one",
                 "message": {"role": "assistant", "content": [
                     {"type": "tool_use", "name": "Bash",
                      "input": {"command": "git -C /Users/fixture/two status"}}]}},
                {"toolUseResult": {"stdout": "https://github.com/o/r/pull/7"}}]
        paths, prs = mod.footprint(rows)
        check("a working directory reaches the footprint",
              "/Users/fixture/one" in paths, True)
        check("a path inside a command reaches the footprint",
              "/Users/fixture/two" in paths, True)
        check("a pull request reaches the footprint", prs, {("o/r", "7")})

        # ----------------------------------------------------------- the guard
        session = "aaaaaaaa-0000-0000-0000-000000000006"
        transcript(scripts, session, [
            said("stop adding the changelog entry to the release"),
            said("never add the changelog entry to the release again"),
        ])
        payload = json.dumps({"session_id": session,
                              "tool_input": {"session_id": "self"}})
        done = subprocess.run(
            [sys.executable, str(TARGET), "guard-archive"], input=payload,
            capture_output=True, text=True,
            env=dict(os.environ, INTELLIGENCE_STATE_DIR=str(state),
                     INTELLIGENCE_TRANSCRIPTS=str(scripts),
                     CLAUDE_CODE_SESSION_ID=session), timeout=300)
        check("the archive is refused over an unharvested lesson",
              done.returncode, 2)
        contains("the refusal says what is wrong", done.stderr,
                 "BLOCKED: the chat is still holding something.")
        contains("the refusal names the way forward", done.stderr, "hand-off")
        contains("the refusal names the override", done.stderr,
                 "INTELLIGENCE_ALLOW_ARCHIVE=1")

        done = subprocess.run(
            [sys.executable, str(TARGET), "guard-archive"], input=payload,
            capture_output=True, text=True,
            env=dict(os.environ, INTELLIGENCE_STATE_DIR=str(state),
                     INTELLIGENCE_TRANSCRIPTS=str(scripts),
                     CLAUDE_CODE_SESSION_ID=session,
                     INTELLIGENCE_ALLOW_ARCHIVE="1"), timeout=300)
        check("the override lets one archive through", done.returncode, 0)

        session = "aaaaaaaa-0000-0000-0000-000000000007"
        transcript(scripts, session, [said("that all looks right, thanks")])
        done = subprocess.run(
            [sys.executable, str(TARGET), "guard-archive"], input=json.dumps(
                {"session_id": session, "tool_input": {"session_id": "self"}}),
            capture_output=True, text=True,
            env=dict(os.environ, INTELLIGENCE_STATE_DIR=str(state),
                     INTELLIGENCE_TRANSCRIPTS=str(scripts),
                     CLAUDE_CODE_SESSION_ID=session), timeout=300)
        check("a clean chat is not refused", done.returncode, 0)

        # ------------------------------------------------------- the hand-off
        session = "aaaaaaaa-0000-0000-0000-000000000008"
        transcript(scripts, session, [
            said("stop adding the driver version to the manifest"),
            said("never add the driver version to the manifest again"),
        ])
        done = ran(mod, ["hand-off", "--session", session, "--print"],
                   state, scripts)
        check("the hand-off can be read before it is fired", done.returncode, 0)
        contains("it carries the rule the agent opens on", done.stdout,
                 "/enforce")
        check("it names no window for anybody to drive",
              "claude://" in done.stdout, False)

        # The hand-off exists to take the work off a person, so the branch that
        # runs away from the Mac has to name the route back rather than end in
        # a request for somebody to go and type something there.
        away = mod.opening_prompt(mod.candidates(session)[0], tmp / "brief.md",
                                  True)
        contains("an agent off the Mac is told how to reach it", away,
                 "remote-access.py run mac")
        check("an agent on the Mac is told nothing about reaching it",
              "remote-access.py run mac" in
              mod.opening_prompt(mod.candidates(session)[0], tmp / "brief.md"),
              False)

        # A hand-off is the documented way past the gate, so a gate that goes
        # on refusing after one leaves only a settle claiming work nobody did.
        # What a hand-off leaves behind is read back off the record rather than
        # off a launch, because a suite that starts an agent is the one outcome
        # this file is not allowed to have.
        payload = json.dumps({"session_id": session,
                              "tool_input": {"session_id": "self"}})

        def guarding():
            return subprocess.run(
                [sys.executable, str(TARGET), "guard-archive"], input=payload,
                capture_output=True, text=True, timeout=300,
                env=dict(os.environ, INTELLIGENCE_STATE_DIR=str(state),
                         INTELLIGENCE_TRANSCRIPTS=str(scripts),
                         CLAUDE_CODE_SESSION_ID=session)).returncode

        check("an unharvested lesson refuses the archive", guarding(), 2)
        mod.record_handoff(mod.candidates(session)[0], tmp / "brief.md",
                           "ab12cd34")
        check("a handed-off lesson stops refusing the archive", guarding(), 0)
        recorded = json.loads(
            (state / "archive" / "ledger.json").read_text())["candidates"]
        check("a hand-off is recorded as handed off rather than settled",
              {e["status"] for e in recorded.values()} & {"handed-off"},
              {"handed-off"})
        check("the agent it started is named in the ledger",
              {e.get("agent") for e in recorded.values()} & {"ab12cd34"},
              {"ab12cd34"})

        # The launch answers to the state it is recorded into, so no way of
        # running this suite reaches a live one. A brief written into a tree
        # that gets deleted is a brief nothing can open, and something running
        # on it that nobody holds is what the gate goes on refusing over.
        session = "aaaaaaaa-0000-0000-0000-000000000011"
        transcript(scripts, session, [
            said("stop adding the schema version to the migration"),
            said("never add the schema version to the migration again"),
        ])
        raised = mod.candidates(session)[0]["id"]
        done = ran(mod, ["hand-off", "--session", session], state, scripts,
                   {"INTELLIGENCE_HANDOFF_HOST": "local"})
        check("a case suite cannot start an agent", done.returncode, 2)
        contains("the refusal names what a suite does instead", done.stderr,
                 "hand-off --print")
        contains("it says where the brief went", done.stderr, "brief")
        held = json.loads(
            (state / "archive" / "ledger.json").read_text())["candidates"]
        check("a refused hand-off records no hand-off", raised in held, False)

        # A lesson's origin is the transcript it was raised from, so a run
        # reading fabricated chats is a suite whatever its state root says.
        without = dict(os.environ)
        del without["INTELLIGENCE_STATE_DIR"]
        with mock_env(without):
            check("a transcript root on its own is a case suite",
                  mod.fixture_run(), True)

        # Anything started here would otherwise inherit the roots and spend its
        # whole run reading this directory as though it were the machine.
        check("what a hand-off starts carries neither root",
              [k for k in mod.FIXTURE_ROOTS if k in mod.child_env()], [])

        # A suite refused and a launcher that would not start are opposite
        # answers out of the same call, and each carries its own number.
        def refusing(prompt, folder):
            raise mod.Undispatched("no")

        stood_in, mod.dispatch = mod.dispatch, refusing
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                code = mod.cmd_handoff(["--session", session])
        finally:
            mod.dispatch = stood_in
        check("a launcher that would not start reads as a failure", code, 1)

        # ------------------------------------------- a chat nobody can read
        # An id off by a character places no file, and no rows read exactly
        # like a chat that closed clean. Reporting that is the one answer this
        # tool cannot give.
        missing = "deadbeef-0000-0000-0000-000000000000"
        for verb in (["check"], ["harvest"], ["hand-off", "--print"]):
            done = ran(mod, verb + ["--session", missing], state, scripts)
            check("%s refuses a chat it cannot read" % verb[0],
                  done.returncode, 2)
            contains("%s says why" % verb[0], done.stderr, "no transcript for")
        done = subprocess.run(
            [sys.executable, str(TARGET), "guard-archive"],
            input=json.dumps({"session_id": missing,
                              "tool_input": {"session_id": missing}}),
            capture_output=True, text=True, timeout=300,
            env=dict(os.environ, INTELLIGENCE_STATE_DIR=str(state),
                     INTELLIGENCE_TRANSCRIPTS=str(scripts)))
        check("the archive is refused over a chat nobody can read",
              done.returncode, 2)
        contains("the refusal names the chat", done.stderr, "no transcript for")

        # ------------------------------------------------- what a count means
        # An untracked directory is one thing somebody has to decide about.
        # Counted file by file, a vendored tree reads as six hundred findings
        # and hides the two beside it.
        vendored = repo / "vendored"
        vendored.mkdir()
        for name in ("one.py", "two.py", "three.py"):
            (vendored / name).write_text("held\n")
        check("an untracked directory counts once",
              mod.tree_findings(repo), ["2 uncommitted change(s)"])

        # ------------------------------------------------ one tree, one area
        # A worktree carries a branch and a pull request, and the walk that
        # knows about both is the one that should name it.
        home = tmp / "home"
        (home / "Development" / "plain" / ".git").mkdir(parents=True)
        (home / "Development" / "worktrees" / "site" / "tree" / ".git").mkdir(
            parents=True)
        was_home, was_trees = mod.HOME, mod.WORKTREES
        mod.HOME = home
        mod.WORKTREES = home / "Development" / "worktrees"
        check("a worktree is not also counted as a checkout",
              [t.name for t in mod.every_tree()], ["plain"])
        mod.HOME, mod.WORKTREES = was_home, was_trees

        # ------------------------------------------------ the mirror's names
        # The first line carries a count and the names are underneath it, so a
        # reading that keeps one line reports a number nobody can act on.
        bench = tmp / "tools"
        bench.mkdir()
        (bench / "archive.py").write_bytes(TARGET.read_bytes())
        # The copy loads the shared module beside itself and falls back on the
        # installed tree, and a checkout is exactly where there is no installed
        # tree to fall back on. Carrying the sibling is what makes the bench a
        # bench rather than a reading of this machine.
        (bench / "_lib.py").write_bytes((TARGET.parent / "_lib.py").read_bytes())
        (bench / "config-sync.py").write_text(
            "#!/usr/bin/env python3\n"
            "print('2 file(s) differ between this machine and the mirror:')\n"
            "print('  tools/one.py')\n"
            "print('  tools/two.py')\n"
            "print('Run: config-sync.py publish')\n"
            "raise SystemExit(1)\n")
        spec = importlib.util.spec_from_file_location(
            "benched", str(bench / "archive.py"))
        benched = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(benched)
        check("the mirror's findings name the files",
              benched.config_findings([]),
              ["2 file(s) differ between this machine and the mirror:",
               "tools/one.py", "tools/two.py"])

        # The sync answers for the whole config tree. Work in progress in a
        # second chat would otherwise refuse an ending it has nothing to do
        # with, which is the false positive that gets a gate switched off.
        held = tmp / "held"
        held.mkdir()
        (held / "archive.py").write_bytes(TARGET.read_bytes())
        (held / "_lib.py").write_bytes((TARGET.parent / "_lib.py").read_bytes())
        (held / "config-sync.py").write_text(
            "#!/usr/bin/env python3\n"
            "print('1 file(s) differ between this machine and the mirror:')\n"
            "print('  tools/archive.py')\n"
            "raise SystemExit(1)\n")
        spec = importlib.util.spec_from_file_location(
            "held_mirror", str(held / "archive.py"))
        scoped = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scoped)
        # The filter keeps only the names the config tree actually holds, so
        # the fixture owns that tree rather than reading whichever one the
        # machine has. A checkout has none, and the filter then keeps nothing
        # and reports every name the sync gave it.
        owned = tmp / "config-tree"
        (owned / "tools").mkdir(parents=True)
        (owned / "tools" / "archive.py").write_bytes(TARGET.read_bytes())
        scoped.CONFIG = owned
        mine = str(owned / "tools" / "archive.py")
        check("a file another chat moved is not answered for here",
              scoped.config_findings([]), [])
        check("a file the chat touched is still reported",
              scoped.config_findings([mine]),
              ["1 file(s) differ from the mirror:", "tools/archive.py"])

        # --------------------------------------------- what a refusal opens on
        # A refusal wants a fact written where the next run reads it. There is
        # no command for that, and a brevity command in the first position asks
        # the chat to be short about work it has not done.
        session = "aaaaaaaa-0000-0000-0000-000000000009"
        transcript(scripts, session, [
            denied("BLOCKED: this command opens a browser with a profile."),
            denied("BLOCKED: this command opens a browser with a profile."),
        ])
        done = ran(mod, ["hand-off", "--session", session, "--print"],
                   state, scripts)
        check("a refusal hands off", done.returncode, 0)
        check("a refusal does not open on a brevity command",
              "/short" in done.stdout, False)
        contains("a refusal settles as context", done.stdout, "--as context")

        # ------------------------------------------------- the name a chat has
        # A chat is named twice and the two names never match. The store keeps
        # a record under one id, the transcript carries another, and a single
        # field inside the record is where the pair meets. A lookup answering
        # with the first file it finds resolves whichever chat the app wrote
        # down first, and one that stops at a file it cannot parse resolves
        # nothing at all.
        session = "aaaaaaaa-0000-0000-0000-000000000012"
        registered(store, "another-chat", "beef",
                   {"sessionId": "local_beef",
                    "cliSessionId": "aaaaaaaa-0000-0000-0000-0000000000ff"})
        registered(store, "damaged", "cafe", "{ this is not json")
        registered(store, "this-chat", "face",
                   {"sessionId": "local_face", "cliSessionId": session})
        check("a record is found by the id the transcript carries",
              (mod.store_record(session) or {}).get("sessionId"), "local_face")
        check("a chat the app never registered has no record",
              mod.store_record("aaaaaaaa-0000-0000-0000-0000000000ee"), None)

        # A registered chat ends through the app's own archive call, so the
        # close resolves the name that call has to carry and stops there.
        # Reaching a process from this branch ends the chat before the call
        # that archives it is ever made.
        transcript(scripts, session, [said("that all looks right, thanks")])
        done = ran(mod, ["close", "--session", session], state, scripts)
        check("a registered chat closes on its store name", done.returncode, 0)
        contains("the close names the record the archive call wants",
                 done.stdout, "registered: local_face")
        contains("it names the call that ends the chat", done.stdout,
                 "archive_session")
        check("nothing is signalled for a chat that holds a record",
              "pid" in done.stdout, False)

        # ------------------------------------------------- the headless close
        # The background listing is the only place a headless chat appears,
        # and the entry under one id is what says which ending applies to it.
        # The listing is answered by a stand-in on the path, so every case
        # below reads processes of its own rather than the machine's.
        binaries = tmp / "bin"
        binaries.mkdir()
        listing = tmp / "agents.json"
        headless = "aaaaaaaa-0000-0000-0000-000000000013"
        foreground = "aaaaaaaa-0000-0000-0000-000000000014"
        known = "aaaaaaaa-0000-0000-0000-000000000016"
        quiet = "aaaaaaaa-0000-0000-0000-000000000017"
        listing.write_text(json.dumps([
            {"sessionId": foreground, "kind": "interactive", "pid": 4242423},
            {"sessionId": headless, "kind": "background", "pid": 4242424,
             "id": "a1b2c3", "name": "a headless run"},
            {"sessionId": known, "kind": "background", "pid": 4242425},
            {"sessionId": quiet, "kind": "background", "pid": 4242426}]))
        # The stand-in answers both calls the tool makes: the listing, and the
        # ending the listing owns. What it was asked to end is written down,
        # and a marker file is what makes it decline.
        route = tmp / "route.log"
        refusing = tmp / "refusing"
        stand_in = binaries / "claude"
        stand_in.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = agents ]; then cat \"%s\"; exit 0; fi\n"
            "echo \"$@\" >> \"%s\"\n"
            "if [ -f \"%s\" ]; then echo 'the route declines' >&2; exit 1; fi\n"
            "exit 0\n" % (listing, route, refusing))
        stand_in.chmod(0o755)
        listed = {"PATH": "%s:%s" % (binaries, os.environ.get("PATH", "")),
                  "INTELLIGENCE_ALLOW_ARCHIVE": "1"}
        with mock_env(dict(os.environ, **listed)):
            check("an id the listing carries places the session that holds it",
                  (mod.agent_entry(headless) or {}).get("kind"), "background")
            check("an id no listing carries places nothing",
                  mod.agent_entry("aaaaaaaa-0000-0000-0000-0000000000dd"),
                  None)

        # A suite reads a listing of processes belonging to the machine, so a
        # close that got as far as the signal here ends one of them.
        done = ran(mod, ["close", "--session", headless], state, scripts,
                   listed)
        check("a case suite reaches no process", done.returncode, 2)
        contains("the refusal says who the pid belongs to", done.stderr,
                 "a case suite may not end a session")

        # A chat somebody is sitting in front of holds neither ending: no
        # record for the archive call to reach, and a process that stopping
        # would take the person's window with it.
        done = ran(mod, ["close", "--session", foreground], state, scripts,
                   listed)
        check("a foreground chat is refused", done.returncode, 2)
        contains("the refusal says which endings apply", done.stderr,
                 "foreground")

        # Neither name places the chat. A close that guessed from here ends a
        # process belonging to something else.
        done = ran(mod, ["close", "--session",
                         "aaaaaaaa-0000-0000-0000-0000000000dd"],
                   state, scripts, listed)
        check("a chat in neither place is refused", done.returncode, 2)
        contains("the refusal says the chat cannot be placed", done.stderr,
                 "unplaceable")

        done = ran(mod, ["close"], state, scripts,
                   dict(listed, CLAUDE_CODE_SESSION_ID=""))
        check("a close with nothing naming the chat is refused",
              done.returncode, 2)
        contains("it says the chat is unnamed", done.stderr,
                 "no session to close")

        # A headless close makes no tool call, so the guard over the archive
        # call never sees it. The gate runs here or the way out of the skill
        # is also the way around it.
        session = "aaaaaaaa-0000-0000-0000-000000000015"
        transcript(scripts, session, [
            said("stop adding the retry count to the request"),
            said("never add the retry count to the request again"),
        ])
        done = ran(mod, ["close", "--session", session], state, scripts,
                   {"PATH": listed["PATH"], "INTELLIGENCE_ALLOW_ARCHIVE": ""})
        check("a chat still holding something does not close",
              done.returncode, 2)
        contains("the close refuses in the gate's own words", done.stderr,
                 "BLOCKED: the chat is still holding something.")

        # The listing owns the ending it reports, so the close asks for it by
        # the name the listing carries. A signal sent while that route works
        # ends a process the listing still believes it is holding. The call
        # that sends one is stood in for and the number handed to it is read
        # back, because a suite that lets one out ends something on the
        # machine.
        sent = []

        def catching(pid, number):
            sent.append((pid, number))

        alone = {k: v for k, v in os.environ.items()
                 if k not in mod.FIXTURE_ROOTS}
        alone.update(listed)

        def closing(session):
            spoke = io.StringIO()
            was_kill, os.kill = os.kill, catching
            try:
                with mock_env(alone), contextlib.redirect_stdout(spoke):
                    code = mod.cmd_close(["--session", session])
            finally:
                os.kill = was_kill
            return code, spoke.getvalue()

        code, spoke = closing(headless)
        check("a headless chat closes on the route the listing owns", code, 0)
        check("nothing is signalled while that route performs the ending",
              sent, [])
        asked = route.read_text() if route.is_file() else ""
        contains("the route is asked for the name the listing carries", asked,
                 "stop a1b2c3")

        # A listing that reports a session and will not end it leaves the
        # process running under a close that answered nothing, so the signal
        # is what a refusal falls through to.
        refusing.write_text("")
        code, spoke = closing(headless)
        check("a route that will not end the session falls through", code, 0)
        check("the pid the listing names is the one signalled", sent,
              [(4242424, signal.SIGTERM)])
        contains("the close says which process ends", spoke, "pid 4242424")

        # ------------------------------------------- what asks for an ending
        # The instruction reaches a transcript two ways, and a sentence about
        # the command is neither of them. Reading prose as an instruction
        # leaves a chat refused at every stop for a command nobody gave.
        marker = "<command-name>/archive</command-name>"
        check("a typed command asks for an ending",
              mod.asked_to_close([typed(marker)]), True)
        check("the same instruction in an opening prompt asks for one",
              mod.asked_to_close([said("/archive")]), True)
        check("prose about the command asks for nothing",
              mod.asked_to_close([said("run /archive once it is clean")]),
              False)
        check("a row carrying no content is read without complaint",
              mod.asked_to_close([{"type": "system"},
                                  {"message": {"content": None}},
                                  {"message": {"content": [None, "text"]}}]),
              False)

        # ----------------------------------------------- the chat left running
        # A headless chat told to close has no archive call to gate, so a
        # sentence saying the ending is unavailable ends nothing and the
        # session runs on. The stop is what refuses instead.
        def stopping(session, extra=None):
            env = dict(os.environ, INTELLIGENCE_STATE_DIR=str(state),
                       INTELLIGENCE_TRANSCRIPTS=str(scripts),
                       CLAUDE_CODE_SESSION_ID=session,
                       PATH=listed["PATH"], INTELLIGENCE_ALLOW_ARCHIVE="")
            env.update(extra or {})
            return subprocess.run(
                [sys.executable, str(TARGET), "guard-stop"],
                input=json.dumps({"session_id": session}),
                capture_output=True, text=True, timeout=300, env=env)

        transcript(scripts, headless, [typed(marker)])
        done = stopping(headless)
        check("a headless chat told to close cannot stop", done.returncode, 2)
        contains("the refusal says what is still running", done.stderr,
                 "BLOCKED: this chat was told to close and is still running.")
        contains("it names the chat", done.stderr, headless)
        contains("it names the process", done.stderr, "4242424")
        contains("it names the way through", done.stderr, "archive.py close")

        check("the override lets one stop through",
              stopping(headless, {"INTELLIGENCE_ALLOW_ARCHIVE": "1"})
              .returncode, 0)

        # A registered chat ends through the archive call, which carries its
        # own gate. Refusing the stop as well leaves the two gates answering
        # for one ending and no way past either.
        registered(store, "closing-chat", "feed",
                   {"sessionId": "local_feed", "cliSessionId": known})
        transcript(scripts, known, [typed(marker)])
        check("a registered chat stops on its own", stopping(known).returncode,
              0)

        # A foreground chat is a person's window, and the ending it was told
        # to make is the one the archive call performs.
        transcript(scripts, foreground, [typed(marker)])
        check("a foreground chat stops on its own",
              stopping(foreground).returncode, 0)

        # A stop is every reply a headless run makes. Refusing one over a
        # command nobody gave leaves a session that cannot answer anything.
        transcript(scripts, quiet, [
            said("run /archive on the other one when it is clean")])
        check("a headless chat nobody told to close stops on its own",
              stopping(quiet).returncode, 0)

        # ------------------------------------------------------ the collision
        # Two mechanisms refusing one reply on different grounds cannot both be
        # satisfied, and the run that walks into it decides which side to take
        # on its own and records nothing. One occurrence is the whole evidence:
        # both demands are down, and so is every draft that failed to meet them.
        session = "aaaaaaaa-0000-0000-0000-000000000009"
        transcript(scripts, session, [
            wrote("The paths and the values are in the table underneath."),
            feedback("Stop hook feedback: BLOCKED: the reply answers in the "
                     "vocabulary of the work."),
            wrote("Four stages, plain English, nothing named."),
            feedback("Stop hook feedback: BLOCKED: the opener owes a table of "
                     "paths and values."),
            wrote("A third draft between the two."),
        ])
        found = mod.candidates(session)
        collisions = [c for c in found if c["kind"] == "collision"]
        check("two grounds across a redraft raise a collision",
              len(collisions), 1)
        check("a collision wants precedence rather than another gate",
              collisions and collisions[0]["wants"], "precedence")
        check("a collision counts the mechanisms rather than the meetings",
              collisions and collisions[0]["count"], 2)

        # A collision needs the run to have answered the first ground before the
        # second lands. Refusals stacked with no draft between them are a list
        # of things wrong with one draft, not two rules pulling against it.
        session = "aaaaaaaa-0000-0000-0000-000000000010"
        transcript(scripts, session, [
            wrote("One draft."),
            feedback("Stop hook feedback: BLOCKED: the reply is the wrong shape."),
            feedback("Stop hook feedback: BLOCKED: the reply names a path."),
        ])
        check("refusals with no draft between them are not a collision",
              [c for c in mod.candidates(session) if c["kind"] == "collision"],
              [])

        # One firing reaches a transcript twice, as feedback on the turn it
        # stopped and again in the summary of the hooks that ran, cut to
        # different lengths. Keyed on the whole line it reads as two mechanisms.
        session = "aaaaaaaa-0000-0000-0000-000000000011"
        transcript(scripts, session, [
            wrote("A draft."),
            feedback("Stop hook feedback: BLOCKED: the reply names a path."),
            wrote("Another draft."),
            summary("BLOCKED: the reply names a path.\nHere is the list of "
                    "every path it named."),
        ])
        check("one firing written down twice is one ground",
              [c for c in mod.candidates(session) if c["kind"] == "collision"],
              [])

        # ------------------------------------------------------- what is kept
        # A guard that refuses once, is obeyed and never fires again raises
        # nothing, and the pair of drafts either side of it says exactly what
        # the machine wanted. Reading it and dropping it is the loss.
        session = "aaaaaaaa-0000-0000-0000-000000000012"
        transcript(scripts, session, [
            wrote("The draft it turned down."),
            feedback("Stop hook feedback: BLOCKED: a lone ground nobody repeats."),
            wrote("The draft that stood in its place."),
        ])
        check("a single refusal raises nothing", mod.candidates(session), [])
        kept = mod.read_evidence()["grounds"]
        pair = [h for h in kept.values()
                if "a lone ground" in h.get("ground", "")]
        check("the pair either side of it is kept anyway", len(pair), 1)
        check("the draft it refused is kept",
              pair and list(pair[0]["chats"].values())[0]["refused"],
              "The draft it turned down.")
        check("the draft that answered it is kept",
              pair and list(pair[0]["chats"].values())[0]["accepted"],
              "The draft that stood in its place.")

        # Held across sittings the same ground is a wall the runs keep meeting,
        # and no one sitting is where that becomes visible.
        for tail in ("13", "14"):
            other = "aaaaaaaa-0000-0000-0000-0000000000" + tail
            transcript(scripts, other, [
                wrote("A draft."),
                feedback("Stop hook feedback: BLOCKED: a lone ground nobody "
                         "repeats."),
                wrote("A better draft."),
            ])
            mod.candidates(other)
        found = mod.candidates(session)
        check("a ground met in enough chats is raised on that alone",
              [c["kind"] for c in found], ["recurrence"])
        check("a recurrence counts the chats", found[0]["count"], 3)
        check("a recurrence wants context", found[0]["wants"], "context")

        # ------------------------------------- what the opening message asked
        # The shape this catches is a message asking for several things and
        # getting some of them. Everything absent from a message where nothing
        # was carried out is a reading that cannot see the work, so the whole
        # message going unanswered raises nothing and half of it raises the
        # half.
        session = "aaaaaaaa-0000-0000-0000-000000000020"
        transcript(scripts, session, [
            said("Add a favicon to the marketing site. Also rename the pricing "
                 "tier from Starter to Basic everywhere it appears."),
            called("Write", {"file_path": "/tmp/site/favicon.ico"}),
            wrote("The favicon is in place at the site root."),
        ])
        found = mod.candidates(session)
        check("half a message answered raises the other half",
              [c["kind"] for c in found], ["omission"])
        contains("it names the ask that was dropped", found[0]["example"],
                 "rename the pricing tier")
        check("an omission wants the work rather than a mechanism",
              found[0]["wants"], "the work finished")

        session = "aaaaaaaa-0000-0000-0000-000000000021"
        transcript(scripts, session, [
            said("Add a favicon to the marketing site. Also rename the pricing "
                 "tier from Starter to Basic everywhere it appears."),
            called("Write", {"file_path": "/tmp/site/favicon.ico"}),
            called("Edit", {"file_path": "/tmp/site/pricing.tsx",
                            "old_string": "Starter", "new_string": "Basic"}),
            wrote("The favicon is in place and the tier now reads Basic."),
        ])
        check("a message answered whole raises nothing",
              mod.candidates(session), [])

        # A chat that answered in prose and touched nothing leaves no trace of
        # what it carried out, so an absence there is the reading failing to see
        # rather than the run failing to act.
        session = "aaaaaaaa-0000-0000-0000-000000000022"
        transcript(scripts, session, [
            said("Add a favicon to the marketing site. Also rename the pricing "
                 "tier from Starter to Basic everywhere it appears."),
            wrote("Both of those are worth doing."),
        ])
        check("a chat that did nothing is not read as a chat that dropped "
              "something", mod.candidates(session), [])

        # Somebody saying it themselves needs none of that machinery, and one
        # telling is the whole evidence: the cost was already paid by the person
        # who had to type it twice.
        session = "aaaaaaaa-0000-0000-0000-000000000023"
        transcript(scripts, session, [
            said("Wire up the newsletter form."),
            called("Write", {"file_path": "/tmp/site/form.js"}),
            wrote("The newsletter form posts to the endpoint."),
            said("you forgot the confirmation email"),
            wrote("Added."),
        ])
        found = mod.candidates(session)
        check("asking a second time is raised on one telling",
              [c["kind"] for c in found], ["omission"])
        contains("it carries the words somebody typed", found[0]["example"],
                 "confirmation email")

        # An omission leads the order. Everything else here is a reading about
        # how the work was done and this is the only one about whether it was
        # done at all.
        session = "aaaaaaaa-0000-0000-0000-000000000024"
        transcript(scripts, session, [
            said("Wire up the newsletter form."),
            called("Write", {"file_path": "/tmp/site/form.js"}),
            wrote("Done."),
            said("you forgot the confirmation email"),
            said("i told you the footer stays on every page"),
            said("i told you the footer stays on every page"),
        ])
        check("an omission outranks a rule with no gate behind it",
              [c["kind"] for c in mod.candidates(session)],
              ["omission", "correction"])

        # ------------------------------------------- the pass over what changed
        root = checkout(tmp / "tree")
        session = "aaaaaaaa-0000-0000-0000-000000000030"
        transcript(scripts, session, [worked_in(root)])
        rows = mod.rows_of(session)
        found = mod.polish_findings(rows, [root])
        check("a changed file is owed a pass", bool(found), True)
        contains("it names the file that changed", " ".join(found), "widget.py")

        done = ran(mod, ["polish", "--files", "--session", session],
                   state, scripts)
        contains("--files hands the diff over as paths", done.stdout,
                 "widget.py")

        done = ran(mod, ["polish", "--mark", "--session", session],
                   state, scripts)
        check("marking records the pass", done.returncode, 0)
        check("a marked file is owed nothing",
              mod.polish_findings(rows, [root]), [])

        # The mark is recorded against what the file holds rather than against
        # its name, so a file edited after its pass reopens on its own instead
        # of carrying a pass that covered work done afterwards.
        (root / "widget.py").write_text("value = 3\n")
        check("editing a marked file reopens it",
              bool(mod.polish_findings(rows, [root])), True)

        # Half the trees on the machine answer to no repository, so there is no
        # diff to read them out of. A file the transcript names that moved after
        # the chat opened moved because of the chat.
        loose = tmp / "loose"
        loose.mkdir()
        page = loose / "index.html"
        page.write_text("<p>one</p>\n")
        session = "aaaaaaaa-0000-0000-0000-000000000031"
        transcript(scripts, session, [
            {"type": "user", "origin": {"kind": "human"},
             "timestamp": "2000-01-01T00:00:00.000Z",
             "message": {"role": "user", "content": "Edit the page."}},
            called("Bash", {"command": "sed -i '' s/one/two/ %s" % page}),
        ])
        rows = mod.rows_of(session)
        check("a file outside any repository is still owed a pass",
              str(page) in mod.changed(rows, []), True)

        # The other half of the same rule. A file whose last change predates the
        # first mention of it was somebody else's work, however recent, and the
        # chat was reading it rather than writing it. Without this the set fills
        # with whatever a routine rewrote in the same minutes.
        theirs = loose / "other.html"
        theirs.write_text("<p>not mine</p>\n")
        session = "aaaaaaaa-0000-0000-0000-000000000033"
        transcript(scripts, session, [
            {"type": "user", "origin": {"kind": "human"},
             "timestamp": "2099-01-01T00:00:00.000Z",
             "message": {"role": "user", "content": "Look at the page."}},
            dict(called("Bash", {"command": "cat %s" % theirs}),
                 timestamp="2099-01-01T00:00:01.000Z"),
        ])
        rows = mod.rows_of(session)
        check("a file that moved before the chat reached it is not the chat's",
              str(theirs) in mod.changed(rows, []), False)

        # The diff empties the moment a branch lands or a mirror takes the file,
        # and neither of those is a pass. What entered the set stays in it.
        session = "aaaaaaaa-0000-0000-0000-000000000032"
        transcript(scripts, session, [worked_in(root)])
        rows = mod.rows_of(session)
        check("the change set is read once", bool(mod.changed(rows, [root],
                                                              session)), True)
        subprocess.run(["git", "-C", str(root), "add", "-A"],
                       capture_output=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "landed"],
                       capture_output=True)
        check("landing the work does not empty what the pass is owed",
              any(one.endswith("widget.py")
                  for one in mod.changed(rows, [root], session)), True)

        # ------------------------------------------------- reading the mirror
        # An empty answer is a mirror in step and None is a mirror nothing
        # could read. Reporting a tree that is fine as a tree nobody can see is
        # the one reading this tool cannot afford to get wrong.
        mod._SYNC[:] = [[]]
        check("a mirror in step raises nothing",
              mod.config_findings(["/nowhere"]), [])
        check("a mirror in step changes nothing",
              mod.config_changed(["/nowhere"]), set())
        mod._SYNC[:] = [None]
        check("a mirror nothing could read says so",
              mod.config_findings(["/nowhere"]),
              ["the mirror could not be read"])
        mod._SYNC[:] = []

        # ------------------------------------------------------------ usage
        for verb in ("", "frobnicate"):
            done = ran(mod, [verb] if verb else [], state, scripts)
            check("usage rejects %r" % verb, done.returncode, 2)

    for failure in FAILURES:
        print("FAIL %s" % failure)
    print("%d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
