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

# The table is transposed: one row per tool, one column per runner. Runners are
# a fixed set that grows rarely while tools grow constantly, and a page scrolls
# down for free but not sideways — so the axis that grows is the one that runs
# down the page. The order below is fixed rather than derived from the data, so
# a runner that lacks a tool shows a gap in the same row as every other runner
# rather than shifting the table around.
RUNTIMES = ["go", "node", "python", "ruby", "php", "rust", "java", "dotnet"]
PACKAGE_MANAGERS = ["npm", "pnpm", "yarn", "composer"]

# Group sections in display order: a heading row, then one row per tool. The
# grouping is real markup — each group is its own <tbody> — not styling.
GROUPS = [
    ("system", ["os/arch"]),
    ("runtimes", RUNTIMES),
    ("package_managers", PACKAGE_MANAGERS),
    ("containers", ["docker engine", "docker compose"]),
    ("changed", ["changed"]),
]


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
# almost entirely version numbers, and the row labels are tool names — "go",
# "docker" — which are identifiers, not words, so they are never translated.
# The group headings are prose, so each language has its own.
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
  What each mark in the table means is spelled out beneath it: the three kinds
  of "no version here" are different facts about a machine, and a workflow that
  treats them alike is the reason this page exists.""",
        "lede2": """A commit exists only when something actually changed, so
  <code>git log</code> on that repository is the history. <strong>Changed</strong>
  below is the date each image last moved.""",
        "env_note": """Environment variable <em>names</em> are
  recorded too, in the linked JSON. Their values are not, and never were: Nyrvo
  does not read them, which is what makes publishing a runner's environment safe
  at all.""",
        # The group headings and the prose labels translate. The runner names
        # (column headers) and the tool names (row labels) stay as they are:
        # they are identifiers from GitHub and from the tools themselves, not
        # words to translate. "docker engine" and "docker compose" are product
        # names, kept as-is in both languages.
        "group_system": "system", "group_runtimes": "runtimes",
        "group_package_managers": "package managers", "group_containers": "containers",
        "group_changed": "changed",
        "row_osarch": "os/arch", "row_changed": "changed",
        "row_docker_engine": "docker engine", "row_docker_compose": "docker compose",
        "unknown_title": "not measured: the probe did not answer in time",
        "unusable_title": "installed, but would not report a version",
        "legend_none": "the image does not carry that tool",
        "legend_unknown": "the probe did not answer in time, so this is unknown rather than ruled out",
        "legend_unusable": "installed, but would not report a version",
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
  O que cada marca da tabela significa está logo abaixo dela: os três tipos de
  "sem versão aqui" são fatos diferentes sobre uma máquina, e tratar todos como
  iguais é justamente o motivo desta página existir.""",
        "lede2": """Um commit só existe quando algo mudou de fato, então o
  <code>git log</code> daquele repositório é o histórico. <strong>Mudou</strong>
  abaixo é a data em que cada imagem mudou pela última vez.""",
        "env_note": """Os <em>nomes</em> das variáveis de ambiente também são
  registrados, no JSON linkado. Os valores não são, e nunca foram: o Nyrvo não
  os lê, e é isso que torna seguro publicar o ambiente de um runner.""",
        # Os cabeçalhos de grupo e os rótulos prosaicos traduzem. Os nomes dos
        # runners (cabeçalhos de coluna) e os nomes das ferramentas (rótulos de
        # linha) ficam como estão: são identificadores do GitHub e das próprias
        # ferramentas, não palavras para traduzir. "docker engine" e "docker
        # compose" são nomes de produto, mantidos nos dois idiomas.
        "group_system": "sistema", "group_runtimes": "ambientes de execução",
        "group_package_managers": "gerenciadores de pacotes", "group_containers": "contêineres",
        "group_changed": "mudou",
        "row_osarch": "so/arch", "row_changed": "mudou",
        "row_docker_engine": "docker engine", "row_docker_compose": "docker compose",
        "unknown_title": "não medido: a sonda não respondeu a tempo",
        "unusable_title": "instalado, mas não informou a versão",
        "legend_none": "a imagem não traz aquela ferramenta",
        "legend_unknown": "a sonda não respondeu a tempo: não se sabe, e isso não é o mesmo que não ter",
        "legend_unusable": "instalado, mas não informou a versão",
        "repository": "Repositório",
        "captured_with": "Capturado com o Nyrvo",
    },
}


