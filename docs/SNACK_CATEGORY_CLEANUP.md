# Snack Category Cleanup Guidance

## Purpose

Open Food Facts `snacks` contains products that are not snacks as CPG
professionals normally define the category. This project keeps products that
fit a packaged-snacks category definition and removes meal products, prepared
foods, bakery deli products, cooking ingredients, and category noise.

MVP cleanup status as of 21 August 2026: France Snacks, US/Canada Snacks, and
UK/Ireland Snacks are locked for Streamlit use.

These are MVP category-scope rules for the current Streamlit markets, not a
universal snack taxonomy.

Use the project definition:

```text
Snack = confectionery, ice cream, savoury snacks, sweet biscuits, snack bars,
cereal bars, and fruit snacks.
```

This follows a Euromonitor-style product-coverage logic and is based on
commercial product format and primary consumption occasion, not every possible
way a consumer might eat the product.

Public citation anchor:
`https://www.marketresearch.com/Euromonitor-International-v746/Snacks-38022421/`

## Output Values

Use only:

```text
snack
not_snack
???
```

Use `???` only when product name and available metadata are genuinely
ambiguous and image review is needed.

Use `???` during manual review only. For final MVP cleanup output, unresolved
`???` rows should be converted to `not_snack` and excluded from the snacks
analytical base unless image review confirms snack format.

If a product cannot be classified from product name, brand, category metadata,
or pack image, exclude it from the analytical base rather than preserving a
low-evidence assignment.

## Execution Order

When multiple cues are present, apply rules in this order:

1. Identify clear category-format positives.
2. Apply explicit route rules.
3. Apply clear exclusion rules.
4. Apply documented override rules.
5. If still ambiguous, assign `???` for manual review.

For snacks, snack-format override can win over meal-like words only when the
product clearly signals snack format.

## Keep As Snack

Classify as `snack` when the product clearly fits one of these groups:

- confectionery: chocolate, chocolate bars, pralines, candy, sweets, gummies,
  jellies, licorice, marshmallows, nougat, caramels, toffees, lollipops,
  chewing gum, fruit paste, or almond paste sold as confectionery;
- ice cream and frozen desserts: ice cream bars, cones, sorbets, frozen snack
  desserts;
- savoury snacks: chips, crisps, crackers, baked snack crackers, sticks,
  pretzels, popcorn, tortilla chips, corn chips, rice cakes sold as snacks,
  puffed/extruded snacks, snack mixes, snacking nuts, fruit-and-nut packs,
  wasabi peas, apéro or party snack mixes;
- sweet biscuits and sweet bakery snacks: biscuits, cookies, wafers,
  madeleines, mini cakes, brownies, muffins, croissants when packaged as sweet
  bakery snacks, panettone, pandoro, sweet filled pastries, sweet brioche-style
  snacks, and pasta frolla with sweet cream;
- snack bars and cereal bars: snack bars, cereal bars, granola bars, protein
  bars, energy bars, fruit bars, nut bars, and breakfast bars in bar format;
- fruit snacks: fruit rolls, fruit strips, dried-fruit snacking packs, and
  fruit-and-nut snack packs.

Sweet brioche, panettone, viennoiserie, and packaged sweet bakery products are
`snack` when the product format is a finished sweet snack or bakery snack.

Sandwich cookies and sandwich biscuits are `snack`; the sandwich wording refers
to biscuit format, not a meal sandwich.

Snack-format wording can override meal-like words.

Texture words are not snack-format signals by themselves. Do not classify a
product as `snack` only because the name contains weak attributes such as
`crisp`, `crispy`, `crunchy`, `creamy`, `baked`, `golden`, or similar texture
and preparation words. These words count as snack evidence only in a clear
snack-format phrase such as `crisps`, `chips`, `crackers`, `crispy snack`,
`baked snack crackers`, or `crunchy snack mix`. Meal-format nouns override
texture adjectives.

Examples:

```text
Pasta Chips -> snack
Noodle Sticks Masala -> snack
Bebeto Spaghetti Candy -> snack
Goldfish baked snack crackers, macaroni & cheese flavour -> snack
Vegetable Gyoza Snack Pot -> snack
Apero mix 24 pieces -> snack
Garlic & mozzarella filled in-fry gnocchi - crisp & creamy -> not_snack
Crispy chicken meal -> not_snack
Crispy coated snack crackers -> snack
Potato crisps -> snack
```

## Classify As Not Snack

Classify as `not_snack` when the product is primarily a meal, prepared dish,
cooking ingredient, deli/traiteur item, or bakery meal component.

Remove:

- pasta, macaroni cheese, lasagne, ravioli meals, gnocchi, tagliatelle meals,
  penne meals, noodles or instant noodles without snack-format wording, rice
  pasta meal kits, mini meal kits, prepared pasta salads;
- gyoza dumplings, shumai, banh bao, bao buns, dumpling mix, matzo ball mix,
  steamed buns, filled buns, unless the pack/name clearly signals snack format
  or snack occasion;
- fresh prepared bakery items, traiteur products, fresh savoury cakes,
  savoury cake loaves, sausage rolls, quiches, mini pies, sandwiches, wraps,
  filled buns, prepared appetizers without snack-pack positioning, prepared
  salads;
