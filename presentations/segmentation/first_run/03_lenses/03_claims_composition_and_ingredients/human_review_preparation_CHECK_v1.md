# Bounded human review and post-v1 evidence gaps · CHECK

**Preparation complete, 18 November 2026.** Twelve existing-image records meet the authorized allocation: two qualifiers and one comparison in each primary region for cream/pudding and lower-fat potato crisps. All 12 saved image URLs returned HTTP 200 with image/jpeg content on 18 November. Image accessibility is verified; identity, legibility and claims await human adjudication.

## Julia’s review incorporated · 18 November 2026

The [original submitted decisions](human_claim_decisions_v1.csv) are preserved byte-for-byte. The [separate interpreted layer](human_claim_adjudications_v1.csv) restores exact keys from the original 12-record manifest and records an explicit, auditable target-proposition interpretation for each observation. [Reproducible interpretation](use_human_review_v1.py)

| Family and region | Two profile qualifiers | Comparison | What this contributes |
|---|---|---|---|
| Cream/pudding · France | Two explicit protein-positioning observations | Julia reports “No claims” | Qualitative examples of the measured profile carrying protein communication. |
| Cream/pudding · UK/Ireland | Two explicit protein-positioning observations, with additional low-fat/low-sugar wording | Ganache/provenance wording; target protein remains unknown | More examples of recognizable protein-pudding positioning. The comparator’s commercial-form ambiguity persists. |
| Lower-fat crisps · France | An unreadable “−50%” comparison and free-from wording | Julia reports “No claims” | Different communication dimensions; the fat target stays uncertain/unknown. |
| Lower-fat crisps · UK/Ireland | “Popped not fried” construction wording and one explicit “Reduced fat” statement | “45% less salt” and origin communication | One reduced-fat positive plus independent construction and salt/origin observations. |

The twelve targeted interpretations are **five positives, two reported non-detections, one uncertain and four unknown**. Reported non-detection records the human “No claims” statement on the submitted image. Identity-match, panel-scope and image-quality fields were left blank, so these observations remain separate from the locked documented-negative framework. Additional communication in the submitted text is preserved verbatim, without converting it automatically into new taxonomy flags.

**Interpretation for v1.** Use these as human-reviewed product examples with exact wording and image references. All four selected pudding qualifiers visibly communicate protein according to Julia’s review. This corroborates recognizable protein-pudding communication among those examples. The crisp review illustrates several simultaneous dimensions of positioning. “−50%” with an unreadable attribute cannot establish fat reduction; “45% less salt” supplies a salt observation; “popped not fried” supplies construction wording. The review supplies no profile-wide positioning rates or new supported comparison.

**Submission handling.** Five GTINs lost leading zeros in the spreadsheet. All reconcile uniquely through review ID, region, category, proposition, exact image URL and the original selected GTIN. Original entered identifiers remain in the derived file alongside restored keys. Eleven dates increase from 2027 to 2037, consistent with a possible spreadsheet autofill. Those dates are preserved and flagged as future recorded dates; normalized dates remain blank. The submission receipt date is recorded separately as 18 November 2026. No correction to Julia’s original file was made.

The post-v1 gap register continues to describe the locked-evidence baseline. This small human layer is separate, with diagnostic sampling and scope/date limitations. Provider execution and expansion remain deferred. Thursday’s work and Saturday’s handover continue.

## Human review

Use the linked images below with the [record pack](human_claim_review_v1.csv). It contains exact GTIN–region–category keys (category is dairy or snacks), working valid nutrition per 100 g, original and saved-claim image pointers, locked assessment metadata and available proposition evidence. Import barcode as text to preserve zeros. Selection used profile eligibility, missing assessment, image pointers and nutritional proximity to the regional centre or profile boundary. Names and nutrition supplied no claim decisions.

All 12 selected records have **no matched assessment in the locked claims layer**. Their image pointers exist independently of that layer. Original state/basis fields remain blank, and the saved-proposition object is empty. These are evidence gaps in the current joined layer, without a conclusion about every historical source elsewhere.

