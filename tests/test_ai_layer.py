from datetime import datetime, time, timedelta

import pytest

from pawpal_ai import guardrails
from pawpal_ai.agent import CareAgent
from pawpal_ai.care_log import REAL, VIRTUAL, CareEvent, CareLog
from pawpal_ai.companion import Companion, compute_state
from pawpal_ai.demo_data import build_demo
from pawpal_ai.retriever import KnowledgeBase
from pawpal_ai.routine_learner import learn_routine, reliable

NOW = datetime(2026, 11, 18, 7, 10)


@pytest.fixture(scope="module")
def kb():
    return KnowledgeBase()


def agent(kb, now=NOW, style="realistic"):
    owner, avail, log = build_demo(now)
    return CareAgent(owner, avail, log, kb, style, trace_path=None), log


# ---- care log
def test_event_rejects_unknown_type():
    with pytest.raises(ValueError):
        CareEvent("Rex", "juggling", NOW)


def test_log_roundtrip_and_corrupt_file(tmp_path):
    log = CareLog([CareEvent("Rex", "walk", NOW)])
    path = tmp_path / "log.json"
    log.save(path)
    assert CareLog.load(path).events == log.events
    path.write_text("{not json")
    assert CareLog.load(path).events == []  # does not crash
    assert path.with_suffix(".corrupt").exists()


# ---- routine learner
def test_learner_finds_true_time():
    _, _, log = build_demo(NOW)
    walk = [p for p in learn_routine(log.events, "Rex") if p.task_type == "walk"][0]
    assert abs(walk.typical_minute - (7 * 60 + 45)) <= 10 and walk.confidence > 0.8


def test_learner_splits_two_meals():
    _, _, log = build_demo(NOW)
    meals = [p for p in learn_routine(log.events, "Rex") if p.task_type == "feeding"]
    assert len(meals) == 2


def test_few_events_means_still_learning():
    _, _, log = build_demo(NOW)
    mia = learn_routine(log.events, "Mia")
    assert mia and not mia[0].learned and reliable(mia) == []


def test_virtual_events_are_not_evidence():
    events = [CareEvent("Rex", "walk", datetime(2026, 11, d, 6, 0), VIRTUAL) for d in range(1, 10)]
    assert learn_routine(events, "Rex") == []


def test_midnight_wraparound():
    events = [CareEvent("Rex", "meds", datetime(2026, 11, d, 23, 55) if d % 2 else datetime(2026, 11, d, 0, 5), REAL)
              for d in range(1, 11)]
    p = learn_routine(events, "Rex")[0]
    assert p.spread_minutes <= 10


# ---- retriever
def test_retrieval_is_species_scoped(kb):
    hits = kb.retrieve("lilies toxic", species="dog")
    assert all("dog" in h.chunk.species for h in hits)


def test_retrieval_empty_query(kb):
    assert kb.retrieve("", "dog") == []


# ---- guardrails
@pytest.mark.parametrize("q,reason", [("", "empty"), (None, "empty"), ("x" * 500, "too_long"),
                                      ("my dog ate chocolate", "emergency")])
def test_question_guardrails(q, reason):
    assert guardrails.check_question(q).reason == reason


def test_normal_question_allowed():
    assert guardrails.check_question("how often to walk?").allowed


# ---- companion
def test_companion_state_drains_without_care():
    log = CareLog([CareEvent("Rex", "feeding", NOW - timedelta(hours=5), VIRTUAL)])
    assert compute_state(log, "Rex", NOW).belly == 50
    assert compute_state(CareLog(), "Rex", NOW).mood == "needy"


def test_styles_share_facts_but_differ_in_voice():
    a = Companion("Rex", "dog", "realistic").say("overdue", task="walk", time="07:45")
    b = Companion("Rex", "dog", "robotic").say("overdue", task="walk", time="07:45")
    assert a != b and "07:45" in a and "07:45" in b


def test_bad_style_rejected():
    with pytest.raises(ValueError):
        Companion("Rex", "dog", "dragon")


# ---- agent
def test_learned_time_changes_the_plan(kb):
    ag, _ = agent(kb)
    b = ag.run(NOW)
    dinner = next(l for l in b.lines if l.task.title == "Dinner")
    assert dinner.slot.start >= time(17, 30) and "learned routine" in dinner.reason


def test_no_task_scheduled_in_the_past(kb):
    ag, _ = agent(kb, datetime(2026, 11, 18, 9, 40))
    b = ag.run(datetime(2026, 11, 18, 9, 40))
    assert all(l.slot.start >= time(9, 40) for l in b.lines)


def test_finished_task_not_replanned_and_dinner_keeps_evening(kb):
    ag, log = agent(kb)
    log.record(CareEvent("Rex", "feeding", datetime(2026, 11, 18, 7, 20), REAL))
    b = ag.run(datetime(2026, 11, 18, 7, 30))
    assert any("Breakfast" in d for d in b.done)
    assert not any(l.task.title == "Breakfast" for l in b.lines)
    assert next(l for l in b.lines if l.task.title == "Dinner").slot.start >= time(17)


def test_required_task_is_flagged_when_no_window(kb):
    owner, _, log = build_demo(NOW)
    ag = CareAgent(owner, [], log, kb, trace_path=None)
    b = ag.run(NOW)
    assert any("REQUIRED" in a for a in b.alerts)


def test_every_tip_has_a_source(kb):
    ag, _ = agent(kb)
    assert all(l.source for l in ag.run(NOW).lines if l.tip)


