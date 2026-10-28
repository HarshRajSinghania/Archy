<!-- mcp-name: io.github.hslee16/archy -->

<p align="center"><img src="docs/assets/logo-wordmark.png" alt="archy" width="420"></p>

[![PyPI](https://img.shields.io/pypi/v/archy.svg)](https://pypi.org/project/archy/)
[![Python](https://img.shields.io/pypi/pyversions/archy.svg)](https://pypi.org/project/archy/)
[![CI](https://github.com/hslee16/archy/actions/workflows/ci.yml/badge.svg)](https://github.com/hslee16/archy/actions/workflows/ci.yml)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/pypi/l/archy.svg)](LICENSE)
[![Glama](https://glama.ai/mcp/servers/hslee16/archy/badges/score.svg)](https://glama.ai/mcp/servers/hslee16/archy)

> **Your folders show your architecture. Your imports decide it.**
> archy turns a Python import graph into something an agent can *use*: blast radius before an edit, the tests that edit affects, the modules most at risk. And it *fails* when the graph disagrees with the layers you declared. Same graph either way, as a CLI and an MCP server, every session and in CI.

## Read this first: I measured the premise, and it was wrong

I built archy after watching coding agents produce changes that passed review and rotted the import graph underneath. Then I measured whether that happens, and **it barely does.**

| measurement | subject | rate |
|---|---|---|
| 25 live agent runs on the riskiest SWE-bench tasks | cycles or declared-layer violations | **0%** (95% upper bound 12%) |
| 1,072 human commits, 11 repos | cycles introduced | **0.5%** per commit |
| 151 commit pairs in projects that declare an architecture | contract violations | **0.66%** per commit |
| 107 samples of those same projects over time | rules going stale, coverage eroding | **null on all four pre-registered signals** |
| 25 agents each building a backend to a specified architecture | wrong dependency direction | **12%**, and a checker in the loop took it to 0% |

So: the problem is real (I have watched a developer's own architecture rule get broken in the wild), and it is **rare, for agents and humans alike**. "Agents will rot your import graph" is a claim I made and have retracted. Nobody has measured what one occurrence costs, so I cannot argue "rare but expensive" either.

**The last row is the one that says what archy is for.** All 25 unaided agents produced the four layer directories correctly. Every failure was an import going the wrong way: entities reaching down into data access. They got the *layout* right and the *direction* wrong, and a directional rule caught all three cases at no cost to the API's behaviour.

That is the shape of the whole thing. **Layout is visible in a file tree. Direction, transitive reach and cycles are visible nowhere**, at any zoom level, in any single file. And a separate study found that once one of these lands it is *never repaired*: zero violations were resolved across the sampled corpus, and 2 of 14 repositories sat on broken contracts indefinitely. Rare and permanent, not rare and self-healing.

**What that means for what gets built.** Feature work premised on "agents will wreck your architecture" went off the table when that premise was retracted, and nothing since has put it back. What survives is narrower and has a number behind it: directional rules, transitive contracts and cycle detection, checked every session. That is a real job and archy does it. What the studies argue against is *more* of it: five of them produced no evidence that another feature is the missing piece, and the honest reading of headroom-limited results is that the next one will not be either.

So the roadmap that was closed in July stays closed, and being active again did not reopen it. Work here goes into the loop that survived rather than into the list that did not: making what archy already computes arrive where an agent will actually read it, and saying honestly what each answer does and does not cover. Bugs get fixed and contributions are welcome, as before.

The full write-up, including the six measurement artifacts that nearly turned a failed study into a success story, is in [docs/WHAT_DIDNT_WORK.md](docs/WHAT_DIDNT_WORK.md). If you only read one thing here, read that.

## The failure it catches

![archy catching a forbidden import](docs/assets/failure.png)

Nothing in that picture is derived. Which layer a module belongs to, and which direction is forbidden, are facts you write down in `archy.yaml`; archy only checks that the source still agrees with them.

Here is the failure it was built for, compressed into one line. This is archy's own source, under archy's own layer rules, with a single import of the kind an agent adds when it needs a helper and the nearest one is upward:

```python
# src/archy/graph.py
from archy.cli import main    # convenience import. The diff looks harmless.
```

```
$ uvx archy check .
# 1 layer violation(s) (config: archy.yaml)

graph -> cli (forbidden):
  archy.graph -> archy.cli  (line: 21)

$ echo $?
1

$ uvx archy cycles .
# 1 cycle(s) found

Cycle of 8 module(s):
  - archy.cli
  - archy.conventions
  - archy.duplicates
  - archy.graph
  - archy.index
  - archy.mcp
  - archy.simulate
  - archy.watcher

$ uvx archy score .
# archy score: 0.647          (0.656 before the edit)
...
acyclicity:  0.942  (1 cycles, tangle=0.058)
# graph: 139 modules, 264 edges     (263 before the edit)
```

One import, one edge. A forbidden layer edge, an eight-module cycle, and the score down 0.009. Nothing in the diff itself says any of that, and no amount of reading the file reveals it, because the rule that makes it a violation is not in the source. You supplied it.

Note the size of the score move. 0.009 is small, and that is the honest shape of this problem: no single edit looks alarming on the number. The cycle count going 0 to 1 and `check` exiting 1 are the signals that matter here, and the score is what catches the version of this that happens forty times over six weeks. Read [docs/SCORING.md](docs/SCORING.md) before treating the composite as a quality gate.

That example is a *direct* forbidden import, which is the easy case: an agent that reads `archy.yaml` first can catch it without archy. The harder and more honest case is a **transitive** violation, where the edit adds no forbidden import at all and reading the config tells you nothing. [docs/WALKTHROUGH.md](docs/WALKTHROUGH.md) is a one-command reproduction of that, and it states plainly which archy surfaces catch it (one) and which miss it (three).

Reproduce the example above on a checkout: add that import to `src/archy/graph.py`, then run the three commands **with the uvx prefix**. It has to be a separate archy, because that one import is a genuine runtime import cycle, and an editable-installed archy can no longer start to report on itself. `archy check` exits 1, which is what it does in CI and what the MCP server reports to an agent before it commits.

![transitive violation walkthrough](docs/assets/walkthrough.png)

**What archy is not:** a code-navigation tool. It will not help an agent find and read code faster; that job belongs to symbol-level, multi-language graph tools like [codegraph](https://github.com/colbymchenry/codegraph), and they are better at it. archy answers the other question: *you declared this codebase should have these layers, no cycles, and this score; is the agent's edit about to break that, and has the trend been sliding for six weeks?* Nothing in a navigation graph carries that intent, because intent is not in the source, you supply it.

The sharp version, re-checked against codegraph on 2026-07-27: it ships no cycle detection, no config in which to declare layers or forbidden edges, and no command that exits non-zero on a violation. It will happily *show* you that `models` imports `repositories` if you ask the right question. It cannot tell you that is wrong, because wrongness needs a declaration and there is nowhere to put one. **Descriptive tools answer questions; archy makes an assertion that breaks the build.** The two are both local MCP servers and compose fine; run them together. See [docs/research/CODEGRAPH_COMPETITIVE_ANALYSIS.md](docs/research/CODEGRAPH_COMPETITIVE_ANALYSIS.md) for the full comparison, including where archy loses and why this distinction is a choice they made rather than a wall they hit.

## Start in one command

uvx archy install     # detects Claude Code, Cursor, Codex, opencode, Continue and wires each one up

Nothing lands on your PATH: the config it writes runs `uvx archy mcp` on demand. Prefer a real install? `pip install archy`, `uv tool install archy`, or `pipx install archy`. Either way, try it on a project without installing anything:

```
uvx archy score .        # one-shot architectural health number
uvx archy cycles .       # import cycles, Tarjan SCCs plus self-loops
uvx archy check .        # layer rules from archy.yaml; exits 1 on violation
```

**Free, MIT licensed, no commercial version planned.** One maintainer, Python only. Built by [Alex Lee](https://github.com/hslee16/Archy).

**Status:** v0.50.1, working, installed and maintained. Usable today via:

| Mode | Command |
|---|---|
| Inspection | `archy graph`, `archy cycles` |
| CI governance | `archy check` (reads `archy.yaml`; `--contracts` nests the transitive import-linter verdict in the same output, reported, never gated) |
| Transitive contracts | `archy contracts` (reads `.importlinter` (canonical) or falls back to `archy.yaml`; requires `archy[contracts]`) |
| One-shot score | `archy score` |
| Trended score | `archy score --record` + `archy trend` |
| Refactor priority | `archy hotspots` (CC x git churn), `archy what-to-refactor-next` (fused hotspots + edit-risk) |
| Duplicate detection | `archy duplicates` (two-tier: likely duplicates vs demoted variants - same-class/boilerplate/test/vendored; advisory, not a score axis) |
| House style | `archy conventions` (naming families by home module, kind families by transitive base, `NAME = Ctor(...)` registries, mirrored surfaces, a gate inventory kept separate from user-error exits, model census, and the members a project's own `__all__` or docs leave out - derived from the source, so an agent stops guessing conventions; advisory, exits 0 on a successful report, and `--module NAME` switches to a complete, unranked lookup on one module - what it imports, what imports it, and whether it was set aside - which answers a negative the ranked report cannot; `--emit-headers` derives a per-module block (what it owns, what mirrors it, whether a finding here gates) from that same report and prints it, `--write` puts it in the module docstring, and `--check` exits 1 when one is stale) |
| Change coupling | `archy coupling` (module pairs that co-change in git history but share no import/call edge - hidden dependencies; source-only, advisory) |
| CI impact lookup | `archy affected` (`git diff` -> impacted modules + tests, depth-capped) |
| Human-facing export | `archy render --view dsm|trend` (one self-contained HTML file: no JS, no CDN, offline, byte-stable) |
| Pre-task briefing | `archy brief` (one screen composing conventions, layer coverage and the gate inventory for an agent to read BEFORE it starts, plus optional `--contracts`; advisory, always exits 0) |
| MCP server | `archy mcp` (cached: warm graph builds in seconds even on 10k+ module repos) |
| Parse cache | `archy index sync` / `archy index clear` (persistent `.archy/index.db`; transparent under the MCP server) |
| Agent install | `archy install` / `archy uninstall` (auto-detect Claude Code, Cursor, Codex, opencode, Continue; wire in or cleanly remove the MCP server) |

How the score is computed and how to read it: [docs/SCORING.md](docs/SCORING.md). Benchmarks against pydantic, fastapi, flask, pytest, and archy-on-archy: [docs/CASE_STUDIES.md](docs/CASE_STUDIES.md). Design rationale and comparison with sentrux: [docs/LEARNINGS.md](docs/LEARNINGS.md).

## In the wild

[ADOPTERS.md](ADOPTERS.md) is empty and no issue has yet been filed by anyone but me. Outside **pull requests** are a different story and recent: three landed on 2026-07-25, two merged. Good-first tickets are labelled and deliberately left for others.

If you are running archy on a real codebase I would like to hear what it found, especially if the answer is "nothing useful" - that answer is now supported by measurement rather than merely possible.

## Why

The failure at the top of this page is the whole reason archy exists: I wanted a single number per commit that would have caught it.

AI agents generate code at machine speed, and the reasoning went: without a feedback loop on *structural* health (module coupling, import cycles, layer violations), codebases drift architecturally even when every individual change looks fine in review.

**That reasoning is the part I tested and could not support.** Twenty-five agent runs produced zero structural regressions, and human commits break their own declared rules on 0.66% of commits. The drift may still be real over long horizons, which is not what a per-edit measurement can see, but I have no evidence for it and I am not going to assert it. The rest of this section is the case as I originally made it, kept because the citations are accurate even where my inference from them was not.

**Where a feedback loop did pay is narrower, and it is the moment code is written rather than the patrol afterwards.** Building a new backend to a specified architecture, 3 of 25 unaided agents got the dependency direction wrong; with a checker in the loop, none did, and the API behaved just as well. That is one model, one framework, and the mildest of the Constraint Decay paper's conditions, so it is not a general claim. It does say the loop is worth having at generation time, where the mistake is cheap to prevent and, per the decay study, never repaired afterwards.

![archy in the loop](docs/assets/in-the-loop.png)

What that buys you is placement: it runs in CI, in pre-commit, and as an MCP server (`archy mcp`), so a coding agent can read its own architectural impact before it commits rather than after review.

## Config

archy is configured by a `archy.yaml` in the project root (or a path you pass). The file is optional: without one, `archy check` does nothing and exits 0, and the other commands still work.

```yaml
layers:
  entities:
    modules:
      - "app.entities.**"
  use_cases:
    modules:
      - "app.use_cases.**"
  adapters:
    modules:
      - "app.adapters.**"

forbid:
  - {from: entities, to: use_cases}
  - {from: entities, to: adapters}
  - {from: use_cases, to: adapters}
```

**`layers:`** maps a short name to the modules that belong to it. The `modules:` list is a glob against the dotted module name, not a path. `app.entities.**` matches `app.entities` and everything under it; `app.entities.*` matches only the direct children.

**`forbid:`** is a list of directed edges that must not exist. `{from: entities, to: use_cases}` means no module in `entities` may import a module in `use_cases`. The check is on the direct edge; transitive violations are the job of `archy contracts`.

**`required:`** is the opposite: edges that must exist. Useful for "every use case must depend on an entity" or similar.

**`sdp:`** enables the Stable Dependencies Principle check. A module may not depend on a module that is less stable than it is (higher instability number). Instability is computed from the import graph.

**`exclude:`** is a list of path globs that archy must not descend into. Use it for vendored code, generated code, or test fixtures that are not part of the architecture under test.

```yaml
exclude:
  - "**/vendor/**"
  - "**/generated/**"
```

`exclude:` applies to every analysis (`graph`, `cycles`, `score`, `check`) and the equivalent MCP tools.

**Scan-size guard (`max_modules:`).** archy refuses to *start* a scan of a tree with more modules than a ceiling, so a stray vendored, cache, or generated directory that the named `exclude:` skips do not cover cannot silently wedge a scan for minutes. The default (10,000) sits well above the largest real projects; a scan that trips it stops with a message pointing at `exclude:` / a narrower path. Override or disable it:

```yaml
max_modules: 25000   # raise the ceiling for a genuinely large monorepo
# max_modules: 0     # disable the guard entirely
```

**Namespace packages (`roots:`).** archy discovers packages by walking `__init__.py` files. PEP 420 namespace packages (no `__init__.py`) are invisible by default. Declare them as roots so descendants get qualified names. A root is the package directory itself, not its parent.

```yaml
roots:
  - app           # `app/main.py` becomes `app.main`
  - src/service   # `src/service/db.py` becomes `service.db`
```

Without `roots:`, a project like `app/libs/db.py` (no `app/__init__.py`) is either skipped entirely or shows up as a top-level `libs.db`, which makes layer rules like `app.libs.**` match nothing.

On a multi-distribution namespace layout (`packages/core/src/acme/core/util.py` and `packages/web/src/acme/web/views.py`, no `__init__.py` under `acme/`) the choice of root decides the module names:

```yaml
# wrong: the intuitive import root
roots:
  - packages/core/src
# resulting module: src.acme.core.util
```

```yaml
# right: the package directory itself
roots:
  - packages/core/src/acme
# resulting module: acme.core.util
```

Several roots may end in the same name and merge into one namespace:

```yaml
roots:
  - packages/core/src/acme
  - packages/web/src/acme
# modules: acme.core.util, acme.web.views
```

(Verified with `archy graph . --format json` on a checkout of that layout.)

**Layer presence (`min_layers_present:`).** Forbidding edges *between* layers says nothing about whether the layers exist. A codebase that collapsed four layers into one module satisfies every `forbid` rule by having no cross-layer edges at all, and passes silently. Set a floor to catch that:

```yaml
min_layers_present: 3   # at least 3 of the declared layers must contain a module
```

Empty declared layers are reported either way, because every rule naming one is dead:

```console
$ uvx archy check .
# 0 layer violation(s) (config: archy.yaml)
#   layer coverage: 4 of 4 modules (100%), 0 of 0 internal edges (n/a)
#   empty layers: adapters
```

## MCP server

`archy mcp` is a stdio MCP server. It exposes the same analysis as the CLI, plus a few tools that are only useful in a session (blast radius of a proposed edit, the tests that edit would affect, a focused subgraph).

The server caches the graph. On a warm cache a 10k-module repo answers in seconds; the cold start is the scan. `archy index sync` builds the cache on demand so the first agent turn is not the slow one.

Install for a client with `archy install`. It detects Claude Code, Cursor, Codex, opencode and Continue and writes the config that runs `uvx archy mcp` on demand. Nothing is added to PATH.

## CLI reference

See `archy --help` and the individual command helps. The commands that exit non-zero on a finding (`check`, `cycles --strict`, `conventions --check`) are the ones that belong in CI. The rest are advisory.

## Development

```
uv sync
uv run ruff check
uv run ruff format --check
uv run ty check
uv run pytest
uv run archy check .
uv run archy cycles . --strict
uv run archy conventions . --emit-headers --check
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full set, including the no-em-dash rule.

## Security

See [SECURITY.md](SECURITY.md) for scope and response targets.

## License

MIT, see [LICENSE](LICENSE).
