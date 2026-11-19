# AI Interactions Log

Evidence for the **Agentic Workflow Enhancement** and **RAG Enhancement** stretch features.

## 1. Agentic workflow: reasoning traces

`CareAgent.run()` is a five-step loop (observe, learn, plan, retrieve, check). Each run appends a JSON
trace to `logs/agent_trace.jsonl`; the two traces below are committed in
[assets/agent_trace_sample.jsonl](assets/agent_trace_sample.jsonl) and were produced by `python demo.py`.

**Run A: 07:10, nothing logged yet today (realistic voice)**

| Step | What the agent recorded |
|---|---|
| observe | 5 pending tasks, 0 already done, 5 remaining |
| learn | `Rex/feeding@07:25 n=14 conf=0.95`, `Rex/feeding@17:57 n=14 conf=0.92`, `Rex/walk@07:49 n=14 conf=0.95`, `Mia/enrichment@17:40 n=2 conf=0.2`; 3 learned hints applied (Mia's 2 events are below the minimum of 3, so no hint) |
| plan | 5 scheduled, 0 unscheduled |
| retrieve | 5 cited tips attached |
| check | no alerts |

**Run B: 09:40, breakfast logged, walk missed (robotic voice)**

| Step | What the agent recorded |
|---|---|
| observe | 5 pending, **1 already done** (Rex breakfast at 07:33), 4 remaining |
| learn | the morning feeding pattern is *excluded* as already satisfied, so Dinner keeps its 17:57 routine |
| plan | morning windows are in the past, so the walk moves to the next free window ("learned time unavailable") |
| check | no alerts; an OVERDUE nudge for the walk is raised separately |

Raw lines:

```
{"day": "2026-11-18", "style": "realistic", "trace": [{"step": "observe", "pending": 5, "already_done": 0, "remaining": 5}, {"step": "learn", "patterns": ["Rex/feeding@07:25 n=14 conf=0.95", "Rex/feeding@17:57 n=14 conf=0.92", "Rex/walk@07:49 n=14 conf=0.95", "Mia/enrichment@17:40 n=2 conf=0.2"], "hints_applied": 3}, {"step": "plan", "scheduled": 5, "unscheduled": 0}, {"step": "retrieve", "tips": 5}, {"step": "check", "alerts": []}]}
{"day": "2026-11-18", "style": "robotic", "trace": [{"step": "observe", "pending": 5, "already_done": 1, "remaining": 4}, {"step": "learn", "patterns": ["Rex/feeding@07:26 n=15 conf=0.95", "Rex/feeding@17:57 n=14 conf=0.92", "Rex/walk@07:49 n=14 conf=0.95", "Mia/enrichment@17:40 n=2 conf=0.2"], "hints_applied": 2}, {"step": "plan", "scheduled": 4, "unscheduled": 0}, {"step": "retrieve", "tips": 4}, {"step": "check", "alerts": []}]}
```

## 2. RAG enhancement: before vs after

| | Before (original PawPal+) | After (retrieval in the loop) |
|---|---|---|
| Plan line for Rex's walk | `Morning walk` + "medium priority" | + *"Most adult dogs need at least 30 to 60 minutes of physical activity a day..."* `[dog_exercise.md > Daily walks for dogs]` |
| "Can Rex eat grapes?" | not possible | answered from `dog_feeding.md > Foods that are dangerous for dogs`, with the source shown |
| Off-topic question | not possible | refused (`no_retrieval`) rather than answered from a loosely related note |

Multiple data sources: the retriever reads every `knowledge/*.md` file, scoped by a `species:` header so a
dog question never returns a cat-only note (tested in `test_retrieval_is_species_scoped`).

## 3. Collaboration notes (Claude Code)

| Step | What the AI did | What I had to verify or fix |
|---|---|---|
| Plan | Read the Module 2 repo, proposed adding care history, a learner, RAG, an agent loop and an eval harness | Chose the virtual-companion direction and the two-style idea myself |
| Build | Wrote the `pawpal_ai/` modules, UI tab and tests | Ran `demo.py` and read the output; it showed four real bugs (greeting said "everyone", tasks scheduled in the past, Dinner reused the morning routine, off-topic question retrieved a note) |
| Fix | Proposed and applied fixes, then added regression tests | Confirmed each fix against the demo output, not just that tests passed |
| Evaluate | First harness passed 46/46 | Did not trust it; added harder paraphrase cases, which exposed 2 real retrieval failures that are kept in the eval |
| Sync + bug report | Reproduced the reported Mia error, found the cause (widget created inside a generator), added the real-to-virtual sync with a property test | My first fuzz test selected the wrong dropdown and "passed"; I only found the bug when I checked which widget I was selecting. Also had to stop a tiny 96% vs 100% gap being reported as a real-care limit |
| Interactive scene | Built the clickable props, drag-to-groom brush and hover menu as a Streamlit v2 component, then drove the real app in headless Chrome (real mouse hover, click and drag) | Checked that each click actually reached the care log with the right source (virtual vs real). Tampered-input tests found a crash on list-valued action types |
