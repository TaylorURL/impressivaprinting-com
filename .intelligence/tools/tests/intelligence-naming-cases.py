#!/usr/bin/env python3
"""Cases the naming guard has to get right.

A retired configuration name is refused wherever one would be created -- a
Write onto one, a shell command that makes one, a session ending with one in
the tree -- while the aliases the harness resolves, the upstream names this
config does not own, and the files defining the mapping all stay untouched.
The scan, convert, sweep, install, and verify verbs answer for the rename
itself: a legacy path becomes a symlink onto the intelligence-named one and
every mention of one in text follows.

One legacy directory is exempt from all of it: the one the harness cuts its
worktrees into. Those are git checkouts registered by absolute path, so the
rename detaches them. Registration is the whole test, and the fixtures for it
are real repositories with real worktrees, so what the exemption reads is what
git actually prints.

Every retired name in this file is assembled from halves, so the file states
the shapes without carrying one. A cases file spelling them out would sit in
the config tree as the thing the tool exists to remove, and every later
guard-stop would refuse over it.

  intelligence-naming-cases.py        run them
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "intelligence-naming.py")

ESCAPE = "INTELLIGENCE_ALLOW_LEGACY_NAME"

LEGACY_DIR = ".cl" + "aude"
LEGACY_MD = "CL" + "AUDE.md"
LEGACY_HOME = "~/" + LEGACY_DIR
LEGACY_ENV = "CLA" + "UDE_STATE_DIR"
FOREIGN_JSON = LEGACY_DIR + ".json"

FAILURES = []


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def load():
    spec = importlib.util.spec_from_file_location("candidate", str(TARGET))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def clean_env(escape=False):
    env = dict(os.environ)
    env.pop(ESCAPE, None)
    if escape:
        env[ESCAPE] = "1"
    return env


def run_guard(verb, stdin, escape=False):
    p = subprocess.run([sys.executable, str(TARGET), verb], input=stdin,
                       capture_output=True, text=True, env=clean_env(escape))
    return p.returncode


def edit(path, body="", escape=False):
    payload = {"tool_input": {"file_path": path, "content": body}}
    return run_guard("guard-edit", json.dumps(payload), escape=escape)


def bash(command, escape=False):
    payload = {"tool_input": {"command": command}}
    return run_guard("guard-bash", json.dumps(payload), escape=escape)


def run_verb(verb, root):
    p = subprocess.run([sys.executable, str(TARGET), verb, str(root)],
                       capture_output=True, text=True, env=clean_env())
    return p


def redirect(mod, tmp):
    """Points every tree global at the temp directory, or refuses to run.

    A name the tool no longer has is not an error Python reports: setattr adds
    an attribute nobody reads, the verbs walk the real config tree, and the
    fixtures land in it for the next session's guards to trip over.
    """
    home = Path(tmp) / "home"
    config = home / ".intelligence"
    config.mkdir(parents=True, exist_ok=True)
    for name, value in (("HOME", home), ("INTELLIGENCE", config),
                        ("SETTINGS", config / "settings.json")):
        if not hasattr(mod, name):
            raise AssertionError(
                "%s exposes no %s global to redirect; these cases would touch "
                "the real config directory" % (TARGET, name))
        setattr(mod, name, value)
    for value in (home, config, mod.SETTINGS):
        assert str(value).startswith(tmp), "escaped the temp tree: %s" % value
    return home, config


def quiet(fn, argv, stdin=None):
    """Runs one command function with its terminal traffic held back."""
    out, err = io.StringIO(), io.StringIO()
    old_stdin = sys.stdin
    if stdin is not None:
        sys.stdin = io.StringIO(stdin)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            return fn(argv)
    finally:
        sys.stdin = old_stdin


def build_legacy(tmp):
    """A checkout carrying both retired path shapes and one text mention."""
    repo = Path(tmp) / "repo"
    (repo / LEGACY_DIR).mkdir(parents=True)
    (repo / LEGACY_DIR / "settings.json").write_text("{}\n")
    (repo / LEGACY_MD).write_text("memory\n")
    (repo / "notes.md").write_text("config sits in %s/tools\n" % LEGACY_HOME)
    return repo


def alias_fixture_edit():
    """An edit under an alias that resolves is an edit onto the real tree."""
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "proj"
        (proj / ".intelligence").mkdir(parents=True)
        os.symlink(".intelligence", proj / LEGACY_DIR)
        return edit(str(proj / LEGACY_DIR / "settings.json"), "{}\n")


def install_then_verify():
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        home, config = redirect(mod, tmp)
        (config / "INTELLIGENCE.md").write_text("memory\n")
        before = quiet(mod.cmd_verify, [])
        quiet(mod.cmd_install, [])
        after = quiet(mod.cmd_verify, [])
        aliased = ((home / LEGACY_DIR).is_symlink()
                   and (home / LEGACY_DIR).resolve() == config.resolve()
                   and (config / LEGACY_MD).is_symlink())
        return before, after, aliased


def verify_broken_alias():
    """A real file where the alias belongs is a retired name again."""
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        home, config = redirect(mod, tmp)
        (config / "INTELLIGENCE.md").write_text("memory\n")
        quiet(mod.cmd_install, [])
        (config / LEGACY_MD).unlink()
        (config / LEGACY_MD).write_text("drifted\n")
        return quiet(mod.cmd_verify, [])


def stop_case(offender=False, unwire=False, escape=False):
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        home, config = redirect(mod, tmp)
        (config / "INTELLIGENCE.md").write_text("memory\n")
        quiet(mod.cmd_install, [])
        if unwire:
            settings = json.loads(mod.SETTINGS.read_text())
            settings["hooks"]["Stop"] = []
            mod.SETTINGS.write_text(json.dumps(settings))
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if offender:
            (repo / LEGACY_MD).write_text("memory\n")
        held = os.environ.pop(ESCAPE, None)
        if escape:
            os.environ[ESCAPE] = "1"
        try:
            return quiet(mod.cmd_guard_stop, [],
                         stdin=json.dumps({"cwd": str(repo)}))
        finally:
            os.environ.pop(ESCAPE, None)
            if held is not None:
                os.environ[ESCAPE] = held


def sweep_case():
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        redirect(mod, tmp)
        if not hasattr(mod, "CHECKOUT_ROOTS"):
            raise AssertionError("no CHECKOUT_ROOTS global to redirect")
        roots = Path(tmp) / "roots"
        proj = roots / "proj"
        (proj / ".git").mkdir(parents=True)
        (proj / LEGACY_MD).write_text("memory\n")
        mod.CHECKOUT_ROOTS = (roots,)
        code = quiet(mod.cmd_sweep, [])
        converted = ((proj / "INTELLIGENCE.md").exists()
                     and (proj / LEGACY_MD).is_symlink())
        return code, converted


def alias_pairs_case():
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        home, config = redirect(mod, tmp)
        pairs = [(str(a), str(t)) for a, t in mod.alias_pairs()]
        want = [(str(home / LEGACY_DIR), str(config)),
                (str(config / LEGACY_MD), str(config / "INTELLIGENCE.md"))]
        return pairs, want


def git(repo, *args):
    """One git command in repo, under a fixed identity and no machine config."""
    env = dict(os.environ)
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=t@example.invalid",
         "-c", "user.name=Test", *args],
        capture_output=True, text=True, env=env,
    )


def git_repo(tmp):
    """A checkout carrying one commit, which is what a worktree is cut from."""
    repo = Path(tmp) / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "file.txt").write_text("one\n")
    git(repo, "add", "-A")
    done = git(repo, "commit", "-qm", "one")
    if done.returncode != 0:
        raise AssertionError("git commit failed: %s" % done.stderr.strip())
    return repo


def cut_worktree(repo, at, name):
    """Registers a worktree at a path, through the command the harness uses."""
    done = git(repo, "worktree", "add", "-q", str(at), "-b", name)
    if done.returncode != 0:
        raise AssertionError("git worktree add failed: %s" % done.stderr.strip())
    return at


def worktrees_registered(tmp):
    """The shape the harness leaves: worktrees git knows, under a retired name."""
    repo = git_repo(tmp)
    cut_worktree(repo, repo / LEGACY_DIR / "worktrees" / "one", "one")
    return repo, repo / LEGACY_DIR


def worktrees_registered_nested(tmp):
    """The same shape below the checkout root, where git still answers for it."""
    repo = git_repo(tmp)
    cut_worktree(repo, repo / "sub" / LEGACY_DIR / "worktrees" / "one", "one")
    return repo, repo / "sub" / LEGACY_DIR


def worktrees_registered_beside_settings(tmp):
    """Registered worktrees and configuration sharing one retired directory."""
    repo, entry = worktrees_registered(tmp)
    (entry / "settings.json").write_text("{}\n")
    (repo / "sub" / LEGACY_DIR).mkdir(parents=True)
    (repo / "sub" / LEGACY_DIR / "settings.json").write_text("{}\n")
    (repo / LEGACY_MD).write_text("memory\n")
    return repo, entry


def settings_only(tmp):
    """A retired directory holding configuration and no worktrees at all."""
    repo = git_repo(tmp)
    (repo / LEGACY_DIR).mkdir()
    (repo / LEGACY_DIR / "settings.json").write_text("{}\n")
    return repo, repo / LEGACY_DIR


def worktrees_unregistered(tmp):
    """The layout without the registration that makes it a set of checkouts."""
    repo = git_repo(tmp)
    (repo / LEGACY_DIR / "worktrees" / "one").mkdir(parents=True)
    return repo, repo / LEGACY_DIR


def worktrees_empty(tmp):
    """A worktrees directory holding nothing git could be detached from."""
    repo = git_repo(tmp)
    (repo / LEGACY_DIR / "worktrees").mkdir(parents=True)
    return repo, repo / LEGACY_DIR


def worktrees_mixed(tmp):
    """One registered checkout and one ordinary directory beside it."""
    repo, entry = worktrees_registered(tmp)
    (entry / "worktrees" / "two").mkdir()
    return repo, entry


def worktrees_deregistered(tmp):
    """A checkout git has stopped knowing about, its directory left standing."""
    repo, entry = worktrees_registered(tmp)
    shutil.rmtree(repo / ".git" / "worktrees" / "one")
    return repo, entry


def worktrees_registered_elsewhere(tmp):
    """Registered worktrees in the repository, none of them under this name."""
    repo = git_repo(tmp)
    cut_worktree(repo, repo / "elsewhere" / "one", "one")
    (repo / LEGACY_DIR / "worktrees" / "one").mkdir(parents=True)
    return repo, repo / LEGACY_DIR


def worktrees_is_a_file(tmp):
    """A retired directory whose worktrees entry is a file rather than a tree."""
    repo = git_repo(tmp)
    (repo / LEGACY_DIR).mkdir()
    (repo / LEGACY_DIR / "worktrees").write_text("one\n")
    return repo, repo / LEGACY_DIR


def outside_a_repository(tmp):
    """The worktree layout in a directory no repository covers."""
    root = Path(tmp) / "plain"
    (root / LEGACY_DIR / "worktrees" / "one").mkdir(parents=True)
    return root, root / LEGACY_DIR


def worktree_name_and_kind():
    """The verdict on an intelligence-named directory and on a retired file.

    The exemption answers for a retired directory. A directory already under
    its intelligence name has nothing to be renamed, and a file holds no
    checkouts whatever it is called.
    """
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        repo = git_repo(tmp)
        cut_worktree(repo, repo / ".intelligence" / "worktrees" / "one", "one")
        memory = repo / LEGACY_MD
        memory.write_text("memory\n")
        return (mod.agent_worktree_root(repo / ".intelligence"),
                mod.agent_worktree_root(memory))


def worktree_case(build):
    """The exemption's verdict on a fixture, and what the scan finds beside it."""
    mod = load()
    with tempfile.TemporaryDirectory() as tmp:
        root, entry = build(tmp)
        return (mod.agent_worktree_root(entry),
                sorted(str(p.relative_to(root)) for p in mod.offenders(root)))


