#!/usr/bin/env python3
"""Render the captured runner snapshots into a static page.

Standard library only, and no template engine: the input is a handful of small
JSON files and the output is one HTML file. A dependency here would have to be
installed on the runner that generates the page, which is the same machine class
this project exists to be suspicious of.

The page states the current contents of each runner image. It deliberately does
not present a history yet: the history lives in git, and a feed with one entry
advertises its own emptiness.
"""

import html
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "docs" / "index.html"

# The order runtimes appear in the table. Fixed rather than derived from the
# data, so a runner that lacks one shows a gap in the same column as every
# other runner rather than shifting the table around.
RUNTIMES = ["go", "node", "npm", "python", "ruby", "php", "rust", "java"]


def load():
    rows = []
    for path in sorted(DATA.glob("*/current.json")):
        with path.open(encoding="utf-8") as f:
            snap = json.load(f)
        rows.append((path.parent.name, snap))
    return rows


def last_changed(label):
    """The date this label's image last actually changed.

    Read from git rather than stored in the file: a commit exists only when a
    runner drifted, so the commit date is the drift date. Storing a timestamp in
    the snapshot would make every day look like a change.

    A file that differs from HEAD right now changed today and has not been
    committed yet — this runs before the commit. Without that case the page
    would date every fresh drift to the previous one, which is exactly the
    question it exists to answer, answered wrongly by a day.
    """
    path = f"data/{label}/current.json"
    try:
        pending = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", path],
            cwd=ROOT, capture_output=True,
        ).returncode != 0
        if pending:
            return subprocess.run(
                ["date", "-u", "+%Y-%m-%d"], capture_output=True, text=True, check=True,
            ).stdout.strip()
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", path],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out or "—"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "—"


def cell(value):
    return html.escape(value) if value else '<span class="none">—</span>'