def cell(value, copy, unknown=False, unusable=False):
    """A value, or a marker saying which kind of nothing this is.

    There are three kinds, and collapsing any two of them is a lie about a real
    machine:

    An empty value is an absence Nyrvo observed — it looked, and the tool is not
    there. `unknown` says the probe never answered, so the absence was never
    observed at all. `unusable` says the binary was found on PATH and refused to
    report a version, usually because a pinned toolchain names something the
    image does not have; the tool IS installed.

    Printing an unusable tool as a dash would publish "this image does not have
    rust" about an image that has rust. This page has already published exactly
    that kind of claim once, about Docker compose on windows-latest.

    `unknown` wins over `unusable`, and both win over any value that came with
    them: a probe that never finished cannot also have refused, and a snapshot
    naming a key in either list is saying that key was not read, whatever else
    the file carries for it.
    """
    if unknown:
        return (f'<span class="unknown" title="{html.escape(copy["unknown_title"])}">'
                "?</span>")
    if unusable:
        return (f'<span class="unusable" title="{html.escape(copy["unusable_title"])}">'
                "!</span>")
    return html.escape(value) if value else '<span class="none">—</span>'


def engine_cell(docker, unmeasured, copy, unusable=frozenset()):
    """The container row for the engine version.

    Compose is its own row; this one is just the engine, and daemon_running is
    treated as part of the engine reading. It is a bool with no third state, so
    a probe that ran out of time leaves a confident false behind, and "(no
    daemon)" would report a machine that was never asked as one whose daemon is
    down.
    """
    if not docker:
        return cell("", copy)
    engine_keys = {"docker.server_version", "docker.client_version", "docker.daemon_running"}
    engine_unknown = bool(unmeasured & engine_keys)
    engine_unusable = bool(unusable & engine_keys)
    engine = docker.get("server_version") or docker.get("client_version") or ""
    # daemon_running is only trustworthy when the engine was actually read: an
    # unmeasured or refused probe leaves a confident false behind.
    if engine and not engine_unknown and not engine_unusable and not docker.get("daemon_running"):
        engine += " (no daemon)"
    return cell(engine, copy, engine_unknown, engine_unusable)


def compose_cell(docker, unmeasured, copy, unusable=frozenset()):
    """The container row for compose.

    Compose is its own row rather than fused into the engine cell: it is the
    piece a compose-backed test suite actually depends on, and "this image ships
    no compose" is exactly the assumption a workflow makes wrongly. An absent
    compose is therefore printed as a dash rather than omitted, because a cell
    that simply stops after the engine version says nothing about whether the
    question was asked.
    """
    if not docker:
        return cell("", copy)
    return cell(docker.get("compose_version", ""), copy,
                "docker.compose_version" in unmeasured,
                "docker.compose_version" in unusable)


# Row labels that are prose rather than tool names; the rest render untranslated.
ROW_LABELS = {
    "os/arch": "row_osarch",
    "docker engine": "row_docker_engine",
    "docker compose": "row_docker_compose",
    "changed": "row_changed",
}


def runner_context(label, snap):
    """Everything one row's cells need from one runner's snapshot."""
    return {
        "label": label,
        "system": snap.get("system") or {},
        # "<component>.<key>" entries the capture could not measure. Optional and
        # usually absent: a snapshot without it is one where everything answered.
        "unmeasured": set(snap.get("unmeasured") or []),
        # "<component>.<key>" entries whose tool was found and refused to answer.
        # Also optional, and absent from every snapshot captured before v0.2.0 —
        # the live data predates the field, so this must never assume it is there.
        "unusable": set(snap.get("unusable") or []),
        "versions": {r["name"]: r.get("version", "") for r in snap.get("runtimes", [])},
        "docker": snap.get("docker") or {},
    }


def tool_cell(name, runner, copy):
    """One cell in a tool row: the value for one runner."""
    if name == "os/arch":
        return (f"<td>{cell(runner['system'].get('os'), copy, 'system.os' in runner['unmeasured'], 'system.os' in runner['unusable'])}"
                f"/{cell(runner['system'].get('arch'), copy, 'system.arch' in runner['unmeasured'], 'system.arch' in runner['unusable'])}</td>")
    if name == "docker engine":
        return f"<td>{engine_cell(runner['docker'], runner['unmeasured'], copy, runner['unusable'])}</td>"
    if name == "docker compose":
        return f"<td>{compose_cell(runner['docker'], runner['unmeasured'], copy, runner['unusable'])}</td>"
    if name == "changed":
        return f'<td class="date">{cell(last_changed(runner["label"]), copy)}</td>'
    return (f"<td>{cell(runner['versions'].get(name, ''), copy, f'runtime.{name}' in runner['unmeasured'], f'runtime.{name}' in runner['unusable'])}</td>")


