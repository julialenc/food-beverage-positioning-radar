"""
MVP beverage view segmentation.

This is a pragmatic Market Overview split, not a full beverage taxonomy.
It separates ready-to-drink beverages from beverage preparations and alcohol
so charts do not mix fundamentally different product forms.
"""

from __future__ import annotations

import re


READY_TO_DRINK_SEGMENT = "ready_to_drink_beverages"
PREPARATION_ALCOHOL_SEGMENT = "beverage_preparations_and_alcohol"
NOT_BEVERAGE_SEGMENT = "not_beverage"
UNKNOWN_BEVERAGE_SEGMENT = "unknown_beverage_segment"

SEGMENT_LABELS = {
    READY_TO_DRINK_SEGMENT: "Ready-to-drink beverages",
    PREPARATION_ALCOHOL_SEGMENT: "Beverage preparations and alcohol",
    UNKNOWN_BEVERAGE_SEGMENT: "Unknown beverage segment",
}

PROTECTED_READY_TO_DRINK_PATTERN = re.compile(
    r"\b("
    r"iced tea|ice tea|nestea|arizona|pure leaf|lipton ice tea|"
    r"green tea zero|sweet tea|unsweet tea|zero icedtea|icetea|kombucha|"
    r"root beer|ginger ale|juice from concentrate|juice blend from concentrate|"
    r"juice cocktail from concentrate|orange juice from concentrate|"
    r"apple juice from concentrate|tomato cocktail from concentrate|"
    r"orange juice|apple juice|homestyle orange juice|100% orange juice|"
    r"100% apple juice|coconut water"
    r")\b",
    re.IGNORECASE,
)

PROTECTED_READY_TO_DRINK_BLOCK_PATTERN = re.compile(
    r"\b("
    r"frozen concentrate|juice concentrate|drink mix contains|"
    r"puro orange juice concentrate|tea bag|tea bags|teabag|teabags|"
    r"syrup|coconut milk|lait de coco"
    r")\b",
    re.IGNORECASE,
)

PREPARATION_ALCOHOL_PATTERN = re.compile(
    r"\b("
    r"syrup|mysyrup|sirop|grenadine|cordial|squash|concentrate|concentré|"
    r"concentrado|drink mix|margarita mix|bloody mary mix|instant drink|"
    r"powder|poudre|polvo|powdered|"
    r"drink powder|powdered drink|instantané|hot cocoa mix|hot chocolate|"
    r"cocoa mix|cocoa powder|chocolate powder|hot chocolate powder|"
    r"drinking chocolate|rich milk chocolate cocoa|cocoa|nesquik|"
    r"ovomaltine|ricoré|chicorée|nescafé|"
    r"instant coffee|freeze dried|soluble|cappuccino soluble|cappuccino|"
    r"chai latte|latte macchiato|ricoré|nescafé|café gold|kaffee|"
    r"coffee - instant|coffee - ground|caffè|crema e gusto|illy classico|"
    r"decaffeinato|löslich|oploskoffie|"
    r"coffee capsule|coffee capsules|coffee pod|coffee pods|capsule|"
    r"capsules|pod|pods|dosette|dosettes|senseo|tassimo|nespresso|"
    r"dolce gusto|ground coffee|roast coffee|espresso|lungo|ristretto|"
    r"tea bag|teabag|teabags|tea bags|sachet|sachets|pyramide|loose tea|"
    r"herbal tea|vrac|thé|té|tee|tea|thés|teas|earl grey|thé vert|"
    r"thé de ceylan|fruit tea|green tea|jasmine tea|infusion|infusions|"
    r"infuso|tisane|tisanes|rooibos|yerba mate|früchtetee|kräuter|"
    r"kamille|camomile|chamomile|peppermint|"
    r"wine|vin|vino|vinho|prosecco|champagne|brut|chardonnay|malbec|"
    r"merlot|rioja|cabernet|syrah|porto|zinfandel|pinot grigio|"
    r"shiraz|bordeaux|chianti|claret|hock|barolo|viognier|chenin blanc|"
    r"beaujolais|sauvignon blanc|pecorino terre di chieti|pinot noir|"
    r"muscadet|dry red|dry white|montepulciano|neropasso|sangria|"
    r"côtes|côtés|cotes|cuvée|"
    r"beer|bi[eè]re|biere|bier|cerveja|lager|cider|cidre|ipa|ale|"
    r"tripel|weissbier|stout|porter|"
    r"sake|spirits|spiritueux|vodka|водка|whisky|whiskey|rum|rhum|"
    r"gin|tequila|cognac|brandy|liqueur|amaretto|campari|cinzano|"
    r"baileys|kirsch|limoncino|angostura|bitters|aperitif|apéritif|"
    r"spritz|cocktail|martini|margarita|pina colada|pina coladajus|"
    r"mojito mocktail|mocktail|"
    r"irish cream|liqueurs|tennessee honey|crodino|fruissette|fruittesse|"
    r"cooking wine|leffe|carlsberg|"
    r"desperados|super bock|sagres|karmeliet|london pride|spitfire|"
    r"la mordue|free damm|peroni|becks blue|birra|cerveza|paulaner|"
    r"hefeweissbier|singha|longdrink|alkoholiton|"
    r"bacardi|fernet|ron gran reserva|cherry sourz|whie alcohol free|"
    r"captain morgan|grand marnier|get 27|"
    r"0\.0%|0,0|0\.0% beer|0% beer|alcohol free beer|desperados virgin|"
    r"carlsberg 0|"
    r"coconut milk|coconut cream|lait de coco|crème de coco"
    r"|meal replacement shake|meal shake|nutrition shake|nutritional shake|"
    r"protein shake|protein shakes|protein beverage|keto meal shake|advanced nutrition|"
    r"formula 1 healthy meal|fórmula 1|liftoff|herbalife"
    r")\b",
    re.IGNORECASE,
)