def mirror_skill_cases(mod):
    """A skill the mirror does not ship belongs to the harness, not this config.

    Two temp trees rather than one: the answer is cached per config directory,
    which is what keeps a content sweep from listing the mirror once per file,
    and a mirror appearing underneath a cache already taken is not a state any
    real run reaches.

    The temp directory is resolved before it is handed over, because on this
    platform it is reached through a symlink and the ownership question measures
    against the resolved tree: built under the unresolved name, every fixture
    sits outside the config directory and answers yes to everything.
    """
    body = "hooks live in %s/settings.json\n" % LEGACY_DIR

    with tempfile.TemporaryDirectory() as raw:
        _, config = redirect(mod, str(Path(raw).resolve()))
        (config / "skills" / "design").mkdir(parents=True)
        (config / "skills" / "session-start-hook").mkdir(parents=True)
        ours = config / "skills" / "design" / "SKILL.md"
        theirs = config / "skills" / "session-start-hook" / "SKILL.md"
        ours.write_text(body)
        theirs.write_text(body)
        check("skills: no mirror on disk leaves every skill answerable",
              (mod.authored(ours), mod.authored(theirs)), (True, True))

    with tempfile.TemporaryDirectory() as raw:
        home, config = redirect(mod, str(Path(raw).resolve()))
        (config / "skills" / "design").mkdir(parents=True)
        (config / "skills" / "session-start-hook").mkdir(parents=True)
        ours = config / "skills" / "design" / "SKILL.md"
        theirs = config / "skills" / "session-start-hook" / "SKILL.md"
        ours.write_text(body)
        theirs.write_text(body)
        (home / "intelligence" / "skills" / "design").mkdir(parents=True)
        check("skills: the mirror ships this one, so its names are ours",
              mod.authored(ours), True)
        check("skills: the harness installed this one, so its names are not",
              mod.authored(theirs), False)
        found = [path for path, _ in mod.content_offenders(config)]
        check("skills: the sweep reports only what the mirror ships",
              found, [ours])


