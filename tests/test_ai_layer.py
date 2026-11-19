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


def agent(kb, now=NOW, style="realistic", include_today=False):
    # include_today=False: nothing has happened yet today, so overdue/planning tests are deterministic.
    owner, avail, log = build_demo(now, include_today=include_today)
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


def _fresh_app_test():
    """AppTest starts each run with an empty component registry, so re-import the stage module
    (otherwise its one-time registration is skipped on the second AppTest in a process)."""
    import sys
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    for mod in ("stage", "companion_ui"):
        sys.modules.pop(mod, None)
    return AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=30)


# ---- UI regression: choosing the second pet used to raise StreamlitDuplicateElementId
def test_ui_second_pet_selectable_without_error():
    at = _fresh_app_test().run()
    next(b for b in at.button if "demo household" in b.label).click().run()
    sel = next(s for s in at.selectbox if s.label == "Companion for")
    for name in ("Mia", "Rex", "Mia"):
        sel.select(name).run()
        assert not at.exception, at.exception[0].message
    for style in ("robotic", "realistic"):
        next(g for g in at.segmented_control if g.key == "companion_style").set_value(style).run()
        assert not at.exception


def test_demo_household_includes_todays_progress_when_asked():
    now = datetime(2026, 11, 18, 12, 0)
    _, _, log = build_demo(now)
    today_real = [e for e in log.query("Rex", REAL, since=datetime(2026, 11, 18)) if e.timestamp <= now]
    assert {"walk", "feeding"} <= {e.task_type for e in today_real}
    _, _, bare = build_demo(now, include_today=False)
    assert not bare.query("Rex", REAL, since=datetime(2026, 11, 18))


def test_empty_state_renders_without_error():
    at = _fresh_app_test().run()
    assert not at.exception and any("demo household" in b.label for b in at.button)


def test_all_done_message_never_hides_alerts(kb):
    owner, _, log = build_demo(NOW)
    b = CareAgent(owner, [], log, kb, trace_path=None).run(NOW)  # meds cannot be scheduled
    assert b.alerts and not b.all_done


def test_scenes_are_valid_svg_for_every_time_of_day():
    from pawpal_ai.scene import scene_svg
    for style in ("realistic", "robotic"):
        for hour in range(24):
            ET.fromstring(scene_svg(style, hour, belly=hour * 4))


# ---- interactive stage: actions from the browser are untrusted input
from pawpal_ai.actions import ACTION_TO_CARE, handle_action
from pawpal_ai.pet_art import stage_payload
from pawpal_ai.props import PROP_ACTIONS, all_props


def test_valid_actions_are_recorded_with_the_right_source():
    log = CareLog()
    for act, care in ACTION_TO_CARE.items():
        for mode in (REAL, VIRTUAL):
            r = handle_action(log, "Rex", {"type": act, "mode": mode, "id": 1}, NOW)
            assert r.ok and r.event.task_type == care and r.event.source == mode
    assert len(log.events) == 2 * len(ACTION_TO_CARE)


@pytest.mark.parametrize("raw", [None, "feed", 42, [], {}, {"type": "feed"}, {"mode": "real"},
                                 {"type": "explode", "mode": "real"}, {"type": "feed", "mode": "admin"},
                                 {"type": ["feed"], "mode": "real"}, {"type": "feed", "mode": None}])
def test_tampered_or_malformed_actions_are_ignored_not_crashing(raw):
    log = CareLog()
    r = handle_action(log, "Rex", raw, NOW)
    assert not r.ok and log.events == []


def test_action_without_a_pet_is_ignored():
    assert not handle_action(CareLog(), None, {"type": "feed", "mode": "real"}, NOW).ok


def test_virtual_action_cannot_make_the_companion_happier_than_real_care():
    log = CareLog()
    for act in ("feed", "play", "groom"):
        handle_action(log, "Rex", {"type": act, "mode": VIRTUAL}, NOW)
    assert compute_synced_state(log, "Rex", NOW).shown.mood == "needy"
    for act in ("feed", "walk", "groom"):
        handle_action(log, "Rex", {"type": act, "mode": REAL}, NOW)
    assert compute_synced_state(log, "Rex", NOW).shown.mood == "happy"


@pytest.mark.parametrize("style", ["realistic", "robotic"])
def test_props_are_valid_svg_and_cover_every_action(style):
    props = all_props(style, belly=80)
    assert set(props) == set(PROP_ACTIONS) and set(PROP_ACTIONS.values()) == set(ACTION_TO_CARE) | {"play", "walk", "groom", "meds", "feed"}
    for svg in props.values():
        ET.fromstring(svg)


def test_bowl_is_full_only_when_the_pet_is_fed():
    assert all_props("realistic", 90)["bowl"] != all_props("realistic", 10)["bowl"]


def test_stage_payload_is_complete_and_valid():
    p = stage_payload("cat", "robotic", CompanionState(5, 10, 20), 14, "Mia")
    assert {"scene", "pet", "props", "style", "mood", "chip", "name", "mode"} <= set(p)
    ET.fromstring(p["scene"]); ET.fromstring(p["pet"])
    assert p["mood"] == "needy" and p["chip"] == "Lab mode" and 'class="pet"' in p["pet"]


def test_ui_works_with_many_pets():
    """The Mia bug: choosing any pet but the first crashed. Check a household of six, every pet, both styles."""
    from pawpal_system import Owner, Pet
    owner = Owner("Jordan", "")
    for i, (name, sp) in enumerate([("Rex", "dog"), ("Mia", "cat"), ("Bo", "dog"), ("Luna", "cat"), ("Kiwi", "other"), ("Max", "dog")]):
        owner.add_pet(Pet(name, sp, i + 1))
    at = _fresh_app_test()
    at.session_state["owner"] = owner
    at.run()
    sel = next(s for s in at.selectbox if s.label == "Companion for")
    for name in ["Mia", "Bo", "Luna", "Kiwi", "Max", "Rex"]:
        sel.select(name).run()
        assert not at.exception, f"{name}: {at.exception[0].message}"
    for style in ("robotic", "realistic"):
        next(g for g in at.segmented_control if g.key == "companion_style").set_value(style).run()
        assert not at.exception
