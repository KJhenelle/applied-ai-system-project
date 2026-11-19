# Model Card: PawPal+ Companion

## System summary

A rule-and-retrieval system, not a trained model. Components: a statistical routine learner (median time
of day + spread + a heuristic confidence), a TF-IDF retriever over six hand-written care notes
(`knowledge/`), a checker/guardrail layer, and a template-based companion voice (realistic or robotic).
No LLM or external API is called. Intended use: helping a pet owner remember routine care. **Not** for
diagnosis, dosing, or emergencies.

## What are the limitations or biases in the system?

- **The knowledge base is tiny and written by me.** Six files, 17 sections, general guidance for dogs and
  cats only. A cat owner gets less coverage than a dog owner, and a rabbit, bird or reptile owner gets
  almost nothing (the app lets you choose "other" as a species, but there are no notes for it).
  Anything I left out the system cannot know, and anything I got wrong it will repeat with a citation, which
  makes it sound more authoritative than it is. It has not been reviewed by a veterinarian.
- **Lexical retrieval misses synonyms.** In my own eval, "kitty" and "summer strolls" failed (16/18 on
  retrieval). A wrong-but-confident retrieval is the most dangerous failure here, because an off-topic
  note comes back with a source attached. The score threshold reduces this but does not eliminate it.
- **The emergency list is keyword matching.** "My dog ate chocolate" is caught; "Rex got into the Halloween
  candy" is not. It errs toward missing paraphrases, so it is a safety net, not a triage system.
- **The routine learner assumes a daily rhythm.** It models time of day only. Weekdays vs weekends, a
  changed work schedule, seasons, illness or ageing will all look like "noise" and lower confidence rather
  than being understood. Two or more events of one type per day are only separated if they are more than 3
  hours apart.
- **Evaluated only on routines I invented.** All evaluation data is synthetic and generated from known schedules
  (`pawpal_ai/demo_data.py`), so the learner's accuracy is the accuracy of recovering a clean, Gaussian-ish
  schedule. Real households are messier. Nothing here was tested on a real pet's history.
- **Assumes a single, attentive owner who logs honestly.** The system only learns what gets logged. If an
  owner forgets to log a walk, the system will nag about a walk that happened; if two family members both
  care for the pet, patterns blur.
- **The sync is a proxy for wellbeing, not a measurement of it.** "Happy" means "fed, walked and groomed recently according to what was logged". It cannot see illness, pain or a pet that was fed but is anxious, and an owner who forgets to log care makes the companion look needy about a well-cared-for animal. The drain times (24 h / 36 h / 1 week) are my assumptions, not veterinary guidance.
- **Cultural/lifestyle bias in the defaults:** the quiet hours (22:00-05:00), the "morning walk" framing and
  the US poison-control number assume a US-style daytime schedule and location.

## Could the AI be misused, and how would you prevent that?

- **Medical misuse / over-trust.** The most realistic harm is someone treating a sick animal using the
  assistant instead of a vet. Mitigations built in: emergency language is never answered, only escalated;
  answers are extractive from reviewed notes rather than generated; the assistant says "I don't know" and
  points to a vet when retrieval is weak; every tip is cited. Still needed before any public release: a vet
  review of the notes and a clear disclaimer in the UI.
- **Medication errors.** The notes deliberately contain no doses. Required tasks (meds) cannot be silently
  dropped, and a missed one raises an alert. The system should never be extended to suggest dosages.
- **Neglect hidden by a game.** A virtual pet could make a distracted owner feel they have cared for their
  animal. I prevent this structurally: virtual care is stored separately, never counts as real care, and is
  excluded from learning.
- **Privacy.** The care log reveals when a home is empty (walk times). It is stored locally in
  `data/care_log.json`, which is git-ignored. A hosted version would need authentication and encryption.
- **Tampered browser input.** The interactive scene sends actions from JavaScript, so a user (or a script) can send anything. Every action is validated server-side (type and mode must be known strings) and ignored otherwise. A test caught one real crash here: a list-valued `type` raised `TypeError` in the validator before I added a type check.
- **Prompt/input abuse.** Input is length-limited and no user text is executed or sent to an external
  service, so injection risk is low today; that would change if an LLM were added.

## What surprised you while testing the AI's reliability?

- **My own fixes broke other things.** Adding the species word to the query (so "Rex" would match "dogs")
  made an off-topic question match every dog note. Only the eval cases I had already written caught it.
- **The demo found bugs the unit tests did not.** The first briefing scheduled meds at 07:00 in a 07:10
  briefing, and Dinner was assigned the *morning* routine once breakfast had been logged. Both were logic
  errors in how pieces fit together, not in any single function.
- **A UI bug that only appeared for the second pet.** Selecting Mia crashed the Companion tab (`StreamlitDuplicateElementId`): the pet selector was created inside a generator expression, so choosing any pet but the first built the widget twice. My smoke tests had only ever used the first pet. The fix is a keyed widget plus a regression test that selects every pet and style.
- **The harder eval cases were more informative than the easy ones.** My first 12 retrieval cases passed
  12/12, which mostly proved I had tuned to them. Writing 6 paraphrases afterwards gave the honest number
  (16/18) and the actual failure mode (synonyms).
- **Confidence was easier to get plausible than to get meaningful.** The formula behaves sensibly (low for 2
  data points, low for noisy data), but I have no evidence that 0.9 means "right 90% of the time".

## Collaboration with AI during this project

I built this with Claude Code as a pair programmer: it read the original PawPal+ repo, proposed the
architecture, wrote most of the code and tests, and ran the demo and eval. I chose the direction (a
virtual companion with realistic/robotic styles that tracks the real pet's routine) and reviewed results.

- **A suggestion I accepted: gate retrieval on the raw question.** After an off-topic question ("best
  cryptocurrency") started matching dog-grooming notes, the AI diagnosed that adding the species word to
  the query was letting the word "dogs" match everything, and proposed scoring the raw question first as a
  gate and only then adding the species word for ranking. That fixed the bug and is covered by a test and
  two eval cases.
- **A suggestion I did not accept as written: an LLM for answers and the companion's voice.** The obvious
  design is to have Claude generate the answers and personality from the retrieved text. I kept the system
  template-based and extractive instead. It was a poor fit for this system: the task is pet *health*, where
  a fluent hallucination is worse than a stiff answer; it would make the demo and eval non-reproducible
  and require an API key from every reviewer; and it would make the "robotic vs realistic" claim harder to
  test, since the style could change the facts. The cost is less natural-sounding text and the synonym
  blind spot noted above; swapping in embeddings or an LLM is the natural next step once those risks can
  be evaluated.
- **One more change to AI output:** the first version of the evaluation harness passed 46/46, which I did
  not trust. I asked for harder, post-hoc paraphrase cases, and kept the two failures rather than tuning
  them away.
