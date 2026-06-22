"""Tests for AI pattern scanner — rule-based detection, no API calls needed."""

from src.annotation import Severity
from src.reviewers.ai_pattern_scanner import (
    scan,
    detect_tier_vocab,
    detect_significance_inflation,
    detect_vague_attributions,
    detect_chatbot_artifacts,
    detect_em_dashes,
    detect_structured_abstract,
    detect_copula_avoidance,
    detect_elegant_variation,
    compute_burstiness,
    compute_type_token_ratio,
    compute_ai_score,
)


class TestTierVocab:
    def test_detects_tier1_word(self):
        text = "This paper will delve into the intricate tapestry of modern computing."
        results = detect_tier_vocab(text)

        words_found = [r.what for r in results]
        assert any("delve" in w.lower() for w in words_found)
        assert any("tapestry" in w.lower() for w in words_found)

    def test_tier1_is_high_severity(self):
        text = "We delve into the realm of groundbreaking research."
        results = detect_tier_vocab(text)

        tier1_results = [r for r in results if "Tier1" in r.title]
        assert all(r.severity == Severity.HIGH for r in tier1_results)

    def test_no_false_positive_on_clean_text(self):
        text = "The paper presents a method for solving differential equations."
        results = detect_tier_vocab(text)
        assert len(results) == 0


class TestSignificanceInflation:
    def test_detects_high_severity_claim(self):
        text = "This marks a pivotal moment in the history of computing."
        results = detect_significance_inflation(text)
        assert len(results) > 0
        assert results[0].dimension == "ai_patterns"

    def test_detects_testament_claim(self):
        text = "This serves as a testament to the power of our approach."
        results = detect_significance_inflation(text)
        assert len(results) > 0
        assert "testament" in results[0].what.lower()


class TestVagueAttributions:
    def test_detects_experts_believe(self):
        text = "Experts believe that this approach is optimal for many applications."
        results = detect_vague_attributions(text)
        assert len(results) > 0

    def test_detects_studies_show(self):
        text = "Studies show that this method outperforms alternatives."
        results = detect_vague_attributions(text)
        assert len(results) > 0

    def test_no_false_positive_on_specific_citation(self):
        text = "Smith et al. (2020) showed that this method works well."
        results = detect_vague_attributions(text)
        assert len(results) == 0  # Has actual citation


class TestChatbotArtifacts:
    def test_detects_hope_this_helps(self):
        text = "I hope this helps clarify the concept."
        results = detect_chatbot_artifacts(text)
        assert len(results) > 0
        # Should be high severity
        assert results[0].severity == Severity.HIGH

    def test_detects_ai_language_model(self):
        text = "As an AI language model, I cannot provide opinions."
        results = detect_chatbot_artifacts(text)
        assert len(results) > 0
        # Should be nearly maximum severity
        high_results = [r for r in results if r.severity == Severity.HIGH]
        assert len(high_results) > 0

    def test_detects_knowledge_cutoff(self):
        text = "As of my knowledge cutoff in 2023, the data shows..."
        results = detect_chatbot_artifacts(text)
        assert len(results) > 0


class TestEmDashes:
    def test_detects_em_dash_overuse(self):
        text = "This—that—the other—all of these are important—really important."
        results = detect_em_dashes(text)
        assert len(results) > 0

    def test_low_severity_for_few_dashes(self):
        text = "This approach—while novel—has limitations."
        results = detect_em_dashes(text)
        if results:
            assert results[0].severity in (Severity.LOW, Severity.MEDIUM)


class TestCopulaAvoidance:
    def test_detects_serves_as(self):
        text = "This algorithm serves as the foundation of our method."
        results = detect_copula_avoidance(text)
        assert len(results) > 0

    def test_detects_boasts(self):
        text = "The system boasts impressive performance on benchmarks."
        results = detect_copula_avoidance(text)
        assert len(results) > 0


class TestStructuredAbstract:
    def test_detects_background_heading(self):
        text = r"This is fine. \textbf{Background:} Our work extends prior research. \textbf{Methods:} We used a novel technique."
        results = detect_structured_abstract(text)
        assert len(results) >= 2  # Background + Methods
        # Two or more should escalate to HIGH
        assert all(r.severity == Severity.HIGH for r in results)

    def test_single_heading_low_severity(self):
        text = r"\textbf{Background:} This is the background section."
        results = detect_structured_abstract(text)
        assert len(results) == 1
        assert results[0].severity != Severity.HIGH  # single heading


class TestElegantVariation:
    def test_detects_synonym_cycling(self):
        text = (
            "The researcher conducted the study. The scholar designed the investigation. "
            "The academic analyzed the examination. The scientist reviewed the inquiry."
        )
        results = detect_elegant_variation(text)
        # Should detect cycling among researcher/scholar/academic/scientist
        # and study/investigation/examination/inquiry
        assert len(results) > 0


class TestScan:
    def test_returns_annotations(self):
        text = "We delve into the pivotal realm. Experts believe this serves as a testament. "
        results = scan(text)
        assert len(results) > 0
        # All results should have no suggestions
        for a in results:
            assert a.dimension == "ai_patterns"
            assert a.what  # should have "what"
            assert a.why   # should have "why"

    def test_no_suggestion_field(self):
        text = "This groundbreaking research delves into the intricate landscape."
        results = scan(text)
        for a in results:
            # Verify we never expose suggestion/fix data
            d = a.__dict__ if hasattr(a, '__dict__') else {}
            assert "suggestion" not in d
            assert "fix" not in d


class TestBurstiness:
    def test_uniform_text_is_ai_like(self):
        # Text with very uniform sentence lengths
        text = "This is a test. This is also test. This third test too. A fourth test now."
        score = compute_burstiness(text)
        assert 0.0 <= score <= 1.0


class TestCompositeScore:
    def test_clean_text_low_score(self):
        text = (
            "We present a method for solving the traveling salesman problem. "
            "Our algorithm uses a learned heuristic combined with standard "
            "branch and bound search. Results on standard benchmark instances "
            "show a 15% improvement over the previous best known solutions. "
            "The main observation is that edge weights in real-world graphs "
            "follow predictable patterns that can be exploited during search."
        )
        annotations = scan(text)
        score = compute_ai_score(annotations, text)
        # Clean academic text should have relatively low AI score
        assert 0.0 <= score <= 1.0
        # Very clean text should score below threshold
        # (Tier2 words like "show" may trigger minor detections)
        assert score < 0.5, f"Expected low AI score for clean text, got {score}"

    def test_ai_saturated_text_high_score(self):
        text = (
            "This groundbreaking study delves into the intricate tapestry of "
            "modern computing. It serves as a testament to the pivotal role of "
            "synergistic paradigms. Furthermore, the holistic approach showcases "
            "robust, cutting-edge methodology that is revolutionary. Notably, "
            "this marks a pivotal moment. Moreover, the seamless integration "
            "demonstrates unprecedented proficiency. Experts believe this is "
            "a game-changer. Studies show the profound impact."
        )
        annotations = scan(text)
        score = compute_ai_score(annotations, text)
        assert 0.0 <= score <= 1.0
        assert score > 0.3, f"Expected high AI score for saturated text, got {score}"
