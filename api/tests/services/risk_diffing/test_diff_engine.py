"""Tests for the semantic diff engine."""

from __future__ import annotations

from margin_api.services.risk_diffing.diff_engine import (
    classify_changes,
    compute_similarity_matrix,
)


class TestComputeSimilarityMatrix:
    def test_identical_vectors_have_similarity_one(self) -> None:
        old = [[1.0, 0.0, 0.0]]
        new = [[1.0, 0.0, 0.0]]
        matrix = compute_similarity_matrix(old, new)
        assert matrix.shape == (1, 1)
        assert abs(matrix[0, 0] - 1.0) < 1e-6

    def test_orthogonal_vectors_have_similarity_zero(self) -> None:
        old = [[1.0, 0.0, 0.0]]
        new = [[0.0, 1.0, 0.0]]
        matrix = compute_similarity_matrix(old, new)
        assert abs(matrix[0, 0]) < 1e-6

    def test_matrix_dimensions_match_inputs(self) -> None:
        old = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
        new = [[1.0, 0.0], [0.5, 0.5]]
        matrix = compute_similarity_matrix(old, new)
        assert matrix.shape == (3, 2)


class TestClassifyChanges:
    def test_new_chunk_no_match_in_prior(self) -> None:
        old_emb = [[1.0, 0.0, 0.0]]
        new_emb = [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
        old_texts = ["Old risk about market conditions."]
        new_texts = ["Old risk about market conditions.", "Brand new risk about AI regulation."]
        changes = classify_changes(old_emb, new_emb, old_texts, new_texts, 0.85, 0.95, 0.20)
        new_changes = [c for c in changes if c.change_type == "new"]
        assert len(new_changes) == 1
        assert new_changes[0].new_text == new_texts[1]

    def test_removed_chunk_no_match_in_current(self) -> None:
        old_emb = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        new_emb = [[1.0, 0.0, 0.0]]
        old_texts = ["Risk about market.", "Risk about legacy systems."]
        new_texts = ["Risk about market."]
        changes = classify_changes(old_emb, new_emb, old_texts, new_texts, 0.85, 0.95, 0.20)
        removed = [c for c in changes if c.change_type == "removed"]
        assert len(removed) == 1
        assert removed[0].old_text == old_texts[1]

    def test_modified_chunk_moderate_similarity(self) -> None:
        old_emb = [[1.0, 0.0, 0.0]]
        new_emb = [[0.90, 0.436, 0.0]]  # cosine ~ 0.90
        old_texts = ["Risk about competition."]
        new_texts = ["Risk about competition in adjacent markets expanding rapidly."]
        changes = classify_changes(old_emb, new_emb, old_texts, new_texts, 0.85, 0.95, 0.20)
        modified = [c for c in changes if c.change_type == "modified"]
        assert len(modified) == 1

    def test_unchanged_chunks_are_skipped(self) -> None:
        old_emb = [[1.0, 0.0, 0.0]]
        new_emb = [[1.0, 0.0, 0.0]]
        old_texts = ["Identical risk factor text."]
        new_texts = ["Identical risk factor text."]
        changes = classify_changes(old_emb, new_emb, old_texts, new_texts, 0.85, 0.95, 0.20)
        assert len(changes) == 0

    def test_empty_inputs_return_no_changes(self) -> None:
        changes = classify_changes([], [], [], [], 0.85, 0.95, 0.20)
        assert changes == []