def main():
    mod = load()

    # guard-edit: a path carrying a retired component is refused, the
    # intelligence name beside it is not, and an alias that resolves counts as
    # the real tree.
    with tempfile.TemporaryDirectory() as tmp:
        proj = str(Path(tmp) / "proj")
        check("edit: legacy memory file",
              edit(proj + "/" + LEGACY_MD, "memory\n"), 2)
        check("edit: file under legacy directory",
              edit(proj + "/" + LEGACY_DIR + "/settings.json", "{}\n"), 2)
        check("edit: intelligence path",
              edit(proj + "/.intelligence/settings.json", "{}\n"), 0)
        check("edit: memory file under its own name",
              edit(proj + "/INTELLIGENCE.md", "memory\n"), 0)
        check("edit: escape overrides the path refusal",
              edit(proj + "/" + LEGACY_MD, "memory\n", escape=True), 0)
        check("edit: content naming a retired path",
              edit(proj + "/notes.md", "state in %s/state\n" % LEGACY_HOME), 2)
        check("edit: content naming the intelligence path",
              edit(proj + "/notes.md", "state in ~/.intelligence/state\n"), 0)
        check("edit: content naming an upstream file",
              edit(proj + "/notes.md", "cat ~/%s\n" % FOREIGN_JSON), 0)
        check("edit: the mapping owner names both sides by definition",
              edit(proj + "/intelligence-naming.py",
                   "CANON = {%r: 1}\n" % LEGACY_HOME), 0)
        check("edit: the alias marker exempts a file that builds the aliases",
              edit(proj + "/wire.sh",
                   "# %s\nln -s .intelligence %s\n"
                   % (mod.ALIAS_MARKER, LEGACY_DIR)), 0)
    check("edit: alias that resolves stays writable", alias_fixture_edit(), 0)
    check("edit: malformed event passes through",
          run_guard("guard-edit", "not json"), 0)

    mirror_skill_cases(mod)

    # guard-bash: creating a retired name is refused; reading one, a comment,
    # an upstream name, and ordinary commands stay allowed.
    check("bash: mkdir legacy directory", bash("mkdir -p " + LEGACY_DIR), 2)
    check("bash: touch legacy memory file", bash("touch " + LEGACY_MD), 2)
    check("bash: redirect into legacy memory file",
          bash("echo x > " + LEGACY_MD), 2)
    check("bash: mkdir intelligence directory", bash("mkdir -p .intelligence"), 0)
    check("bash: reading a legacy name", bash("cat " + LEGACY_MD), 0)
    check("bash: comment line", bash("# touch " + LEGACY_MD), 0)
    check("bash: upstream file", bash("touch " + FOREIGN_JSON), 0)
    check("bash: ordinary command", bash("git status"), 0)
    check("bash: escape overrides", bash("mkdir -p " + LEGACY_DIR, escape=True), 0)
    check("bash: malformed event passes through",
          run_guard("guard-bash", "not json"), 0)

    # guard-stop: a retired name in the checkout, or an unwired hook, holds the
    # session open; a clean tree with the wiring in place lets it end.
    check("stop: clean tree ends", stop_case(), 0)
    check("stop: retired name in the checkout refused", stop_case(offender=True), 2)
    check("stop: unwired hook refused", stop_case(unwire=True), 2)
    check("stop: escape overrides", stop_case(offender=True, escape=True), 0)

    # scan and convert: findings exit non-zero, the convert leaves symlinked
    # aliases and rewritten text, and a converted tree scans clean.
    with tempfile.TemporaryDirectory() as tmp:
        repo = build_legacy(tmp)
        p = run_verb("scan", repo)
        check("scan: legacy tree exits 1", p.returncode, 1)
        check("scan: names the paths", "path" in p.stdout and "content" in p.stdout,
              True)
    with tempfile.TemporaryDirectory() as tmp:
        clean = Path(tmp) / "repo"
        clean.mkdir()
        check("scan: clean tree exits 0", run_verb("scan", clean).returncode, 0)
    with tempfile.TemporaryDirectory() as tmp:
        repo = build_legacy(tmp)
        check("convert: exits 0", run_verb("convert", repo).returncode, 0)
        check("convert: directory renamed with alias",
              (repo / ".intelligence").is_dir() and (repo / LEGACY_DIR).is_symlink(),
              True)
        check("convert: memory file renamed with alias",
              (repo / "INTELLIGENCE.md").exists()
              and (repo / LEGACY_MD).is_symlink(), True)
        check("convert: text mention rewritten",
              "~/.intelligence/tools" in (repo / "notes.md").read_text(), True)
        check("convert: converted tree scans clean",
              run_verb("scan", repo).returncode, 0)

    # The worktree exemption. Renaming a retired directory detaches every
    # checkout registered under it by absolute path, so registration in
    # `git worktree list --porcelain` buys the directory a pass, and nothing
    # else does.
    check("worktree: registered worktrees exempt the directory",
          worktree_case(worktrees_registered), (True, []))
    check("worktree: the same shape below the root is exempt",
          worktree_case(worktrees_registered_nested), (True, []))
    check("worktree: registration outranks settings sharing the directory",
          worktree_case(worktrees_registered_beside_settings),
          (True, [LEGACY_MD, "sub/" + LEGACY_DIR]))
    check("worktree: settings and no worktrees directory is an offender",
          worktree_case(settings_only), (False, [LEGACY_DIR]))
    check("worktree: the layout git does not know is an offender",
          worktree_case(worktrees_unregistered), (False, [LEGACY_DIR]))
    check("worktree: a worktrees directory holding nothing is an offender",
          worktree_case(worktrees_empty), (False, [LEGACY_DIR]))
    check("worktree: one unregistered child costs the whole directory",
          worktree_case(worktrees_mixed), (False, [LEGACY_DIR]))
    check("worktree: the exemption lapses when git drops the registration",
          worktree_case(worktrees_deregistered), (False, [LEGACY_DIR]))
    check("worktree: worktrees registered elsewhere do not carry this one",
          worktree_case(worktrees_registered_elsewhere), (False, [LEGACY_DIR]))
    check("worktree: a worktrees file is not a worktrees directory",
          worktree_case(worktrees_is_a_file), (False, [LEGACY_DIR]))
    check("worktree: the layout outside a repository is an offender",
          worktree_case(outside_a_repository), (False, [LEGACY_DIR]))
    check("worktree: an intelligence name and a file are both outside it",
          worktree_name_and_kind(), (False, False))

    code, converted = sweep_case()
    check("sweep: exits 0", code, 0)
    check("sweep: converts the checkout it finds", converted, True)

    before, after, aliased = install_then_verify()
    check("verify: unwired settings fail", before, 1)
    check("verify: installed tree passes", after, 0)
    check("install: both aliases resolve", aliased, True)
    check("verify: alias replaced by a real file fails", verify_broken_alias(), 1)

    pairs, want = alias_pairs_case()
    check("aliases: the two names the harness resolves", pairs, want)

    # The rewrite touches retired paths only; upstream names ride through.
    check("rewrite: home path",
          mod.rewrite_content(LEGACY_HOME + "/tools/x.py\n"),
          ("~/.intelligence/tools/x.py\n", 1))
    check("rewrite: memory file name",
          mod.rewrite_content("read " + LEGACY_MD + "\n"),
          ("read INTELLIGENCE.md\n", 1))
    check("rewrite: environment prefix",
          mod.rewrite_content("export %s=/x\n" % LEGACY_ENV),
          ("export INTELLIGENCE_STATE_DIR=/x\n", 1))
    check("rewrite: upstream name beside a legacy path",
          mod.rewrite_content("claude-code reads %s/settings.json\n" % LEGACY_HOME),
          ("claude-code reads ~/.intelligence/settings.json\n", 1))
    check("rewrite: upstream file untouched",
          mod.rewrite_content("cat ~/%s\n" % FOREIGN_JSON),
          ("cat ~/%s\n" % FOREIGN_JSON, 0))

    check("hits: legacy path found",
          len(mod.content_hits("state in %s/state\n" % LEGACY_HOME)), 1)
    check("hits: upstream-only text clean",
          mod.content_hits("cat ~/%s\n" % FOREIGN_JSON), [])
    check("hits: the alias marker exempts the file",
          mod.content_hits(mod.ALIAS_MARKER + "\n" + LEGACY_HOME + "\n"), [])

    p = subprocess.run([sys.executable, str(TARGET), "nope"],
                       capture_output=True, text=True, env=clean_env())
    check("cli: unknown verb exits 2 with usage",
          (p.returncode, "scan" in p.stderr), (2, True))

    # A heredoc is the other way a file gets authored, and it has to answer to
    # the same content check as an edit. It did not on 2026-08-28: the guard
    # refused a retired literal written through Edit and allowed the identical
    # string written through Bash, and the copy that got through failed every
    # cloud routine's setup for an hour. Each case below pairs the two paths, so
    # they cannot drift apart again without a case saying so.
    LITERAL = 'SKIP = ("INTELLIGENCE.md", "%s")\n' % LEGACY_MD
    MARKED = mod.ALIAS_MARKER + "\nThe alias is %s.\n" % LEGACY_MD

    def by_bash(command):
        return bash(command)

    def by_edit(path, content):
        return edit(path, content)

    def heredoc(target, body):
        return "cat > %s <<'EOF'\n%sEOF" % (target, body)

    check("a retired literal through Bash is refused",
          by_bash(heredoc("tools/x.py", LITERAL)), 2)
    check("and through Edit, the same",
          by_edit("tools/x.py", LITERAL), 2)
    check("the alias marker exempts a heredoc",
          by_bash(heredoc("docs/naming.md", MARKED)), 0)
    check("and exempts an edit, the same",
          by_edit("docs/naming.md", MARKED), 0)
    check("a heredoc carrying no retired name passes",
          by_bash(heredoc("tools/x.py", 'SKIP = re.compile(r"^[A-Z_]+\\.md$")\n')), 0)
    check("a command with no heredoc is untouched",
          by_bash("git status && echo done"), 0)
    check("a heredoc body is read even after an unrelated line",
          by_bash("echo starting\n" + heredoc("tools/x.py", LITERAL)), 2)

    for f in FAILURES:
        print(f"FAIL {f}")
    print(f"{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
