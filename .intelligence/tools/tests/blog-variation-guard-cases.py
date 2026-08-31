#!/usr/bin/env python3
"""Cases the blog variation guard has to get right.

The guard is the door; the measure is `scripts/blog-variation.js` in the blog's
own repository, which is where the article format and the corpus live. So the
cases here hold the door: which edits it looks at, that the file it hands over
is the file the edit would have left behind, that a verdict of collision stops
the call, and that anything short of a verdict stops it too.

The measure's own cases -- a pair that must pass, a pair that must fail, and
the boundary counted exactly -- are `--self-test` inside the checker, run by
that repository's continuous integration. They are run here as well whenever a
checkout is reachable, along with a clean article and a recycled one driven
through the guard end to end.

  blog-variation-guard-cases.py        run them
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path(os.environ.get("INTELLIGENCE_TEST_TARGET")
              or Path(__file__).resolve().parent.parent / "blog-variation-guard.py")
HOME = Path.home()

FAILURES = []

# A checker honouring the contract and nothing else: it reports the verdict the
# case asks for and copies the candidate it was handed somewhere the case can
# read, which is how the reconstruction is checked without a corpus.
STUB = """#!/usr/bin/env node
import fs from 'node:fs'
const at = process.argv.indexOf('--candidate')
if (process.env.CASES_ECHO) fs.copyFileSync(process.argv[at + 1], process.env.CASES_ECHO)
if (process.env.CASES_VERDICT === 'crash') { console.error('checker fell over'); process.exit(3) }
if (process.env.CASES_VERDICT === 'collision') {
  console.log(JSON.stringify({ ok: false, bar: 0.1, collisions: [
    { draft: 'a-new-piece', against: 'one-already-published', where: 'published',
      score: 0.42, lifted: ['a run of words already on the blog'] }] }))
  process.exit(1)
}
console.log(JSON.stringify({ ok: true, bar: 0.1, collisions: [] }))
"""


def check(label, got, want):
    if got != want:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")


def run(payload, env=None):
    proc = subprocess.run([sys.executable, str(TARGET), "guard-edit"],
                          input=json.dumps(payload), capture_output=True, text=True,
                          env={**os.environ, **(env or {})})
    return proc.returncode, proc.stdout + proc.stderr


def fixture(root, checker=STUB, declared=True):
    """A project shaped like the blog's, with an article file and a checker."""
    blog = root / "src/app/data/blog"
    blog.mkdir(parents=True, exist_ok=True)
    scripts = {"test": "node scripts/blog-variation.js"} if declared else {}
    (root / "package.json").write_text(
        json.dumps({"name": "fixture", "type": "module", "scripts": scripts}) + "\n")
    (blog / "articles4.js").write_text("export const ARTICLES = [\n]\n")
    if checker is not None:
        (root / "scripts").mkdir(exist_ok=True)
        (root / "scripts" / "blog-variation.js").write_text(checker)
    return blog / "articles4.js"


