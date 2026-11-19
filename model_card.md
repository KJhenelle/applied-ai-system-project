# Model Card: PawPal+ Companion

## System summary

PawPal+ Companion is a pet-care helper with a virtual pet. It is a rules-and-retrieval system, not a trained
model, and it calls no outside AI service. It learns a real pet's routine from the care history (median time
of day and how much it varies, with a confidence score), plans the day around that routine, looks up care tips
in six hand-written notes (`knowledge/`) and shows the source for each one, and checks its own output before the
owner sees it. The virtual pet is drawn as a chibi-style dog or cat in a realistic or robotic style, in a scene
that changes with the real time of day. It is for helping an owner keep a consistent routine. It is **not** for
diagnosing, giving doses, or handling emergencies.

## What are the limitations or biases in the system?

My biggest worry was never the code. It was a person getting so wrapped up in caring for a virtual pet that they
neglect the real one. That is why the virtual pet **cannot be happy unless the real pet is happy**: each need
(belly, fun, clean) on the virtual pet is capped by how well the real animal has been cared for. I wanted the app
to encourage people toward the real pet, not replace it.

The limits that come with the system itself:

- **The knowledge is small and written by me.** Six notes, mostly general dog and cat guidance, not reviewed by a
  vet. It has almost nothing for other animals, even though the app lets you pick "other" as a species. If a note
  is wrong, the app repeats it with a source attached, which makes it sound more trustworthy than it is.
- **Search matches words, not meaning.** In my own tests, "kitty" and "summer strolls" failed to find the right
  note (16 of 18 retrieval tests passed). A wrong note coming back with a source on it is the failure I would
  most want to fix, for example with a search that understands synonyms.
- **It only learns time of day.** Weekends, a new work schedule, seasons, illness or age just look like noise and
  lower its confidence. It does not understand them. It also only knows what gets logged, so if I forget to log a
  walk it will nag me about a walk that happened.
- **"Happy" is a stand-in, not a measurement.** It means "fed, walked and groomed recently, according to what was
  logged". It cannot see pain, illness or an anxious animal. The timings I used (fed within about 24 hours, walked
  within about 36, groomed within about a week) are my own assumptions, not vet guidance.
- **I only tested it on made-up routines.** Nothing has been tried on a real pet's history, and no real person has
  reviewed its output. I also assumed a US-style daytime schedule (quiet hours of 10 p.m. to 5 a.m., a US poison
  hotline number).

## Could the AI be misused, and how would you prevent that?

The misuse I thought about most is someone **ignoring real advice, especially from a vet, because the app says
otherwise**. A vet might change a pet's schedule or treatment, and an app that keeps nudging the old routine could
get in the way. That is also why I did not want the app to give any restricted advice. It has no doses and no
diagnoses. Questions that sound like emergencies are never answered, only sent to a vet or poison hotline. Answers
only use the notes I wrote, they always name their source, and when nothing matches it says "I don't know" and
points to a vet. Required tasks like medication are never dropped quietly. They show a warning.

What it still does not do: it does not know when a vet has changed the plan. A task's own set time always beats a
learned one, so an owner can set a vet-directed time by hand, but until the history catches up it could still
nudge the old routine. Before real people used it, I would add a plain disclaimer in the app, have a vet review the
notes, and let the owner say "my vet changed this."

Two smaller points. The care history shows when a home is empty, so it is saved only on the computer running the
app and is kept out of the repo. And the scene sends clicks to the server, so every one is checked and anything
unexpected is ignored.

## What surprised you while testing the AI's reliability?

- **The error with the "mirror" (the Mia bug).** When I picked a pet other than the first one in the Companion tab,
  the whole tab broke. The cause was that the pet picker was being created more than once. My first checks had only
  ever used the first pet, so they missed it. It is fixed, and there is now a test that picks every pet in a
  household of six, in both styles, so it works for as many pets as someone wants to add.
- **My first test score was too good.** The first evaluation passed 46 of 46, which told me more about how the
  tests were written than about the app. Harder questions added afterward made two fail. I kept those failures
  and documented them instead of tuning them away.
- **Putting the pieces together found bugs the single-function tests missed.** The first morning plan scheduled
  tasks in the past, and after breakfast was logged, dinner got the morning routine.
- **Checking client input found a crash.** A test with unexpected input to the clickable scene crashed the
  validator before I fixed it.

## Collaboration with AI during this project

I built this with Claude Code. The AI read my original PawPal+ project, wrote most of the code and tests, and ran
the demos. I set the direction (a virtual robot-or-realistic pet that tracks the real pet's schedule), decided what
mattered, and tested the results myself.

- **A suggestion I accepted: draw the pet in Streamlit instead of switching to a different codebase.** The AI gave
  me four options (an animated SVG, Lottie animations, a canvas mini-game, or a different stack). I picked the SVG
  one, in a chibi style that is not heavily pixelated, because I think the visuals are the main draw of an app
  like this. It also kept everything in one project that is easy to run. I then pushed it further: a background
  scene, a bigger pet, and clickable props.
- **A suggestion I did not accept as written: the AI's first design.** In its first version the virtual pet's
  mood came from game play alone, with a row of separate care buttons and a second menu. I changed both. I
  required the virtual pet to be capped by the real pet's care, because I did not want anyone neglecting a real
  animal for a game. I also removed the extra button menu and made the care purely visual and interactive: you
  click the bowl, ball, leash and medicine cabinet, or drag the brush onto the pet. It kept the app simple, which
  is why the information now sits in a small hover menu instead.
