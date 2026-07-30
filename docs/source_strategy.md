# Source Strategy

## Purpose

The source strategy ensures that factual educational and non-medical ergonomics records are accurate, traceable, copyright-safe, and suitable for concise paraphrasing. `data/sources/source_catalog.csv` is the authoritative Stage 2 inventory. Inclusion in the catalog means a source is a candidate for record curation, not that every claim in it is accepted.

## Source categories

The initial catalog covers five needs:

1. Learning and memory strategies: systematic or major evidence reviews plus representative primary studies.
2. Study scheduling: spacing, retrieval, task switching where appropriate, and the limits of fixed break schedules.
3. Subject-specific activities: official practice guides, curriculum frameworks, and standards that describe real learning tasks.
4. Breaks and prolonged sitting: systematic reviews and public-health or occupational-health guidance.
5. General ergonomics and posture: official, non-medical workstation and movement guidance.

No paid service or paid API is required. A source may be paywalled for full text only when an authoritative abstract or official evidence review supports a narrow paraphrase; such records receive a limitation and may require stronger manual review.

## Current source-coverage gap matrix

This matrix assesses only the 19 sources already present in `source_catalog.csv`. It does not assume or invent additional evidence.

| Knowledge area | Stage 2 assessment | Current support and gap |
| --- | --- | --- |
| General learning science and study strategies | Sufficient for Stage 3 | Major evidence review, spacing meta-analysis, retrieval studies, self-explanation, interleaving, concept-mapping comparison, and an official study guide provide a strong initial base. |
| Mathematics and problem solving | Sufficient for Stage 3 | The IES mathematics guide plus worked-example, self-explanation, interleaving, and general learning sources support an initial curated set. University coverage must retain limitations. |
| Reading and comprehension | Sufficient for Stage 3 | The IES adolescent-literacy guide and general learning sources support secondary-school and transferable reading-task records. |
| Writing and revision | Sufficient for Stage 3 | The IES secondary-writing guide directly supports model-practice-reflect, reading-writing integration, and feedback-oriented writing tasks. |
| Computer science and coding | Partially covered | The CS2023 curriculum framework describes tasks, knowledge areas, testing, and debugging, but the catalog lacks direct evidence reviews for independent coding practice and programming pedagogy. |
| School science | Partially covered | NGSS describes school science practices and the learning-science sources support general methods, but subject-specific independent-study evidence is limited. |
| Languages and vocabulary learning | Partially covered | Retrieval, spacing, and adolescent vocabulary guidance are relevant, but the catalog lacks language-learning-specific authoritative or review evidence. |
| Business, economics, and accounting | Source expansion required | No current source directly describes these subject tasks, quantitative practice, case work, or accounting procedures. |
| Law and case-based subjects | Source expansion required | No current source directly supports legal reading, case briefing, issue-rule-application reasoning, or legal writing tasks. |
| Health and medical study tasks | Source expansion required | Current health sources address sedentary behavior and ergonomics, not safe study methods for anatomy, clinical reasoning, or medical-science learning. |
| Design, engineering, and project-based work | Source expansion required | No current source directly supports iterative design, critique, project planning, studio work, or portfolio tasks. |
| Ergonomics, movement, posture, and prolonged sitting | Sufficient for Stage 3 | OSHA, HSE, WHO, NIOSH, and two systematic reviews support cautious non-medical records while explicitly preserving uncertainty about timing and transfer to students. |

"Sufficient for Stage 3" means sufficient to begin a limited, source-traceable first curation pass. It does not mean complete coverage or permission to generalize beyond each source's population and limitations.

## Required Stage 3 source expansion

Before accepting canonical records in a partially covered or uncovered area, Stage 3 must add and review appropriate authoritative sources in this priority order:

1. **Business, economics, and accounting:** authoritative curriculum or professional frameworks for typical learning tasks, plus credible evidence for quantitative practice, case analysis, and accounting problem work.
2. **Law and case analysis:** authoritative legal-education or university sources for case reading, issue identification, rule application, comparison, and evidence-based legal writing.
3. **Health and medical-science study tasks:** education-focused systematic reviews or authoritative health-professions education sources. Clinical diagnosis and treatment content remains out of scope.
4. **Design and project-based subjects:** authoritative design-education or project-learning sources covering iteration, critique, prototyping, and reflective documentation.
5. **Computer science and coding:** primary or review evidence for active programming, code tracing, debugging practice, feedback, and transfer beyond the descriptive CS2023 framework.
6. **School science:** additional authoritative sources for independent study activities across physical, life, and earth science without turning the dataset into curriculum-specific tutoring content.
7. **Languages and vocabulary:** language-learning-specific reviews or authoritative educational guidance for vocabulary, grammar, reading, listening, and productive practice.

New sources must pass the same identity, evidence, licensing, paraphrase, and manual-review checks as the current catalog before they support records. Areas marked `source expansion required` cannot contribute factual canonical records until that expansion is complete.

## Evidence hierarchy

From strongest default support to weakest:

1. Current systematic reviews, meta-analyses, and major evidence reviews with transparent methods.
2. Official evidence-based practice guides from public educational or health bodies.
3. Replicated or high-quality peer-reviewed primary studies directly relevant to the claim.
4. Official curriculum frameworks and standards for descriptive subject activities, not causal effectiveness claims.
5. Reputable university learning-science resources when primary or major-review coverage is unavailable.
6. Expert consensus used only when empirical evidence is unavailable and clearly labeled.

Source type does not automatically determine evidence strength. Reviewers must consider population, task, outcome, comparison, date, consistency, and transfer to independent study.

## Selection criteria

A source is accepted for cataloging when it:

- has identifiable authors or an accountable organization;
- has a stable official, DOI, PubMed, ERIC, or publisher URL;
- directly supports one or more planned fields or recommendations;
- states enough methodology or provenance to judge its role;
- can support a concise paraphrase without copying protected expression;
- exposes relevant limitations, evidence ratings, or population boundaries;
- does not depend on product marketing or a paid service.

For ergonomics, prefer government occupational-health agencies, WHO guidance, and systematic reviews. For subject activities, curriculum standards describe what learners do; they do not prove that a study technique is effective.

## Catalog fields

Each row records:

- `source_id`
- `title`
- `organization_or_authors`
- `publication_year`
- `source_type`
- `url`
- `license_or_reuse_note`
- `access_date`
- `topics_supported`
- `evidence_strength_note`
- `limitations`
- `supports_paraphrased_records`
- `manual_review_status`

Unknown rights are written as `Unknown; metadata and short paraphrase only pending review`, never guessed. `supports_paraphrased_records` means a source can support short factual summaries with citation; it does not authorize copying figures, tables, or long text.

## Citation rules

- Every factual record cites at least one cataloged `source_id`.
- A citation must support the exact recommendation, population, and limitation expressed.
- Multiple sources are used when a claim combines distinct facts.
- Source IDs remain stable even if a URL changes; URL changes are logged.
- The retrieval response will eventually expose source title, organization or authors, year, and URL.
- Evaluation queries and purely navigational alias variants are not research claims, but alias records should cite a descriptive curriculum or authoritative terminology source when available.
- Synthetic expansions inherit source IDs only from their reviewed parent and may not broaden the claim.

## Paraphrasing and copyright safety

Curators will write short original summaries. They will not copy abstracts, recommendations, tables, figures, assessment items, or substantial passages. Direct quotations should be exceptional, brief, necessary, and recorded with quotation context during Stage 3.

The project may rely on facts and ideas from copyrighted research while preserving citation. Reuse permission is treated separately from access. Public-domain and open-license sources are preferred for foundational guidance, but license compatibility still requires review for the intended distribution.

Special cases in the initial catalog include:

