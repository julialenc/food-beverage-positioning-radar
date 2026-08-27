# Category Cleanup Governance

**Status:** MVP launch governance  
**Last updated:** August 2026

This document defines how Open Food Facts category tags are converted into the
Food & Beverage Positioning Radar analytical categories used by Streamlit.

Open Food Facts categories are contributor-assigned folksonomy tags. They are
useful for broad retrieval, but they are not clean retail shelf definitions.
Products can inherit broad parent tags, appear in multiple categories, or carry
metadata that is too broad for nutrition and positioning comparisons.

The project therefore treats category cleanup as a governed analytical layer.
The goal is not to correct Open Food Facts itself. The goal is to decide which
records are comparable enough to appear in a given MVP category view.

## MVP Scope

The August 2026 MVP focuses on these Streamlit categories:

```text
snacks
cereals
dairies
beverages
```

The user-facing app displays `dairies` as **Dairy**.

The main manually reviewed category bases are France, UK/Ireland, and
US/Canada. Other observed regions may appear in source data, but they should
not be treated as equally cleaned analytical markets unless explicitly reviewed.

Category cleanup rules are implemented through shared category logic in
`pipeline/category_rules.py` and consumed by bulk and incremental ingestion.

## General Principles

1. Classify by product format and commercial use case, not only by ingredient.
2. Keep the analytical category narrow enough for meaningful comparison.
3. Route products to a better project category where possible.
4. Exclude clear meal, cooking, ingredient, or category-noise records from the
   analytical base when they are not comparable.
5. Use manual review only when product name, category metadata, brand, and image
   evidence do not support a clear deterministic decision.

Duplicate OFF category membership is normal. The project assigns one primary
analytical category for MVP Streamlit use.

## Snacks

For this project:

```text
Snack = confectionery, ice cream, savoury snacks, sweet biscuits, snack bars,
cereal bars, and fruit snacks.
```

This follows a Euromonitor-style product-coverage logic and is based on
commercial product format and primary consumption occasion, not every possible
way a consumer might eat the product.

Public citation anchor:
`https://www.marketresearch.com/Euromonitor-International-v746/Snacks-38022421/`

MVP cleanup status as of August 2026: France Snacks, UK/Ireland Snacks, and
US/Canada Snacks are locked for Streamlit use.

### Snack Review Values

Use:

```text
snack
not_snack
???
```

Use `???` only during manual review. For final MVP cleanup output, unresolved
`???` rows should be converted to `not_snack` and excluded from the snacks
analytical base unless image review confirms snack format.

### Keep As Snack

Classify as `snack` when the product clearly fits one of these groups:

- confectionery: chocolate, chocolate bars, pralines, candy, sweets, gummies,
  jellies, licorice, marshmallows, nougat, caramels, toffees, lollipops,
  chewing gum, fruit paste, or almond paste sold as confectionery;
- ice cream and frozen desserts: ice cream bars, cones, sorbets, frozen snack
  desserts;
- savoury snacks: chips, crisps, crackers, baked snack crackers, sticks,
  pretzels, popcorn, tortilla chips, corn chips, rice cakes sold as snacks,
  puffed or extruded snacks, snack mixes, snacking nuts, fruit-and-nut packs,
  wasabi peas, apero or party snack mixes;
- sweet biscuits and sweet bakery snacks: biscuits, cookies, wafers,
  madeleines, mini cakes, brownies, muffins, croissants when packaged as sweet
  bakery snacks, panettone, pandoro, sweet filled pastries, sweet brioche-style
  snacks, and pasta frolla with sweet cream;
- snack bars and cereal bars: snack bars, cereal bars, granola bars, protein
  bars, energy bars, fruit bars, nut bars, and breakfast bars in bar format;
- fruit snacks: fruit rolls, fruit strips, dried-fruit snacking packs, and
  fruit-and-nut snack packs.

Sandwich cookies and sandwich biscuits are `snack`; the sandwich wording refers
to biscuit format, not a meal sandwich.

Texture words are not snack-format signals by themselves. Do not classify a
product as `snack` only because the name contains weak attributes such as
`crisp`, `crispy`, `crunchy`, `creamy`, `baked`, `golden`, or similar texture
and preparation words. These words count as snack evidence only in a clear
snack-format phrase such as `crisps`, `chips`, `crackers`, `crispy snack`,
`baked snack crackers`, or `crunchy snack mix`.