READY_TO_DRINK_PATTERN = re.compile(
    r"\b("
    r"water|eau|agua|acqua|mineral water|spring water|sparkling water|"
    r"flavoured water|flavored water|volvic|evian|nestlé pure life|"
    r"pure life|life wtr|aquafina|highland spring|sidi ali|ramlösa|"
    r"loka|novelle|imsdal|"
    r"juice|jus|zumo|sok|saft|orangensaft|apfelsaft|traubensaft|"
    r"tomatensaft|sinaasappelsap|appelsap|jugo|jugo de naranja|"
    r"zumo de naranja|jus d'orange|orange juice|apple juice|"
    r"pear juice|pineapple juice|mango juice|tropical juice|tomato cocktail|"
    r"pressed apple|cranberry|cranberry classic|tropicana|simply orange|"
    r"martinelli|pran frooto|frooto|"
    r"orange without pulp|nectar|nektar|mangonektar|smoothie|lemonade|"
    r"limonade|citronnade|limeade|seltzer|soda|sodas|sparkling mandarin|"
    r"sparkling orange|pink grapefruit|"
    r"cola|soft drink|fanta|sprite|dr pepper|pepsi|coca cola|coke|"
    r"mountain dew|mtn dew|gini|orangina|schweppes|capri-sun|capri sun|"
    r"appletiser|sunnyd|hawaiian punch|fruit punch|kombucha|"
    r"sanpellegrino|sanpellecrino|sparkling ice|perrier|pago|tropico|"
    r"mogu mogu|faxe kondi|vichy|multivitamin|multivitaminsaft|"
    r"aloe vera|body armor|energy drink|monster|red bull|sports drink|"
    r"electrolyte drink|aquarius|gatorade|"
    r"plant drink|plant-based drink|"
    r"oat drink|almond drink|soy drink|soya drink|sojadrink|mandeldrink|"
    r"oat milk|almond milk|almond-milk|soy milk|soya milk|almondmilk|"
    r"lait d'amande|seed milk|hemp milk|cashewmilk|cashew dream|"
    r"almond breeze|coconut beverage|"
    r"coconut water|fresh drinking coconut|coconutmilk beverage|agua de coco|milk drink|"
    r"iced coffee|cold brew|apple beverage|sparkling lemon beverage|"
    r"sparkling lemon and lime|boisson|boissons|bebida|bevanda|"
    r"drink|drinks"
    r")\b",
    re.IGNORECASE,
)


def beverage_view_segment(category: str, product_name: str = "", off_categories: str = "") -> str:
    """Classify a product into the MVP beverage view segment."""
    if str(category or "").strip().lower() != "beverages":
        return NOT_BEVERAGE_SEGMENT

    text = f"{product_name or ''} {off_categories or ''}".lower()
    if (
        PROTECTED_READY_TO_DRINK_PATTERN.search(text)
        and not PROTECTED_READY_TO_DRINK_BLOCK_PATTERN.search(text)
    ):
        return READY_TO_DRINK_SEGMENT
    if PREPARATION_ALCOHOL_PATTERN.search(text):
        return PREPARATION_ALCOHOL_SEGMENT
    if READY_TO_DRINK_PATTERN.search(text):
        return READY_TO_DRINK_SEGMENT
    return UNKNOWN_BEVERAGE_SEGMENT