- bread, buns, rolls, brioche meal products, flour, baking mixes, dough,
  pizza bases, wraps, and tortillas when sold as meal components;
- ham, meat packs, surimi salads, cheese meal components, prepared salads,
  meal bowls, ready meals, lunch kits, dinner kits, and meal kits;
- cooking mixes, sauces, seasonings, dips, dressings, and spreads when they
  are ingredients or accompaniments rather than finished snack products;
- actual cheese or dairy components when the product is not clearly sold as a
  packaged snack format.

Meal-format wording can override snack tags. Small pack size does not
automatically make a product a snack.

Savoury filled brioche, traiteur brioche products, sandwich-style brioche,
apéro prepared foods, préfou, pain surprise, meat/cheese/vegetable fillings,
and brioche preparation mixes are `not_snack`.

Actual sandwiches, pain surprise, baguette sandwiches, wraps, and filled
bread-based meal products are `not_snack`, even when they are packaged in small
formats or tagged by Open Food Facts as snacks.

For US/Canada cleanup, sandwich cookies and cracker snack formats stay in
`snacks`; actual sandwiches, dinner kits, coleslaw, bread/buns,
tortillas/wraps as meal components, lunch kits, cooking mixes, sauces,
seasonings, prepared-meal items, and standalone cheese/dairy components are
removed from the snacks analytical base unless a clear packaged-snack format
overrides the meal or ingredient cue.

For UK/Ireland cleanup, chocolate, confectionery, biscuits, cookies, wafers,
shortbread, panettone, pandoro, Belgian buns, churros, profiteroles, choux
buns, croissants in sweet bakery-snack format, snack bars, cereal bars,
protein bars, crisps, chips, crackers, popcorn, tortilla chips, rice cakes,
pork scratchings/crackling, jerky-style snacks, and snack-format flavour cues
stay in `snacks`. Sausage rolls, pork pies, scotch eggs, coleslaw, garlic
bread, mini pizzas, sandwiches, wraps, meal kits, pakora, samosas, onigiri,
sauces, spreads, dips, cooking mixes, prepared meats, and prepared meal
components are removed unless a clear packaged-snack format overrides the meal
cue.

Soup/salad wording requires product-format review:

- soup crackers and oyster crackers are `snack`;
- soup-flavoured chips, crisps, popcorn, and extruded snacks are `snack`;
- Saladitas, saltines, crackers, and similar cracker formats are `snack`;
- salad toppers are `not_snack` when clearly sold as topping-use products
  rather than snacking packs;
- chicken salad, tuna salad, couscous salad kits, prepared salad kits, soup
  mixes, instant soup, and matzo ball soup mix are `not_snack`;
- prepared restaurant trays, bread-bite trays, and meat-and-cheese trays are
  `not_snack`.

Examples:

```text
Macaroni 'tomato' -> not_snack
Mini Meal Kit, Rice Pasta & Cheddar -> not_snack
Macaroni Cheese With Bacon -> not_snack
Gyoza Dumplings Chicken & Spring Onion -> not_snack
Shumai -> not_snack
Bun bao champignon teriyaki -> not_snack
M&S sausage rolls -> not_snack
Cake brioche jambon olive, recette traiteur -> not_snack
Dumpling or matzo ball mix -> not_snack
Pain surprise brioche -> not_snack
Baguette sandwich -> not_snack
Preparation pour brioche -> not_snack
Pain brioche chevre -> not_snack
Le prefou brioche -> not_snack
```

## Manual Review

Use `???` when both are true:

1. The name contains both meal-like and snack-like cues.
2. There is not enough evidence from product name, brand, or metadata to
   decide.

Send to image review when names include combinations such as pasta + snack,
ravioli + snacking, gyoza + snack, noodle + sticks, apéro + meal-like
components, or bao/bun + unclear occasion.

If image review confirms snack format, update to `snack`.

If image review is impossible because no pack image is available and metadata
does not support a clear classification, remove the product from the snacks
analytical base. In the US/Canada Snacks residue cleanup on 20 August 2026,
this rule affected 1 product.

## Cereal Interaction

For this project:

```text
Cereal = breakfast cereal only.
Cereal bars = snacks.
```

Include in cereal only dry breakfast-cereal formats such as corn flakes, bran
flakes, muesli, granola, puffed cereals, choco balls/loops/pillows, breakfast
cereal flakes, and porridge/oats when they are in breakfast-cereal format.

Classify as snacks:

```text
cereal bars
granola bars
protein bars
fruit and cereal bars
breakfast bars in bar format
```

Exclude from cereal:

```text
flour
bread
buns
pasta
rice
grains
gnocchi
pizza bases
bakery staples
meal components
```

## Dairy Interaction

For MVP, all milk-related products stay in `dairies`: milk, hard cheese,
yogurt, drinkable yogurt, flan, mousse, dairy desserts, and similar products.

A future version may add a `snacking_occasion_flag` or allow double assignment
so small yogurts and dairy desserts can appear in both `dairies` and a
holistic snacking view.
