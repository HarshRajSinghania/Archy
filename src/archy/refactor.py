"""Fused refactor-priority ranking: hotspots x edit-risk in one list.

archy already ships two refactor-priority signals through separate tools,
each with a different lens:

* The behavioral lens (``archy_what_to_refactor_next(lens=\"behavioral\")``,
  formerly ``archy_hotspots``) is cyclomatic complexity x git churn
  (Tornhill / CodeScene's "Code Red"). It answers "where is the
  refactoring leverage?" and needs git history.
* The structural lens (``archy_what_to_refactor_next(lens=\"structural\")``,
  formerly ``archy_high_risk_modules``) is the ``edit_risk`` composite
  (geometric mean of propagation cost, normalized fan-in, and instability).
  It answers "is this edit dangerous?" and needs no git.

An agent asked "what should I clean up first?" otherwise has to call both
and merge them by hand. ``compute_refactor_priorities`` does that fusion:
it gathers candidates from both lenses, ranks them by a fused priority,
and attaches a one-line rationale naming which lenses fired and why.

This is pure aggregation over the two existing primitives - no new
analysis. It deliberately does **not** invent a cross-project absolute
"refactor score": the ``priority`` field is a within-project normalized
rank, useful for ordering a cleanup queue inside one repository and
nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from archy.hotspots import compute_hotspots
from archy.risk import compute_edit_risk

DEFAULT_MIN_RISK = 0.15


@dataclass(frozen=True)
class RefactorPriority:
    module: str
    priority: float
    rationale: str
    behavioral: bool
    structural: bool
    cc_sum: float | None
    churn: int | None
    edit_risk: float | None


def compute_refactor_priorities(
    graph: nx.DiGraph,
    churn: dict[str, int] | None,
    min_risk: float = DEFAULT_MIN_RISK,
) -> list[RefactorPriority]:
    """Fuse hotspots and edit-risk into one ranked refactor-priority list.

    ``churn`` is the per-file commit count from :func:`archy.hotspots.git_churn`
    (pass ``None`` when the project is not under git: the behavioral lens is
    then skipped and ranking falls back to the structural lens alone, mirroring
    the behavioral lens's git-absent behavior). ``min_risk`` is the structural
    floor below which a module is not surfaced on the edit-risk lens.

    Returns the full ranked candidate list (callers cap with their own
    ``top_n``). An **empty list** is a meaningful result: nothing is both
    complex and churned, and nothing clears ``min_risk`` - there is genuinely
    nothing to prioritize.
    """
    # Behavioral lens. `compute_hotspots` already filters to files with both
    # cc_sum > 0 and churn > 0, so every returned row is a real hotspot.
    hotspots = compute_hotspots(graph, churn=churn) if churn is not None else []
    hotspot_by_module = {h.module: h for h in hotspots}

    # Structural lens.
    risks = compute_edit_risk(graph)

    candidates: set[str] = set(hotspot_by_module) | {
        m for m, r in risks.items() if r >= min_risk
    }

    out: list[RefactorPriority] = []
    for module in candidates:
        h = hotspot_by_module.get(module)
        r = risks.get(module)
        behavioral = h is not None
        structural = r is not None and r >= min_risk
        # Priority: prefer the behavioral signal when present (it already
        # incorporates churn, the stronger "this is actually changing"
        # signal), fall back to structural. The exact weighting is a
        # within-project ranking device, not a portable score.
        if behavioral and structural:
            priority = 0.6 * (h.cc_sum * h.churn) + 0.4 * r
        elif behavioral:
            priority = float(h.cc_sum * h.churn)
        else:
            priority = r or 0.0
        reasons = []
        if behavioral:
            reasons.append(f"hotspot (cc={h.cc_sum:.0f}, churn={h.churn})")
        if structural:
            reasons.append(f"edit-risk {r:.2f}")
        rationale = "; ".join(reasons) or "structural"
        out.append(
            RefactorPriority(
                module=module,
                priority=priority,
                rationale=rationale,
                behavioral=behavioral,
                structural=structural,
                cc_sum=h.cc_sum if h else None,
                churn=h.churn if h else None,
                edit_risk=r,
            )
        )
    out.sort(key=lambda x: x.priority, reverse=True)
    return out
