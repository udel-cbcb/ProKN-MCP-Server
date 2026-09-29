# Inference from the evidence

How to draw conclusions on top of the retrieved papers without turning synthesis into fiction.
Every inference here is grounded in PMIDs, labeled as an inference, and graded for confidence. If you
can't do all three, don't make the inference.

## The four kinds, and how to do each

### 1. Confidence calibration

Take a connection (a ProKN edge, or a claim) and say how well the evidence actually backs it, rather
than just that a paper exists.

- Count the independent primary studies (different groups, not one lab citing itself).
- Weigh the tier (below). One preprint is not three primary papers.
- Fold in the graph side: a ChEMBL/DrugCentral-only edge with strong primary literature moves up; a
  LINCS-only signal with no paper stays low.
- Output: a graded call plus what would raise it. "High confidence: EGFR is a lapatinib target
  (PMIDs a, b, c; primary). Would rise further with a co-crystal structure."

### 2. Mechanistic inference

When several papers together imply *why* a connection holds (a pathway, a binding mode, a regulatory
step) that no single edge or abstract states outright, say it as an inference and cite the papers
that each contribute a piece.

### 3. Bridging hypotheses (Swanson ABC / literature-based discovery)

The classic move: the literature supports A-B and, separately, B-C, but nobody has connected A-C.
Propose A-C as a testable hypothesis.

- Show both halves: the A-B PMIDs and the B-C PMIDs, and the shared B.
- State it as a hypothesis and give the confidence (usually moderate at best) and how to test it.
- Never assert A-C as established, and never claim it's "in ProKN" if it isn't.
- Watch for a spurious B: if B means two different things in the two literatures (same word, different
  entity), the bridge is invalid. Check the B is the same node.

### 4. Gap and contradiction inference

- **Gap:** the literature supports a connection ProKN lacks. Infer it as a candidate edge to add,
  labeled as literature-only.
- **Contradiction:** papers disagree, or newer work fails to replicate. Weigh them (recency, tier,
  sample size, independence) into a current-consensus call and say how firm it is.

## Confidence rubric

Grade every inference:

- **High** — multiple independent primary studies agree; mechanism or measurement is direct; no
  serious contradiction.
- **Moderate** — one solid primary study plus supporting reviews, or consistent but indirect
  evidence; some gaps.
- **Low** — single study, single species/cell line, indirect or correlational only, or a
  computational prediction.
- **Speculative** — a bridging hypothesis or a mechanistic guess with partial support. Always phrased
  as "to be tested".

Say, in one clause, what evidence would move the grade up. A grade with no path to improve it isn't
useful.

## Evidence tiers (same as the review)

Curated primary experiment > review/meta-analysis > preprint or computational prediction. ProKN edge
PMIDs are usually curated primary; a LINCS perturbation signal or a docking prediction is weaker and
an inference built only on those cannot be more than Low.

## Anchoring (the anti-hallucination rule)

- Base each inference on what the **abstract (or full text) actually says**, not the title, not the
  journal, not the paper's existence. Where you can, point to the specific claim.
- If the abstract doesn't support a step in the chain, the step is dropped and the inference weakens
  or falls.
- Don't infer across a term the papers use loosely (a gene symbol that maps to two genes, a drug
  class vs a specific drug). Resolve the entity first.

## Output shape

Present the inferences as a Markdown table, after the review, one row per inference:

| # | Inference | Kind | Confidence | Basis (PMIDs) | To raise confidence / test |
|---|-----------|------|------------|---------------|----------------------------|
| 1 | EGFR is a bona fide lapatinib target | calibration | High | 22178589, 38986734 (primary) | co-crystal or independent replication |
| 2 | Lapatinib may modulate C via B | bridge (A-B-C) | Speculative | A-B: 12345678; B-C: 23456789 | direct A-C assay |

Column meanings:

- **Kind:** calibration / mechanism / bridge / gap / contradiction.
- **Confidence:** high / moderate / low / speculative.
- **Basis:** the PMIDs the inference rests on, tier noted; for a bridge, give both halves of the
  chain (A-B and B-C PMIDs) in this cell so the reasoning is visible.
- **To raise confidence / test:** the one thing that would move the grade up, or how to test a
  hypothesis.

Keep the table separate from the cited review above it, so a reader can take the facts and leave the
hypotheses (or vice versa). If there's nothing worth inferring, say so in one line instead of an
empty table. (DOIs still go with the citations in the review itself, per PubMed's attribution rule;
the table carries PMIDs.)