def write_event(path, content):
    return {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": content}}


def door_cases(work):
    article = fixture(work / "repo")

    # Only the article data files, and only the tools that write one.
    check("a file outside the blog is not measured",
          run(write_event(work / "repo/src/app/App.jsx", "export default null"))[0], 0)
    check("a file beside the articles that is not one is not measured",
          run(write_event(work / "repo/src/app/data/blog/notes.md", "# notes"))[0], 0)
    check("a read is not an edit",
          run({"tool_name": "Read", "tool_input": {"file_path": str(article)}})[0], 0)

    check("a clear verdict lets the write through",
          run(write_event(article, "export const ARTICLES = []\n"),
              {"CASES_VERDICT": "clear"})[0], 0)

    code, output = run(write_event(article, "export const ARTICLES = []\n"),
                       {"CASES_VERDICT": "collision"})
    check("a collision stops the write", code, 2)
    check("the refusal names what it collided with",
          "one-already-published" in output, True)
    check("the refusal carries the score", "0.42" in output, True)
    check("the refusal quotes what was lifted",
          "a run of words already on the blog" in output, True)

    # The checker is handed the file the edit would have left behind, not the
    # fragment the edit carries.
    echo = work / "handed-over.js"
    article.write_text("export const ARTICLES = [\n  'first',\n]\n")
    code, _ = run({"tool_name": "Edit",
                   "tool_input": {"file_path": str(article),
                                  "old_string": "  'first',",
                                  "new_string": "  'first',\n  'second',"}},
                  {"CASES_VERDICT": "clear", "CASES_ECHO": str(echo)})
    check("an edit is measured", code, 0)
    handed = echo.read_text() if echo.exists() else ""
    check("the whole file reaches the checker", "'first'" in handed and "'second'" in handed, True)

    # An edit that would not apply is left to fail on its own terms.
    check("an edit whose anchor is missing is not judged",
          run({"tool_name": "Edit",
               "tool_input": {"file_path": str(article),
                              "old_string": "text that is not in the file",
                              "new_string": "anything"}},
              {"CASES_VERDICT": "collision"})[0], 0)

    # Fail closed: no verdict is not a pass.
    check("a checker that falls over stops the write",
          run(write_event(article, "export const ARTICLES = []\n"),
              {"CASES_VERDICT": "crash"})[0], 2)

    stripped = fixture(work / "no-checker", checker=None)
    code, output = run(write_event(stripped, "export const ARTICLES = []\n"))
    check("removing the checker a project calls for stops the write", code, 2)
    check("and says which file is missing", "scripts/blog-variation.js" in output, True)

    # A project that never declared the check is left alone, so a checkout cut
    # before the check existed does not have its whole blog frozen.
    never = fixture(work / "never-had-one", checker=None, declared=False)
    check("a project that never declared the check is left alone",
          run(write_event(never, "export const ARTICLES = []\n"))[0], 0)

    loose = work / "loose/src/app/data/blog/articles4.js"
    loose.parent.mkdir(parents=True, exist_ok=True)
    check("an article file in no project is left alone",
          run(write_event(loose, "export const ARTICLES = []\n"))[0], 0)

    check("the override lifts it",
          run(write_event(article, "export const ARTICLES = []\n"),
              {"CASES_VERDICT": "collision",
               "INTELLIGENCE_ALLOW_BLOG_DUPLICATE": "1"})[0], 0)


def real_checker():
    """A checkout of the blog, if this machine holds one."""
    named = os.environ.get("INTELLIGENCE_BLOG_CHECKER")
    if named and Path(named).is_file():
        return Path(named)
    roots = [HOME / "Development/WebstormProjects/taylorurl-com",
             Path("/home/user/taylorurl-com")]
    roots += sorted((HOME / "Development/worktrees/taylorurl-com").glob("*"))
    for root in roots:
        checker = root / "scripts/blog-variation.js"
        if checker.is_file():
            return checker
    return None


ARTICLE = """  {{
    slug: '{slug}',
    title: '{title}',
    excerpt: '{first}',
    category: 'Business',
    date: 'August 28, 2026',
    readTime: '5 min read',
    content: [
{body}
    ],
  }},
"""


def as_article(slug, title, sentences):
    body = "\n".join("      {{ type: 'p', text: '{0}' }},".format(line) for line in sentences)
    return ARTICLE.format(slug=slug, title=title, first=sentences[0], body=body)


def measure_cases(checker):
    """The measure itself, through the door, against the real blog."""
    proc = subprocess.run(["node", str(checker), "--self-test"],
                          capture_output=True, text=True, cwd=str(checker.parent.parent))
    check("the measure passes its own cases", proc.returncode, 0)
    if proc.returncode:
        FAILURES.append(f"  {(proc.stdout + proc.stderr).strip()}")

    blog = checker.parent.parent / "src/app/data/blog"
    articles = blog / "articles4.js"
    if not articles.is_file():
        FAILURES.append("the checkout has no articles4.js to write a draft into")
        return
    existing = articles.read_text()
    opened = existing.rstrip()[:-1].rstrip() + ",\n"

    fresh = as_article(
        "what-a-welder-puts-on-a-capability-page",
        "What a Welder Puts on a Capability Page",
        ["A general contractor comparing three fabrication shops wants the one that has already done the job.",
         "Aluminium to half an inch, stainless to a quarter, mild steel to an inch answers more email than a paragraph about craftsmanship.",
         "Where the bid needs a certified procedure, the shop without it on the page is skipped rather than asked."])
    check("an article the blog does not have is written",
          run(write_event(articles, opened + fresh + "]\n"))[0], 0)

    published = subprocess.run(
        ["node", "--input-type=module", "-e",
         "import { registerHooks } from 'node:module';"
         "registerHooks({ resolve(s, c, n) { return s.startsWith('.') && !/\\.[a-z]+$/i.test(s)"
         " ? n(s + '.js', c) : n(s, c) } });"
         "const m = await import(process.env.CORPUS);"
         "const p = m.BLOG_POSTS[0];"
         "console.log(JSON.stringify(p.content.filter(b => b.type === 'p').map(b => b.text)))"],
        capture_output=True, text=True,
        env={**os.environ, "CORPUS": str(blog / "index.js")})
    if published.returncode:
        FAILURES.append(f"could not read the blog to recycle it: {published.stderr.strip()}")
        return
    lines = [line.replace("'", " ").replace("\\", " ") for line in json.loads(published.stdout)]
    recycled = as_article("the-same-piece-again", "The Same Piece Again", lines)
    code, output = run(write_event(articles, opened + recycled + "]\n"))
    check("a published article written back under a new slug is refused", code, 2)
    check("and the refusal names the article it repeats",
          "the-same-piece-again repeats" in output, True)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        door_cases(work)

    checker = real_checker()
    if checker:
        measure_cases(checker)
    else:
        print("no taylorurl-com checkout here; the measure's own cases run in that repository")

    if not shutil.which("node"):
        FAILURES.append("node is not on the path, and the guard cannot run the checker without it")

    for failure in FAILURES:
        print(f"  {failure}")
    print(f"blog-variation-guard: {len(FAILURES)} failed" if FAILURES
          else "blog-variation-guard: all cases pass")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
