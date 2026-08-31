#!/usr/bin/env python3
"""Cases the Sunday profile build has to get right.

The profile is the copy Sunday enforces from, and it is derived rather than
written, so every fault here is a rule that holds on one machine and not on the
others. Three shapes matter.

The renaming is a path rename, not a word rename. `.intelligence` as a path
component becomes Sunday's own directory; the same letters in prose, in the
repository's name, or inside a longer word are left alone, because a build that
rewrites those produces a profile naming repositories that do not exist.

The prune is what makes a retirement travel. A skill dropped here stays in a
profile nothing prunes, and Sunday goes on loading it everywhere. The two hand
written parts have no source to be missing from, so the prune has to know them
by name or it deletes the rules on every run.

Fixtures stay behind. A case file carrying a fake key reads as a real one to
anything scanning bytes, and the profile is the half that travels.

  sunday-profile-cases.py     run them
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "sunday-profile.py")


def load(target: Path):
    spec = importlib.util.spec_from_file_location("sunday_profile", target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(root: Path, rel: str, body: str = "x") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path


def run_build(live: dict[str, str], already: dict[str, str] | None = None,
              twice: bool = False):
    """Build a profile out of a made-up live tree and report what it holds."""
    module = load(TARGET)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source, dest = root / "live", root / "profile"
        for rel, body in live.items():
            write(source, rel, body)
        for rel, body in (already or {}).items():
            write(dest, rel, body)
        dest.mkdir(parents=True, exist_ok=True)
        module.INTELLIGENCE = source
        # The build reports every path it writes, which is the point of running
        # it by hand and only noise between one case and the next.
        with contextlib.redirect_stdout(io.StringIO()):
            module.build(dest, write=True)
            if twice:
                module.build(dest, write=True)
        held = sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())
        bodies = {rel: (dest / rel).read_text() for rel in held}
    return held, bodies


def renamed(body: str) -> str:
    module = load(TARGET)
    return module.renamed(body)


def built(live, already=None, twice=False):
    return run_build(live, already, twice)[0]


def body_of(live, rel):
    return run_build(live)[1][rel]


LIVE = {"skills/a/SKILL.md": "a", "tools/t.py": "t"}


CASES = [
    ("a path component is renamed onto Sunday's own directory",
     lambda: renamed('INTELLIGENCE = HOME / ".intelligence"'),
     'INTELLIGENCE = HOME / ".sunday/profile"'),
    ("a home-relative path is renamed too",
     lambda: renamed("~/.intelligence/tools/x.py"),
     "~/.sunday/profile/tools/x.py"),
    ("the environment prefix is renamed",
     lambda: renamed("INTELLIGENCE_ALLOW_INLINE=1"), "SUNDAY_ALLOW_INLINE=1"),
    ("the repository's own name is left alone",
     lambda: renamed("https://github.com/bradley-t-t/intelligence.git"),
     "https://github.com/bradley-t-t/intelligence.git"),
    ("the word in prose is left alone",
     lambda: renamed("the intelligence tree holds the rules"),
     "the intelligence tree holds the rules"),
    ("a live tree lands in the profile",
     lambda: built(LIVE), ["skills/a/SKILL.md", "tools/t.py"]),
    ("the rename reaches the files it writes",
     lambda: body_of({"tools/t.py": 'P = "~/.intelligence/x"'}, "tools/t.py"),
     'P = "~/.sunday/profile/x"'),
    ("a skill the live tree dropped is pruned",
     lambda: built(LIVE, already={"skills/gone/SKILL.md": "old"}),
     ["skills/a/SKILL.md", "tools/t.py"]),
    ("the hand-written rules are never pruned",
     lambda: built(LIVE, already={"gates/attribution.yaml": "rule"}),
     ["gates/attribution.yaml", "skills/a/SKILL.md", "tools/t.py"]),
    ("the sharing judgement is never pruned",
     lambda: built(LIVE, already={"share.yaml": "skills: []"}),
     ["share.yaml", "skills/a/SKILL.md", "tools/t.py"]),
    ("test fixtures do not travel",
     lambda: built({**LIVE, "tools/tests/t-cases.py": "key"}),
     ["skills/a/SKILL.md", "tools/t.py"]),
    ("a fixture already in the profile is pruned out of it",
     lambda: built(LIVE, already={"tools/tests/t-cases.py": "key"}),
     ["skills/a/SKILL.md", "tools/t.py"]),
    ("vendored skills do not travel",
     lambda: built({**LIVE, "skills/synced/v/SKILL.md": "v"}),
     ["skills/a/SKILL.md", "tools/t.py"]),
    ("a second build changes nothing",
     lambda: built(LIVE, twice=True), ["skills/a/SKILL.md", "tools/t.py"]),
]


def main() -> int:
    bad = 0
    for name, case, want in CASES:
        try:
            got = case()
        except Exception as err:                       # noqa: BLE001
            got = "raised %s" % err
        ok = got == want
        bad += not ok
        print("%s  %s" % ("pass" if ok else "FAIL", name))
        if not ok:
            print("    got  %r" % (got,))
            print("    want %r" % (want,))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