def render_rows(rows):
    out = []
    for label, snap in rows:
        system = snap.get("system") or {}
        versions = {r["name"]: r.get("version", "") for r in snap.get("runtimes", [])}
        docker = snap.get("docker") or {}
        docker_text = ""
        if docker:
            docker_text = docker.get("server_version") or docker.get("client_version") or ""
            if docker_text and not docker.get("daemon_running"):
                docker_text += " (no daemon)"

        cells = "".join(f"<td>{cell(versions.get(name, ''))}</td>" for name in RUNTIMES)
        out.append(
            f'<tr><th scope="row"><a href="https://github.com/nyrvo-dev/nyrvo-runners'
            f'/blob/main/data/{html.escape(label)}/current.json">{html.escape(label)}</a></th>'
            f"<td>{cell(system.get('os'))}/{cell(system.get('arch'))}</td>"
            f"{cells}<td>{cell(docker_text)}</td>"
            f'<td class="date">{cell(last_changed(label))}</td></tr>'
        )
    return "\n".join(out)


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GitHub-hosted runners, as they actually are — Nyrvo</title>
<meta name="description" content="What GitHub Actions runner images actually contain: Go, Node, Python, Ruby, PHP, Rust, Java and Docker versions, captured daily with Nyrvo.">
<link rel="canonical" href="https://runners.nyrvo.dev/">
<meta property="og:title" content="GitHub-hosted runners, as they actually are">
<meta property="og:description" content="What GitHub Actions runner images actually contain, captured daily.">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' rx='3' fill='%23161826'/%3E%3Crect x='4' y='4' width='8' height='8' rx='2' fill='%239184d9'/%3E%3C/svg%3E">
<style>
/* Same rule as nyrvo.dev: nothing is loaded from anyone else. */
:root{
  --bg:#161826; --surface:#232532; --text:#e9e9ed; --accent:#9184d9;
  --divider:color-mix(in srgb, #e9e9ed 16%, transparent); --dim:#9397ab;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
  --body:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
}
@media (prefers-color-scheme: light){
  :root{ --bg:#f3f5fe; --surface:#e4e7f5; --text:#292b31; --accent:#5d5294;
    --divider:color-mix(in srgb, #292b31 18%, transparent); --dim:#75798c; }
}
*,*::before,*::after{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--body);font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:48px 24px}
a{color:var(--accent);text-underline-offset:3px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
h1{font-size:clamp(26px,4vw,38px);letter-spacing:-0.02em;line-height:1.1;margin:0 0 16px;font-weight:500}
.lede{max-width:64ch;line-height:1.65;text-wrap:pretty;color:color-mix(in srgb, var(--text) 80%, transparent);margin:0 0 10px}
.brand{font-family:var(--mono);font-size:15px;text-decoration:none;color:var(--text);display:inline-flex;align-items:center;gap:9px;margin-bottom:28px}
.brand span{width:9px;height:9px;background:var(--accent);display:block;border-radius:2px}
.tablewrap{margin-top:32px;overflow-x:auto;border:1px solid var(--divider);border-radius:8px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-family:var(--mono);font-size:13px;white-space:nowrap}
th,td{padding:10px 14px;text-align:left;border-bottom:1px solid var(--divider)}
thead th{font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:var(--dim);font-weight:400}
tbody tr:last-child th,tbody tr:last-child td{border-bottom:0}
tbody th{font-weight:500}
tbody th a{text-decoration:none}
.none{color:var(--dim)}
.date{color:var(--dim)}
footer{border-top:1px solid var(--divider);margin-top:48px}
footer div{max-width:1180px;margin:0 auto;padding:24px;display:flex;flex-wrap:wrap;gap:16px 24px;font-size:13px;color:var(--dim)}
footer a{text-decoration:none}
</style>
</head>
<body>
<main class="wrap">
  <a class="brand" href="https://nyrvo.dev/"><span></span>nyrvo</a>
  <h1>GitHub-hosted runners, as they actually are</h1>
  <p class="lede">Every runner image below is captured once a day with
  <a href="https://github.com/nyrvo-dev/nyrvo">Nyrvo</a> and committed to
  <a href="https://github.com/nyrvo-dev/nyrvo-runners">a public repository</a>.
  A dash means the image does not carry that tool at all — which is worth
  knowing before a workflow assumes it does.</p>
  <p class="lede">A commit exists only when something actually changed, so
  <code>git log</code> on that repository is the history. <strong>Changed</strong>
  below is the date each image last moved.</p>

  <div class="tablewrap">
    <table>
      <thead><tr>
        <th scope="col">runner</th><th scope="col">os/arch</th>
        __HEADERS__
        <th scope="col">docker</th><th scope="col">changed</th>
      </tr></thead>
      <tbody>
__ROWS__
      </tbody>
    </table>
  </div>

  <p class="lede" style="margin-top:24px">Environment variable <em>names</em> are
  recorded too, in the linked JSON. Their values are not, and never were: Nyrvo
  does not read them, which is what makes publishing a runner's environment safe
  at all.</p>
</main>
<footer><div>
  <a href="https://nyrvo.dev/">nyrvo.dev</a>
  <a href="https://github.com/nyrvo-dev/nyrvo-runners">Repository</a>
  <a href="https://github.com/nyrvo-dev/nyrvo">Nyrvo</a>
  <span>MIT</span>
  <span>Captured with Nyrvo __VERSION__</span>
</div></footer>
</body>
</html>
"""


def main():
    rows = load()
    if not rows:
        print("no snapshots in data/", file=sys.stderr)
        return 1
    headers = "".join(f'<th scope="col">{name}</th>' for name in RUNTIMES)
    version = sys.argv[1] if len(sys.argv) > 1 else "—"
    page = (TEMPLATE
            .replace("__HEADERS__", headers)
            .replace("__ROWS__", render_rows(rows))
            .replace("__VERSION__", html.escape(version)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} from {len(rows)} snapshots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
