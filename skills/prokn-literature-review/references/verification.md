# Checking inferences against the literature

The details behind step 3 of `SKILL.md`. The inferences are already written (`inference.md`); this
step tests them and doesn't rewrite them. The verdicts, the confidence rubric, and the output table
are in `SKILL.md`.

## One inference at a time

Give each inference its own searches and its own list of papers. One broad query for several
inferences makes it unclear which paper bears on which claim. Sort each paper by what it says, not
by which query or Paperclip label found it: a paper from the support query can still contradict
the inference.

## Two sources

PubMed is the primary source. It covers the peer-reviewed literature, including paywalled papers
at abstract level, and its PMIDs match ProKN's edges. Paperclip, when connected, adds preprints,
trial registries, FDA documents, a claim-level `evidence` search, and line-numbered full text for
open-access papers.

- **Count each paper once.** Match by PMC ID, then DOI, then title. Give a Paperclip-only paper a
  PMID with PubMed's `convert_article_ids` if it has one; otherwise cite preprints by DOI, trials
  by NCT number, and FDA documents by path.
- **Same rules for both.** Paperclip papers go through the same circularity rule, tiers, quoting,
  and tiered reading. Its `evidence` labels never replace your own sort (`paperclip-tools.md`).
- **Without Paperclip,** say in the summary that preprints, trials, and FDA documents weren't
  searched.

## Quoting

Every supporting or contradicting paper is backed by the sentence that justifies putting it there.

- **Word for word.** Don't reword, tidy, or join sentences. The link searches the page for these
  exact words.
- **The result, not the background.** Quote the sentence that reports the finding (what was
  measured, in what system, and which way it went), not an opening sentence restating what was
  known.
- **One or two sentences.** Longer quotes bury the point and run into copyright limits.
- **No quotable sentence, no support.** If neither the abstract nor the full text (if read) states
  the support or contradiction, the paper stays out of the table. If a sentence shows a related
  finding, record the paper as partly addressing the inference; otherwise leave it out. A paper
  can only change a verdict by making the connection explicit, and then it's support or
  contradiction, not partial.
- **Edge PMIDs** can be linked to their sentence in the ProKN basis column, but never go in the
  supporting column.

## Linking each paper to its quote

The link is a text-fragment URL: the page, then `#:~:text=` and the quote. The browser scrolls to
the quote and highlights it (current Chrome, Edge, Safari, and Firefox). If the text doesn't
match, the page still opens, without the highlight.

- **Link to the page the quote is on.** Abstract: `https://pubmed.ncbi.nlm.nih.gov/<PMID>/`. Full
  text: `https://pmc.ncbi.nlm.nih.gov/articles/<PMCID>/`. Preprint: `https://doi.org/<DOI>`.
  Trial: `https://clinicaltrials.gov/study/<NCT>`. FDA documents have no stable page; cite the path
  without a link. Highlighting on preprint and trial pages is best effort.
- **Use the start and end, not the whole quote:** `#:~:text=START,END`, with the first four to
  six words and the last three to five. A quote under about ten words can go in whole.
- **Encode it:** spaces as `%20`, and inside START and END, commas as `%2C`, hyphens as `%2D`, and
  ampersands as `%26`. The comma between START and END stays as it is.
- **Keep plain words at the edges.** Greek letters, superscripts and subscripts, symbols, and
  citation numbers like "[18]" can break the match, so move START or END inward. Leave out the
  headings PubMed adds to structured abstracts ("Results:").
- **Add a DOI link for each paper.** It comes from `get_article_metadata`, and the PubMed MCP asks
  that cited articles carry it.

For example, "Lapatinib, an inhibitor of HER2 and EGFR, was more effective in inhibiting growth of
cholangiocarcinoma cell lines than trastuzumab." (PMID 22178589) becomes:

`https://pubmed.ncbi.nlm.nih.gov/22178589/#:~:text=Lapatinib%2C%20an%20inhibitor%20of%20HER2,lines%20than%20trastuzumab`

## Tiered reading

Abstracts lean positive and often leave out the conditions (cell type, dose, time point) and the
partial or negative findings a verdict can turn on. Full text is 20 to 60 times longer and often
unavailable. So:

- **Every paper:** the abstract (or Paperclip's passage), to triage, sort, and take a first quote.
- **The deciding papers:** the full text, when the verdict rests on the paper, when the verdict
  would be Mixed (read both sides to find what differs), or when the abstract doesn't say which
  way the effect went, in what system, or whether it was measured at all.
- **At most two per inference,** primary studies first. Don't escalate reviews or preprints;
  follow a review to the primary paper it cites.
- **Read only what matters:** the Results and figure legends that mention the entities, and the
  Methods only to confirm cell line, dose, or species. In Paperclip, `lookup` the paper by PMC ID
  or DOI, `cat` its Results section, and `grep` with line numbers. Otherwise use PubMed's
  `get_copyright_status`, then `get_full_text_article`.
- **Let it change the call.** The full text can move a paper to another column ("reduced" in the
  abstract, but only at the top dose in the Results) or give a more precise quote. Once you've read
  it, sort and quote by it and mark the cell "full text"; the section and line go in the record.
- **When it isn't available** (in neither source, or copyright rules it out), keep the
  abstract-level call, mark the cell "abstract only", and don't present it as a deeper check.

## The circularity rule

The PMIDs on the edges an inference was built from are its ProKN basis. Check that they say what
the edge claims, but don't list them as support. Only papers that add something beyond the graph
count. If the search finds only the edge's own PMID, the verdict is "No literature found".

## Evidence tiers

- **Primary experimental study:** strongest.
- **Review or meta-analysis:** secondary. Cite the primary paper it rests on instead, and count
  several reviews of one result once.
- **Preprint or computational prediction:** weakest, and can't make a verdict Supported on its
  own. Cite the published version if there is one.
- **Trial with posted results** (drug inferences): primary clinical evidence.
- **FDA label or review text** (drug inferences): a curated statement of mechanism or target.
  Treat it like a database assertion: good support for a mechanism of action, not a substitute for
  an experiment on a downstream effect.
- **Trial registration without results:** shows only that the drug was tested. At most partly
  addressing, so it goes in the record, not the table.
