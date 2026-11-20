"""Offline, additive BEVERAGE 05A audit. Never changes RUN 06B inputs."""
from pathlib import Path
import csv
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'presentations/segmentation'
FROZEN = BASE / 'run_06b_v2'
OUT = BASE / 'beverage_05a_v1'
DB = ROOT / 'data/06_brand_governance_outputs/incremental_ingestion_trials/release_real_proxy_20261018_v1/release_work.db'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def norm(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))

def load():
    manifest = json.loads((FROZEN / 'run_06b_manifest.json').read_text(encoding='utf-8'))
    for name in ['selected_manifest.csv', 'reserve_manifest.csv', 'unfilled_slots.csv', 'final_country_component_reconciliation.csv']:
        expected = manifest['outputs_sha256'].get(name)
        if expected is None:
            expected = manifest['outputs_sha256'].get('presentations/segmentation/run_06b_v2/' + name)
        if isinstance(expected, dict):
            expected = expected['sha256']
        assert expected and sha(FROZEN / name) == expected, (name, expected)
    rows = []
    for role, name in [('selected', 'selected_manifest.csv'), ('reserve', 'reserve_manifest.csv')]:
        for row in read_csv(FROZEN / name):
            if row['category'] == 'beverages':
                row['audit_manifest_role'] = role
                rows.append(row)
    assert sum(r['audit_manifest_role'] == 'selected' for r in rows) == 3563
    assert sum(r['audit_manifest_role'] == 'reserve' for r in rows) == 593
    assert len({(r['barcode'], r['region'], r['category']) for r in rows}) == len(rows)
    con = sqlite3.connect(DB.as_uri() + '?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    evidence = {}
    codes = sorted({r['barcode'] for r in rows})
    for start in range(0, len(codes), 400):
        batch = codes[start:start+400]
        for r in con.execute('SELECT barcode, product_name, brands, off_categories, quantity, packaging, image_url, last_modified_t, ingested_at FROM products WHERE barcode IN (' + ','.join('?' for _ in batch) + ')', batch):
            evidence[r['barcode']] = dict(r)
    con.close()
    for row in rows:
        row['source_evidence'] = evidence.get(row['barcode'], {})
    assert all(r['source_evidence'] for r in rows)
    return rows

# Screening is deliberately broad. It creates review leads, never exclusions.
SUSPECT = re.compile(r'\b(sauces?|oils?|huile[s]?|olive|vinaigr\w*|vinegar|dressings?|condiments?|ketchup|mustard|moutarde|mayonnais\w*|season\w*|assaisonn\w*|epice[s]?|spices?|rubs?|bouillons?|broths?|soups?|soupes?|pesto|gravy|grill\w*|marinad\w*|salsa|tahin\w*|teriyaki|tapenade|honey|miel|maple|erable|agave|flour|farine|baking|levure|gelatin\w*|gelatine|desserts?|custard|pudding|confit\w*|jams?|jell\w*|bonbons?|sweets?|cand\w*|chips?|crisps?|biscuits?|cookies?|pasta|pates|noodles?|rice|riz|cheese|fromage|cream|creme|butter|beurre|ghee|eggs?|oeufs?|cereals?|cereal\w*|porridge|oats?|oatmeal|granola|muesli|meats?|chicken|poulet|beef|boeuf|fish|poisson|tuna|thon|salads?|salades?|purees?|compotes?|pickl\w*|gherkins?|cornichon\w*|haricots?|beans|lentils?|lentilles|chocolates?|chocolat|caramel|pepper|poivre|salt|sel|garlic|ail|tomato\w*|tomate\w*|coconut|coco|nuts?|noix|almonds?|amandes?|fruits?|fruit\w*|seeds?|graines?|complement\w*|supplement\w*|capsules?|caps|gummies|gummy|tablets?|tablett\w*|vitamin\w*|vitamin\w*)\b')

def inspect():
    rows = load()
    OUT.mkdir(exist_ok=True)
    (OUT / 'local_evidence_inventory.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
    leads = []
    for r in rows:
        e = r['source_evidence']
        text = norm(r['product_name'] + ' ' + str(e.get('off_categories') or ''))
        hits = sorted(set(m.group() for m in SUSPECT.finditer(text)))
        if hits:
            leads.append(r)
    print('ALL', len(rows), 'SCREEN LEADS', len(leads))
    for r in leads:
        e = r['source_evidence']
        # Keep names complete; tags concise enough for first screening.
        print(r['audit_manifest_role'][0], r['barcode'], r['region'], r['product_name'], '|', str(e.get('off_categories') or '')[:600], sep='\t')

VISUAL_INDICES = [73,101,135,167,216,250,253,278,401,403,443,464,470,474,506,512,537,621,658,669,747,797,820,847,890,908,911,982,990,1006,1013,1044,1113,1116,1118,1153,1171,1176,1332,1337,1374,1425,1478,1489,1520,1544,1551,1592,1615,1625,1626,1632,1650,1671,1677,1706,1708,1715,1729,1731,1756,1763,1788,1790,1792,1793,1794,1805,1829,1859,1875,1885,1886,1949,1950,1955,1962,1972,1976,1992,2020,2043,2052,2120,2177,2194,2241,2255,2291,2301,2371,2389,2393,2398,2487,2565,2634,2635,2708,2762,2892,2944,2960,3039,3059,3063,3115,3277,3291,3298,3302,3310,3363,3373,3392,3394,3411,3418,3427,3431,3437,3440,3458,3463,3471,3474,3478,3480,3483,3484,3487,3491,3496,3497,3499,3507,3510,3512,3513,3520,3528,3534,3547,3548,3551,3587,3598,3614,3690,3705,3766,3776,3778,3780,3851,3856,3943,3952,3986,4005,4054,4108,4131,4155]

def contact_sheets():
    rows = json.loads((OUT / 'local_evidence_inventory.json').read_text(encoding='utf-8'))
    directory = OUT / 'local_visual_review'
    directory.mkdir(exist_ok=True)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
    visual_indices = VISUAL_INDICES + [i for i,r in enumerate(rows) if not r['product_name'].strip() and i not in VISUAL_INDICES] + [49,289,1556,1670,2213,1050]
    for start in range(0, len(visual_indices), 16):
        indices = visual_indices[start:start+16]
        page = Image.new('RGB', (1440, 1600), 'white')
        draw = ImageDraw.Draw(page)
        for pos, idx in enumerate(indices):
            r = rows[idx]
            x, y = (pos % 4) * 360, (pos // 4) * 400
            path = ROOT / r['immutable_image_path']
            assert sha(path) == r['image_sha256'], r['barcode']
            with Image.open(path) as source:
                im = source.convert('RGB')
                im.thumbnail((350, 320))
            page.paste(im, (x + (360-im.width)//2, y+65))
            name = r['product_name']
            draw.text((x+5,y+3), f"{idx} | {r['barcode']}", font=font, fill='black')
            draw.text((x+5,y+23), name[:43], font=font, fill='black')
            draw.text((x+5,y+43), name[43:86], font=font, fill='black')
        page.save(directory / f'page_{start//16+1:02d}.png')
    print('Local contact sheets:', (len(visual_indices)+15)//16)

def source_urls():
    import pandas as pd
    source = ROOT / 'data/02_raw_off_downloads/incremental_snapshots/wave2_proxy_20260929_retrieved_20261017T153127Z/source.csv.gz'
    rows = json.loads((OUT / 'local_evidence_inventory.json').read_text(encoding='utf-8'))
    codes = {r['barcode'] for r in rows}
    records = []
    for chunk in pd.read_csv(source, sep='\t', usecols=['code','url','product_name','categories'], dtype=str, keep_default_na=False, chunksize=100000, low_memory=False):
        records.extend(chunk[chunk.code.isin(codes)].to_dict('records'))
    (OUT / 'local_original_source_urls.json').write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding='utf-8')
    print('Exact source URL matches:', len(records), 'of', len(codes))

def source_url_aliases():
    """Recover URL fields only, retaining source code and explicit alias provenance.

    First two OFF TSV fields are numeric code and URL. Continuation lines from
    quoted later text fields cannot pass both numeric-code and HTTP URL checks.
    No nutrition, product identity or assignment is normalized by this lookup.
    """
    import gzip
    rows = json.loads((OUT / 'local_evidence_inventory.json').read_text(encoding='utf-8'))
    codes = {r['barcode'].lstrip('0') for r in rows}
    source = ROOT / 'data/02_raw_off_downloads/incremental_snapshots/wave2_proxy_20260929_retrieved_20261017T153127Z/source.csv.gz'
    records = []
    with gzip.open(source, 'rb') as f:
        next(f)
        for line in f:
            parts = line.split(b'\t',2)
            if len(parts) < 3:
                continue
            code = parts[0].strip(b'"').decode('ascii',errors='ignore')
            if code.isdigit() and code.lstrip('0') in codes:
                url = parts[1].strip(b'"').decode('utf-8')
                assert url.startswith(('http://','https://')), (code,url)
                records.append({'code':code,'url':url})
    (OUT / 'local_source_url_aliases.json').write_text(json.dumps(records,ensure_ascii=False,indent=1),encoding='utf-8')
    print('URL-only exact/zero-padding reference matches:',len(records))

# These are case-specific audit proposals made after viewing the saved images.
# Indices address the hash-checked frozen inventory; outputs always carry exact
# barcode + region + category keys. They are not executable exclusion rules.
CLEAR = {
    73: ('sauce_condiment', 'LA WILLIAM ANDALOUSE sauce bottle, with plated-food serving illustration.'),
    135: ('sugar_sweetener', 'Daddy sucre en poudre 500 g bag. Source wine tags conflict with the sugar identity.'),
    470: ('solid_food', 'Excelencia jar of pitted Manzanilla olives; visible ACEITUNAS MANZANILLA DESHUESADAS.'),
    506: ('cooking_stock', 'Exsalt fond de volaille tub, presented as poultry cooking stock.'),
    621: ('solid_food', 'La belle-iloise tin explicitly says Mousse de Homard au Cognac.'),
    890: ('coconut_cooking', 'Co-op Thai coconut milk can: An essential ingredient for Thai, Indian and Caribbean recipes; curry serving image.'),
    908: ('solid_food', 'Delacre Tea Time biscuit assortment tin with biscuit pictures.'),
    982: ('oil', 'Tartufo Bianco tin: CONDIMENTO A BASE DI OLIO EXTRA VERGINE DI OLIVA AROMATIZZATO AL Tartufo Bianco.'),
    990: ('oil', 'Five-litre olive-oil container explicitly labelled Olio d oliva.'),
    1332: ('coconut_cooking', 'M&S coconut cream can explicitly says IDEAL FOR ORIENTAL, INDIAN AND CARIBBEAN COOKING.'),
    1374: ('solid_food', 'M&S gastropub Sticky Toffee Pudding dessert carton; sponge with salted caramel sauce.'),
    1425: ('solid_food', 'Tub labelled HUMMUS NATUR 200 g.'),
    1478: ('solid_food', 'Sainsburys little ones organic pear & apple baby puree pouch, from 4-6 months.'),
    1551: ('solid_food', 'M&S SEEDLESS RASPBERRY CONSERVE jar; brands field disagrees with the photographed retailer.'),
    1615: ('sauce_condiment', 'Thai Boy SWEET CHILLI SAUCE bottle.'),
    1671: ('coconut_cooking', 'Ready Set Cook! coconut milk can: ADD TO YOUR FAVOURITE DISHES FOR A CREAMY COCONUT FLAVOUR.'),
    1729: ('solid_food', 'M&S ROASTED AUBERGINE WITH MOZZARELLA tray; MAIN FOR 2.'),
    1792: ('solid_food', 'fruitpot MANDARIN fruit pieces in fruit juice, spoon included. Solid fruit dessert rather than juice.'),
    1794: ('solid_food', 'Waitrose wafer thin Brunswick ham sliced-meat pack.'),
    1829: ('coconut_cooking', 'Ready Set Cook! coconut milk can: ADD TO YOUR FAVOURITE DISHES FOR A CREAMY COCONUT FLAVOUR.'),
    1859: ('solid_food', 'Ready to eat sweet chilli chicken breast slices; GREAT WITH A SALAD.'),
    1976: ('solid_food', 'Cofresh CHILLI & LEMON GRILLS bag; FLAVOURED POTATO SNACK.'),
    2043: ('sauce_condiment', 'Mirin sauce bottle explicitly says Japanese style and has a plated-food serving illustration.'),
    2094: ('solid_food', 'Unnamed source record. Cached Tuscanini can explicitly says Whole Cherry TOMATOES.'),
    2635: ('table_syrup', 'Smuckers Sugar Free BREAKFAST SYRUP bottle with pancakes and butter illustration.'),
    3310: ('cooking_stock', 'Unicorn organic BOUILLON POWDER bag with cooking-stock ingredients.'),
    3363: ('table_syrup', 'Aunt Jemima original table syrup bottle with pancake serving illustration.'),
    3392: ('solid_food', 'M&S SEEDLESS RASPBERRY CONSERVE jar; separate exact source barcode from 940207 is preserved.'),
    3427: ('sauce_condiment', 'Mymoune POMEGRANATE MOLASSES bottle explicitly says SEASONING.'),
    3431: ('sugar_sweetener', 'Coconut Secret Raw Coconut Nectar explicitly labelled Low Glycemic Sweetener, with waffle illustration.'),
    3440: ('solid_food', 'Rich Tea biscuits in a biscuit packet, visibly solid round biscuits.'),
    3480: ('solid_food', 'Appleton Farms SPICY BITE SIZE DRY SALAMI pack.'),
    3483: ('solid_food', 'Signature Select Hass Avocados bag containing whole avocados.'),
    3497: ('solid_food', 'BRIX smooth dark chocolate bar, CHOCOLATE FOR WINE, 54% cacao. A pairing food, not wine.'),
    3520: ('coconut_cooking', 'Pacific Jade coconut milk can explicitly says FOR COOKING AND BAKING.'),
    3551: ('solid_food', 'Bridgford Sweet Baby Rays SWEET TERIYAKI BEEF JERKY bag.'),
    3598: ('solid_food', 'Delhaize Crunchy Muesli chocolate cereal container.'),
    3614: ('solid_food', 'Delacre Tea Time box visibly contains biscuits and chocolate-coated biscuits.'),
    3778: ('solid_food', 'LAngelys sorbet dessert carton: FRAMBOISE and FRUIT DE LA PASSION, pour 6 a 8 invites.'),
    4054: ('cooking_wine', 'Golden Swan bottle explicitly says Shaoxing Cooking Wine.'),
}

# Consistent culinary tags and coconut-milk/cream packaging are a review lead,
# not sufficient evidence to reject all coconut products or dual-use products.
COCONUT_LIKELY = [250,253,278,443,512,537,669,820,1044,1489,1520,1544,1625,1677,1706,1715,1756,1788,1805,1885,1949,1962,1972,1992,2120,2177,2194,2762,3039,3471,3474,3487,3496,3499,3512,3513,3534,3547,3690,3705,3766,3851,3856,3943,3986,4005,4131]

AMBIGUOUS = {
    401: ('multipurpose_ingredient', 'Maca powder superfood bag. Beverage use is possible but not established by the front label alone.'),
    464: ('identity_conflict', 'Source name is ice cream; cached image is Plein Sud sirop de citron. Do not exclude a syrup on this name alone.'),
    658: ('identity_uncertain', 'Petti Il piccanto tomato bottle. Source tags say tomato juice; front image does not establish sauce versus drink use.'),
    747: ('dual_use_syrup', 'Agave syrup sweetener with tea/food serving images; beverage use and general sweetening both plausible.'),
    797: ('identity_conflict', 'Source name Meat Loaf; cached image shows Ozarka water. Exact source/image identity needs reconciliation.'),
    911: ('multipurpose_ingredient', 'Liquid stevia sweetening solution. It can sweeten drinks; scope needs confirmation rather than automatic exclusion.'),
    1013: ('dual_use_syrup', 'Natural Zero caramel syrup with pancakes; source beverage-syrup tags. Drink flavouring versus topping not resolved.'),
    1118: ('dual_use_syrup', 'Black Shank raspberry-flavoured maple syrup. Drink/cocktail use is not established in saved front evidence.'),
    1153: ('dual_use_syrup', 'Coconut blossom syrup labelled high sweetening power. General sweetener versus beverage syrup needs review.'),
    1171: ('multipurpose_ingredient', 'Bag of fermented whole cacao beans. No ready drink or explicit drink-mix preparation shown.'),
    1176: ('dual_use_syrup', 'Yakso coconut blossom syrup amber. General sweetener versus beverage preparation is unresolved.'),
    1337: ('identity_conflict', 'Source name Petit Pain Pack; cached image is Naturis orange juice. Do not exclude on the bread-like name.'),
    1650: ('identity_conflict', 'Source name Napolina pasra sauce; cached image is Sainsburys orange & mango double-strength squash.'),
    1708: ('identity_conflict', 'Source name Ice Cream Carton; cached image is Nexba strawberry & raspberry sparkling water.'),
    1763: ('identity_conflict', 'Source name Nespresso coffee capsules; cached image is Guph gang Guphoria hazelnut spread. Identity reconciliation needed.'),
    2052: ('multipurpose_ingredient', 'Fennel seed bag labelled HERBS & SPICES; source also has herbal-tea tags. Possible brewing use must be preserved pending review.'),
    2241: ('identity_conflict', 'Source name chocolate bars; cached image is M&S pomegranate & raspberry juice drink.'),
    2301: ('identity_conflict', 'Source bilingual name includes marzipan egg and turmeric teabags; image shows M&S turmeric teabags.'),
    2371: ('multipurpose_ingredient', 'Natural cacao powder with cooking imagery. Beverage preparation remains possible; do not reject all cacao powders.'),
    2393: ('multipurpose_ingredient', 'Belbake Backkakao baking cocoa; multi-use cacao powder could also be used for drinks. Review use rather than excluding powders.'),
    2634: ('multipurpose_ingredient', 'Snows clam juice bottle advertises sauces and seafood dishes. Cocktail use is possible; dedicated drink use is not established.'),
    2708: ('multipurpose_ingredient', 'Organic cacao powder with baking illustration; explicit drink mix not shown. Beverage use remains possible.'),
    2892: ('identity_conflict', 'Source name Light Mayonnaise; cached image shows a clear bottled-water nutrition panel, not mayonnaise.'),
    3063: ('identity_conflict', 'Source name Meat Loaf; cached image is Ozarka water. Leading-zero barcode differs from France assignment and is preserved exactly.'),
    3277: ('multipurpose_ingredient', 'Maca powder superfood bag; drink use possible but not established on saved front evidence.'),
    3386: ('multipurpose_ingredient', 'Unnamed source record. Image is Natures Charm sweetened condensed coconut milk; possible beverage ingredient versus dessert use.'),
    3437: ('multipurpose_ingredient', 'Raw maca powder superfood bag; drink use possible but not established on saved front evidence.'),
    3507: ('multipurpose_ingredient', 'Ground flax seed retail screenshot shows a smoothie alongside seeds. General ingredient versus beverage preparation remains unresolved.'),
    3528: ('unassessable_identity', 'Placeholder-like name dsdsds, brand bfgfg, barcode 12345678; cached photo shows fabric, not an identifiable product. No corrected identity inferred.'),
}

LEGITIMATE_NOTES = {
    101: 'Auchan coconut milk carton with rice; ready plant drink despite inherited cooking tags.',
    167: 'Oasis Pomme-Poire can; compote tags do not describe the pictured drink.',
    403: 'Pure Flow bottle includes Bevanda di cocco; preserve beverage/dual-use product despite cooking tags.',
    474: 'Dardenne chocolate package presents a cup of hot chocolate and petit dejeuner/dessert use; retain beverage preparation.',
    847: 'Mazza Tropical fruit drink carton; fish tag is category noise.',
    1006: 'Simplement Bon Bio mango nectar bottle.',
    1116: 'La Tisaniere thyme infusion bags; legitimate brewing material.',
    1592: 'Coco Lopez panel has explicit authentic Pina Colada recipe; legitimate cocktail preparation.',
    1626: 'OSHEE Vitamin Water Magnesium B6 bottle; not a supplement tablet.',
    1632: 'eo3 nutritional ready-to-drink smoothie carton with omega-3; retain.',
    1790: 'Castello Original sparkling mineral water bottle; not cheese.',
    1793: 'Pecorino wine bottle; not cheese.',
    1875: 'ASDA creamy and smooth long-life coconut plant drink carton.',
    1886: 'Fresh Drinking Coconut, sold for its drinkable coconut water; retain.',
    1955: 'VOOM FUSION FUEL ENERGY DRINK sachet; name Gel conflicts but pack supports drink preparation.',
    2020: 'Morrisons Beefy Drink jar explicitly instructs boiling water; retain savoury drink preparation.',
    2255: 'Get More Vits vitamin B12 pink grapefruit still-water bottle; retain.',
    2291: 'Nutra Defence herbal tea bags; retain brewing preparation.',
    2389: 'Mushrooms 4 Life Lions Mane MATCHA LATTE; retain drink powder.',
    2398: 'MOJU Fresh Root Ginger bottled shot; not a root vegetable.',
    2944: 'Matcha green tea powder remains legitimate brewing/drink preparation even when culinary grade.',
    3059: 'C4 Cereal Killer performance energy drink can; cereal is a flavour/name.',
    3115: 'Simple Truth coconutmilk carton, creamy and rich plant drink; retain.',
    3291: 'Whole Moon pistachio whole protein plant beverage bottle.',
    3302: 'Sambazon acai packs explicitly GREAT FOR SMOOTHIES & BOWLS; retain smoothie preparation.',
    3373: 'Coco Lopez panel has explicit Pina Colada recipe; preserve separate exact barcode.',
    3411: 'Chocolate de mesa con canela is a hot-chocolate preparation; not excluded for solid format.',
    3458: 'Calahua cream of coconut can: potential cocktail preparation; no exclusion without contrary use evidence.',
    3463: 'Milk Magic milk-flavouring straws; beverage preparation, not plain confectionery.',
    3491: 'Superfood powder presents beverage/smoothie use; retain preparation.',
    3548: 'Nutricost chocolate-flavoured Bone Broth Protein powder; retain specialist drink preparation, not cooking bouillon.',
    3587: 'Wei Ming Taiwan Pearl Milk Tea preparation pack; not loose tapioca food.',
    3776: 'Eau de Quinton oral liquid product; no demonstrated non-beverage identity from saved evidence.',
    3780: 'Pure Flow coconut milk bottle includes Bevanda di cocco; preserve beverage/dual-use preparation.',
    3952: 'Alpro coconut unsweetened plant-drink carton; retain.',
    4155: 'Kuro Goma Latte HOT & ICE black sesame drink powder; retain.',
    1814: 'Trader Joes half & half carton may be a coffee addition, but source lemonade tags conflict; identity review separately.',
}

def reviewed_indices(rows):
    return VISUAL_INDICES + [i for i,r in enumerate(rows) if not r['product_name'].strip() and i not in VISUAL_INDICES] + [49,289,1556,1670,2213,1050]

def decisions(rows):
    result = []
    for idx in reviewed_indices(rows):
        r = rows[idx]
        label = 'Legitimate beverage or beverage preparation'
        family = 'beverage_or_preparation'
        evidence = LEGITIMATE_NOTES.get(idx, 'Cached pack evidence supports a beverage or beverage preparation. No non-beverage identity established.')
        action = 'Retain under existing scope; no change proposed'
        if idx in CLEAR:
            label = 'Clearly non-beverage'
            family, evidence = CLEAR[idx]
            action = 'Propose exact-assignment exclusion, subject to Julia approval; no exclusion applied'
        elif idx in COCONUT_LIKELY:
            label = 'Likely non-beverage, requiring confirmation'
            family = 'coconut_cooking_review'
            evidence = 'Saved cooking/coconut-cream category evidence with coconut milk/cream culinary-style packaging. Front evidence does not establish a dedicated drink product. Confirm intended use; can/carton format and nutrition alone are not exclusion criteria.'
            action = 'Confirm intended commercial use before deciding; no exclusion applied'
        elif idx == 1113:
            label = 'Likely non-beverage, requiring confirmation'
            family = 'table_syrup_review'
            evidence = 'Myprotein syrup has pancake serving illustration and source Nappages (toppings) tag. Beverage-use alternative is not ruled out.'
            action = 'Confirm topping versus beverage syrup use; no exclusion applied'
        elif idx in [1731,3418]:
            label = 'Likely non-beverage, requiring confirmation'
            family = 'cooking_wine_review'
            evidence = 'Saved Mirin identity/categories and sweet rice wine/fermented mirin bottle. Confirm cooking seasoning rather than beverage sake or a drinkable wine before exclusion.'
            action = 'Confirm cooking-only commercial identity; no exclusion applied'
        elif idx == 1950:
            label = 'Likely non-beverage, requiring confirmation'
            family = 'sports_gel_scope'
            evidence = 'Applied Nutrition ENDURANCE ISOTONIC ENERGY GEL sachet. Confirm ready-to-eat gel versus preparation diluted as a drink; sports use alone is not decisive.'
            action = 'Confirm direct-consumption gel use and scope; no exclusion applied'
        elif idx in AMBIGUOUS:
            label = 'Ambiguous'
            family, evidence = AMBIGUOUS[idx]
            action = 'Review identity or intended use; no exclusion proposed without resolution'
        if idx == 1814:
            label, family = 'Ambiguous', 'identity_conflict'
            action = 'Resolve lemonade tags versus half-and-half pack; beverage-addition scope also needs confirmation'
        result.append(dict(inventory_index=idx, barcode=r['barcode'], region=r['region'], category=r['category'], proposed_classification=label, issue_family=family, evidence=evidence, proposed_decision=action, visual_review='Codex inspected existing cached image; no new image download', approval_status='Pending Julia review', image_sha256=r['image_sha256'], immutable_image_path=r['immutable_image_path']))
    return result

def preview_decisions():
    from collections import Counter
    rows = json.loads((OUT / 'local_evidence_inventory.json').read_text(encoding='utf-8'))
    d = decisions(rows)
    (OUT / 'case_decision_register.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Inspected',len(d),'Classifications',dict(Counter(x['proposed_classification'] for x in d)))
    print('Suspects by role',dict(Counter(rows[x['inventory_index']]['audit_manifest_role'] for x in d if not x['proposed_classification'].startswith('Legitimate'))))

def key(r):
    return (r['sampling_group_id'],r['country_cell'],r['accounting_component'])

def prepare_tables():
    from collections import Counter
    rows = load()  # Rechecks the frozen shortlist hashes before analysis.
    stored = json.loads((OUT / 'local_evidence_inventory.json').read_text(encoding='utf-8'))
    assert [(r['barcode'],r['region']) for r in rows] == [(r['barcode'],r['region']) for r in stored]
    reviews = decisions(rows)
    suspects = [d for d in reviews if not d['proposed_classification'].startswith('Legitimate')]
    flags = {d['inventory_index']:d for d in suspects}
    source_urls = json.loads((OUT / 'local_source_url_aliases.json').read_text(encoding='utf-8'))
    urls_by_equivalent = {}
    for u in source_urls:
        k = u['code'].lstrip('0')
        assert k not in urls_by_equivalent
        urls_by_equivalent[k] = u
    for r in rows:
        assert r['status'] == 'technical_pass' and r['m1_eligible'] == '1'
        assert r['manual_review_hold'] == '0' and r['existing_successful_ocr_llm'] == '0'
        assert r['prior_failed_or_unusable'] == '0' and r['fresh_history_first_attempt_verified'] == 'True'
    unf = read_csv(FROZEN / 'unfilled_slots.csv')
    assert len(unf) == 63
    bev_unf = [r for r in unf if r['category']=='beverages']
    assert len(bev_unf)==37
    reserves = Counter(key(r) for i,r in enumerate(rows) if r['audit_manifest_role']=='reserve')
    unflagged_reserves = Counter(key(r) for i,r in enumerate(rows) if r['audit_manifest_role']=='reserve' and i not in flags)
    reviewed_legit_reserves = Counter(key(rows[d['inventory_index']]) for d in reviews if d['proposed_classification'].startswith('Legitimate') and rows[d['inventory_index']]['audit_manifest_role']=='reserve')
    review_table = []
    for d in suspects:
        r = rows[d['inventory_index']]
        u = urls_by_equivalent.get(r['barcode'].lstrip('0'))
        assert u, r['barcode']
        review_table.append({
            'barcode':r['barcode'], 'product_name':r['product_name'],
            'manifest_role':r['audit_manifest_role'], 'region':r['region'],
            'sampling_group_id':r['sampling_group_id'], 'country_cell':r['country_cell'],
            'sampling_component':r['accounting_component'], 'country_assignments':r['countries'],
            'original_product_url':u['url'], 'source_url_barcode':u['code'],
            'url_provenance':'exact source code, preserved OFF TSV URL' if u['code']==r['barcode'] else 'preserved OFF TSV URL at zero-padded equivalent code; audit barcode unchanged',
            'original_image_url':r['original_image_url'],
            'proposed_classification':d['proposed_classification'], 'issue_family':d['issue_family'],
            'evidence':d['evidence'], 'source_category_evidence':r['source_evidence'].get('off_categories') or '',
            'proposed_decision':d['proposed_decision'],
            'same_cell_component_reserves_without_any_audit_flag':unflagged_reserves[key(r)],
            'nutrition_warning_present':int(r['nutrition_warning_present']),
            'image_sha256':r['image_sha256'], 'cached_image_path':r['immutable_image_path'],
            'approval_status':'Pending Julia review; no exclusion or replacement applied',
        })
    order = {'Clearly non-beverage':0,'Likely non-beverage, requiring confirmation':1,'Ambiguous':2}
    review_table.sort(key=lambda x:(order[x['proposed_classification']],x['region'],x['manifest_role'],x['barcode']))
    groups = sorted({(r['region'],r['sampling_group_id']) for r in rows})
    counts = []
    for region,group in groups:
        out = {'region':region,'sampling_group_id':group}
        for role in ['selected','reserve']:
            ix = [i for i,r in enumerate(rows) if r['sampling_group_id']==group and r['audit_manifest_role']==role]
            out[role+'_frozen_records'] = len(ix)
            for prefix,label in [('clear','Clearly non-beverage'),('likely','Likely non-beverage, requiring confirmation'),('ambiguous','Ambiguous')]:
                out[role+'_'+prefix] = sum(i in flags and flags[i]['proposed_classification']==label for i in ix)
            out[role+'_total_suspected'] = sum(i in flags for i in ix)
        out['existing_beverage_shortfall'] = sum(r['sampling_group_id']==group for r in bev_unf)
        counts.append(out)
    cells = sorted(set(key(r) for r in rows) | {key(r) for r in bev_unf})
    existing = Counter(key(r) for r in bev_unf)
    selected = Counter(key(r) for r in rows if r['audit_manifest_role']=='selected')
    scenarios = {
        'clear_only': {'Clearly non-beverage'},
        'clear_plus_likely_if_confirmed': {'Clearly non-beverage','Likely non-beverage, requiring confirmation'},
        'all_suspects_held_for_review_upper_bound': {'Clearly non-beverage','Likely non-beverage, requiring confirmation','Ambiguous'},
    }
    quota = []
    for scenario, labels in scenarios.items():
        lost = Counter(key(rows[d['inventory_index']]) for d in suspects if d['proposed_classification'] in labels and rows[d['inventory_index']]['audit_manifest_role']=='selected')
        for cell in cells:
            group,country,component = cell
            demand = existing[cell] + lost[cell]
            capacity = min(demand,unflagged_reserves[cell])
            quota.append(dict(
                scenario=scenario,region=next(r['region'] for r in rows if r['sampling_group_id']==group),
                sampling_group_id=group,country_cell=country,sampling_component=component,
                approved_cell_component_slots=selected[cell]+existing[cell],
                frozen_selected=selected[cell],existing_unfilled_slots=existing[cell],
                potential_additional_selected_losses=lost[cell],combined_potential_slots_to_fill=demand,
                remaining_frozen_reserves=reserves[cell],
                reserves_with_any_audit_flag=reserves[cell]-unflagged_reserves[cell],
                reserves_without_any_audit_flag=unflagged_reserves[cell],
                cached_reviewed_legitimate_reserves=reviewed_legit_reserves[cell],
                same_cell_component_reserve_exists=bool(unflagged_reserves[cell]),
                maximum_theoretical_coverage=capacity,
                potential_uncovered_slots_after_theoretical_coverage=demand-capacity,
                reserve_qualification='Frozen technical/history checks only; category screen not a full visual census; front/usability and execution gates remain pending',
                action_taken='None; no exclusions, promotions, redraws or quota changes',
            ))
    assert sum(x['selected_frozen_records'] for x in counts)==3563
    assert sum(x['reserve_frozen_records'] for x in counts)==593
    for name in scenarios:
        q = [x for x in quota if x['scenario']==name]
        assert sum(x['approved_cell_component_slots'] for x in q)==3600
        assert sum(x['existing_unfilled_slots'] for x in q)==37
        assert sum(x['remaining_frozen_reserves'] for x in q)==593
        assert sum(x['reserves_without_any_audit_flag'] for x in q)==580
    tables = {'suspected_products_review.csv':review_table,'counts_by_region_group.csv':counts,'potential_quota_impact.csv':quota}
    (OUT / 'audit_tables.json').write_text(json.dumps(tables,ensure_ascii=False,indent=1),encoding='utf-8')
    (OUT / 'case_decision_register.json').write_text(json.dumps(reviews,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Tables prepared', {k:len(v) for k,v in tables.items()})
    print('Group counts',json.dumps(counts))
    for name in scenarios:
        q=[x for x in quota if x['scenario']==name]
        print(name, {k:sum(x[k] for x in q) for k in ['potential_additional_selected_losses','combined_potential_slots_to_fill','maximum_theoretical_coverage','potential_uncovered_slots_after_theoretical_coverage']})

def verify_and_register():
    from collections import Counter
    from datetime import datetime, timezone
    tables = json.loads((OUT / 'audit_tables.json').read_text(encoding='utf-8'))
    checks = {}
    for name,expected in tables.items():
        actual = read_csv(OUT / name)
        assert len(actual)==len(expected), name
        for a,e in zip(actual,expected):
            assert list(a)==list(e), name
            for k,value in e.items():
                expected_value = str(value).lower() if isinstance(value,bool) else str(value)
                assert a[k] == expected_value, (name,k,a[k],expected_value)
        checks[name+'_exact_export_roundtrip'] = 'PASS'
    frozen = json.loads((FROZEN / 'run_06b_manifest.json').read_text(encoding='utf-8'))
    frozen_verified = {}
    for name,expected in frozen['outputs_sha256'].items():
        path = ROOT / name if '/' in name or '\\' in name else FROZEN / name
        assert sha(path)==expected, ('Frozen output changed',name)
        frozen_verified[str(path.relative_to(ROOT))] = expected
    protected_verified = {}
    for name,expected in frozen['protected_source_sha256'].items():
        path = ROOT / name
        assert sha(path)==expected, ('Protected source differs',name)
        protected_verified[str(path.relative_to(ROOT))] = expected
    checks['all_run_06b_registered_outputs_unchanged'] = len(frozen_verified)
    checks['all_run_06b_protected_sources_match_frozen_hashes'] = len(protected_verified)
    source_manifest = json.loads((BASE / 'run_01/run_01_manifest.json').read_text(encoding='utf-8'))
    db_hash = sha(DB)
    assert db_hash==source_manifest['source_database_sha256']
    raw = ROOT / 'data/02_raw_off_downloads/incremental_snapshots/wave2_proxy_20260929_retrieved_20261017T153127Z/source.csv.gz'
    raw_hash = sha(raw)
    # The raw transport gzip has its own manifest. RUN 01's release source hash
    # describes the governed ingestion input, not this downloaded gzip file.
    raw_manifest = raw.parent / 'manifest.json'
    assert raw_hash == json.loads(raw_manifest.read_text(encoding='utf-8'))['sha256']
    checks['same_release_database_and_raw_source_hashes'] = 'PASS'
    rows = json.loads((OUT / 'local_evidence_inventory.json').read_text(encoding='utf-8'))
    reviews = json.loads((OUT / 'case_decision_register.json').read_text(encoding='utf-8'))
    checked_images = {}
    for d in reviews:
        path = ROOT / d['immutable_image_path']
        assert sha(path)==d['image_sha256']
        checked_images[d['immutable_image_path']] = d['image_sha256']
    checks['reviewed_assignments_with_cache_hash_verified'] = len(reviews)
    review_csv = tables['suspected_products_review.csv']
    assert len({(r['barcode'],r['region'],'beverages') for r in review_csv}) == 121
    assert len({r['barcode'] for r in review_csv}) == 121
    assert Counter(r['manifest_role'] for r in review_csv)=={'selected':108,'reserve':13}
    assert Counter(r['proposed_classification'] for r in review_csv)=={'Clearly non-beverage':40,'Likely non-beverage, requiring confirmation':51,'Ambiguous':30}
    assert all(r['barcode'].lstrip('0')==r['source_url_barcode'].lstrip('0') for r in review_csv)
    checks['review_keys_classifications_urls_and_leading_zeros'] = 'PASS'
    all_selected = read_csv(FROZEN / 'selected_manifest.csv')
    all_reserve = read_csv(FROZEN / 'reserve_manifest.csv')
    evidence_keys = [r['evidence_candidate_key'] for r in all_selected+all_reserve]
    assert len(evidence_keys) == len(set(evidence_keys)) == 14170
    checks['frozen_primary_and_reserve_proposed_evidence_keys_disjoint'] = 'PASS'
    unf = read_csv(FROZEN / 'unfilled_slots.csv')
    assert len(all_selected)+len(unf)==12000 and len(unf)==63
    assert sum(r['category']=='beverages' for r in unf)==37
    checks['unchanged_12000_target_11937_selected_63_shortfall'] = 'PASS'
    expected = {'clear_only':(36,26,47,73),'clear_plus_likely_if_confirmed':(78,58,57,83),'all_suspects_held_for_review_upper_bound':(108,83,62,88)}
    for scenario,(loss,capacity,bev_gaps,global_gaps) in expected.items():
        q=[r for r in tables['potential_quota_impact.csv'] if r['scenario']==scenario]
        assert sum(r['potential_additional_selected_losses'] for r in q)==loss
        assert sum(r['maximum_theoretical_coverage'] for r in q)==capacity
        assert sum(r['potential_uncovered_slots_after_theoretical_coverage'] for r in q)==bev_gaps
        assert bev_gaps+26==global_gaps
        for r in q:
            assert r['maximum_theoretical_coverage'] <= r['reserves_without_any_audit_flag']
            assert r['maximum_theoretical_coverage'] <= r['combined_potential_slots_to_fill']
    checks['cell_component_capacity_and_existing_gap_reconciliation'] = 'PASS'
    report = BASE / 'BEVERAGE 05A - Non-beverage shortlist audit.md'
    output_paths = [report,Path(__file__),ROOT / 'pipeline/segmentation/beverage_05a_export_tables.mjs']
    output_paths += [p for p in OUT.iterdir() if p.is_file() and p.name!='audit_manifest.json']
    output_paths += sorted((OUT / 'local_visual_review').glob('page_*.png'))
    result = {
        'audit':'BEVERAGE 05A','version':'v1','decision_date':'2026-10-24',
        'verified_at_utc':datetime.now(timezone.utc).isoformat(),
        'status':'Pending Julia review; no exclusions or replacement authorization',
        'scope':{'selected_beverages':3563,'reserve_beverages':593,'regional_assignments':4156,'exact_barcode_strings':4109,'visually_reviewed_assignments':227,'suspected_assignments':121,'clear_selected':36,'clear_reserve':4,'likely_selected':42,'likely_reserve':9,'ambiguous_selected':30,'ambiguous_reserve':0},
        'url_provenance':{'saved_source_urls':121,'exact_source_code':108,'zero_padding_equivalent_reference_only':13,'audit_barcodes_changed':0},
        'frozen_run_06b_manifest_sha256':sha(FROZEN / 'run_06b_manifest.json'),
        'frozen_verification_receipt_sha256':sha(FROZEN / 'verification_receipt.json'),
        'frozen_registered_outputs_verified_sha256':frozen_verified,
        'protected_run_06b_sources_verified_sha256':protected_verified,
        'release_database':{'path':str(DB.relative_to(ROOT)),'sha256':db_hash,'access':'sqlite mode=ro'},
        'original_off_tsv':{'path':str(raw.relative_to(ROOT)),'sha256':raw_hash,'manifest':str(raw_manifest.relative_to(ROOT)),'manifest_sha256':sha(raw_manifest),'purpose':'saved product-page URL recovery only'},
        'reviewed_cached_images_sha256':checked_images,
        'validation':checks,
        'outputs_sha256':{str(p.relative_to(ROOT)):sha(p) for p in output_paths},
        'reproduction':[
            'Bundled Python: beverage_05a_non_beverage_audit.py (inventory screen)',
            'Bundled Python: beverage_05a_non_beverage_audit.py --source-url-aliases',
            'Bundled Python: beverage_05a_non_beverage_audit.py --contact-sheets',
            'Review saved case-specific decisions; --prepare-tables',
            'Bundled Node: beverage_05a_export_tables.mjs',
            'Bundled Python: beverage_05a_non_beverage_audit.py --verify',
        ],
        'actions':{'source_changes':0,'manifest_changes':0,'exclusions_applied':0,'holds_applied':0,'reserve_promotions':0,'redraws':0,'quota_changes':0,'new_image_downloads':0,'paid_ocr_llm_calls':0,'prompt_or_historical_claim_changes':0},
        'limitations':['Targeted cached-image review, not all 4156 images','Cached image association not independently verified printed GTIN','13 product URLs use explicitly recorded zero-padding-equivalent source code','Remaining reserve capacity is hypothetical under frozen group/country/component constraints','Existing RUN 06B hard gates remain unresolved'],
    }
    (OUT / 'audit_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(checks,indent=2))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--contact-sheets' in sys.argv:
        contact_sheets()
    elif '--source-urls' in sys.argv:
        source_urls()
    elif '--source-url-aliases' in sys.argv:
        source_url_aliases()
    elif '--preview-decisions' in sys.argv:
        preview_decisions()
    elif '--prepare-tables' in sys.argv:
        prepare_tables()
    elif '--verify' in sys.argv:
        verify_and_register()
    else:
        inspect()