- U.S. Department of Education practice guides that explicitly state public-domain status.
- HSE web content under the Open Government Licence v3.0, excluding third-party media.
- WHO guidance under CC BY-NC-SA 3.0 IGO, with non-commercial and share-alike conditions.
- CDC/NIOSH material that is generally U.S. public domain but may contain third-party exceptions and attribution requirements.
- Journal articles where publisher copyright remains in force; use only concise paraphrased claims and metadata unless an open license is confirmed.

## License tracking

Reviewers record the most specific known license or reuse condition and its evidence location. License status values in Stage 3 should become:

- `public_domain_confirmed`
- `open_license_confirmed`
- `copyright_paraphrase_only`
- `unknown_requires_review`
- `rejected_incompatible`

The current CSV uses human-readable notes because the final license vocabulary and distribution model still require review. Logos and third-party images are excluded from reuse even when surrounding government text is reusable.

## Source rejection criteria

Reject or quarantine a source when it is:

- an SEO blog, unsupported productivity article, or commercial marketing page;
- anonymous or missing a responsible organization;
- a secondary summary that misstates or overgeneralizes research;
- medical diagnosis or treatment advice outside project scope;
- based on fabricated, unverifiable, or retracted evidence;
- too narrow to justify the proposed population or claim;
- a universal timer or posture claim without credible support;
- inaccessible enough that the claim cannot be manually checked;
- unclear in licensing when the intended use would require copying protected expression;
- superseded by a materially newer authoritative source without a reason to retain it.

## Review workflow

1. **Discover:** Record candidate metadata and intended topics.
2. **Verify identity:** Confirm title, author or organization, year, and stable URL.
3. **Screen quality:** Classify source type, methods, population, outcomes, and conflicts.
4. **Check reuse:** Record license or state that it is unknown.
5. **Extract claims:** Write short claim notes with page, section, recommendation, or abstract context.
6. **Draft record:** Paraphrase narrowly and include limitations.
7. **Risk-tier review:** Apply the Tier A, B, or C policy. Tier A claims receive full documented manual review; Tier B canonical templates receive full manual review followed by automated expansion validation; Tier C receives automated validation and stratified sampling.
8. **Accept or reject:** Set the source and record review status; rejected material stays out of processed data.
9. **Audit:** Sample accepted records and all safety-sensitive records before release.

The initial catalog status is `screened_stage_2`, not final approval. Full-text and license review belongs to Stage 3.

The competition prototype may use one documented reviewer because the project currently has one AI developer. A second independent reviewer is recommended before production or public deployment, especially for Tier A content, but is not required to complete the competition prototype. No unreviewed sensor record may enter the production corpus.

## Handling disagreement and limitations

Conflicting studies are not averaged into a false consensus. Records must expose the disagreement or use the strongest current review. For example, concept mapping can be useful for organizing relationships, while claims that it is always inferior to retrieval practice are not justified. Likewise, the current work-break evidence does not establish one optimal frequency and duration for all users.

Evidence from employees or controlled laboratory tasks may inform cautious study-design proposals but cannot be presented as direct proof for all students. Each such transfer is documented as a limitation.

## Updating stale sources

- Recheck live guidance pages and licenses at least every 12 months.
- Recheck systematic-review topics at least every 24 months or when a new review is known.
- Recheck curriculum frameworks when the issuing body publishes a new edition.
- Store `last_checked_date`, `superseded_by_source_id`, and change notes in the Stage 3 provenance log.
- Deprecate records whose only support is retracted, materially superseded, or no longer accessible.
- Do not silently replace a URL or evidence rating in a released dataset.

## Current weak areas

- Direct evidence for translating workplace break guidance into student session templates is limited.
- Pressure-distribution and posture-direction semantics are hardware-dependent and unconfirmed.
- Curriculum frameworks describe activities well but usually do not establish the effectiveness of independent study methods.
- Many foundational learning-science articles are copyrighted; the project must rely on concise paraphrase and careful citation.
- Alias coverage across countries and institutions will require manual review to avoid false matches.
