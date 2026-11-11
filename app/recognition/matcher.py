"""Compare face embeddings and decide: match, unknown, or ambiguous.

This module is pure NumPy (no OpenCV, no database) so the decision rules are
easy to test and explain.

An embedding is a list of 128 numbers that describes a face. Two photos of
the same person should produce embeddings that point in a similar direction.
Cosine similarity measures that direction:

     1.0  -> same direction (very similar faces)
     0.0  -> unrelated
    -1.0  -> opposite

Decision rules for one probe (the new camera capture):

    best    = highest similarity to any template of the closest employee
    runner  = highest similarity among all *other* employees

    best < threshold                 -> UNKNOWN   (not similar enough to anyone)
    best - runner < ambiguity_margin -> AMBIGUOUS (two employees nearly tied)
    otherwise                        -> MATCH

A score is a similarity, not a probability. Thresholds must be calibrated
on consented evaluation data before they mean anything in practice.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

import numpy as np


class MatchStatus(str, Enum):
    MATCH = "match"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class MatchResult:
    status: MatchStatus
    employee_id: int | None
    best_score: float | None
    runner_up_score: float | None


def l2_normalize(vector: np.ndarray) -> np.ndarray:
    """Scale a vector to length 1, so cosine similarity becomes a dot product."""

    flat = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(flat))
    if not np.isfinite(norm) or norm == 0.0:
        raise ValueError("An embedding must be a non-zero, finite vector.")
    return flat / norm


def cosine_similarity(first: np.ndarray, second: np.ndarray) -> float:
    a, b = l2_normalize(first), l2_normalize(second)
    if a.shape != b.shape:
        raise ValueError("Embeddings must have the same length to be compared.")
    # Clip tiny floating-point overshoots such as 1.0000001.
    return float(np.clip(np.dot(a, b), -1.0, 1.0))


def validate_thresholds(threshold: float, ambiguity_margin: float) -> None:
    if not -1.0 <= threshold <= 1.0:
        raise ValueError("The match threshold must be between -1 and 1.")
    if not 0.0 <= ambiguity_margin <= 2.0:
        raise ValueError("The ambiguity margin must be between 0 and 2.")


def match_embedding(
    probe: np.ndarray,
    gallery: Mapping[int, Sequence[np.ndarray]],
    *,
    threshold: float,
    ambiguity_margin: float,
) -> MatchResult:
    """Compare one probe embedding with every enrolled employee's templates."""

    validate_thresholds(threshold, ambiguity_margin)
    probe_unit = l2_normalize(probe)

    scores: list[tuple[float, int]] = []
    for employee_id, templates in gallery.items():
        if templates:
            # An employee's score is their best-matching enrolment image.
            scores.append((max(cosine_similarity(probe_unit, t) for t in templates), employee_id))

    if not scores:
        return MatchResult(MatchStatus.UNKNOWN, None, None, None)

    scores.sort(reverse=True)
    best_score, best_employee = scores[0]
    runner_up = scores[1][0] if len(scores) > 1 else None

    if best_score < threshold:
        return MatchResult(MatchStatus.UNKNOWN, None, best_score, runner_up)
    if runner_up is not None and best_score - runner_up < ambiguity_margin:
        return MatchResult(MatchStatus.AMBIGUOUS, None, best_score, runner_up)
    return MatchResult(MatchStatus.MATCH, best_employee, best_score, runner_up)
