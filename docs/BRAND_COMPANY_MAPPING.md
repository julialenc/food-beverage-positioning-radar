# Brand and company mapping

This document explains how brand strings from Open Food Facts are normalized
and mapped to parent companies, what the mapping covers, and what it
deliberately does not attempt.

The mapping file itself is at `data/reference/company_brand_mapping.csv`.

## Purpose

Open Food Facts brand strings are entered by contributors and are often
inconsistent, fragmented, or multi-valued. A single product may list its
brand as "Nestlé", "nestle", or "Nestlé France", and the same underlying
brand appears under different parent companies depending on the market (see
known complications below). This mapping exists to support company-level
filtering and aggregation in the Streamlit app and Power BI deck.

All claim-pattern analysis and benchmark-flag computation is performed at
brand level, not company level, since a parent company's portfolio is
typically too heterogeneous to support meaningful company-level findings.
Company mapping is provided for navigation and filtering — to allow a user
to ask "show me all products I associate with Nestlé" — not for aggregate
scoring across a portfolio.

## File structure

`data/reference/company_brand_mapping.csv` has six columns:

| Column | Description |
|---|---|
| `parent_company` | The parent company as of the mapping's last update (June 2026). Reflects ownership at the time of mapping, not at any historical point or future state. |
| `brand` | The brand name as it commonly appears in the source data or in market usage. |
| `primary_brand_db` | The normalized form of the brand used as a join key to `products.primary_brand` in the database — lowercased, accent-stripped, comma-normalized. This is the field used for all joins. |
| `category` | Broad product category the brand is primarily associated with. Not a hard constraint — brands may appear in other categories in the actual data. |
| `hq_country` | Headquarters country of the parent company (ISO 2-letter code), as a reference point for company-level geographic context. |
| `notes` | Analyst notes on brand-ownership caveats, licensing conflicts, market-scope limitations, or acquisition status. These are methodologically important and should be read before using a brand in company-level analysis. |

## Coverage

The mapping covers 276 brands across roughly 40 parent companies, selected
on the basis of brand presence in the actual product sample (snacks,
beverages, and breakfast cereals from Open Food Facts) and prominence in
Western European and North American markets. It is not exhaustive relative
to the full universe of brands present in the underlying data.

Brands not in this mapping remain in the dataset and are fully analysable
at brand level — they simply do not appear in the company-level filter.

## Known complications and mapping decisions

Several situations in this mapping require interpretation rather than a
clean one-to-one relationship between brand and parent company. The most
important are documented here.

**Kellogg's brand split.** Following the 2023 Kellogg Company spin-off and
the subsequent 2024 Kellanova acquisition by Mars, the Kellogg's cereal
brand now operates under two separate ownership structures: WK Kellogg
(North America cereals, subsequently acquired by Ferrero) and Kellanova
(international cereals and snacks, now part of Mars). Products in the
database under "kellogg's" or "special k" or "corn flakes" may belong to
either entity depending on their country of origin. The mapping uses
suffixed brand entries (`special k north america`, `special k international`)
to disambiguate where this matters.

**KitKat.** Nestlé owns the KitKat brand globally except in the United
States, where Hershey manufactures and sells KitKat under a perpetual
license. Products in the database under "kitkat" are mapped to Nestlé;
US KitKat products are mapped separately as "kitkat us" under Hershey.
In practice, OFF product records may not reliably distinguish these.

**Cheerios.** In most markets outside the United States, Cheerios is a
Cereal Partners Worldwide (CPW) brand, a Nestlé/General Mills joint
venture. In the United States, Cheerios is a General Mills brand. Both
are in the mapping under their respective entities.

**Kellanova brands now under Mars.** As of August 2024, Mars completed
the acquisition of Kellanova, bringing Pringles, Cheez-It, Pop-Tarts,
RxBar, NutriGrain, and other brands into the Mars portfolio. These are
mapped under Mars in this file. Products in the database ingested before
the acquisition date may carry different brand-owner attribution in their
source records.

**Danone / Huel.** Danone announced a definitive agreement to acquire Huel
in March 2026; this transaction was pending regulatory approval at the time
of this mapping. Huel is listed under Danone in this file to reflect the
announced but not yet completed acquisition. Verify before use in any
time-sensitive market analysis.

**Fonterra consumer brands / Lactalis.** Fonterra sold the majority of its
consumer brands (Anchor, Mainland, Anlene, Anmum, Kapiti, Bega license)
to Lactalis in most markets. An exception applies: Fonterra retained the
Anchor consumer business in Greater China. The mapping reflects this split.

**Accent normalization.** `primary_brand_db` values are accent-stripped to
match the normalization applied in `clean.py` (NFKD encoding, ASCII
coercion). For example, `gerblé` is stored as `gerble`, `côte d'or` as
`cote d or`. Any join between this file and the database must use
`primary_brand_db`, not `brand`.

## What this mapping does not cover

- **Historical ownership.** Brands are mapped to their parent company as
  of June 2026. The mapping does not track pre-acquisition ownership or
  attempt to reconstruct historical company structures.
- **Sub-brand or product-line detail.** Each row is a brand, not an
  individual product line. Analytical sub-distinctions (e.g. Kellogg's
  Special K cereal vs Special K bars) are not represented.
- **Non-Western European / North American markets.** Coverage prioritises
  the markets most represented in the current snack/beverage/cereal sample.
  Brand ownership in South and Southeast Asia, Latin America, and Africa
  may differ materially from what is shown here.
- **Legal compliance or current accuracy.** This is a reference mapping
  for analytical navigation, not a legal document. Ownership structures
  can change; always verify before use in any context where accuracy of
  company attribution is material.

## How to update

When a brand acquisition, spin-off, or ownership change occurs that affects
products in the current dataset:

1. Update `parent_company` in `company_brand_mapping.csv`.
2. Add a note in the `notes` column describing the change and its
   effective date.
3. If a brand splits or is licensed differently by market, add a new row
   with a distinct `primary_brand_db` value (e.g. `kitkat us` vs `kitkat`)
   rather than overwriting an existing row.
4. Commit with a message referencing the acquisition or change:
   `data: update brand mapping for [event] ([date])`.
5. Re-run `tag_claims.py` if the mapping change affects any brands present
   in the current analysis run, since `claim_category_1` and
   `claim_category_2` are written using the brand-level groupings.
