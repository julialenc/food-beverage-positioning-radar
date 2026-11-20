"""Shared text-only juice-family identity rules. No nutrition or claims inputs.

v1, corrected 19 November 2026: broad parent tags never determine a child type.
Classifications are proposed commercial interpretations, not verified pack facts.
"""
import re
import unicodedata

VERSION = "juice_identity_v1_20261119"
NAMED = {"juice", "nectar", "fruit drink", "smoothie"}


def norm(value):
    return re.sub(r"[-_]", " ", unicodedata.normalize("NFKD", str(value).lower()).encode("ascii", "ignore").decode())


def cues(value, tags=False):
    text = norm(value)
    if tags:
        text = ", ".join(t for t in text.split(",") if not re.search(
            r"without.*juice|sans.*jus|soft drinks?.*juice|boissons? gazeuses?.*jus|fruit soft drinks?", t))
    text = re.sub(r"juices? (?:and|et) nectars?|jus et nectars?|sucos e nectares|sumos e nectares", " ", text)
    if tags:
        text = re.sub(r"boissons? (?:a base de|aux) fruits|fruit based beverages", " ", text)
    result = set()
    drink = r"\b(?:fruit drinks?|juice drinks?|juice beverages?|juice cocktails?|boissons? (?:aux?|a base de) jus(?: de fruits)?)\b"
    if re.search(drink, text):
        result.add("fruit drink")
        text = re.sub(drink, " ", text)
    if not tags and re.search(r"\bboissons? aux fruits\b", text):
        result.add("fruit drink")
    for key, pattern in [("smoothie", r"\bsmoothies?\b"), ("nectar", r"\b(?:nectars?|nektars?)\b"),
                         ("juice", r"\b(?:juices?|jus|zumos?|sumos?|sucos?)\b")]:
        if re.search(pattern, text):
            result.add(key)
    return result


def decide(name, tags):
    """Return identity, confidence and reasons without using nutrition or claim evidence."""
    n, t = cues(name), cues(tags, True)
    union = n | t
    plain = norm(name)
    reason = "insufficient specific identity evidence"
    identity = "juice family unresolved"
    confidence = "LOW"
    use_caution = bool(re.search(r"\b(?:salads?|salades?|soups?|soupes?|sauces?|smoothie bowls?|eau de vie|culinary|cooking|syrup|sirop|cordial|powder|poudre|a diluer|concentrate for dilution)\b", plain))
    adjacent = bool(re.search(r"\b(?:iced tea|the glace|energy drinks?|sports? drinks?|coffee smoothie|almondmilk|almond milk|coconut water|eau de coco|fruit drink water|flavou?red water)\b", plain))
    if use_caution:
        reason = "non-comparable intended use or preparation wording"
    elif adjacent:
        reason = "overlapping commercial identity; preserve unresolved"
    elif len(n) > 1:
        reason = "multiple identities in product name"
    elif len(n) == 1 and len(t) == 1 and n != t:
        reason = "conflicting name and specific tags"
    elif len(union) == 1:
        identity = next(iter(union))
        confidence = "HIGH" if n and t else "MEDIUM"
        reason = "specific name and tags agree" if n and t else "specific name only" if n else "specific tags only"
    elif "juice" in t and len(t) == 2 and (not n or n <= t):
        child = next(iter(t - {"juice"}))
        if n == {"juice"}:
            reason = "juice name conflicts with more-specific child tags"
        else:
            identity = child
            confidence = "HIGH" if n == {child} else "MEDIUM"
            reason = "specific child within nested juice-family tags"
    elif union:
        reason = "overlapping or conflicting specific evidence"
    return dict(identity=identity, confidence=confidence, reason=reason,
                name_evidence="; ".join(sorted(n)), tag_evidence="; ".join(sorted(t)),
                name_supported=bool(n), tag_supported=bool(t), corroborated=bool(n & t),
                overlap=len(union) > 1, use_caution=use_caution, version=VERSION)


def regression_checks():
    assert decide("Pur jus de pomme", "Boissons aux fruits,Jus et nectars,Jus de pomme")["identity"] == "juice"
    assert decide("Orange juice", "Fruit drinks,Orange juices")["identity"] == "juice family unresolved"
    assert decide("", "Boissons aux fruits,Jus et nectars")["identity"] == "juice family unresolved"
    assert decide("Nectar de pêche", "Jus de fruits,Nectars de pêche")["identity"] == "nectar"
    assert decide("Smoothie fraise", "Juices,Smoothies")["identity"] == "smoothie"
    assert decide("Jus d'abricot", "Nectars d'abricot")["identity"] == "juice family unresolved"
    assert decide("Orange juice drink", "Fruit-based beverages")["identity"] == "fruit drink"
    assert decide("", "Apple juices")["identity"] == "juice"
    assert decide("Pure apple juice", "")["identity"] == "juice"
    assert decide("Lemon juice concentrate for dilution", "Lemon juices")["identity"] == "juice family unresolved"
    assert cues("Carbonated soft drinks without fruit juice", True) == set()
    assert cues("Boissons gazeuses sans jus de fruits", True) == set()
    assert decide("Iced tea with cranberry juice", "Fruit juices")["identity"] == "juice family unresolved"


if __name__ == "__main__":
    regression_checks()
    print("PASS shared juice identity regression checks")