### Remove From Snacks

Classify as `not_snack` when the product is primarily a meal, prepared dish,
cooking ingredient, deli/traiteur item, or bakery meal component.

Remove:

- pasta, macaroni cheese, lasagne, ravioli meals, gnocchi, tagliatelle meals,
  penne meals, noodles or instant noodles without snack-format wording, rice
  pasta meal kits, mini meal kits, prepared pasta salads;
- gyoza dumplings, shumai, banh bao, bao buns, dumpling mix, matzo ball mix,
  steamed buns, and filled buns unless the pack/name clearly signals snack
  format or snack occasion;
- fresh prepared bakery items, traiteur products, fresh savoury cakes, savoury
  cake loaves, sausage rolls, quiches, mini pies, sandwiches, wraps, filled
  buns, prepared appetizers without snack-pack positioning, and prepared salads;
- bread, buns, rolls, brioche meal products, flour, baking mixes, dough, pizza
  bases, wraps, and tortillas when sold as meal components;
- ham, meat packs, surimi salads, cheese meal components, prepared salads, meal
  bowls, ready meals, lunch kits, dinner kits, and meal kits;
- cooking mixes, sauces, seasonings, dips, dressings, and spreads when they are
  ingredients or accompaniments rather than finished snack products;
- actual cheese or dairy components when the product is not clearly sold as a
  packaged snack format.

Meal-format wording can override snack tags. Small pack size does not
automatically make a product a snack.

Soup/salad wording requires product-format review:

- soup crackers and oyster crackers are `snack`;
- soup-flavoured chips, crisps, popcorn, and extruded snacks are `snack`;
- Saladitas, saltines, crackers, and similar cracker formats are `snack`;
- salad toppers are `not_snack` when clearly sold as topping-use products;
- chicken salad, tuna salad, couscous salad kits, prepared salad kits, soup
  mixes, instant soup, and matzo ball soup mix are `not_snack`.

### Snack Examples

```text
Pasta Chips -> snack
Noodle Sticks Masala -> snack
Bebeto Spaghetti Candy -> snack
Goldfish baked snack crackers, macaroni & cheese flavour -> snack
Vegetable Gyoza Snack Pot -> snack
Garlic & mozzarella filled in-fry gnocchi - crisp & creamy -> not_snack
Crispy chicken meal -> not_snack
Macaroni Cheese With Bacon -> not_snack
M&S sausage rolls -> not_snack
Baguette sandwich -> not_snack
Preparation pour brioche -> not_snack
```

## Cereals

For this project:

```text
Cereal = breakfast cereal only.
Cereal bars = snacks.
```

`cereals` means breakfast cereal products intended to be eaten as cereal,
usually with milk or yogurt, or prepared as hot cereal. The category is based on
product format and commercial occasion, not simply on whether the product
contains grains, cereal ingredients, oats, rice, wheat, or flour.

MVP cleanup status as of August 2026: France Cereals, UK/Ireland Cereals, and
US/Canada Cereals are locked for Streamlit use.

### Cereal Review Values

Use:

```text
cereal
route_to_snacks
not_cereal
???
```

### Keep As Cereal

Keep products that are clearly breakfast-cereal formats:

- ready-to-eat breakfast cereals;
- corn flakes, bran flakes, wheat flakes, and other breakfast flakes;
- choco balls, loops, pillows, filled breakfast cereals, puffs, and clusters;
- cereal chips when "chips" describes breakfast-cereal shape or format, such as
  Schoko Chips, Zimt Chips, chocolate cereal chips, flakes, puffs, loops,
  pillows, or clusters;
- muesli;
- loose granola;
- toasted flakes, toasted oats, toasted muesli, and toasted loose granola;
- porridge, oats, oatmeal, and other hot cereals;
- wheat biscuits, shredded wheat, and Weetabix-style products;
- breakfast cereal variety packs and cereal assortments.

