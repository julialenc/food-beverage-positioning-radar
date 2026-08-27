"""
Validate shared category assignment rules against documented edge cases.

This script is intentionally read-only. It does not download Open Food Facts
data, update the database, or write outputs. It checks whether
category_rules.assign_category() matches the frozen MVP category-scope rules
documented in:

- docs/CATEGORY_CLEANUP.md

Run before a bulk bootstrap or incremental ingest rule change:

    python pipeline/validate_category_rules.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from category_rules import assign_category  # noqa: E402


@dataclass(frozen=True)
class Case:
    area: str
    rule: str
    product_name: str
    categories_tags: str
    expected: str | None
    note: str


def tags(*values: str) -> str:
    """Build an OFF-like comma-separated categories_tags string."""
    return ",".join(values)


CASES: list[Case] = [
    # Snacks: clear positives.
    Case("snacks", "confectionery", "Milk Chocolate Bar", tags("en:snacks", "en:sweet-snacks", "en:chocolates"), "snacks", "Chocolate is snack."),
    Case("snacks", "confectionery", "Bebeto Spaghetti Candy", tags("en:snacks", "en:sweet-snacks", "en:candies", "en:pastas"), "snacks", "Candy overrides spaghetti wording."),
    Case("snacks", "confectionery", "Gummy Bears", tags("en:snacks", "en:sweet-snacks", "en:gummies"), "snacks", "Gummy sweets are snack."),
    Case("snacks", "confectionery", "Licorice Twists", tags("en:snacks", "en:sweet-snacks", "en:licorice"), "snacks", "Licorice is snack."),
    Case("snacks", "confectionery", "Caramel Toffees", tags("en:snacks", "en:sweet-snacks", "en:toffees"), "snacks", "Toffees are snack."),
    Case("snacks", "ice cream", "Mini Ice Cream Cones", tags("en:snacks", "en:ice-creams", "en:frozen-desserts"), "snacks", "Ice cream snack dessert."),
    Case("snacks", "ice cream", "Chocolate Sorbet Bar", tags("en:snacks", "en:sorbets", "en:frozen-desserts"), "snacks", "Frozen dessert snack."),
    Case("snacks", "savoury snacks", "Potato Crisps", tags("en:snacks", "en:salty-snacks", "en:crisps"), "snacks", "Crisps are snack."),
    Case("snacks", "savoury snacks", "Tortilla Chips", tags("en:snacks", "en:salty-snacks", "en:tortilla-chips"), "snacks", "Tortilla chips are protected snacks."),
    Case("snacks", "savoury snacks", "Corn Chips", tags("en:snacks", "en:salty-snacks", "en:corn-chips"), "snacks", "Corn chips are snack."),
    Case("snacks", "savoury snacks", "Pasta Chips", tags("en:snacks", "en:salty-snacks", "en:chips-and-crackers", "en:pastas"), "snacks", "Chips format overrides pasta wording."),
    Case("snacks", "savoury snacks", "Goldfish Macaroni & Cheese Baked Snack Crackers", tags("en:snacks", "en:crackers", "en:pastas"), "snacks", "Snack crackers override macaroni flavour wording."),
    Case("snacks", "savoury snacks", "Crispy coated snack crackers", tags("en:snacks", "en:crackers"), "snacks", "Snack crackers are snack despite texture words."),
    Case("snacks", "savoury snacks", "Soup & Oyster Crackers", tags("en:snacks", "en:crackers"), "snacks", "Soup/oyster crackers are snack."),
    Case("snacks", "savoury snacks", "Soup Flavoured Popcorn", tags("en:snacks", "en:popcorn"), "snacks", "Soup-flavoured popcorn is snack."),
    Case("snacks", "savoury snacks", "Saladitas Crackers", tags("en:snacks", "en:crackers"), "snacks", "Saladitas/crackers are snack."),
    Case("snacks", "savoury snacks", "Rice Cakes", tags("en:snacks", "en:rice-cakes"), "snacks", "Rice cakes sold as snacks are snack."),
    Case("snacks", "savoury snacks", "Pork Scratchings", tags("en:snacks", "en:pork-scratchings"), "snacks", "Pork scratchings are snack."),
    Case("snacks", "savoury snacks", "Beef Jerky", tags("en:snacks", "en:jerky"), "snacks", "Jerky-style snacks are snack."),
    Case("snacks", "snack wording", "Vegetable Gyoza Snack Pot", tags("en:snacks", "en:gyoza"), "snacks", "Snack pot wording overrides gyoza wording."),
    Case("snacks", "snack wording", "Apero Mix 24 Pieces", tags("en:snacks", "en:salty-snacks"), "snacks", "Apero/party snack format."),
    Case("snacks", "sweet bakery", "Packaged Croissant", tags("en:snacks", "en:sweet-snacks", "en:viennoiseries"), "snacks", "Sweet packaged bakery snack."),
    Case("snacks", "sweet bakery", "Panettone", tags("en:snacks", "en:sweet-snacks", "en:panettone"), "snacks", "Panettone kept as snack."),
    Case("snacks", "sweet bakery", "Pandoro", tags("en:snacks", "en:sweet-snacks", "en:pandoro"), "snacks", "Pandoro kept as snack."),
    Case("snacks", "sweet bakery", "Belgian Bun", tags("en:snacks", "en:sweet-snacks", "en:pastries"), "snacks", "Sweet bakery snack."),
    Case("snacks", "sweet bakery", "Churros", tags("en:snacks", "en:sweet-snacks", "en:pastries"), "snacks", "Sweet bakery snack."),
    Case("snacks", "sweet bakery", "Profiteroles", tags("en:snacks", "en:sweet-snacks", "en:pastries"), "snacks", "Sweet bakery snack."),
    Case("snacks", "biscuits", "Chocolate Sandwich Biscuits", tags("en:snacks", "en:biscuits"), "snacks", "Sandwich biscuit is not meal sandwich."),
    Case("snacks", "biscuits", "Cream Sandwich Cookies", tags("en:snacks", "en:cookies"), "snacks", "Sandwich cookie is snack."),
    Case("snacks", "bars", "Chocolate Cereal Bar", tags("en:snacks", "en:cereal-bars"), "snacks", "Cereal bars are snacks."),
    Case("snacks", "bars", "Protein Bar", tags("en:snacks", "en:protein-bars"), "snacks", "Protein bars are snacks."),
    Case("snacks", "bars", "Fruit And Nut Bar", tags("en:snacks", "en:fruit-bars", "en:nut-bars"), "snacks", "Fruit/nut bars are snacks."),

    # Snacks: exclusions / not snack.
    Case("snacks", "pasta meals", "Macaroni Tomato 400 g", tags("en:snacks", "en:pastas", "en:prepared-meals"), None, "Pasta meal is not snack."),
    Case("snacks", "pasta meals", "Mini Meal Kit Rice Pasta & Cheddar", tags("en:snacks", "en:pastas", "en:meal-kits"), None, "Meal kit is not snack."),
    Case("snacks", "pasta meals", "Macaroni Cheese With Bacon", tags("en:snacks", "en:pastas", "en:prepared-meals"), None, "Macaroni cheese meal is not snack."),
    Case("snacks", "pasta meals", "Ravioli au boeuf et legumes", tags("en:snacks", "en:ravioli", "en:prepared-meals"), None, "Ravioli meal is not snack."),
    Case("snacks", "pasta meals", "Gnocchi", tags("en:snacks", "en:gnocchi"), None, "Gnocchi is not snack."),
    Case("snacks", "pasta meals", "GARLIC & MOZZARELLA FILLED IN-FRY GNOCCHI - CRISP & CREAMY", tags("en:snacks", "en:gnocchi"), None, "Texture adjectives crisp/creamy do not override gnocchi meal format."),
    Case("snacks", "noodles", "Instant Noodles", tags("en:snacks", "en:instant-noodles"), None, "Instant noodles without snack format are not snack."),
    Case("snacks", "dumplings", "Gyoza Dumplings Chicken & Spring Onion", tags("en:snacks", "en:gyoza", "en:dumplings"), None, "Gyoza dumplings without snack cue are not snack."),
    Case("snacks", "dumplings", "Shumai", tags("en:snacks", "en:dumplings"), None, "Shumai/dim sum without snack cue is not snack."),
    Case("snacks", "dumplings", "Bun Bao Champignon Teriyaki", tags("en:snacks", "en:bao-buns"), None, "Filled bao/bun meal format is not snack."),
    Case("snacks", "bakery meals", "Sausage Rolls", tags("en:snacks", "en:sausage-rolls"), None, "Sausage rolls excluded in UK/Ireland cleanup."),
    Case("snacks", "bakery meals", "Pork Pie", tags("en:snacks", "en:pork-pies"), None, "Pork pie is meal/deli product."),
    Case("snacks", "bakery meals", "Scotch Egg", tags("en:snacks", "en:scotch-eggs"), None, "Scotch egg is meal/deli product."),
    Case("snacks", "bakery meals", "Pain Surprise Brioche", tags("en:snacks", "en:breads"), None, "Pain surprise is not snack."),
    Case("snacks", "sandwich meals", "Baguette Sandwich", tags("en:snacks", "en:sandwiches"), None, "Actual sandwich is not snack."),
    Case("snacks", "sandwich meals", "Chicken Wrap", tags("en:snacks", "en:wraps"), None, "Wrap meal component is not snack."),
    Case("snacks", "prepared meals", "Chicken Salad Kit", tags("en:snacks", "en:salads"), None, "Prepared salad kit is not snack."),
    Case("snacks", "prepared meals", "Crispy chicken meal", tags("en:snacks", "en:prepared-meals"), None, "Crispy is a texture adjective, not a snack format."),
    Case("snacks", "prepared meals", "Coleslaw", tags("en:snacks", "en:salads"), None, "Coleslaw is not snack."),
    Case("snacks", "prepared meals", "Homestyle coleslaw salad with carrots & onions in a sweet, tangy dressing", tags("en:snacks", "en:sweet-snacks", "en:prepared-salads", "en:biscuits", "en:salads"), None, "Real bootstrap residue: coleslaw remains not snack even with sweet/biscuits tags."),
    Case("snacks", "prepared meals", "Sweet Chopped Coleslaw", tags("en:snacks", "en:salty-snacks", "en:appetizers", "en:coleslaw"), None, "Real bootstrap residue: coleslaw remains not snack."),
    Case("snacks", "prepared meals", "Lunch Kit", tags("en:snacks", "en:meal-kits"), None, "Lunch kit is not snack."),
    Case("snacks", "prepared meals", "Peeled apple slices, cheddar cheese crackers, yogurt raisins, lunch kitz", tags("en:snacks"), None, "Real bootstrap residue: lunch kit is not snack even with snack components."),
    Case("snacks", "prepared meals", "Sliced uncured smoked ham crackers colby cheese chocolate-flavored bear cookies lunch kit", tags("en:snacks"), None, "Real bootstrap residue: lunch kit is not snack even with crackers/cookies."),
    Case("snacks", "prepared meals", "Hummus & crackers lunch kit", tags("en:snacks"), None, "Real bootstrap residue: lunch kit is not snack."),
    Case("snacks", "prepared meals", "Dinner Kit", tags("en:snacks", "en:meal-kits"), None, "Dinner kit is not snack."),
    Case("snacks", "prepared meals", "Taco dinner kit", tags("en:snacks", "en:sweet-snacks", "en:biscuits"), None, "Real bootstrap residue: dinner kit is not snack even with biscuits tags."),
    Case("snacks", "prepared meals", "Old El Paso Stand 'N Stuff Taco Dinner Kit 3 Pack", tags("en:snacks", "en:sweet-snacks", "en:biscuits"), None, "Real bootstrap residue: dinner kit is not snack."),
    Case("snacks", "prepared meals", "Onigiri", tags("en:snacks", "en:prepared-meals"), None, "Onigiri is prepared food."),
    Case("snacks", "prepared meals", "Pakora", tags("en:snacks", "en:prepared-meals"), None, "Pakora is prepared food unless snack format is explicit."),
    Case("snacks", "ingredients", "Dumpling Mix", tags("en:snacks", "en:cooking-mixes"), None, "Cooking mix is not snack."),
    Case("snacks", "ingredients", "Matzo Ball Soup Mix", tags("en:snacks", "en:soup-mixes"), None, "Soup mix is not snack."),
    Case("snacks", "ingredients", "Garlic Bread", tags("en:snacks", "en:breads"), None, "Garlic bread is not snack in UK/Ireland cleanup."),
    Case("snacks", "ingredients", "Pizza Base", tags("en:snacks", "en:pizzas"), None, "Pizza base/meal component is not snack."),
    Case("snacks", "ingredients", "Tomato Dip", tags("en:snacks", "en:dips"), None, "Dip/accompaniment is not finished snack product."),
    Case("snacks", "ingredients", "Salad Topper", tags("en:snacks", "en:toppings"), None, "Topping-use product is not snack."),

    # Cereals: clear positives.
    Case("cereals", "breakfast cereal", "Corn Flakes", tags("en:cereals-and-their-products", "en:breakfast-cereals"), "cereals", "Corn flakes are cereal."),
    Case("cereals", "breakfast cereal", "Bran Flakes", tags("en:cereals-and-their-products", "en:breakfast-cereals"), "cereals", "Bran flakes are cereal."),
    Case("cereals", "breakfast cereal", "Wheat Flakes", tags("en:cereals-and-their-products", "en:breakfast-cereals"), "cereals", "Wheat flakes are cereal."),
    Case("cereals", "breakfast cereal", "Choco Balls", tags("en:cereals-and-their-products", "en:breakfast-cereals"), "cereals", "Choco balls are cereal."),
    Case("cereals", "breakfast cereal", "Cereal Loops", tags("en:cereals-and-their-products", "en:breakfast-cereals"), "cereals", "Loops/hoops in cereal format are cereal."),
    Case("cereals", "breakfast cereal", "Chocolate Pillows", tags("en:cereals-and-their-products", "en:breakfast-cereals"), "cereals", "Pillows in cereal format are cereal."),
    Case("cereals", "breakfast cereal", "Cereal Clusters", tags("en:cereals-and-their-products", "en:breakfast-cereals"), "cereals", "Clusters are cereal."),
    Case("cereals", "breakfast cereal", "Chocolate Cereal Chips", tags("en:cereals-and-their-products", "en:breakfast-cereals"), "cereals", "Cereal chips shape is cereal."),
    Case("cereals", "breakfast cereal", "Cinnamon Chips", tags("en:cereals-and-their-products", "en:breakfast-cereals"), "cereals", "Harvest Morn-style cinnamon chips are cereal."),
    Case("cereals", "muesli", "Toasted Muesli", tags("en:cereals-and-their-products", "en:mueslis"), "cereals", "Muesli is cereal."),
    Case("cereals", "granola", "Loose Granola", tags("en:cereals-and-their-products", "en:granolas"), "cereals", "Loose granola is cereal."),
    Case("cereals", "hot cereal", "Porridge Oats", tags("en:cereals-and-their-products", "en:oatmeal"), "cereals", "Porridge/oats are cereal."),
    Case("cereals", "hot cereal", "Oats Overnight Performance Oatmeal", tags("en:cereals-and-their-products", "en:oatmeal"), "cereals", "Oatmeal/hot cereal is cereal."),
    Case("cereals", "wheat biscuits", "Weetabix Original", tags("en:cereals-and-their-products", "en:breakfast-cereals"), "cereals", "Weetabix-style wheat biscuits are cereal."),
    Case("cereals", "branded cereal", "Coco Pops", tags("en:cereals-and-their-products", "en:breakfast-cereals"), "cereals", "Coco Pops-style product is cereal."),
    Case("cereals", "branded cereal", "Rice Krispies", tags("en:cereals-and-their-products", "en:breakfast-cereals"), "cereals", "Rice Krispies-style product is cereal."),
    Case("cereals", "branded cereal", "Frosties", tags("en:cereals-and-their-products", "en:breakfast-cereals"), "cereals", "Frosties-style product is cereal."),
    Case("cereals", "ingredient noise", "Kashi Organic Cereal Sweet Potato Sunshine", tags("en:cereals-and-their-products", "en:breakfast-cereals", "en:potatoes"), "cereals", "Breakfast-cereal format overrides sweet potato ingredient/flavour."),
    Case("cereals", "brand noise", "Barbara's Puffins Cereal", tags("en:cereals-and-their-products", "en:breakfast-cereals"), "cereals", "Brand-name bar noise should not route to snacks."),
    Case("cereals", "brand noise", "Picky Bars Performance Oatmeal", tags("en:cereals-and-their-products", "en:oatmeal"), "cereals", "Brand-name bar noise should not route oatmeal to snacks."),
    Case("cereals", "brand noise", "Larabar Renola Grain Free Granola", tags("en:cereals-and-their-products", "en:granolas"), "cereals", "Loose granola remains cereal despite brand name."),

    # Cereals: route to snacks.
    Case("cereals", "bars to snacks", "Chocolate Cereal Bar", tags("en:cereals-and-their-products", "en:cereal-bars"), "snacks", "Cereal bars route_to_snacks."),
    Case("cereals", "bars to snacks", "Granola Snack Bar", tags("en:cereals-and-their-products", "en:snack-bars"), "snacks", "Snack bars route_to_snacks."),
    Case("cereals", "bars to snacks", "Protein Bar", tags("en:cereals-and-their-products", "en:protein-bars"), "snacks", "Protein bars route_to_snacks."),
    Case("cereals", "bars to snacks", "Larabar Apple Pie Fruit And Nut Bar", tags("en:cereals-and-their-products", "en:fruit-bars", "en:nut-bars"), "snacks", "Larabar core bar route_to_snacks."),
    Case("cereals", "bars to snacks", "Muesli Breakfast Bounties", tags("en:cereals-and-their-products", "en:muesli-bars"), "snacks", "Muesli breakfast-bounty snack format routes to snacks."),
    Case("cereals", "rice cakes", "Multigrain Rice Cakes", tags("en:cereals-and-their-products", "en:rice-cakes"), "snacks", "Rice cakes route_to_snacks."),
    Case("cereals", "crackers", "Wholegrain Crackers", tags("en:cereals-and-their-products", "en:crackers"), "snacks", "Crackers route_to_snacks."),
    Case("cereals", "crisps", "Walkers French Fries", tags("en:cereals-and-their-products", "en:snacks", "en:crisps"), "snacks", "UK bagged crisps-style French Fries route_to_snacks."),
    Case("cereals", "crisps", "Potato Skins", tags("en:cereals-and-their-products", "en:snacks", "en:chips-and-crackers"), "snacks", "Potato snack pack routes to snacks."),
    Case("cereals", "energy foods", "CLIF Loose Granola Snack Pack", tags("en:cereals-and-their-products", "en:granolas"), "snacks", "CLIF products route_to_snacks by project rule."),

    # Cereals: exclusions / not cereal.
    Case("cereals", "pasta", "Barilla Spaghetti", tags("en:cereals-and-their-products", "en:pastas"), None, "Pasta is not cereal."),
    Case("cereals", "pasta", "Fusilli Pasta, Whole Wheat", tags("en:cereals-and-their-products", "en:breakfast-cereals"), None, "Real bootstrap residue: pasta name overrides erroneous breakfast-cereal ancestry."),
    Case("cereals", "pasta", "Gnocchi", tags("en:cereals-and-their-products", "en:gnocchi"), None, "Gnocchi is not cereal."),
    Case("cereals", "pasta", "GNOCCHI aux flocons de pomme de terre", tags("en:cereals-and-their-products", "en:breakfast-cereals", "en:gnocchi"), None, "Real bootstrap residue: gnocchi/flocons is not breakfast cereal."),
    Case("cereals", "pasta", "GARLIC & MOZZARELLA FILLED IN-FRY GNOCCHI - CRISP & CREAMY", tags("en:cereals-and-their-products", "en:pastas", "en:cereal-pastas", "en:gnocchi"), None, "Real bootstrap residue: singular crisp is a texture adjective, not crisps snack format."),
    Case("cereals", "pasta", "Tortellini Ricotta Spinach", tags("en:cereals-and-their-products", "en:tortellini"), None, "Stuffed pasta is not cereal."),
    Case("cereals", "noodles", "Instant Noodles", tags("en:cereals-and-their-products", "en:instant-noodles"), None, "Noodles are not cereal."),
    Case("cereals", "bread", "White Bread", tags("en:cereals-and-their-products", "en:breads"), None, "Bread is not cereal."),
    Case("cereals", "bread", "Hot Dog Buns", tags("en:cereals-and-their-products", "en:breads"), None, "Buns are not cereal."),
    Case("cereals", "bread", "Crisp Toasts", tags("en:cereals-and-their-products", "en:breads"), None, "Crisp toasts/dry bread replacement are not cereal."),
    Case("cereals", "bread", "Toastie Soft Thick White", tags("en:cereals-and-their-products", "en:breads"), None, "Toast bread/dry bread replacement is not cereal."),
    Case("cereals", "toastie", "Five Cheese Toastie", tags("en:cereals-and-their-products", "en:sandwiches"), None, "Sandwich toastie is not cereal."),
    Case("cereals", "oil", "Toasted Sesame Oil", tags("en:cereals-and-their-products", "en:oils"), None, "Sesame oil is not cereal."),
    Case("cereals", "potatoes", "Sweet Potatoes", tags("en:cereals-and-their-products", "en:potatoes"), None, "Potatoes are not cereal."),
    Case("cereals", "potatoes", "Frozen Crinkle Cut Chips", tags("en:cereals-and-their-products", "en:frozen-chips", "en:potatoes"), None, "Frozen chips/fries are not cereal."),
    Case("cereals", "potatoes", "Hash Browns", tags("en:cereals-and-their-products", "en:hash-browns", "en:potatoes"), None, "Hash browns are not cereal."),
    Case("cereals", "potatoes", "Mashed Potatoes", tags("en:cereals-and-their-products", "en:mashed-potatoes"), None, "Mashed potatoes are not cereal."),
    Case("cereals", "rice staples", "Basmati Rice", tags("en:cereals-and-their-products", "en:rices"), None, "Rice staple is not cereal."),
    Case("cereals", "grains", "Couscous", tags("en:cereals-and-their-products", "en:couscous"), None, "Couscous is not cereal."),
    Case("cereals", "grains", "Dinkel Couscous", tags("en:cereals-and-their-products", "en:breakfast-cereals"), None, "Real bootstrap residue: couscous name overrides erroneous breakfast-cereal ancestry."),
    Case("cereals", "grains", "Polenta", tags("en:cereals-and-their-products", "en:polenta"), None, "Polenta is not cereal."),
    Case("cereals", "flour", "Plain Flour", tags("en:cereals-and-their-products", "en:flours"), None, "Flour is not cereal."),
    Case("cereals", "semolina", "Semolina", tags("en:cereals-and-their-products", "en:cereal-semolinas"), None, "Semolina staple is not cereal."),
    Case("cereals", "mixes", "Pancake Mix", tags("en:cereals-and-their-products", "en:pancake-mixes"), None, "Pancake mix is not cereal."),
    Case("cereals", "mixes", "Waffle Mix", tags("en:cereals-and-their-products", "en:waffle-mixes"), None, "Waffle mix is not cereal."),
    Case("cereals", "mixes", "Cake Mix", tags("en:cereals-and-their-products", "en:cake-mixes"), None, "Cake mix is not cereal."),
    Case("cereals", "prepared products", "Maple Pancakes", tags("en:cereals-and-their-products", "en:pancakes"), None, "Actual pancake product is not cereal."),
    Case("cereals", "prepared products", "Wheat Waffles", tags("en:cereals-and-their-products", "en:waffles"), None, "Actual waffle product is not cereal."),
    Case("cereals", "prepared products", "Pizza Base", tags("en:cereals-and-their-products", "en:pizzas"), None, "Pizza base is not cereal."),
    Case("cereals", "prepared products", "Chicken Salad Bowl", tags("en:cereals-and-their-products", "en:salads"), None, "Prepared meal/salad is not cereal."),
    Case("cereals", "sauces", "Tahini", tags("en:cereals-and-their-products", "en:tahini"), None, "Tahini is not cereal."),
    Case("cereals", "sauces", "Tomato Sauce", tags("en:cereals-and-their-products", "en:sauces"), None, "Sauce is not cereal."),
    Case("cereals", "meat/staple noise", "Pork Panko", tags("en:cereals-and-their-products", "en:breadcrumbs"), None, "Pork panko is not cereal."),
    Case("cereals", "meal/staple noise", "Breakfast Hash", tags("en:cereals-and-their-products", "en:prepared-meals"), None, "Breakfast hash is not cereal."),

    # MVP category priority.
    Case("priority", "dairy first", "Strawberry Yogurt Snack Pot", tags("en:dairies", "en:snacks"), "dairies", "Milk-related products stay dairies for MVP."),
    Case("priority", "beverage", "Oat Drink", tags("en:beverages", "en:plant-based-beverages"), "beverages", "Beverages still route to beverages."),
]


def run() -> int:
    failures: list[tuple[Case, str | None]] = []
    by_area: dict[str, list[bool]] = {}

    for case in CASES:
        actual = assign_category(case.categories_tags, case.product_name)
        passed = actual == case.expected
        by_area.setdefault(case.area, []).append(passed)
        status = "PASS" if passed else "FAIL"
        print(
            f"{status} | {case.area:8} | {case.rule:22} | "
            f"{case.product_name:48} | expected={case.expected!r} actual={actual!r}"
        )
        if not passed:
            failures.append((case, actual))

    print("\nSummary")
    print("-------")
    total_passed = len(CASES) - len(failures)
    print(f"Total: {total_passed}/{len(CASES)} passed")
    for area, results in sorted(by_area.items()):
        print(f"{area}: {sum(results)}/{len(results)} passed")

    if failures:
        print("\nFailures")
        print("--------")
        for case, actual in failures:
            print(
                f"- {case.area} / {case.rule}: {case.product_name}\n"
                f"  expected={case.expected!r}, actual={actual!r}\n"
                f"  tags={case.categories_tags}\n"
                f"  note={case.note}"
            )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
