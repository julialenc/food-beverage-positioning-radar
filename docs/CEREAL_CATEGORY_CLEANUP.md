# Cereal Category Cleanup

For this project, `cereals` means breakfast cereal products.

`cereals` = breakfast cereal products intended to be eaten as cereal, usually
with milk or yogurt, or prepared as hot cereal.

This category is based on product format and commercial occasion, not simply on
whether the product contains grains, cereal ingredients, oats, rice, wheat, or
flour.

MVP cleanup status as of 21 August 2026: France Cereals, US/Canada Cereals,
and UK/Ireland Cereals are locked for Streamlit use.

## Decision Rule

Use these cleanup decisions:

- `cereal` = breakfast cereal, hot cereal, or loose cereal format;
- `route_to_snacks` = cereal bars, snack bars, chips, crisps, biscuits, rice
  cakes, crackers, bites, cookies, and sweet snack formats;
- `not_cereal` = bread, toast, biscottes, flour, rice, pasta, pizza, meal
  products, flatbreads, couscous, polenta, potatoes, pancake/waffle mixes,
  sauces, toppings, and other non-breakfast meal staples.

## Keep As Cereal

Keep products that are clearly breakfast-cereal formats:

- ready-to-eat breakfast cereals;
- corn flakes, bran flakes, wheat flakes, and other breakfast flakes;
- choco balls, loops, pillows, filled breakfast cereals, puffs, and clusters;
- cereal chips when the word "chips" describes breakfast-cereal shape or
  format, such as Schoko Chips, Zimt Chips, chocolate cereal chips, flakes,
  puffs, loops, pillows, or clusters;
- muesli;
- loose granola;
- toasted flakes, toasted oats, toasted muesli, and toasted loose granola;
- porridge, oats, oatmeal, and other hot cereals;
- wheat biscuits, shredded wheat, and Weetabix-style products;
- breakfast cereal variety packs and cereal assortments when they are breakfast
  cereal packs.

Ingredient/flavour wording can be present in valid cereal products. For
example, keep `Kashi Organic Cereal Sweet Potato Sunshine` and sweet potato
granola when the product is clearly sold as breakfast cereal or loose granola.
Also keep pancake or waffle flavour when the product is explicitly a
breakfast-cereal product, such as waffle-flavoured cereal, pancake-flavoured
oatmeal, or Oats Overnight/oatmeal products. Cookie Crisp, cookie-bites cereal,
and Cheerios cookie-flavour cereals are also `cereal`.

## Route To Snacks

Cereal bars, granola bars, breakfast bars, protein bars, snack bars, fruit bars,
nut bars, and energy bars belong in `snacks`, not `cereals`.

The word "chips" is not automatically a snack cue in cereals. Route savoury
chips/crisps to `snacks`, but keep breakfast cereal packs where "chips"
describes the cereal piece shape or product line.

For UK/Ireland review, distinguish bagged snack formats from meal-side potato
formats. Walkers French Fries and similar small bagged crisps-style products
route to `snacks`. Frozen chips, crinkle-cut chips, fries, wedges, hash
browns, mash, and other meal-side potato formats are `not_cereal`.

Bars, biscuits, cookies, bites, wafers, crackers, rice cakes, crisps, chips,
and sweet bakery snack formats should not remain in `cereals`. When they fit
the snack definition, route them to `snacks`; otherwise remove them from the
cereal analytical base.

Muesli breakfast-bounty or snack-bite formats route to `snacks`, even when
the product name includes muesli.

Potato wording can also appear in snack formats. Route potato skins and similar
potato snack packs to `snacks` when they are clearly snack products rather than
meal staples.

Trail mix and CLIF-style energy-food formats route to `snacks`, even when they
contain oats or cereal ingredients.

Rice cakes and breakfast-cookie formats route to `snacks`, not `cereals`.

Brand names containing `bar` do not automatically make a product a snack.
Classify by product format, not by brand-string noise. Barbara's cereals,
Picky Bars oatmeal or hot-cereal formats, Larabar Renola / grain-free loose
granola, and Larabar Peanut Butter Chocolate Chip in cereal format can remain
`cereal` when the pack is clearly a bowl/hot cereal or loose granola product.
Larabar core fruit/nut bars, fruit-and-nut bites, and fruit/nut/seed snacking
mixes route to `snacks`.

CLIF products route to `snacks` for this project, even when they contain oats
or granola, because the brand's product formats are portion-packed and
snack/sports-occasion positioned rather than breakfast-cereal positioned.

## Remove From Cereals

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

## Review Values

Use these review values in cereal cleanup files:

```text
keep_cereal
route_to_snacks
not_cereal
manual_review
```
