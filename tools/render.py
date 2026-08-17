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


# Every string on the page that is prose rather than data. The table itself is
# almost entirely version numbers, and the column headers are tool names — "go",
# "docker" — which are identifiers, not words, so they are never translated.
#
# Both languages are generated as separate files rather than switched by script.
# nyrvo.dev keeps its copy in JavaScript, which suits a page whose content is
# copy; here the content is a table of facts, and a page that renders blank
# without JavaScript would be a worse trade for five sentences of prose.
COPY = {
    "en": {
        "lang": "en", "dir": "", "other": "pt/", "other_label": "Português",
        "title": "GitHub-hosted runners, as they actually are — Nyrvo",
        "description": "What GitHub Actions runner images actually contain: Go, Node, Python, Ruby, PHP, Rust, Java and Docker versions, captured daily with Nyrvo.",
        "og_description": "What GitHub Actions runner images actually contain, captured daily.",
        "h1": "GitHub-hosted runners, as they actually are",
        "lede1": """Every runner image below is captured once a day with
  <a href="https://github.com/nyrvo-dev/nyrvo">Nyrvo</a> and committed to
  <a href="https://github.com/nyrvo-dev/nyrvo-runners">a public repository</a>.
  A dash means the image does not carry that tool at all — which is worth
  knowing before a workflow assumes it does. A question mark means the probe
  did not answer in time, so whether the image carries that tool is unknown
  rather than ruled out.""",
        "lede2": """A commit exists only when something actually changed, so
  <code>git log</code> on that repository is the history. <strong>Changed</strong>
  below is the date each image last moved.""",
        "env_note": """Environment variable <em>names</em> are
  recorded too, in the linked JSON. Their values are not, and never were: Nyrvo
  does not read them, which is what makes publishing a runner's environment safe
  at all.""",
        "col_runner": "runner", "col_osarch": "os/arch",
        "col_docker": "docker", "col_changed": "changed",
        "unknown_title": "not measured: the probe did not answer in time",
        "repository": "Repository",
        "captured_with": "Captured with Nyrvo",
    },
    "pt": {
        "lang": "pt-BR", "dir": "pt/", "other": "", "other_label": "English",
        "title": "Os runners do GitHub, como eles realmente são — Nyrvo",
        "description": "O que as imagens de runner do GitHub Actions realmente contêm: versões de Go, Node, Python, Ruby, PHP, Rust, Java e Docker, capturadas todo dia com o Nyrvo.",
        "og_description": "O que as imagens de runner do GitHub Actions realmente contêm, capturado todo dia.",
        "h1": "Os runners do GitHub, como eles realmente são",
        "lede1": """Cada imagem de runner abaixo é capturada uma vez por dia com o
  <a href="https://github.com/nyrvo-dev/nyrvo">Nyrvo</a> e gravada em
  <a href="https://github.com/nyrvo-dev/nyrvo-runners">um repositório público</a>.
  Um traço significa que a imagem não traz aquela ferramenta — o que vale saber
  antes que um workflow assuma que ela está lá. Uma interrogação significa que a
  sonda não respondeu a tempo: não se sabe se a imagem tem a ferramenta, e isso
  não é o mesmo que saber que ela não tem.""",
        "lede2": """Um commit só existe quando algo mudou de fato, então o
  <code>git log</code> daquele repositório é o histórico. <strong>Mudou</strong>
  abaixo é a data em que cada imagem mudou pela última vez.""",
        "env_note": """Os <em>nomes</em> das variáveis de ambiente também são
  registrados, no JSON linkado. Os valores não são, e nunca foram: o Nyrvo não
  os lê, e é isso que torna seguro publicar o ambiente de um runner.""",
        # "runner" and the tool names stay as they are: they are identifiers
        # from GitHub and from the tools themselves, not words to translate.
        "col_runner": "runner", "col_osarch": "so/arch",
        "col_docker": "docker", "col_changed": "mudou",
        "unknown_title": "não medido: a sonda não respondeu a tempo",
        "repository": "Repositório",
        "captured_with": "Capturado com o Nyrvo",
    },
}