def test_overdue_nudge_fires(kb):
    t = datetime(2026, 11, 18, 9, 40)
    ag, _ = agent(kb, t, "robotic")
    assert any("OVERDUE" in n for n in ag.run(t).nudges)


def test_ask_refuses_offtopic_and_emergency(kb):
    ag, _ = agent(kb)
    assert ag.ask("What is the best cryptocurrency?", "Rex").reason == "no_retrieval"
    assert ag.ask("Rex is having a seizure", "Rex").reason == "emergency"


def test_ask_answers_from_sources(kb):
    a = agent(kb)[0].ask("Can Rex eat grapes?", "Rex")
    assert "grapes" in a.text.lower() and a.sources


def test_trace_written(kb, tmp_path):
    owner, avail, log = build_demo(NOW)
    path = tmp_path / "trace.jsonl"
    CareAgent(owner, avail, log, kb, trace_path=path).run(NOW)
    assert path.read_text().count("\n") == 1 and '"step": "check"' in path.read_text()


# ---- pet art
import xml.etree.ElementTree as ET

from pawpal_ai.companion import CompanionState
from pawpal_ai.pet_art import REACTION_EMOJI, build_svg, lowest_need, render_html


@pytest.mark.parametrize("species", ["dog", "cat", "other"])
@pytest.mark.parametrize("style", ["realistic", "robotic"])
@pytest.mark.parametrize("mood", ["happy", "okay", "needy"])
def test_every_pet_renders_valid_svg(species, style, mood):
    ET.fromstring(build_svg(species, style, mood, need="belly", reaction="eat"))  # raises if malformed


def test_art_rejects_bad_input():
    for kwargs in ({"style": "pixel"}, {"mood": "furious"}, {"reaction": "explode"}):
        args = {"species": "dog", "style": "realistic", "mood": "happy", **kwargs}
        with pytest.raises(ValueError):
            build_svg(**args)


def test_mood_changes_the_art_and_reaction_adds_effects():
    assert build_svg("dog", "realistic", "happy") != build_svg("dog", "realistic", "needy")
    assert "fx-float" in build_svg("cat", "robotic", "happy", reaction="play")
    assert "fx-float" not in build_svg("cat", "robotic", "happy")


def test_bubble_shows_the_lowest_need_only_when_low():
    assert lowest_need(CompanionState(90, 80, 70)) is None
    assert lowest_need(CompanionState(60, 10, 70)) == "fun"
    assert "🧸" in render_html("dog", "realistic", CompanionState(60, 10, 70))


# ---- real/virtual sync
import random

from pawpal_ai.companion import compute_real_state, compute_synced_state

RANK = {"needy": 0, "okay": 1, "happy": 2}


def _log(real_hours_ago: dict, virtual_hours_ago: dict) -> CareLog:
    ev = [CareEvent("Rex", k, NOW - timedelta(hours=h), REAL) for k, h in real_hours_ago.items()]
    ev += [CareEvent("Rex", k, NOW - timedelta(hours=h), VIRTUAL) for k, h in virtual_hours_ago.items()]
    return CareLog(ev)


def test_virtual_cannot_be_happy_if_real_pet_is_neglected():
    # Lots of game play, zero real care.
    log = _log({}, {"feeding": 0, "walk": 0, "grooming": 0})
    s = compute_synced_state(log, "Rex", NOW)
    assert s.virtual.mood == "happy" and s.real.mood == "needy"
    assert s.shown.mood == "needy" and set(s.limited_by) == {"belly", "fun", "clean"}


def test_real_care_unlocks_the_companion():
    log = _log({"feeding": 1, "walk": 1, "grooming": 24}, {"feeding": 0, "walk": 0, "grooming": 0})
    s = compute_synced_state(log, "Rex", NOW)
    assert s.shown.mood == "happy" and s.limited_by == ()


def test_real_care_alone_is_not_enough_if_nobody_plays_with_the_toy():
    log = _log({"feeding": 1, "walk": 1, "grooming": 1}, {})
    s = compute_synced_state(log, "Rex", NOW)
    assert s.real.mood == "happy" and s.shown.mood == "needy"


def test_property_companion_mood_never_exceeds_real_mood():
    rng = random.Random(3)
    for _ in range(300):
        real = {k: rng.uniform(0, 200) for k in ("feeding", "walk", "grooming") if rng.random() < .7}
        virt = {k: rng.uniform(0, 80) for k in ("feeding", "walk", "grooming") if rng.random() < .7}
        s = compute_synced_state(_log(real, virt), "Rex", NOW)
        assert RANK[s.shown.mood] <= RANK[s.real.mood]
        assert all(getattr(s.shown, n) <= getattr(s.real, n) for n in ("belly", "fun", "clean"))


def test_sync_note_names_the_real_bottleneck_in_both_voices():
    s = compute_synced_state(_log({}, {"feeding": 0}), "Rex", NOW)
    assert "fed" in Companion("Rex", "dog", "realistic").sync_note(s)
    assert "SYNC LIMIT" in Companion("Rex", "dog", "robotic").sync_note(s)


# ---- UI regression: choosing the second pet used to raise StreamlitDuplicateElementId
def test_ui_second_pet_selectable_without_error():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(__import__("pathlib").Path(__file__).resolve().parent.parent / "app.py"), default_timeout=30).run()
    next(b for b in at.button if "demo household" in b.label).click().run()
    sel = next(s for s in at.selectbox if s.label == "Companion for")
    for name in ("Mia", "Rex", "Mia"):
        sel.select(name).run()
        assert not at.exception, at.exception[0].message
    for style in ("robotic", "realistic"):
        at.radio[0].set_value(style).run()
        assert not at.exception
