"""
validate_beverage_segments.py
-----------------------------
Lightweight checks for the MVP beverage_view_segment helper.

Usage:
    python pipeline/nutrition_outliers/validate_beverage_segments.py
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shared.beverage_segments import (
    NOT_BEVERAGE_SEGMENT,
    PREPARATION_ALCOHOL_SEGMENT,
    READY_TO_DRINK_SEGMENT,
    UNKNOWN_BEVERAGE_SEGMENT,
    beverage_view_segment,
)


def main() -> None:
    cases = [
        (
            "beverages",
            "Coca Cola Zero",
            "Boissons, Sodas, Sodas au cola",
            READY_TO_DRINK_SEGMENT,
        ),
        (
            "beverages",
            "Natural mineral water",
            "Beverages, Waters, Mineral waters",
            READY_TO_DRINK_SEGMENT,
        ),
        (
            "beverages",
            "Sirop de grenadine",
            "Boissons, Sirops aromatisés",
            PREPARATION_ALCOHOL_SEGMENT,
        ),
        (
            "beverages",
            "Thé Earl Grey",
            "Boissons chaudes, Thés, Infusions",
            PREPARATION_ALCOHOL_SEGMENT,
        ),
        (
            "beverages",
            "Vodka",
            "Alcoholic beverages, Spirits",
            PREPARATION_ALCOHOL_SEGMENT,
        ),
        (
            "snacks",
            "Cola sweets",
            "Snacks, Confectionery",
            NOT_BEVERAGE_SEGMENT,
        ),
        (
            "beverages",
            "Unclear beverage product",
            "",
            UNKNOWN_BEVERAGE_SEGMENT,
        ),
        ("beverages", "Volvic Nature", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Evian 500ml", "", READY_TO_DRINK_SEGMENT),
        (
            "beverages",
            "Tropicana orange without pulp",
            "Orange juice",
            READY_TO_DRINK_SEGMENT,
        ),
        ("beverages", "Sinaasappelsap", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Oat Milk", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Alpro Sojadrink", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Monster Energy Ultra", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Cinzano Bianco", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Captain Morgan Tiki", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "GET 27", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Amaretto", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Tripel Karmeliet", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Prosecco", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Ricoré", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Nesquik", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Ovomaltine", "", PREPARATION_ALCOHOL_SEGMENT),
        (
            "beverages",
            "Freeze Dried Instant Coffee",
            "",
            PREPARATION_ALCOHOL_SEGMENT,
        ),
        ("beverages", "Kamille Te Pyramide", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Arizona Green Tea", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Yorkshire Gold", "Tea bags", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Coconut Cream", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Nestlé Pure Life", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Cranberry classic", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Tropicana orange", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Orangensaft", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Jugo de Naranja", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Sok 100%", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Agua de coco", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Almondmilk", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Mountain Dew", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "SunnyD", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Hawaiian Punch", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Leffe", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Baileys", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Carlsberg 0%", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Desperados Virgin 0.0%", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Cabernet-Syrah", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Rioja", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Merlot", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Super Bock", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Sagres", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Kirsch", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Thé vert au Jasmin", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Fruit Tea Sampler Infusion", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Assam fine tea", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Jasmine Green Tea", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Yerba Mate", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Nescafé Classic", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Hot Cocoa Mix", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Swiss Miss Hot Cocoa Mix", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Coconut Beverage", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Coconut Water", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Lait de coco", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Coconut Milk", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Zero IcedTea", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Cherry seltzer, cherry", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Old-fashioned limeade, lime", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Apple beverage", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Rich Milk Chocolate Cocoa", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Sanpellecrino Orange", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Pago ace", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Sparkling Ice +Caffeine Citrus Twist", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "London Pride", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Drinking Chocolate", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Shiraz California", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Bordeaux Claret", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Chianti Classico", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Almond-milk, vanilla", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Limoncino Bottega", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Bloody mary mix, fiery pepper", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Cherry Lime Rita sparkling margarita", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Iced coffee", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Cold brew unsweetened black coffee", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Cashewmilk, unsweetened", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Almond Breeze Unsweetened Low Fat Milk Alternative", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "La Mordue Original", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Barolo 2014", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Viognier Valle Del Bío Bío", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Free Damm", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Soda, root beer", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Caffeine free soda, ginger ale", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Apple juice from concentrate", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Juice blend from concentrate, orange", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Homestyle orange juice", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "100% Apple Juice", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Orange Juice, Not From Concentrate", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "100% Orange Juice Frozen Concentrate", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Kroger drink mix contains coconut water concentrate", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Advanced Nutrition Meal Replacement Shake", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "STRAWBERRIES & CREAM MEAL REPLACEMENT SHAKE", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Caramel cappuccino coffee & protein beverage with real milk", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Keto meal shake", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "non-dairy protein shake", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Formula 1 Healthy Meal", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Liftoff", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Herbalife", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Peroni Nastro Azzurro 0.0%", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Becks blue", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Tennessee honey", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Sangria Republic", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Crodino", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Neropasso", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Montepulciano", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Original Longdrink", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Mojito mocktail alkoholiton", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Earl Grey", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Thé vert au Jasmin", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Thé de Ceylan", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Früchtetee", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Kräuter", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Chai Latte", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Café Gold löslich", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Kaffee milde bohne", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Caffè Decaffeinato", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Crema e Gusto Classico", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Illy Classico", "", PREPARATION_ALCOHOL_SEGMENT),
        ("beverages", "Simply Orange High Pulp", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Martinelli's Gold Medal", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Pran Frooto mango", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Fresh Drinking Coconut", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Highland Spring", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Sidi Ali", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Ramlösa Original", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Loka Naturell", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "Novelle Kivennäisvesi Citronelle", "", READY_TO_DRINK_SEGMENT),
        ("beverages", "IMSDAL vann", "", READY_TO_DRINK_SEGMENT),
    ]

    for category, product_name, off_categories, expected in cases:
        actual = beverage_view_segment(category, product_name, off_categories)
        assert actual == expected, (category, product_name, actual, expected)

    print("All beverage segment validation checks passed.")


if __name__ == "__main__":
    main()