def cell(value, copy, unknown=False):
    """A value, or a marker saying which kind of nothing this is.

    An empty value is an absence Nyrvo observed; `unknown` says the probe never
    answered, so the absence was never observed at all. Reporting the second as
    the first is the untruth this argument exists to stop.

    `unknown` wins over any value that came with it. A snapshot that names a key
    as unmeasured is saying that key was not measured, whatever else the file
    carries for it, and printing that leftover as a reading would be the same
    kind of claim this is here to stop making.
    """
    if unknown:
        return (f'<span class="unknown" title="{html.escape(copy["unknown_title"])}">'
                "?</span>")
    return html.escape(value) if value else '<span class="none">—</span>'


def docker_cell(docker, unmeasured, copy):
    """The container tooling column: engine version, then compose.

    Compose gets its own half of the cell rather than being left to the linked
    JSON. It is the piece a compose-backed test suite actually depends on, and
    "this image ships no compose" is exactly the assumption a workflow makes
    wrongly. An absent compose is therefore printed as a dash rather than
    omitted, because a cell that simply stops after the engine version says
    nothing about whether the question was asked.

    daemon_running is treated as part of the engine reading: it is a bool with
    no third state, so a probe that ran out of time leaves a confident false
    behind, and "(no daemon)" would report a machine that was never asked as
    one whose daemon is down.
    """
    if not docker:
        return cell("", copy)
    engine_unknown = bool(unmeasured & {
        "docker.server_version", "docker.client_version", "docker.daemon_running"})
    engine = docker.get("server_version") or docker.get("client_version") or ""
    if engine and not engine_unknown and not docker.get("daemon_running"):
        engine += " (no daemon)"
    compose = cell(docker.get("compose_version", ""), copy,
                   "docker.compose_version" in unmeasured)
    return f"{cell(engine, copy, engine_unknown)} · compose {compose}"


def render_rows(rows, copy):
    out = []
    for label, snap in rows:
        system = snap.get("system") or {}
        versions = {r["name"]: r.get("version", "") for r in snap.get("runtimes", [])}
        # "<component>.<key>" entries the capture could not measure. Optional and
        # usually absent: a snapshot without it is one where everything answered.
        unmeasured = set(snap.get("unmeasured") or [])

        cells = "".join(
            f"<td>{cell(versions.get(name, ''), copy, f'runtime.{name}' in unmeasured)}</td>"
            for name in RUNTIMES
        )
        out.append(
            f'<tr><th scope="row"><a href="https://github.com/nyrvo-dev/nyrvo-runners'
            f'/blob/main/data/{html.escape(label)}/current.json">{html.escape(label)}</a></th>'
            f"<td>{cell(system.get('os'), copy, 'system.os' in unmeasured)}"
            f"/{cell(system.get('arch'), copy, 'system.arch' in unmeasured)}</td>"
            f"{cells}<td>{docker_cell(snap.get('docker') or {}, unmeasured, copy)}</td>"
            f'<td class="date">{cell(last_changed(label), copy)}</td></tr>'
        )
    return "\n".join(out)


