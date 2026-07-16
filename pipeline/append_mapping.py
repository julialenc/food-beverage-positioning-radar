"""
Appends all new company mapping rows directly to company_brand_mapping.csv.
Run once, then restart the app.

Usage: python pipeline/append_mapping.py
"""
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
TARGET  = ROOT / "data" / "reference" / "company_brand_mapping.csv"

NEW_ROWS = """Coca-Cola,coca-cola,coca-cola,beverages,US,Flagship brand
Coca-Cola,fanta,fanta,beverages,US,Flavored carbonated drinks
Coca-Cola,sprite,sprite,beverages,US,Lemon-lime carbonated drink
Coca-Cola,minute maid,minute maid,beverages,US,Juice brand
Coca-Cola,schweppes,schweppes,beverages,GB,Tonic and mixers — Coca-Cola in most markets
Coca-Cola,powerade,powerade,beverages,US,Sports drink brand
Coca-Cola,vitaminwater,vitaminwater,beverages,US,Flavored water brand
Coca-Cola,simply,simply,beverages,US,Simply Orange juice range
Coca-Cola,innocent,innocent,beverages,GB,Smoothies and juices — Coca-Cola owned
PepsiCo,pepsi,pepsi,beverages,US,Core PepsiCo beverage brand
PepsiCo,walkers,walkers,snacks,GB,UK crisps — PepsiCo (Lay's equivalent)
PepsiCo,mountain dew,mountain dew,beverages,US,Citrus carbonated drink
PepsiCo,doritos,doritos,snacks,US,Tortilla chips — Frito-Lay (PepsiCo)
PepsiCo,gatorade,gatorade,beverages,US,Sports drink brand
General Mills,general mills,general mills,snacks,US,Parent company brand used directly
Mars,mars,mars,snacks,US,Parent company brand used directly
Kraft Heinz,kraft,kraft,snacks,US,Kraft brand
Kraft Heinz,heinz,heinz,snacks,US,Heinz brand
Kraft Heinz,velveeta,velveeta,dairies,US,Processed cheese brand
Nestlé,nestle,nestle,snacks,CH,Canonical brand spelling without accent
Nestlé,nescafe,nescafe,beverages,CH,Nestlé instant coffee brand
Nestlé,maggi,maggi,snacks,CH,Soups sauces and seasonings
Nestlé,buitoni,buitoni,snacks,CH,Pasta and Italian food brand
Nestlé,san pellegrino,san pellegrino,beverages,CH,Sparkling mineral water
Nestlé,perrier,perrier,beverages,CH,Sparkling mineral water
Nestlé,vittel,vittel,beverages,CH,Still mineral water
Danone,danone,danone,dairies,FR,Parent company brand used directly
Danone,evian,evian,beverages,FR,Premium water brand
Danone,volvic,volvic,beverages,FR,Mineral water brand
Ferrero,ferrero,ferrero,snacks,DE,Parent company brand used directly
Ferrero,raffaello,raffaello,snacks,IT,Coconut almond chocolate balls
Ferrero,ferrero rocher,ferrero rocher,snacks,IT,Premium chocolate
Mondelez,trident,trident,snacks,US,Chewing gum brand
The Campbell's Company,campbell's,campbell's,snacks,US,Parent company brand
The Campbell's Company,v8,v8,beverages,US,Vegetable and fruit juice brand
Chobani,chobani,chobani,dairies,US,Parent company brand
Starbucks,starbucks,starbucks,beverages,US,RTD coffee and packaged food products
Tesco,tesco,tesco,snacks,GB,UK retailer own-label
Sainsbury's,sainsbury's,sainsbury's,snacks,GB,UK retailer own-label
Asda,asda,asda,snacks,GB,UK retailer own-label
Marks & Spencer,marks & spencer,marks & spencer,snacks,GB,UK retailer own-label
Marks & Spencer,m&s,m&s,snacks,GB,Marks & Spencer abbreviation
Waitrose,waitrose,waitrose,snacks,GB,John Lewis Partnership own-label
Morrisons,morrisons,morrisons,snacks,GB,UK supermarket own-label
Leclerc,marque repere,marque repere,snacks,FR,Leclerc Repère private label
Leclerc,e.leclerc,e.leclerc,snacks,FR,Leclerc full-name variant
Leclerc,bio village,bio village,snacks,FR,Leclerc organic private label
Leclerc,delisse,delisse,dairies,FR,Leclerc private label
Intermarché,intermarche,intermarche,snacks,FR,Les Mousquetaires
Intermarché,chabrior,chabrior,snacks,FR,Intermarché private label
Intermarché,paturages,paturages,dairies,FR,Intermarché dairy private label
Monoprix,monoprix,monoprix,snacks,FR,French urban retailer
Franprix,franprix,franprix,snacks,FR,French urban convenience retailer
Aldi,aldi,aldi,snacks,DE,German discount retailer
Aldi,milbona,milbona,dairies,DE,Lidl dairy private label
Lidl,sondey,sondey,snacks,DE,Lidl biscuits brand
Lidl,solevita,solevita,beverages,DE,Lidl juice brand
Kroger,kroger,kroger,snacks,US,US largest supermarket chain
Kroger,harris teeter,harris teeter,snacks,US,Kroger subsidiary
Ahold Delhaize,ahold,ahold,snacks,NL,Dutch-US retailer group
Ahold Delhaize,delhaize,delhaize,snacks,BE,Belgian-US retailer
Ahold Delhaize,giant,giant,snacks,NL,Giant Food stores private label
Ahold Delhaize,food lion,food lion,snacks,NL,Food Lion stores private label
Target,market pantry,market pantry,snacks,US,Target private label
Target,target stores,target stores,snacks,US,Target stores brand variant
Walmart / Great Value,great value,great value,snacks,US,Walmart private label brand
Whole Foods / Amazon,whole foods market,whole foods market,snacks,US,US organic specialty retailer
Whole Foods / Amazon,365 everyday value,365 everyday value,snacks,US,Whole Foods private label
H-E-B,h-e-b,h-e-b,snacks,US,Texas family-owned retailer
Hy-Vee,hy-vee,hy-vee,snacks,US,Midwest US employee-owned retailer
Trader Joe's,trader joe's,trader joe's,snacks,US,US specialty retailer
Meijer,meijer,meijer,snacks,US,Midwest US retailer
Wegmans,wegmans,wegmans,snacks,US,US regional retailer
Carrefour,reflets de france,reflets de france,snacks,FR,Carrefour premium regional range
Carrefour,eco+,eco+,snacks,FR,Carrefour economy range
Carrefour,saveurs de nos regions,saveurs de nos regions,snacks,FR,Carrefour regional flavors range
La Vie Claire,la vie claire,la vie claire,snacks,FR,French organic retail chain
Belle France,belle france,belle france,snacks,FR,French retailer own-label
Dia,dia,dia,snacks,ES,Spanish discount retailer
Coop,coop,coop,snacks,CH,Swiss cooperative retailer
Biocoop,biocoop,biocoop,snacks,FR,French organic cooperative
Hema,hema,hema,snacks,NL,Dutch retailer own-label
Netto,netto,netto,snacks,DE,German/Danish discount retailer
Picard,picard,picard,dairies,FR,Independent French frozen food specialist
Barilla,barilla,barilla,snacks,IT,Italian pasta — family-owned
Panzani,lustucru,lustucru,snacks,FR,Panzani subsidiary (Ebro Foods)
Ecotone,bjorg,bjorg,snacks,FR,Ecotone organic brand
Ecotone,bonneterre,bonneterre,snacks,FR,Ecotone organic brand
Thiriet,thiriet,thiriet,snacks,FR,Independent French frozen food delivery
St Michel,st michel,st michel,snacks,FR,Independent French biscuit company
Tropicana,tropicana,tropicana,beverages,US,Now independent brand (PAI Partners)
Wawa,wawa,wawa,snacks,US,US convenience store chain
Andros,bonne maman,bonne maman,snacks,FR,French jam and dessert brand
Léa Nature,jardin bio,jardin bio,snacks,FR,French organic food brand
Perfetti Van Melle,mentos,mentos,snacks,IT,Mints and confectionery
Alnatura,alnatura,alnatura,snacks,DE,German organic food retailer and brand
Ocean Spray,ocean spray,ocean spray,beverages,US,Cranberry growers cooperative
Arizona Beverages,arizona,arizona,beverages,US,US independent RTD tea brand
Giant Eagle,giant eagle,giant eagle,snacks,US,US independent retailer
Sheetz,sheetz,sheetz,snacks,US,US convenience store chain
Wakefern / ShopRite,shoprite,shoprite,snacks,US,US cooperative supermarket chain
Priméal,primeal,primeal,snacks,FR,French organic food specialist
Tipiak,tipiak,tipiak,snacks,FR,French food company
Moulin des Moines,moulin des moines,moulin des moines,cereals,FR,Independent French flour and grain mill
Yum! Brands,taco bell,taco bell,snacks,US,Restaurant brand retail products
Red Robin,red robin,red robin,snacks,US,Restaurant brand retail products
White Castle,white castle,white castle,snacks,US,Restaurant brand retail products
Associated Wholesale Grocers,food club,food club,snacks,US,AWG cooperative private label
Papa John's,papa john's,papa john's,snacks,US,Restaurant brand retail products
Sonic,sonic,sonic,beverages,US,Restaurant brand retail products
TGI Friday's,tgi friday's,tgi friday's,snacks,US,Restaurant brand retail products
Firehouse Subs,firehouse subs,firehouse subs,snacks,US,Restaurant brand retail products
"""

# Read existing content and get mapped primary_brand_db values
import csv
existing = set()
with open(TARGET, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        existing.add(row.get("primary_brand_db", "").strip().lower())

# Append only rows not already in the file
added = 0
with open(TARGET, "a", encoding="utf-8", newline="") as f:
    for line in NEW_ROWS.strip().splitlines():
        parts = line.split(",")
        if len(parts) >= 3:
            brand_db = parts[2].strip().lower()
            if brand_db not in existing:
                f.write("\n" + line)
                existing.add(brand_db)
                added += 1

print(f"Added {added} new rows to {TARGET.name}")
print(f"Skipped rows already in file: {len(NEW_ROWS.strip().splitlines()) - added}")
