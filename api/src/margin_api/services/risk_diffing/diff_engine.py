"""Semantic diff engine for risk factor paragraphs.

Computes cosine similarity between old and new paragraph embeddings,
then classifies each paragraph as NEW, REMOVED, MODIFIED, or unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ChangeCandidate:
    """A detected change between two consecutive risk factor sections."""

    change_type: str  # "new", "removed", "modified"
    old_text: str | None
    new_text: str | None
    similarity: float | None


def compute_similarity_matrix(
    old_embeddings: list[list[float]],
    new_embeddings: list[list[float]],
) -> np.ndarray:
    """Cosine similarity matrix between old and new embeddings."""
    old_arr = np.array(old_embeddings, dtype=np.float64)
    new_arr = np.array(new_embeddings, dtype=np.float64)
    old_norms = np.linalg.norm(old_arr, axis=1, keepdims=True)
    new_norms = np.linalg.norm(new_arr, axis=1, keepdims=True)
    old_norms = np.where(old_norms == 0, 1, old_norms)
    new_norms = np.where(new_norms == 0, 1, new_norms)
    old_normed = old_arr / old_norms
    new_normed = new_arr / new_norms
    return old_normed @ new_normed.T


def classify_changes(
    old_embeddings: list[list[float]],
    new_embeddings: list[list[float]],
    old_texts: list[str],
    new_texts: list[str],
    similarity_threshold: float,
    unchanged_threshold: float,
    length_change_threshold: float,
) -> list[ChangeCandidate]:
    """Classify changes between old and new risk factor paragraph sets."""
    if not old_embeddings and not new_embeddings:
        return []
    changes: list[ChangeCandidate] = []
    if not old_embeddings:
        return [
            ChangeCandidate(change_type="new", old_text=None, new_text=t, similarity=None)
            for t in new_texts
        ]
    if not new_embeddings:
        return [
            ChangeCandidate(change_type="removed", old_text=t, new_text=None, similarity=None)
            for t in old_texts
        ]
    matrix = compute_similarity_matrix(old_embeddings, new_embeddings)
    n_old, n_new = matrix.shape
    old_matched: set[int] = set()
    new_matched: set[int] = set()
    pairs: list[tuple[int, int, float]] = []
    all_pairs = []
    for i in range(n_old):
        for j in range(n_new):
            all_pairs.append((float(matrix[i, j]), i, j))
    all_pairs.sort(reverse=True)
    for sim, i, j in all_pairs:
        if i in old_matched or j in new_matched:
            continue
        if sim < similarity_threshold:
            break
        old_matched.add(i)
        new_matched.add(j)
        pairs.append((i, j, sim))
    for i, j, sim in pairs:
        if sim >= unchanged_threshold:
            old_len = len(old_texts[i])
            new_len = len(new_texts[j])
            max_len = max(old_len, new_len, 1)
            length_delta = abs(new_len - old_len) / max_len
            if length_delta < length_change_threshold:
                continue
        changes.append(
            ChangeCandidate(
                change_type="modified",
                old_text=old_texts[i],
                new_text=new_texts[j],
                similarity=sim,
            )
        )
    for j in range(n_new):
        if j not in new_matched:
            changes.append(
                ChangeCandidate(
                    change_type="new", old_text=None, new_text=new_texts[j], similarity=None
                )
            )
    for i in range(n_old):
        if i not in old_matched:
            changes.append(
                ChangeCandidate(
                    change_type="removed", old_text=old_texts[i], new_text=None, similarity=None
                )
            )
    return changes