TEMPLATE = """<!DOCTYPE html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<meta name="description" content="__DESCRIPTION__">
<link rel="canonical" href="https://runners.nyrvo.dev/__DIR__">
<link rel="alternate" hreflang="en" href="https://runners.nyrvo.dev/">
<link rel="alternate" hreflang="pt-BR" href="https://runners.nyrvo.dev/pt/">
<link rel="alternate" hreflang="x-default" href="https://runners.nyrvo.dev/">
<meta property="og:title" content="__H1__">
<meta property="og:description" content="__OGDESC__">
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
.topbar{display:flex;align-items:baseline;justify-content:space-between;gap:16px;margin-bottom:28px}
.topbar .brand{margin-bottom:0}
.langlink{font-family:var(--mono);font-size:13px;text-decoration:none}
.tablewrap{margin-top:32px;overflow-x:auto;border:1px solid var(--divider);border-radius:8px;background:var(--surface);
  scrollbar-width:thin;scrollbar-color:color-mix(in srgb, var(--accent) 45%, transparent) transparent}
.tablewrap::-webkit-scrollbar{height:8px}
.tablewrap::-webkit-scrollbar-track{background:transparent}
.tablewrap::-webkit-scrollbar-thumb{background:color-mix(in srgb, var(--accent) 35%, transparent);border-radius:99px;border:2px solid transparent;background-clip:padding-box}
table{border-collapse:collapse;width:100%;font-family:var(--mono);font-size:13px;white-space:nowrap}
th,td{padding:10px 14px;text-align:left;border-bottom:1px solid var(--divider)}
thead th{font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:var(--dim);font-weight:400}
tbody tr:last-child th,tbody tr:last-child td{border-bottom:0}
tbody th{font-weight:500}
tbody th a{text-decoration:none}
.none{color:var(--dim)}
.unknown{color:var(--dim);cursor:help}
.date{color:var(--dim)}
footer{border-top:1px solid var(--divider);margin-top:48px}
footer div{max-width:1180px;margin:0 auto;padding:24px;display:flex;flex-wrap:wrap;gap:16px 24px;font-size:13px;color:var(--dim)}
footer a{text-decoration:none}
</style>
</head>
<body>
<main class="wrap">
  <div class="topbar">
    <a class="brand" href="https://nyrvo.dev/"><span></span>nyrvo</a>
    <a class="langlink" href="https://runners.nyrvo.dev/__OTHER__" hreflang="__OTHERLANG__">__OTHERLABEL__</a>
  </div>
  <h1>__H1__</h1>
  <p class="lede">__LEDE1__</p>
  <p class="lede">__LEDE2__</p>

  <div class="tablewrap">
    <table>
      <thead><tr>
        <th scope="col">__COLRUNNER__</th><th scope="col">__COLOSARCH__</th>
        __HEADERS__
        <th scope="col">__COLDOCKER__</th><th scope="col">__COLCHANGED__</th>
      </tr></thead>
      <tbody>
__ROWS__
      </tbody>
    </table>
  </div>

  <p class="lede" style="margin-top:24px">__ENVNOTE__</p>
</main>
<footer><div>
  <a href="https://nyrvo.dev/">nyrvo.dev</a>
  <a href="https://github.com/nyrvo-dev/nyrvo-runners">__REPOSITORY__</a>
  <a href="https://github.com/nyrvo-dev/nyrvo">Nyrvo</a>
  <span>MIT</span>
  <span>__CAPTUREDWITH__ __VERSION__</span>
</div></footer>
</body>
</html>
"""


def render_page(rows, copy, version):
    """One language's page. Substitution is by __NAME__ rather than str.format
    because the template carries CSS, and every brace in it would have to be
    doubled for format to leave it alone."""
    headers = "".join(f'<th scope="col">{name}</th>' for name in RUNTIMES)
    page = TEMPLATE
    for key, value in {
        "__LANG__": copy["lang"], "__DIR__": copy["dir"],
        "__OTHER__": copy["other"], "__OTHERLABEL__": copy["other_label"],
        "__OTHERLANG__": COPY["pt" if copy["lang"] == "en" else "en"]["lang"],
        "__TITLE__": copy["title"], "__DESCRIPTION__": copy["description"],
        "__OGDESC__": copy["og_description"], "__H1__": copy["h1"],
        "__LEDE1__": copy["lede1"], "__LEDE2__": copy["lede2"],
        "__ENVNOTE__": copy["env_note"],
        "__COLRUNNER__": copy["col_runner"], "__COLOSARCH__": copy["col_osarch"],
        "__COLDOCKER__": copy["col_docker"], "__COLCHANGED__": copy["col_changed"],
        "__REPOSITORY__": copy["repository"], "__CAPTUREDWITH__": copy["captured_with"],
        "__HEADERS__": headers, "__ROWS__": render_rows(rows, copy),
        "__VERSION__": html.escape(version),
    }.items():
        page = page.replace(key, value)
    return page


def main():
    rows = load()
    if not rows:
        print("no snapshots in data/", file=sys.stderr)
        return 1
    version = sys.argv[1] if len(sys.argv) > 1 else "—"
    for code, copy in COPY.items():
        out = OUT.parent / copy["dir"] / "index.html" if copy["dir"] else OUT
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_page(rows, copy, version), encoding="utf-8")
        print(f"wrote {out} ({code}) from {len(rows)} snapshots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
