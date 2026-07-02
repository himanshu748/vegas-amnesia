import pytest

from backend.models.facts import load_ground_truth
from backend.services.solve import build_timeline, evaluate_solve


@pytest.fixture(scope="module")
def truth():
    return load_ground_truth()


def test_ground_truth_shape(truth):
    assert len(truth.facts) == 20
    assert len(truth.red_herrings) == 5
    assert len(truth.key_fact_ids) == 10
    assert all(rh.is_red_herring for rh in truth.red_herrings)
    assert all(not f.is_red_herring for f in truth.facts)
    # every derivable inference points at real fact ids
    all_ids = {f.id for f in truth.facts}
    for d in truth.derivable:
        assert set(d.derived_from) <= all_ids
    # every red herring names its debunker
    assert all(rh.debunked_by for rh in truth.red_herrings)


def test_win_with_all_key_facts_no_herrings(truth):
    result = evaluate_solve(truth, remembered_ids=truth.key_fact_ids, forgotten_ids=set())
    assert result.won
    assert result.coverage == 1.0
    assert result.key_facts_missing == []
    assert result.verdict == truth.solution_summary


def test_win_at_exactly_threshold(truth):
    key = sorted(truth.key_fact_ids)
    result = evaluate_solve(truth, remembered_ids=set(key[:8]), forgotten_ids=set())
    assert result.coverage == 0.8
    assert result.won


def test_lose_below_threshold(truth):
    key = sorted(truth.key_fact_ids)
    result = evaluate_solve(truth, remembered_ids=set(key[:7]), forgotten_ids=set())
    assert not result.won
    assert "gaps" in result.verdict


def test_lose_when_contaminated_by_red_herrings(truth):
    remembered = truth.key_fact_ids | {"rh1", "rh2"}
    result = evaluate_solve(truth, remembered_ids=remembered, forgotten_ids=set())
    assert not result.won
    assert result.active_red_herrings == ["rh1", "rh2"]
    assert "contaminated" in result.verdict


def test_one_red_herring_is_forgiven(truth):
    remembered = truth.key_fact_ids | {"rh3"}
    result = evaluate_solve(truth, remembered_ids=remembered, forgotten_ids=set())
    assert result.won


def test_forgetting_a_red_herring_restores_the_win(truth):
    remembered = truth.key_fact_ids | {"rh1", "rh2"}
    result = evaluate_solve(truth, remembered_ids=remembered, forgotten_ids={"rh1"})
    assert result.won
    assert result.active_red_herrings == ["rh2"]


def test_forgetting_a_true_fact_costs_coverage(truth):
    key = sorted(truth.key_fact_ids)
    result = evaluate_solve(
        truth, remembered_ids=set(key[:8]), forgotten_ids={key[0]}
    )
    assert not result.won  # 7/10 active < threshold


def test_timeline_is_chronological_across_midnight(truth):
    all_true = {f.id for f in truth.facts}
    timeline = build_timeline(truth, all_true)
    assert len(timeline) == 20
    times = [e["time"] for e in timeline]
    # evening (>= 20:00) must come before small hours (< 20:00)
    assert times[0] == "20:45"  # engagement ring into the safe
    assert times[-1] == "04:30"  # Dev passes out
    # red herrings never appear in the ending timeline
    assert all(not e["id"].startswith("rh") for e in timeline)


def test_timeline_lines_carry_citations(truth):
    timeline = build_timeline(truth, {"f04"})
    assert timeline[0]["id"] == "f04"
    assert timeline[0]["source"]["ref"] == "casino_chip_receipt"