Ingredient/flavour wording can be present in valid cereal products. For
example, keep `Kashi Organic Cereal Sweet Potato Sunshine` and sweet potato
granola when the product is clearly sold as breakfast cereal or loose granola.
Also keep pancake or waffle flavour when the product is explicitly a
breakfast-cereal product, such as waffle-flavoured cereal, pancake-flavoured
oatmeal, or Oats Overnight/oatmeal products.

### Route To Snacks

Cereal bars, granola bars, breakfast bars, protein bars, snack bars, fruit bars,
nut bars, and energy bars belong in `snacks`, not `cereals`.

Bars, biscuits, cookies, bites, wafers, crackers, rice cakes, crisps, chips,
and sweet bakery snack formats should not remain in `cereals`. When they fit
the snack definition, route them to `snacks`; otherwise remove them from the
cereal analytical base.

Trail mix and CLIF-style energy-food formats route to `snacks`, even when they
contain oats or cereal ingredients.

Brand names containing `bar` do not automatically make a product a snack.
Classify by product format, not by brand-string noise. Barbara's cereals,
Picky Bars oatmeal or hot-cereal formats, Larabar Renola / grain-free loose
granola, and Larabar Peanut Butter Chocolate Chip in cereal format can remain
`cereal` when the pack is clearly a bowl/hot cereal or loose granola product.

CLIF products route to `snacks` for this project, even when they contain oats
or granola, because the brand's product formats are portion-packed and
snack/sports-occasion positioned rather than breakfast-cereal positioned.

### Remove From Cereals

Exclude products that contain cereal, grain, flour, rice, oats, or wheat but are
not breakfast-cereal products:

- bread, buns, brioche, rolls, toast bread, rusks, and crispbread;
- crisp toasts, dry bread replacements, sandwich toasties, and sesame oil;
- toast, biscottes, flatbreads, couscous, polenta, potatoes, and other meal
  staples;
- flour, semolina, starch, baking mixes, and dough;
- pancake mixes, waffle mixes, cake mixes, and other cooking-helper mixes;
- pancake syrup, actual pancakes/waffles, pancake/waffle batter, and similar
  prepared/cooking-helper formats;
- beans, bread mixes, hot dog buns, pork panko, breakfast hash, mashed
  potatoes, and similar meal/staple formats;
- pasta, noodles, gnocchi, ravioli, tortellini, and couscous meal kits;
- rice, grains, quinoa, bulgur, lentils, and raw meal staples;
- pizza bases, wraps, tortillas, galettes, and crepes;
- prepared meals, bowls, soups, salads, sauces, toppings, and meal kits.

Potatoes, sweet potatoes, pommes de terre, fries/frites, hash browns, and tater
tots are `not_cereal` unless the product is explicitly a breakfast-cereal or
loose-granola format.

Granola, muesli, corn flakes, porridge, oats, and oatmeal belong in `cereals`
only when sold as loose, bowl, or breakfast-cereal formats.

## Dairy Interaction

For MVP, all milk-related products remain in the internal `dairies` category
(displayed as Dairy in the app): milk, hard cheese, yogurt, drinkable yogurt,
flan, mousse, dairy desserts, and similar products.

Some dairy products may function as snacks, especially small yogurts or dairy
dessert packs, but the current app uses one primary analytical category. A
future version may add a separate snacking-occasion flag or allow
double-assignment.

## Beverage Interaction

Beverages use a separate MVP view segmentation layer documented in
`docs/NUTRITION_OUTLIER_GOVERNANCE.md` and implemented in
`shared/beverage_segments.py`.

The beverage segment split is used for chart readability and nutrition
comparability. It separates ready-to-drink products from syrups, concentrates,
powders, tea/coffee preparations, alcohol-related products, meal-replacement
shakes, and unknown beverage records.

## Execution Order

When multiple cues are present, apply rules in this order:

1. Identify clear category-format positives.
2. Apply explicit route rules.
3. Apply clear exclusion rules.
4. Apply documented override rules.
5. If still ambiguous, assign manual review.

For snacks, snack-format override can win over meal-like words only when the
product clearly signals snack format. For cereals, breakfast-cereal format can
win over flavour or ingredient noise.

## Launch Notes

The original detailed snack and cereal cleanup notes were merged into this
single governance file for the August 2026 launch documentation cleanup. The
merge preserves the operational logic but gives category mapping one consistent
documentation home.
