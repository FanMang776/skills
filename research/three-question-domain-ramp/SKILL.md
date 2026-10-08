---
name: three-question-domain-ramp
description: Ramp up on an unfamiliar domain fast with consensus/divergence/self-quiz.
version: 0.2.0
author: cj (FanMang776)
license: MIT
platforms: [any]
---

# Three-Question Domain Ramp

Method distilled from a viral X post (MIT grad student consuming a new discipline
in 48 hours with AI; retold in Chinese by the Douyin account "学习有了方法").
The agent acts as quiz-setter and grader — never as ghost-writer: the learner must
do the cognitive work themselves or nothing is learned.

## When to Use

- User asks to rapidly get up to speed on an unfamiliar domain, discipline,
  business area, or tech stack within hours to days
- Target level: able to hold an expert conversation or pass a qualifying exam
- Not for: shallow Q&A (just answer), or plugging gaps in an already-mastered field

## Procedure

1. **Scope & acceptance criteria.** Confirm with the user: domain boundary,
   target proficiency, time budget. Write all three into the map document header.
2. **Build the corpus (hallucination floor).** Collect 5-15 authoritative
   primary sources (textbook-grade surveys, official docs, classic papers,
   lecture notes) into `domain-ramp-<domain>/kb/`. User-provided files take
   priority; otherwise search/fetch. Review the list with the user before
   proceeding — bad corpus poisons every later step.
3. **The three questions.** Every answer must cite the corpus (file + section);
   say "not covered by the corpus" rather than invent. Merge Q1+Q2 into
   `knowledge-map.md` (template: `templates/knowledge-map.md`).
   - Q1 Consensus: "Based only on the corpus, what five core mental models do
     all experts in this field share? For each: one-line definition, source,
     and what it explains."
   - Q2 Divergence: "List 3 genuine controversies among experts found in the
     corpus, with the strongest argument for each side and sources." If the
     corpus shows high consensus, say so — never fabricate disagreement.
4. **Set the quiz.** Write `quiz.md` (template: `templates/quiz.md`): 10 deep
   questions covering all five frameworks and all controversies. Test
   understanding and application (scenarios, comparisons, whys), not term
   recall. Tag each question with the framework it probes; attach a grading
   rubric (bullet key points). The template also carries the coverage map and
   the drill-round log.
   **`quiz.md` is grader-owned.** The rubric is the scoring key: a learner who
   sees it will pattern their answers to the key points and grading measures
   nothing. Deliver questions to the learner in the conversation (or a
   rubric-free copy) — never point them at the full `quiz.md`. The knowledge
   map is likewise for grading and post-round review, not pre-reading: the
   learner answers blind first, then fills gaps from the map/corpus only on
   questions they missed (pretesting effect).
5. **Drill loop (the bulk).** Round = learner answers in their own words →
   agent grades per rubric (right / partial / wrong + missed points) → for each
   miss, ask "where exactly is your answer wrong, which key points did you
   miss?" and point to the corpus location → learner re-answers. After a clean
   round, mix past misses with 2-3 fresh questions for one more round to beat
   short-term memory.
6. **Deliverables.** Finalize `knowledge-map.md` with a blind-spot list
   (weaknesses exposed by drills + what to read next) and an expert-question
   list (questions the learner can now ask a domain expert).

Pass bar: one full round at 10/10 against the rubric, plus one mixed retest
round passed, and the learner can restate at least three of the five frameworks
without looking at the document.

## Pitfalls

- **Hallucinated consensus in niche domains.** LLMs will confidently invent
  "expert agreement." The only defense: corpus-only answers with citations.
- **Softball questions.** Default quiz generation skews to recall. Before
  grading, ask: could the learner answer this in a different scenario?
- **Fake controversies.** A manufactured disagreement misleads worse than none.
  Both sides must exist in the corpus text.
- **Answering for the learner.** Under time pressure the user will ask you to
  just answer. That voids the entire method — the grader cannot sit the exam.
- **Handing the rubric (or map) to the learner.** Rubrics and the finished
  knowledge map are grader artifacts. Learner-visible copies must not contain
  rubrics; the learner answers blind, then checks sources only on graded
  misses. Watch for the user "preparing" by reading both before round 1 —
  that's the same trap as being answered for, just self-inflicted.

## Optional extension: knowledge-base integration

If you maintain a knowledge base (Obsidian vault, wiki), archive the finished
`knowledge-map.md` as a query-page that links the concepts/entities it touched,
and feed existing notes back into step 2 as corpus. Skip if you have none.