def tool_row(name, runners, copy):
    """One tool row: the sticky label, then one cell per runner."""
    label = copy[ROW_LABELS[name]] if name in ROW_LABELS else name
    cells = "".join(tool_cell(name, runner, copy) for runner in runners)
    return f'<tr><th scope="row" class="label">{html.escape(label)}</th>{cells}</tr>'


def render_groups(rows, copy):
    """The table body: a heading row and its tool rows per group."""
    runners = [runner_context(label, snap) for label, snap in rows]
    cols = len(runners) + 1
    out = []
    for group_key, tool_names in GROUPS:
        out.append("<tbody>")
        out.append(f'<tr class="group"><th scope="rowgroup" colspan="{cols}">'
                   f'{html.escape(copy[f"group_{group_key}"])}</th></tr>')
        out.extend(tool_row(name, runners, copy) for name in tool_names)
        out.append("</tbody>")
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
.legend{margin:16px 0 0;display:grid;grid-template-columns:auto 1fr;gap:6px 12px;align-items:baseline;
  font-size:14px;color:var(--dim)}
.legend dt{text-align:center;min-width:1.5em}
.legend dd{margin:0}
.tablewrap{margin-top:32px;overflow-x:auto;border:1px solid var(--divider);border-radius:8px;background:var(--surface);
  scrollbar-width:thin;scrollbar-color:color-mix(in srgb, var(--accent) 45%, transparent) transparent}
.tablewrap::-webkit-scrollbar{height:8px}
.tablewrap::-webkit-scrollbar-track{background:transparent}
.tablewrap::-webkit-scrollbar-thumb{background:color-mix(in srgb, var(--accent) 35%, transparent);border-radius:99px;border:2px solid transparent;background-clip:padding-box}
table{border-collapse:separate;border-spacing:0;width:100%;font-family:var(--mono);font-size:13px;white-space:nowrap}
th,td{padding:10px 14px;text-align:left;border-bottom:1px solid var(--divider)}
thead th{font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:var(--dim);font-weight:400}
/* The runner column headers are identifiers, so they keep their own case and size. */
thead th.runner{font-size:12px;letter-spacing:0;text-transform:none;color:var(--text);font-weight:500}
thead th.runner a{text-decoration:none}
/* The label column stays put while the runner columns scroll, so the row names
   remain readable on a narrow screen. Needs an opaque background, or the cells
   underneath would show through, and the separate border model so the sticky
   borders move with it. */
.label{position:sticky;left:0;background:var(--surface);border-right:1px solid var(--divider);z-index:1}
table>tbody:last-child>tr:last-child th,table>tbody:last-child>tr:last-child td{border-bottom:0}
tbody th{font-weight:500}
tbody tr.group th{font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:var(--dim);font-weight:400;background:color-mix(in srgb, var(--text) 6%, transparent)}
.none{color:var(--dim)}
.unknown{color:var(--dim);cursor:help}
.unusable{color:var(--accent);cursor:help}
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
        <th scope="col" class="label"></th>
        __HEADERS__
      </tr></thead>
__GROUPS__
    </table>
  </div>

  <dl class="legend">
    <dt><span class="none">&mdash;</span></dt><dd>__LEGEND_NONE__</dd>
    <dt><span class="unknown">?</span></dt><dd>__LEGEND_UNKNOWN__</dd>
    <dt><span class="unusable">!</span></dt><dd>__LEGEND_UNUSABLE__</dd>
  </dl>

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
    headers = "".join(
        f'<th scope="col" class="runner"><a href="https://github.com/nyrvo-dev/nyrvo-runners'
        f'/blob/main/data/{html.escape(label)}/current.json">{html.escape(label)}</a></th>'
        for label, snap in rows
    )
    page = TEMPLATE
    for key, value in {
        "__LANG__": copy["lang"], "__DIR__": copy["dir"],
        "__OTHER__": copy["other"], "__OTHERLABEL__": copy["other_label"],
        "__OTHERLANG__": COPY["pt" if copy["lang"] == "en" else "en"]["lang"],
        "__TITLE__": copy["title"], "__DESCRIPTION__": copy["description"],
        "__OGDESC__": copy["og_description"], "__H1__": copy["h1"],
        "__LEDE1__": copy["lede1"], "__LEDE2__": copy["lede2"],
        "__LEGEND_NONE__": html.escape(copy["legend_none"]),
        "__LEGEND_UNKNOWN__": html.escape(copy["legend_unknown"]),
        "__LEGEND_UNUSABLE__": html.escape(copy["legend_unusable"]),
        "__ENVNOTE__": copy["env_note"],
        "__REPOSITORY__": copy["repository"], "__CAPTUREDWITH__": copy["captured_with"],
        "__HEADERS__": headers, "__GROUPS__": render_groups(rows, copy),
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
