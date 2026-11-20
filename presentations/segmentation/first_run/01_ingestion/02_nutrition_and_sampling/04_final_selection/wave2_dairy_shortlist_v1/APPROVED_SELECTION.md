# Wave 2 US/CA dairy — approved selection

**Completion update, 12 November 2026.** The 224 new US jobs completed on 9 November, with 135 PASS and 89 HOLD. Start with the [completion report and review CSVs](../wave2_dairy_completion_quality_v1/REPORT.md). The execution instructions below preserve the historical workflow. Further paid calls require a separate decision.

**Decision, 9 November 2026.** Julia approved the [final 259-row roster](approved_selection.csv) for the September 29 reporting wave. It contains **224 distinct new US job owners and 35 historical reuse owners**. **Paid execution requires separate authorization.** The five substitutions below are the full change in membership from the [original proposal](shortlist.csv). Keep the [candidate frame](candidate_frame.csv) and [original audit](audit.json) for lineage.

## Approved membership changes

Each replacement occupies its predecessor's place in the CSV. The held GTIN and its original aliases, observations and country assignments remain in the candidate frame. The market-attribution holds apply to selection for US claims processing.

| Held GTIN | Decision on proposed source | Approved replacement | Sampling purpose |
|---|---|---|---|
| `0810934030192` Violife | Dairy-free coconut-oil cheese alternative. | `00621892` Trader Joe’s onion and chive cream cheese spread | US cheese, same three nutrient bands. Front gives 227 g. |
| `4056489545224` Milbona | Horseradish cream cheese confirmed. Romanian source context and a US tag leave US distribution unverified. | `0078742120638` Great Value chive and onion cream cheese spread | US dairy cheese spread, same three nutrient bands, 8 oz. |
| `3596710495795` Auchan | French promotional cream pack, 6 × 20 cl. US distribution unverified. | `00540131` Trader Joe’s half & half | Large-volume US cream, 946 ml. Protein and fat bands match. Sugar moves from high to middle. |
| `5000119407283` Tesco | Salted butter made with Welsh milk. US distribution of the selected pack unverified. | `0767707001258` Kerrygold unsalted Irish butter | Conventional butter, same three nutrient bands and medium size. The replacement is unsalted. [Exact UPC in US distributor catalogue](https://eurousa.com/products/kerrygold-unsalted-irish-butter/) |
| `5900120044722` Bifidus | The selected image shows a Nutri-Score explanation and cannot establish front-pack claims. | `0036632029546` Activia strawberry low-fat yogurt drink | Same three nutrient bands. The eight-bottle pack totals 744 ml and carries explicit gut-health wording. [Held image](https://images.openfoodfacts.org/images/products/590/012/004/4722/front_en.11.400.jpg) · [Replacement front](https://images.openfoodfacts.org/images/products/003/663/202/9546/front_en.4.400.jpg) |

## Format and country coverage

| Approved reporting format | New US jobs | Historical reuse |
|---|---:|---:|
| Other yogurt | 94 | 16 |
| Drinkable yogurt | 6 | 0 |
| Fermented milk | 9 | 0 |
| Cheese | 67 | 12 |
| Milk | 23 | 5 |
| Cream | 14 | 1 |
| Butter and related formats | 11 | 1 |
| **Total** | **224** | **35** |

Use `approved_format` and `reviewed_subformat` for reporting. The six drinkable yogurts are `0818290011794`, `0796252300271`, `0036632035745`, `0819393020577`, `0078742086569` and `0036632029546`. The packs for `00731546` and `0070470137780` show squeeze tubes. Both stay in other yogurt. The Trader Joe’s tub `00508056` is French vanilla low-fat yogurt. Its first ingredient explains the original milk label. Of the nine fermented milks, seven are kefir, one is ayran and one is cultured buttermilk (`0028300000551`). The eleven new butter jobs comprise seven conventional butters, one flavored garlic butter, one ghee and two butter–oil blends. The historical butter is conventional.

**Country coverage.** All 224 new jobs are US-only assignments. Reuse comprises 34 US-only owners and one Canada-only owner, with zero shared US/CA owners in this roster. Keep eligible US and Canadian observations in nutritional segmentation. For `3560070475711`, the French Carrefour milk, reuse wording from `vision_results_carrefour_targeted_fr.csv`, record 247. Its Canadian assignment does not establish Canadian distribution or positioning. Attribute wording to the French pack. [Carrefour front](https://images.openfoodfacts.org/images/products/356/007/047/5711/front_fr.93.400.jpg)

## Pack-size and nutrition decisions

Use `reporting_pack_band` for the approved sampling interpretation. A blank `reviewed_pack_quantity` means no explicit quantity override. Original `quantity`, `pack_band`, nutrients and warning fields are retained verbatim.

| GTIN | Original quantity | Reviewed net quantity and band | Evidence |
|---|---|---|---|
| `0775075110304` Skotidakis | 480 oz | 48 oz / 1.36 kg, weight large | [Net weight on tub](https://images.openfoodfacts.net/images/products/077/507/511/0304/1.400.jpg) |
| `0077890588659` Wegmans | 1 g | Half gallon / 1.89 L, volume large. The origin of “1 g” is unresolved. | [Carton](https://images.openfoodfacts.org/images/products/007/789/058/8659/front_en.3.400.jpg) |
| `0073420778149` Daisy | 30 g serving | 14 oz / 397 g, weight medium | [Pouch](https://images.openfoodfacts.org/images/products/007/342/077/8149/front_en.3.400.jpg) |
| `0034500151849` Land O’Lakes | 14 g serving | 15 oz / 425 g, weight medium | [Label](https://images.openfoodfacts.net/images/products/003/450/015/1849/nutrition_en.12.full.jpg) · [USDA exact UPC](https://fdc.nal.usda.gov/food-details/2671746/nutrients) |
| `00508056` Trader Joe’s | 100 g | 32 oz / 2 lb, weight large | [Yogurt tub](https://images.openfoodfacts.org/images/products/000/000/050/8056/front_en.41.400.jpg) |

**Salt reconciliation is pending.** Both products remain selected. Carry `salt_review_status` into nutritional QA for the owner and its linked barcode strings. Withhold these salt measurements from validated salt features, benchmark calculations and final segment interpretation until reviewed. A blank flag on another row conveys no new validation. The label equivalents below use sodium × 2.5 and are evidence for reconciliation only.

| GTIN | Wave 2 salt g/100 g | Photographed label | Approximate salt equivalent g/100 g |
|---|---:|---|---:|
| `0641548550062` Chef Shamy | 21.1632723214286 | [170 mg sodium per 9 g](https://images.openfoodfacts.net/images/products/064/154/855/0062/nutrition_en.6.400.jpg) | 4.72 |
| `0034500151849` Land O’Lakes | 11.475 | [90 mg sodium per 14 g](https://images.openfoodfacts.net/images/products/003/450/015/1849/nutrition_en.12.full.jpg) | 1.61 |

**US yogurt image selection — PENDING analytical QA.** Before interpreting claims coverage, compare all eligible US yogurts, those with a primary image URL and those with usable historical claims evidence. Report group sizes, missingness, protein, total sugars, fat and interpretable pack sizes, including full-population versus image-subset nutrient quartiles. The existing investigation counted 8,030 US dairy assignments with complete nutrition but no image, including 7,687 with yogurt ancestry. The distribution comparison remains open. It does not gate shortlist freeze or processing. Nutritional peer benchmarks use the full eligible population, including products without images. [Existing investigation](../us_ca_dairy_investigation/report.md)

## Execution planning and freeze integrity

### Local Windows commands

Run the paid command below from the repository root in Command Prompt. It checks the roster and history, automatically downloads and freezes any missing public OFF images, then requests typed confirmation before Azure submissions. The separate preparation command is optional.

```cmd
.venv\Scripts\python.exe -m pipeline.vision_ops.wave2_dairy --check
.venv\Scripts\python.exe -m pipeline.vision_ops.wave2_dairy --prepare-images
```

Review any preparation failures or history HOLDs. Repeat the same command after interrupted public downloads. The paid command below is for Julia to run **only after deciding to authorize execution**. The existing Azure credentials and nano deployment are read from the project environment or local `.env`. The command displays the exact budget and rates and requires a typed confirmation of paid execution at verified rates.

```cmd
.venv\Scripts\python.exe -m pipeline.vision_ops.wave2_dairy --execute
```

Use that same command after interruption. Keep the entire `presentations/segmentation/wave2_dairy_execution_v1/` directory. It holds the image bytes, frozen input manifest and append-only `staging.sqlite` with requests, results, usage, reservations and assessments. A saved OCR operation can be polled on resume. A submission with an uncertain outcome keeps its reservation and receives no automatic repeat. A global configuration or spending stop requires review. The program prints the assessed, accepted and unresolved counts and spending at completion.

At the [historical reservation rates](audit.json), 224 new OCR calls and 224 core calls budget to **CHF 1.16** if all reach core. Existing dairy triggers allow up to 224 context reviews and up to 224 re-extractions. The all-follow-ups bound is **CHF 2.76**, within a **provisional CHF 3.00 aggregate ceiling**. Historical reuse, beverage v6 and Canadian paid calls each add zero. No retries are budgeted. Use the existing English US/CA core prompt and GPT-4.1-nano for core and conditional dairy stages.

Before dispatch, recheck current matching history and prior reservations to prevent duplicate work, verify selected image revisions and bind the exact inputs and existing model/prompt configuration to a separate dairy run. Confirm current tariffs and the spending guard against the proposed ceiling, then obtain Julia’s explicit paid-execution authorization. Identity or history conflicts return to review. This selection grants no RUN 06B budget or runtime authorization.

The approved CSV has 259 distinct job owners and 259 distinct revision-bearing image URLs. String aliases in `source_barcodes` share one owner. Import identifiers as text. The 35 historical rows retain their original evidence pointers and require no calls. The freeze records references to the selected images, without attesting to downloaded image-byte hashes.

| File | SHA-256 |
|---|---|
| [Approved selection](approved_selection.csv) | `80fa0e89d00ad85212a14a9c3674f73e998cb7feced626d5c3822eb4d0d2d6fe` |
| [Original shortlist](shortlist.csv) | `494a4e283198e97efa2d4659679953977b365706d861e77af0808569384e5ad2` |
| [Original candidate frame](candidate_frame.csv) | `6e56e40e08ca324559077e0798fb43ba5a29f81a6e4469c28b96b2dd3e389759` |
| [Original audit](audit.json) | `d37eb554ce5471597dcfa92ad3900af7ec31c78b4759f9af79942e7cb9bc55d7` |
