# nyrvo-runners

A daily record of what GitHub-hosted runner images actually contain, captured
with [Nyrvo](https://github.com/nyrvo-dev/nyrvo).

Runner images change without announcing it. Node moves a minor version, a
toolchain disappears, Docker's compose plugin jumps — and you find out when a
build that passed on Tuesday fails on Wednesday for no reason you can see in
your own diff. This repository exists to make that a dated event instead of a
mystery.

## Git is the database

There is no server here, and no database. Each runner label has exactly one
file:

```
data/ubuntu-latest/current.json
data/macos-latest/current.json
…
```

The file always holds the latest observation. **The history is the git
history**, which means `git log -p` is the feed:

```
git log -p --follow data/ubuntu-latest/current.json
```

One file per label rather than one per day is a deliberate choice. Committing a
dated snapshot every morning would grow this repository forever and bury the
handful of days that mattered under a year of identical ones. Storing only the
current state means a commit exists **only when something changed**, so the log
carries events rather than heartbeats, and "when did this change?" becomes a
question git answers natively.

## How a day works

A scheduled workflow captures every label in parallel, uploads each snapshot as
an artifact, and a single final job normalises them and makes at most one
commit. Six jobs pushing to one branch would race; one commit a day also reads
better, because the diff shows everything that moved together.

Three details that are load-bearing rather than incidental:

- **The capture does not run inside a checkout.** A Nyrvo snapshot describes the
  directory it runs in as well as the machine, so inside this repository it
  would record this repository's own commit and read its files as declared
  requirements. Every snapshot would then churn on data about itself. An empty
  directory yields the runner and nothing else.
- **`created_at` is dropped before storing.** It changes on every run, so
  keeping it would produce a commit a day whether or not a runner drifted. The
  commit's own date already records when we looked.
- **The Nyrvo version is pinned.** If this tracked the latest release, a change
  in the tool would look exactly like a change in a runner and the dataset would
  stop meaning what it claims. Bumping it is its own commit, so that commit is
  the one to blame when every label moves at once.

## What a snapshot contains

Operating system, architecture and kernel; the versions and install paths of
Go, npm, Node, Python, Ruby, PHP, Rust and Java; Docker's client, server and
compose versions and whether the daemon answers; the images of any running
containers; and the **names** of environment variables.

Never the values of environment variables. Nyrvo does not record them, which is
why publishing a runner's environment here is safe at all.

## What would prove this worth keeping

After roughly a month, three things should be true: no job broke unattended, at
least one real drift was captured, and this repository answers "when did node
change on ubuntu-latest?" faster than reading the runner image changelog.

If nothing drifts on any runner in a month, that is worth knowing too, and
cheaper to learn here than by building anything larger on the assumption.

## Licence

MIT for the tooling. The captured data describes public GitHub-hosted runner
images and is published as fact rather than claimed as property.