| ID | Profile family | Region | Role | Text GTIN | Recorded product name | References |
|---|---|---|---|---|---|---|
| HR01 | dessert cream/pudding | France | qualifier | 4002971243802 | High-Protein-Pudding - Vanilla | [Image](https://images.openfoodfacts.org/images/products/400/297/124/3802/front_de.103.400.jpg) · [Product](https://world.openfoodfacts.org/product/4002971243802) |
| HR02 | dessert cream/pudding | France | qualifier | 0034361824364 | Hipro crème dessert saveur vanille | [Image](https://images.openfoodfacts.org/images/products/003/436/182/4364/front_en.3.400.jpg) · [Product](https://world.openfoodfacts.org/product/0034361824364) |
| HR03 | dessert cream/pudding | France | comparison | 3033491214585 | Danette Crème dessert chocolat/caramel les 4 pots de 125 g | [Image](https://images.openfoodfacts.org/images/products/303/349/121/4585/front_fr.9.400.jpg) · [Product](https://world.openfoodfacts.org/product/3033491214585) |
| HR04 | dessert cream/pudding | UK/Ireland | qualifier | 4025500294786 | PUDDING VANILLA FLAVOUR | [Image](https://images.openfoodfacts.org/images/products/402/550/029/4786/front_en.18.400.jpg) · [Product](https://world.openfoodfacts.org/product/4025500294786) |
| HR05 | dessert cream/pudding | UK/Ireland | qualifier | 3023290064214 | Protein Pudding | [Image](https://images.openfoodfacts.org/images/products/302/329/006/4214/front_en.3.400.jpg) · [Product](https://world.openfoodfacts.org/product/3023290064214) |
| HR06 | dessert cream/pudding | UK/Ireland | comparison | 5060253702705 | Chocolate & hazelnut praline ganache | [Image](https://images.openfoodfacts.org/images/products/506/025/370/2705/front_en.14.400.jpg) · [Product](https://world.openfoodfacts.org/product/5060253702705) |
| HR07 | potato crisps | France | qualifier | 3168930002970 | Cuites au four | [Image](https://images.openfoodfacts.org/images/products/316/893/000/2970/front_fr.4.400.jpg) · [Product](https://world.openfoodfacts.org/product/3168930002970) |
| HR08 | potato crisps | France | qualifier | 0020685084423 | Croustilles cuites en marmite - Sel de mer | [Image](https://images.openfoodfacts.org/images/products/002/068/508/4423/front_en.43.400.jpg) · [Product](https://world.openfoodfacts.org/product/0020685084423) |
| HR09 | potato crisps | France | comparison | 0059749878692 | Chips | [Image](https://images.openfoodfacts.org/images/products/005/974/987/8692/front_fr.18.400.jpg) · [Product](https://world.openfoodfacts.org/product/0059749878692) |
| HR10 | potato crisps | UK/Ireland | qualifier | 5000237139394 | sour cream & onion flavour potato snacks | [Image](https://images.openfoodfacts.org/images/products/500/023/713/9394/front_en.17.400.jpg) · [Product](https://world.openfoodfacts.org/product/5000237139394) |
| HR11 | potato crisps | UK/Ireland | qualifier | 00066549 | Sweet & Smoky BBQ | [Image](https://images.openfoodfacts.org/images/products/000/000/006/6549/front_en.16.400.jpg) · [Product](https://world.openfoodfacts.org/product/00066549) |
| HR12 | potato crisps | UK/Ireland | comparison | 0000200003086 | Cheese and onion | [Image](https://images.openfoodfacts.org/images/products/000/020/000/3086/front_en.3.400.jpg) · [Product](https://world.openfoodfacts.org/product/0000200003086) |

The comparison products come from the other measurable products in the same inherited commercial form. **HR06's ganache name needs commercial-form confirmation** despite its inherited cream/pudding classification. Use the identity/scope fields to record a mismatch or continued uncertainty. Maintain the 12-record bound; an unassessable image remains unresolved.

### Enter decisions in the separate keyed layer

Fill only the human fields in [human_claim_decisions_v1.csv](human_claim_decisions_v1.csv). The template was originally blank. Julia’s completed submission now supplies the human observations; the interpreted layer preserves the exact selected keys.

- Record reviewer/date, image used, product/variant match, inspected panel (front/back/mixed/unclear), and image quality.
- For the targeted proposition, enter POSITIVE, DOCUMENTED_NOT_DETECTED, UNCERTAIN or UNASSESSABLE. A blank is pending review.
- For POSITIVE, copy the observed wording. Protein and reduced-fat decisions require wording visible in the inspected evidence. Baked or popped construction may be recorded under human_other_wording, independently of a reduced-fat proposition.
- Use DOCUMENTED_NOT_DETECTED only when the matching product and relevant panel are adequately readable and inspected. It refers to that image/panel. Wrong variant, unreadable or unsuitable evidence supports UNASSESSABLE or continued uncertainty.
- Preserve exact wording and scope where the human reading differs from the locked taxonomy. Names and nutrient values cannot establish a claim.

The record pack supplies context. The human CSV is a separate keyed adjudication layer; the preparation script preserves any future existing human decisions and refuses changed identities. It does not merge those decisions into the master or release automatically. This diagnostic selection cannot estimate profile-wide claim prevalence. Thursday's research and Saturday's handover proceed on their accepted evidence, independently of when the 12 reviews are completed.

## Prioritized post-v1 register

The [evidence-gap register](post_v1_evidence_gaps_v1.csv) contains **six proposed batches, represented by 24 region × formulation-arm rows**. Every row is POST_V1_ONLY_NOT_AUTHORIZED. It reports full arm size, known proposition states, unassessed records, proposition-specific unknown matched records, existing image pointers and poor-quality unknown assessments. Pointer counts for the full cohorts are availability indicators; only the selected 12 images received HTTP checks.

| Priority | Proposed evidence gap | Analytical decision it could change | Comparison and prerequisites |
|---|---|---|---|
| 1 | Cream/pudding protein | Does protein communication accompany the measured formulation rather than only selected examples? | Both primary regions and comparable ordinary creams/puddings. Aim to cover the 27 French and 15 UK/Irish qualifiers with prespecified comparison arms. The UK/Irish profile remains a small descriptive census. Confirm commercial form and variant. |
| 1 | Lower-fat potato crisps | Is measured lower fat communicated through an explicit fat proposition, construction wording or neither? | Include >20 g fat products with comparable construction/flavour. Target at least 30 known assessments per arm per region as a reporting target, with later power/precision design. Separate construction from fat claims. |
| 2 | Energy-drink sugar-related communication | Does the formulation/communication association repeat within commercial energy drinks? | Include very-low-sugar and other drinks in both regions. Clarify exact sugar wording, preserve functional evidence and keep sports products distinct. |
| 2 | French soda sugar-related communication | Does the selected UK association repeat in France and which wording drives it? | Both sugar arms; at least 30 known assessments each as a reporting target. Taxonomy clarification precedes a new extraction protocol. Retain the existing UK evidence. |
| 3 | Granola protein | Is the UK descriptive association reproducible across regions? | Qualifiers and other measurable granola, direct wording versus existing-rule provenance, and explicit known denominators. |
| 3 | Granola fibre | Does additional evidence distinguish the profile or confirm similar communication across it? | Both arms, claim-specific unknowns and relevant fibre availability if comparing composition. Existing 25-known profile arms remain descriptive. |

The reporting targets are planning conventions, not power calculations or guarantees of supported effects. A post-v1 protocol must set comparison sampling, precision/power, panel requirements and independent state handling before any provider work. Do not simply reprocess every unknown: good-quality matched records can remain proposition-unknown because of assessment consistency or insufficient evidence. Poor or wrong images require better source evidence before a retry. The no-added-sugar/literal-sugar-free distinction needs taxonomy clarification before a new sugar extraction, while v1 keeps its existing namespace.

## First-release reporting correction · approved

The release display label is **sugar-related communication** for locked **sugar_free_claim**. Preserve the original field, exact saved wording, state and basis. The 62.8 percentage-point UK/Irish soda comparison describes positive locked-field assessments among known records.

Cloudy Lemonade (5060054132725, UK-IE, beverages) records 3.3 g total sugars/100 ml and direct saved normalized wording “no added sugar.” Within the very-low-sugars soda arm, three positives have that wording, two have direct “sugar free” wording, and 23 rely on saved model assessments without explicit normalized wording in the join evidence. The result cannot be presented as the prevalence of literal sugar-free wording.

This label is recorded in the [segmentation methodology](../../../SEGMENTATION.md), learning_plan.md, the [accepted Wednesday CHECK](communication_overlays_CHECK_v1.md), and the display_label column of [communication_overlays_v1.csv](communication_overlays_v1.csv). Original analytical values and provenance were preserved when that column was added. Reporting correction is complete.

## Validation and STOP

The [versioned preparation](prepare_human_review_v1.py) reuses Tuesday's cohort implementation and existing classification keys. It verifies the corrected source through the shared reader, the 12 distinct GTINs and required allocation, and preserves subsequent human fields separately. The image checks used read-only HEAD requests with certificate verification; using the installed certificate bundle resolved the initial certificate-chain errors. No image content was classified by the assistant.

The initial preparation entered no human decisions. Julia’s subsequent submitted observations are incorporated in the separate layer above. No OCR/vision/model extraction, sample expansion or master changes were made. Existing locked evidence stays intact. Additional provider execution is a post-v1 proposal requiring separate authorization. STOP after this preparation; keep Thursday and Saturday on schedule.
