#!/usr/bin/env python3
"""
Portugal & Spain — Moorish Architecture Tour — Interactive Map
August 6–20, 2026

Built on the same framework as iceland_interactive_map.py:
  - Leaflet/Folium map with color-coded, toggleable layers
  - Rich marker popups with notes + official booking links + Google Maps
  - A full "Itinerary" agenda view (filter chips, skip toggles, delay tracking)
  - August climate-normal panels (matching the itinerary's heat outlook)

Requires: pip install folium polyline requests
Usage:    python3 spain_interactive_map.py
Output:   spain.html
"""

import folium
from folium import FeatureGroup, Marker, PolyLine, Popup, Icon, LayerControl
from folium.plugins import LocateControl
import polyline as pl_lib
import requests, json, time, os, hashlib

MAP_CENTER = [40.0, -5.6]
ZOOM_START = 6
VALHALLA_URL = "https://valhalla1.openstreetmap.de/route"
ROUTE_CACHE = "spain_route_cache.json"

# ─── Regions (map layers + colours) ───────────────────────────────────────
# Sub-cities (Sintra/Cordoba/Toledo/Transit) fold into a base region.
REGION_OF = {
    "Porto": "Porto", "Lisbon": "Lisbon", "Sintra": "Lisbon",
    "Seville": "Seville", "Cordoba": "Seville",
    "Granada": "Granada", "Madrid": "Madrid", "Toledo": "Madrid",
    "Transit": "Transit",
}
REGION_COLORS = {
    "Porto": "#2A9D8F", "Lisbon": "#457B9D", "Seville": "#E63946",
    "Granada": "#D4A017", "Madrid": "#7B2D8E", "Transit": "#6c757d",
}
REGION_MARKER = {  # Leaflet.awesome-markers palette
    "Porto": "cadetblue", "Lisbon": "blue", "Seville": "red",
    "Granada": "orange", "Madrid": "purple", "Transit": "gray",
}
REGION_ORDER = ["Porto", "Lisbon", "Seville", "Granada", "Madrid", "Transit"]

def region(city):
    return REGION_OF.get(city, "Madrid")
def rcolor(city):
    return REGION_COLORS[region(city)]

# ─── Days ──────────────────────────────────────────────────────────────────
DAY_DATES = {d: f"2026-08-{5+d:02d}" for d in range(1, 16)}  # 1→08/06 … 15→08/20
DAY_CITY = {1:"Transit",2:"Porto",3:"Porto",4:"Lisbon",5:"Sintra",6:"Lisbon",
            7:"Seville",8:"Seville",9:"Cordoba",10:"Granada",11:"Granada",
            12:"Madrid",13:"Toledo",14:"Madrid",15:"Transit"}
DAY_LABELS = {
    1:"Day 1 — Thu Aug 6: Depart Washington",
    2:"Day 2 — Fri Aug 7: Arrive Porto → Ribeira",
    3:"Day 3 — Sat Aug 8: Porto + port lodges",
    4:"Day 4 — Sun Aug 9: Train to Lisbon → Alfama",
    5:"Day 5 — Mon Aug 10: Sintra day trip",
    6:"Day 6 — Tue Aug 11: Belém + azulejos",
    7:"Day 7 — Wed Aug 12: Fly to Seville · Eclipse",
    8:"Day 8 — Thu Aug 13: Seville's Moorish core",
    9:"Day 9 — Fri Aug 14: Cordoba day trip",
    10:"Day 10 — Sat Aug 15: Train to Granada → Albaicín",
    11:"Day 11 — Sun Aug 16: THE ALHAMBRA",
    12:"Day 12 — Mon Aug 17: Train to Madrid",
    13:"Day 13 — Tue Aug 18: Toledo day trip",
    14:"Day 14 — Wed Aug 19: Madrid full day + farewell",
    15:"Day 15 — Thu Aug 20: Fly home",
}

# ─── Per-day route in Google Maps (🗺 links straight from the itinerary) ────
DAY_MAP = {
 2:"https://www.google.com/maps/dir/?api=1&origin=Porto%20Airport%20OPO&destination=Adega%20Sao%20Nicolau%2C%20Porto&waypoints=Sheraton%20Porto%20Hotel%20%26%20Spa%2C%20Porto%7CRibeira%2C%20Porto%7CPonte%20Luis%20I%2C%20Porto&travelmode=driving",
 3:"https://www.google.com/maps/dir/?api=1&origin=Sheraton%20Porto%20Hotel%20%26%20Spa%2C%20Porto&destination=O%20Valentim%2C%20Matosinhos&waypoints=Livraria%20Lello%2C%20Porto%7CSao%20Bento%20Station%2C%20Porto%7CPalacio%20da%20Bolsa%2C%20Porto%7CMercado%20do%20Bolhao%2C%20Porto%7CGraham%27s%20Port%20Lodge%2C%20Vila%20Nova%20de%20Gaia&travelmode=walking",
 4:"https://www.google.com/maps/dir/?api=1&origin=Lisboa%20Santa%20Apolonia%20Station&destination=Taberna%20Sal%20Grosso%2C%20Lisbon&waypoints=HF%20Fenix%20Urban%2C%20Lisbon%7CMiradouro%20de%20Santa%20Luzia%2C%20Lisbon%7CMuseu%20do%20Aljube%2C%20Lisbon%7CCastelo%20de%20Sao%20Jorge%2C%20Lisbon&travelmode=driving",
 5:"https://www.google.com/maps/dir/?api=1&origin=Rossio%20Railway%20Station%2C%20Lisbon&destination=Tascantiga%2C%20Sintra&waypoints=Sintra%20Station%7CCastelo%20dos%20Mouros%2C%20Sintra%7CPalacio%20Nacional%20da%20Pena%2C%20Sintra&travelmode=transit",
 6:"https://www.google.com/maps/dir/?api=1&origin=HF%20Fenix%20Urban%2C%20Lisbon&destination=Time%20Out%20Market%2C%20Lisbon&waypoints=Mosteiro%20dos%20Jeronimos%2C%20Lisbon%7CPasteis%20de%20Belem%2C%20Lisbon%7CEmbaixada%2C%20Principe%20Real%2C%20Lisbon%7CA%20Vida%20Portuguesa%2C%20Rua%20Anchieta%2C%20Lisbon%7CLargo%20do%20Carmo%2C%20Lisbon&travelmode=driving",
 7:"https://www.google.com/maps/dir/?api=1&origin=Seville%20Airport&destination=Bodega%20Santa%20Cruz%20Las%20Columnas%2C%20Seville&waypoints=Prado%20de%20San%20Sebastian%2C%20Seville%7CHotel%20Giralda%20Center%2C%20Seville%7CBarrio%20Santa%20Cruz%2C%20Seville&travelmode=driving",
 8:"https://www.google.com/maps/dir/?api=1&origin=Hotel%20Giralda%20Center%2C%20Seville&destination=Plaza%20de%20Espana%2C%20Seville&waypoints=Real%20Alcazar%2C%20Seville%7CCatedral%20de%20Sevilla%7CEl%20Rinconcillo%2C%20Seville%7CCasa%20de%20Pilatos%2C%20Seville%7CSetas%20de%20Sevilla&travelmode=walking",
 9:"https://www.google.com/maps/dir/?api=1&origin=Cordoba%20Railway%20Station&destination=Palacio%20de%20Viana%2C%20Cordoba&waypoints=Mezquita-Catedral%20de%20Cordoba%7CBar%20Santos%2C%20Cordoba%7CAlcazar%20de%20los%20Reyes%20Cristianos%2C%20Cordoba%7CPuente%20Romano%20de%20Cordoba&travelmode=walking",
 10:"https://www.google.com/maps/dir/?api=1&origin=Granada%20Railway%20Station&destination=Los%20Diamantes%2C%20Calle%20Navas%2C%20Granada&waypoints=Melia%20Granada%7CPlaza%20Nueva%2C%20Granada%7CMirador%20de%20San%20Nicolas%2C%20Granada&travelmode=driving",
 11:"https://www.google.com/maps/dir/?api=1&origin=Melia%20Granada&destination=Casa%20Juanillo%2C%20Sacromonte%2C%20Granada&waypoints=Alhambra%2C%20Granada%7CCapilla%20Real%20de%20Granada%7CCentro%20Federico%20Garcia%20Lorca%2C%20Granada&travelmode=walking",
 12:"https://www.google.com/maps/dir/?api=1&origin=Madrid%20Atocha%20Station&destination=Taberna%20El%20Sur%2C%20Madrid&waypoints=Calle%20de%20Felipe%20III%206%2C%20Madrid%7CPalacio%20Real%20de%20Madrid%7CMuseo%20Cerralbo%2C%20Madrid%7CMercado%20de%20San%20Miguel%2C%20Madrid%7CLa%20Latina%2C%20Madrid&travelmode=walking",
 13:"https://www.google.com/maps/dir/?api=1&origin=Toledo%20Railway%20Station&destination=Catedral%20de%20Toledo&waypoints=Mezquita%20del%20Cristo%20de%20la%20Luz%2C%20Toledo%7CBar%20Ludena%2C%20Toledo%7CSanta%20Maria%20la%20Blanca%2C%20Toledo%7CSinagoga%20del%20Transito%2C%20Toledo%7CIglesia%20de%20Santo%20Tome%2C%20Toledo&travelmode=walking",
 14:"https://www.google.com/maps/dir/?api=1&origin=Calle%20de%20Felipe%20III%206%2C%20Madrid&destination=Templo%20de%20Debod%2C%20Madrid&waypoints=Museo%20Reina%20Sofia%2C%20Madrid%7CCuesta%20de%20Moyano%2C%20Madrid%7CMuralla%20Arabe%2C%20Madrid%7CCasa%20Revuelta%2C%20Madrid%7CChocolateria%20San%20Gines%2C%20Madrid%7CCasa%20Hernanz%2C%20Madrid&travelmode=walking",
 15:"https://www.google.com/maps/dir/?api=1&origin=Calle%20de%20Felipe%20III%206%2C%20Madrid&destination=Adolfo%20Suarez%20Madrid-Barajas%20Airport&travelmode=driving",
}

# ─── August climate normals (from the itinerary heat outlook, NOT a forecast) ─
CLIMATE = {
 "Porto":  {"hi":"77°F / 25°C","lo":"61°F / 16°C","pat":"Mild, Atlantic breeze, possible AM fog","emoji":"🌤","warn":0},
 "Lisbon": {"hi":"83°F / 28°C","lo":"64°F / 18°C","pat":"Sunny, breezy and dry","emoji":"☀️","warn":0},
 "Sintra": {"hi":"75°F / 24°C","lo":"62°F / 17°C","pat":"Cooler hilltop, misty mornings","emoji":"🌤","warn":0},
 "Seville":{"hi":"97–102°F / 36–39°C","lo":"68°F / 20°C","pat":"Extreme dry heat; 104°F+ days routine","emoji":"🔥","warn":1},
 "Cordoba":{"hi":"100°F / 38°C","lo":"70°F / 21°C","pat":"Spain's hottest city — mornings only","emoji":"🔥","warn":1},
 "Granada":{"hi":"94°F / 34°C","lo":"63°F / 17°C","pat":"Very hot days, cooler nights (680 m)","emoji":"☀️","warn":1},
 "Madrid": {"hi":"92°F / 33°C","lo":"66°F / 19°C","pat":"Hot, dry, big daily swing","emoji":"☀️","warn":1},
 "Toledo": {"hi":"94°F / 34°C","lo":"66°F / 19°C","pat":"Hot, exposed stone streets","emoji":"☀️","warn":1},
 "Transit":{"hi":"—","lo":"—","pat":"Travel day","emoji":"✈️","warn":0},
}

# ─── Guides / weather links per region (shown in popups) ────────────────────
CITY_GUIDE = {
 "Porto":"https://visitporto.travel/en-GB/","Lisbon":"https://www.visitlisboa.com/en",
 "Sintra":"https://www.parquesdesintra.pt/en/","Seville":"https://visitasevilla.es/en",
 "Cordoba":"https://www.turismodecordoba.org/en","Granada":"https://www.granadatur.com/en/",
 "Madrid":"https://www.esmadrid.com/en","Toledo":"https://toledomonumental.com","Transit":None,
}

# ─── Live weather (Open-Meteo) — same engine as the Iceland map ─────────────
# Forecasts only reach ~16 days out, so live data appears as the trip nears;
# until then (and if the fetch fails) each stop falls back to the climate panel.
WEATHER_CACHE = "spain_weather_cache.json"
CACHE_MAX_AGE_HOURS = 1
WX_COORD = {
 "Porto":(41.15,-8.61),"Lisbon":(38.72,-9.14),"Sintra":(38.79,-9.39),
 "Seville":(37.38,-5.99),"Cordoba":(37.88,-4.78),"Granada":(37.17,-3.60),
 "Madrid":(40.41,-3.70),"Toledo":(39.86,-4.02),
}
WX_TZ = {  # Portugal is WEST (UTC+1) in August, Spain is CEST (UTC+2)
 "Porto":"Europe/Lisbon","Lisbon":"Europe/Lisbon","Sintra":"Europe/Lisbon",
 "Seville":"Europe/Madrid","Cordoba":"Europe/Madrid","Granada":"Europe/Madrid",
 "Madrid":"Europe/Madrid","Toledo":"Europe/Madrid",
}
WMO = {
 0:("Clear sky","☀️"),1:("Mainly clear","🌤️"),2:("Partly cloudy","⛅"),3:("Overcast","☁️"),
 45:("Fog","🌫️"),48:("Rime fog","🌫️"),51:("Light drizzle","🌦️"),53:("Drizzle","🌦️"),
 55:("Dense drizzle","🌧️"),61:("Slight rain","🌦️"),63:("Rain","🌧️"),65:("Heavy rain","🌧️"),
 71:("Light snow","🌨️"),73:("Snow","🌨️"),75:("Heavy snow","❄️"),
 80:("Light showers","🌦️"),81:("Showers","🌧️"),82:("Heavy showers","⛈️"),
 95:("Thunderstorm","⛈️"),96:("T-storm + hail","⛈️"),99:("T-storm + heavy hail","⛈️"),
}

def fetch_weather():
    if os.path.exists(WEATHER_CACHE):
        age=time.time()-os.path.getmtime(WEATHER_CACHE)
        if age<CACHE_MAX_AGE_HOURS*3600:
            try:
                data=json.load(open(WEATHER_CACHE))
                print(f"✓ Weather from cache (expires in {int((CACHE_MAX_AGE_HOURS*3600-age)/60)} min).")
                return data
            except Exception: pass
    print("Fetching weather from Open-Meteo…")
    out={}
    for city,(lat,lon) in WX_COORD.items():
        url=(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
             f"&hourly=temperature_2m,apparent_temperature,precipitation,weathercode,windspeed_10m,windgusts_10m"
             f"&daily=sunrise,sunset&forecast_days=16&timezone={WX_TZ[city]}")
        try:
            r=requests.get(url,timeout=15).json()
            if "hourly" in r: out[city]={"hourly":r["hourly"],"daily":r.get("daily",{})}; print(f"  ✓ {city}")
            else: print(f"  – {city}: no hourly data")
        except Exception as e:
            print(f"  ⚠ {city}: {e}")
        time.sleep(0.3)
    try: json.dump(out,open(WEATHER_CACHE,"w"))
    except Exception: pass
    return out

def get_wx(weather, city, day, hour):
    """Return live forecast dict for a city at a given day+hour, or None.
    Guards every value so a null from the API can never crash formatting."""
    if not weather or city not in weather: return None
    h=weather[city].get("hourly")
    if not h or "time" not in h: return None
    t=f"{DAY_DATES[day]}T{hour:02d}:00"
    try: i=h["time"].index(t)
    except ValueError: return None
    def g(k):
        a=h.get(k)
        if not a or i>=len(a): return None
        return a[i]
    tc=g("temperature_2m"); fc=g("apparent_temperature")
    p=g("precipitation"); w=g("windspeed_10m"); gu=g("windgusts_10m"); wc=g("weathercode")
    if tc is None: return None  # no usable live reading → fall back to climate
    desc,emoji=WMO.get(wc,("—","🌡️"))
    def cf(v): return None if v is None else round(v*9/5+32)
    return {"tc":tc,"tf":cf(tc),"fc":fc,"ff":cf(fc),"p":p,"w":w,"g":gu,
            "desc":desc,"emoji":emoji,"hour":hour}

# ═══════════════════════ STOPS ═══════════════════════
# (name, lat, lon, day, type, city, notes, link, hour, dur_min, anchor)
#  type → icon/colour.  🕌 moorish · ✊ history · ⭐ must-see · 📚 books · 🇪🇸 friend tip
S = [
# ---- Day 1: Depart Washington ----
("IAD — Depart Washington ✈️",38.9531,-77.4565,1,"flight","Transit",
 "6:45 PM arrive IAD (3 hrs early). 9:45 PM Delta/Air France, 1 stop → Porto. Sleep on the transatlantic leg — a plane nap is the whole jetlag strategy. Pack a layer; the cabin runs cold.",
 "https://www.delta.com",21,0,True),

# ---- Day 2: Arrive Porto → Ribeira ----
("OPO Airport — Arrive Porto",41.2481,-8.6814,2,"flight","Porto",
 "Land 3:25 PM (Fri Aug 7). To Boavista: Metro Line E (violet) → Casa da Música ~25 min (€2.25 + Andante card) + 8–10 min walk, or taxi/Bolt €20–25. After a red-eye the taxi is worth it.",
 None,15,30,True),
("Sheraton Porto Hotel & Spa 🏨",41.1580,-8.6293,2,"hotel","Porto",
 "🏨 Aug 7–9 (BOOKED, $511.29). Boavista, 2.5 km from Ribeira. Premium Queen listed for 2 — call +351 22 040 4000 to arrange third-person bedding. Real pool + spa after the red-eye.",
 None,17,0,True),
("Ribeira riverfront",41.1408,-8.6110,2,"attraction","Porto",
 "Evening stroll along the Douro. ~5:45 PM from the hotel — taxi ~10 min €8, or metro to São Bento + walk down.",
 None,18,60,False),
("Dom Luís I Bridge 🌄",41.1399,-8.6094,2,"viewpoint","Porto",
 "Walk the upper deck across to Gaia for the classic skyline. 15-min walk up from Ribeira; sunset ~8:50 PM, plenty of light.",
 None,20,45,False),
("Café Santiago (dinner)",41.1487,-8.6060,2,"food","Porto",
 "🍽 Francesinha benchmark, ~€13; expect a short queue. Or book a river-view table in Ribeira. Early night.",
 None,20,60,False),

# ---- Day 3: Porto full day + port lodges ----
("Livraria Lello 📚",41.1470,-8.6146,3,"shop","Porto",
 "📚 9:00 AM timed entry (book ahead; €8 voucher credits toward a book). One of the world's most beautiful bookshops.",
 "https://www.livrarialello.pt",9,45,False),
("Clérigos Tower",41.1456,-8.6142,3,"attraction","Porto",
 "Baroque bell-tower climb, then the São Bento azulejo hall (free) 8-min walk downhill.",
 None,10,45,False),
("São Bento azulejo hall",41.1457,-8.6106,3,"moorish","Porto",
 "🕌 Blue-and-white azulejo tiles — the Portuguese craft that descends directly from Moorish tradition. Free station concourse.",
 None,10,20,False),
("⭐ Palácio da Bolsa (Arab Room)",41.1414,-8.6153,3,"moorish","Porto",
 "🕌⭐ 11:00 AM guided visit (~€12, 45 min): the gilded Arab Room is a 19th-c. neo-Moorish fantasy — a perfect on-theme bonus.",
 "https://palaciodabolsa.com/en/",11,45,False),
("Mercado do Bolhão (lunch)",41.1497,-8.6062,3,"food","Porto",
 "🍽 12:30 PM graze the restored market counters, €8–15.",
 None,12,60,False),
("Rua das Flores 🛍",41.1435,-8.6118,3,"shop","Porto",
 "⭐🛍 Shopping stroll: Claus Porto flagship (heritage soaps/leather) + Portuguese-cotton shops. Scout prices — the bigger haul is Lisbon Day 6.",
 None,14,45,False),
("✊ UNICEPE bookshop",41.1478,-8.6155,3,"history","Porto",
 "✊📚 Porto's student book cooperative, a left-wing institution since 1964, near Praça de Carlos Alberto. 15-min browse. If shut, Livraria Latina fills in.",
 None,15,20,False),
("🍷 Graham's 1890 Port Lodge",41.1360,-8.6210,3,"food","Porto",
 "🍷 4:00 PM guided tour + tasting (reserve, ~€25–45), Vila Nova de Gaia. Everyone's 18+, so it works for all three. Taylor's is the easier self-guided alt.",
 "https://www.grahams-port.com/visit-us",16,90,False),
("O Valentim (dinner, Matosinhos)",41.1830,-8.6960,3,"food","Porto",
 "🍽 Matosinhos grilled-fish row, €15–25. Metro Line A direct from Casa da Música ~20 min. Or the optional 6-Bridges river cruise (~€20) at 6 PM first.",
 None,20,90,False),

# ---- Day 4: Train to Lisbon → Alfama ----
("Porto Campanhã → Lisbon 🚆",41.1490,-8.5850,4,"train","Lisbon",
 "🚆 9:00 AM Alfa Pendular to Lisboa Santa Apolónia, ~3h (book cp.pt, promo from €9.50). Taxi to Campanhã (NOT São Bento) ~12 min. Arrive ~12:30 PM.",
 "https://www.cp.pt/passageiros/en",9,180,True),
("HF Fénix Urban 🏨",38.7267,-9.1500,4,"hotel","Lisbon",
 "🏨 Aug 9–12 (BOOKED, $649.79; refundable before Aug 5). Marquês de Pombal — metro hub on the doorstep, family room with 2 queens sleeps 3. Verify breakfast.",
 None,13,0,True),
("🕌 Alfama + Miradouro de Santa Luzia",38.7118,-9.1300,4,"moorish","Lisbon",
 "🕌 2:00 PM the old Moorish quarter (from Arabic al-hamma) — wander the lanes up to the tiled Santa Luzia terrace.",
 None,14,90,False),
("✊ Museu do Aljube",38.7107,-9.1330,4,"history","Lisbon",
 "✊ 4:00 PM (~€3, 45 min): the Estado Novo's political prison, now a museum of the dictatorship and the resistance — the essential primer before Largo do Carmo on Day 6.",
 None,16,45,False),
("🕌 Castelo de São Jorge",38.7139,-9.1335,4,"moorish","Lisbon",
 "🕌 5:30 PM (book online, ~€15): the Moorish-era citadel, for golden-hour views over the city and river.",
 "https://castelodesaojorge.pt/en/",17,90,False),
("Tasca do Chico (fado + dinner)",38.7113,-9.1447,4,"food","Lisbon",
 "🍽 8:30 PM Alfama/Bairro Alto dinner; for fado, Tasca do Chico (cheap, authentic) or a booked show ~€20–35.",
 None,20,90,False),

# ---- Day 5: Sintra day trip ----
("Rossio → Sintra train 🚆",38.7143,-9.1400,5,"train","Sintra",
 "🚆 8:30 AM train from Rossio (every 20–30 min, Viva Viagem card; no advance booking). Leave the hotel by 8:00. Sintra is Portugal's busiest day trip — the early train matters.",
 None,8,40,True),
("🕌 Castelo dos Mouros, Sintra",38.7925,-9.3888,5,"moorish","Sintra",
 "🕌 9:30 AM the 8th–9th c. Moorish hilltop fortress — Portugal's Moorish highlight. Bus 434 loop from Sintra station ~15 min + short climb.",
 "https://www.parquesdesintra.pt/en/",9,120,False),
("⭐ Pena Palace",38.7877,-9.3906,5,"attraction","Sintra",
 "⭐ 12:00 PM timed entry — book the official Pena + Moorish Castle combo (~€26) 1–2 weeks ahead; August sells out. Grounds rate above the interior if slots are tight.",
 "https://www.parquesdesintra.pt/en/",12,120,False),
("⭐ Quinta da Regaleira (optional)",38.7963,-9.3963,5,"attraction","Sintra",
 "⭐ 2:30 PM optional — the initiation well (~€15). 25-min walk downhill from town or ~€8 tuk-tuk from Pena.",
 None,14,90,False),
("Bairro Alto (evening)",38.7118,-9.1447,5,"food","Lisbon",
 "🍽 ~5 PM train back (~40 min). Bairro Alto is a 10-min uphill walk from Rossio or one Glória funicular ride; sunset drinks + dinner (Bonjardim piri-piri, Tasca do Manel).",
 None,19,90,False),

# ---- Day 6: Belém + azulejos ----
("⭐🕌 Jerónimos Monastery, Belém",38.6979,-9.2065,6,"moorish","Lisbon",
 "⭐ 9:30 AM at opening (book ahead, ~€18). Manueline masterpiece; then Belém Tower exterior and the original pastéis de Belém next door.",
 None,9,120,False),
("Pastéis de Belém",38.6975,-9.2032,6,"food","Lisbon",
 "🍽 The original custard tarts, since 1837 — €2–5 snack beside the monastery.",
 None,11,30,False),
("⭐ Oceanário de Lisboa",38.7634,-9.0938,6,"attraction","Lisbon",
 "⭐ 1:00 PM choose one: Oceanário (one of the world's best aquariums, ~€25, A/C, a guaranteed hit)…",
 "https://www.oceanario.pt/en",13,120,False),
("🕌 National Tile Museum (Azulejo)",38.7247,-9.1136,6,"moorish","Lisbon",
 "🕌 …or the Museu do Azulejo — the tile tradition is a direct Moorish inheritance, also A/C. (Alternative to the Oceanário.)",
 None,13,120,False),
("⭐ Tram 28 / Ler Devagar 📚",38.7159,-9.1338,6,"attraction","Lisbon",
 "⭐ 4:00 PM ride tram 28 end-to-end through Graça/Alfama (board mid-afternoon to dodge pickpocket crowds) — or LX Factory + 📚 Ler Devagar, the bookshop in a former print works.",
 None,16,60,False),
("⭐🛍 Embaixada (Príncipe Real)",38.7169,-9.1487,6,"shop","Lisbon",
 "⭐🛍 5:30 PM Portuguese cotton/linen/leather run — Embaixada (Portuguese designers in a Neo-Moorish palace 🕌), then A Vida Portuguesa in Chiado. Ask every shop for the tax-free form.",
 None,17,60,False),
("✊ Largo do Carmo",38.7118,-9.1401,6,"history","Lisbon",
 "✊ 7:15 PM the square where the Carnation Revolution ended on 25 April 1974 — the regime surrendered here while soldiers carried carnations in their rifles. The ruined Carmo Convent above is Lisbon's most atmospheric shell.",
 None,19,20,False),
("Time Out Market (dinner)",38.7071,-9.1459,6,"food","Lisbon",
 "🍽 8:00 PM Time Out Market or Cais do Sodré. Pack for the early flight; check in online.",
 None,20,90,False),

# ---- Day 7: Lisbon AM → fly to Seville → Eclipse ----
("⭐ Calouste Gulbenkian Museum",38.7376,-9.1537,7,"museum","Lisbon",
 "⭐ 10:00 AM (~€14, 10-min walk) — one of Europe's great private collections, Egyptian to Lalique, with a strong Islamic-art room 🕌. A/C, in gardens. Open Wednesdays.",
 "https://gulbenkian.pt/museu/en/",10,150,False),
("LIS → Seville ✈️ (Ryanair FR3628)",38.7742,-9.1342,7,"flight","Seville",
 "✈️ 2:50 PM taxi to LIS. FR3628 departs 5:20 PM, 1h05 nonstop → land SVQ 7:25 PM (Spain +1h). Priority + 2 cabin + 3×10 kg checked bags already paid. Check the boarding pass for T2.",
 "https://www.ryanair.com",17,120,True),
("🌘 Solar eclipse — SVQ arrival",37.4180,-5.8931,7,"eclipse","Seville",
 "🌘 ECLIPSE DAY. Partial begins ~7:30 PM as you walk off the plane; maximum ~8:30 PM (~85–90% covered), the Sun 8–10° above the western horizon. Watch max from arrivals with a clear WESTERN view. Bring 3 pairs of ISO 12312-2 glasses from the US — sold out across Spain. Verify minutes at timeanddate.com/eclipse.",
 "https://www.timeanddate.com/eclipse/",20,60,False),
("Hotel Giralda Center 🏨",37.3833,-5.9822,7,"hotel","Seville",
 "🏨 Aug 12–15 (BOOKED, $516.60). San Bernardo — 1 double + 2 twins + sofa bed, the room genuinely built for 3. Rooftop pool. To hotel: Tussam EA bus €4 + walk, or taxi €25.",
 None,21,0,True),
("Barrio Santa Cruz — late tapas",37.3855,-5.9905,7,"food","Seville",
 "🍽 9:45 PM Santa Cruz lanes by night + rooftop drink with Giralda view (La Terraza de EME). 10:15 PM late tapas — Spanish dinner time from night one.",
 None,22,90,False),

# ---- Day 8: Seville's Moorish core ----
("🕌 Real Alcázar",37.3830,-5.9906,8,"moorish","Seville",
 "🕌 9:30 AM at opening — Spain's finest Mudéjar palace. Book the earliest slot 2+ weeks ahead on the OFFICIAL site (€15.50; resellers charge 2–3×). Allow 2.5h; add Cuarto Real Alto if offered.",
 "https://realalcazarsevilla.sacatuentrada.es/en",9,150,False),
("🕌 Cathedral + Giralda",37.3859,-5.9932,8,"moorish","Seville",
 "🕌 12:30 PM (~€13 timed) — climb the 12th-c. Almohad minaret; ramps, not stairs, built for a horse.",
 "https://www.catedraldesevilla.es",12,90,False),
("Siesta / pool 🏊",37.3833,-5.9822,8,"hotel","Seville",
 "☀️ 2:00–6:00 PM long lunch, siesta, pool. Heat protocol: sights 8:30–12:00, rest 14:00–18:00, back out after 19:00.",
 None,14,0,True),
("⭐🕌 Casa de Pilatos",37.3906,-5.9878,8,"moorish","Seville",
 "⭐🕌 6:30 PM (~€12) — Mudéjar-Renaissance mansion, gorgeous and nearly empty late-day. Or ⭐ Setas de Sevilla rooftop at sunset (~€15).",
 None,18,75,False),
("⭐ Plaza de España",37.3775,-5.9868,8,"attraction","Seville",
 "⭐ 8:30 PM in golden light (free), your closest big sight. Then optional Triana flamenco — Teatro Flamenco Triana or Casa de la Guitarra, €20–30.",
 None,20,60,False),

# ---- Day 9: Cordoba day trip ----
("Seville → Cordoba 🚆",37.3919,-5.9757,9,"train","Cordoba",
 "🚆 8:00 AM AVE to Cordoba, 45 min (book RT on renfe.com, €15–22 each way). Cordoba is routinely Spain's hottest city (38–41°C) — morning only, be on a train back by mid-afternoon.",
 "https://www.renfe.com/es/en",8,45,True),
("🕌 Mezquita-Catedral, Cordoba",37.8790,-4.7794,9,"moorish","Cordoba",
 "🕌 9:00 AM first slots (€13) — the great mosque's forest of red-and-white arches, 8th–10th c. Allow 2h. 25-min walk from the station or €8 taxi.",
 "https://mezquita-catedraldecordoba.es/en/",9,120,False),
("Alcázar + Judería + Roman bridge",37.8765,-4.7817,9,"attraction","Cordoba",
 "11:00 AM Alcázar de los Reyes Cristianos, the Roman bridge, and the Judería patios.",
 None,11,60,False),
("⭐ Palacio de Viana (patios)",37.8890,-4.7745,9,"attraction","Cordoba",
 "⭐ If patios are your thing, Palacio de Viana (12 courtyards, ~€14) is the connoisseur stop.",
 None,12,60,False),
("Taberna Salinas (lunch)",37.8846,-4.7772,9,"food","Cordoba",
 "🍽 1:30 PM old-town lunch — salmorejo + flamenquín. Taberna Salinas (patio taberna since 1879) or Bar Santos' giant tortilla slice by the Mezquita. Train back ~3:30 PM; easy Triana / Calle Betis evening in Seville.",
 None,13,60,False),

# ---- Day 10: Train to Granada → Albaicín ----
("Seville → Granada 🚆",37.3919,-5.9757,10,"train","Granada",
 "🚆 Morning Renfe direct, 2.5–3h (first ~07:40). ⚠️ Aug 15 is Assumption Day — book the moment Renfe opens sales. Arrive ~1:00 PM.",
 "https://www.renfe.com/es/en",8,180,True),
("Meliá Granada 🏨",37.1735,-3.5990,10,"hotel","Granada",
 "🏨 Aug 15–17 (BOOKED, $438.50). Puerta Real — most central base of the trip. Premium Double booked for 3 — call +34 958 22 74 00 to add a bed. 15-min walk to Plaza Nueva. 1:30–6 PM check in, lunch, rest through the heat.",
 None,13,0,True),
("🕌 Albaicín → Mirador de San Nicolás 🌄",37.1809,-3.5924,10,"moorish","Granada",
 "🕌 7:00 PM the old Moorish quarter (UNESCO) up to the Mirador de San Nicolás: sunset over the Alhambra with the Sierra Nevada behind — the single best free view of the trip. 20–25 min uphill walk or C31/C32 minibus.",
 None,19,90,False),
("Calle Navas — free-tapas crawl",37.1740,-3.5975,10,"food","Granada",
 "🍽 9:00 PM free-tapas crawl on Calle Navas or Plaza Nueva — in Granada a ~€3 drink still buys a tapa. Bodegas Castañeda, Los Diamantes, Bar Poë.",
 None,21,90,False),

# ---- Day 11: The Alhambra ----
("🕌 THE ALHAMBRA + Generalife",37.1760,-3.5881,11,"moorish","Granada",
 "🕌 8:00 AM (BOOKED, non-changeable). ⚠️ Be at the Nasrid Palaces gate 30 min before the printed slot — a missed window is forfeited. Passports scanned; screenshot the QR codes. Full circuit 3.5–4h: Nasrid Palaces → Alcazaba → Partal → Generalife. Stone stays cool until ~10 AM.",
 "https://tickets.alhambra-patronato.es/en/",8,240,False),
("Rest / pool 🏊",37.1735,-3.5990,11,"hotel","Granada",
 "☀️ 1:00–5:00 PM lunch, rest, pool. Los Manueles (famous croquetas) 5 min from the hotel.",
 None,13,0,True),
("⭐ Royal Chapel + Cathedral",37.1765,-3.5985,11,"attraction","Granada",
 "⭐ 5:00 PM (~€13; verify Sunday hours) — the tombs of Ferdinand and Isabella, the Reconquista's endpoint: the perfect counterweight to the morning. Or 🛁 Hammam Al Ándalus Arab baths (€45–75, book ahead).",
 "https://granada.hammamalandalus.com/en/",17,60,False),
("✊ Centro Federico García Lorca",37.1760,-3.6000,11,"history","Granada",
 "✊ Lorca — Spain's great leftist literary martyr — was executed by Francoist forces outside Granada in August 1936. His centre (often free); his summer house Huerta de San Vicente sits in a park 15 min south for the fuller pilgrimage.",
 None,17,45,False),
("Sacromonte — carmen dinner 🌄",37.1830,-3.5870,11,"food","Granada",
 "🍽 8:30 PM Sacromonte cave district; dinner at a carmen with Alhambra views — Carmen Mirador de Aixa or Casa Juanillo (in-budget). Reserve. Perseids peak this week under a new Moon — the trip's darkest skies.",
 None,20,120,False),

# ---- Day 12: Train to Madrid ----
("Granada → Madrid 🚆",37.1918,-3.6089,12,"train","Madrid",
 "🚆 AVE direct ~3h20 (first ~06:56). ⚠️ Check the ARRIVAL STATION — some services arrive Atocha, others Chamartín. Renfe-only route; book early. Arrive ~1:30 PM.",
 "https://www.renfe.com/es/en",10,200,True),
("Airbnb — Plaza Mayor 🏨",40.4155,-3.7075,12,"hotel","Madrid",
 "🏨 Aug 17–20 (BOOKED, $651.36 paid). Calle de Felipe III 6, directly on Plaza Mayor. Doorstep: Mercado de San Miguel 2 min, Botín 2 min, Casa Hernanz 3 min, Sol 4 min, Royal Palace 10 min. Save door codes offline; pack earplugs.",
 None,14,0,True),
("Royal Palace + Campo del Moro",40.4180,-3.7143,12,"attraction","Madrid",
 "4:00 PM Royal Palace (10-min walk). 🇪🇸 Friends say approach from below via Campo del Moro / Cuesta de la Vega (where Day 14's Muralla Árabe sits) — flat frontal view has 'no depth'. Alt: Prado free window 18:00–20:00.",
 None,16,90,False),
("La Latina → Mercado de San Miguel",40.4154,-3.7090,12,"food","Madrid",
 "🍽 8:30 PM La Latina tapas crawl → Plaza Mayor → Mercado de San Miguel (2 min from your door). 🇪🇸 Friend alt in Lavapiés: Taberna El Sur, near ✊ Traficantes de Sueños left bookshop.",
 None,20,120,False),

# ---- Day 13: Toledo day trip ----
("Madrid Atocha → Toledo 🚆",40.4067,-3.6906,13,"train","Toledo",
 "🚆 9:00 AM Avant from Atocha, 33 min (renfe.com, ~€14 RT, fixed fares). ⚠️ Atocha has airport-style security — arrive 15–20 min early. Toledo station sits below the old town: bus L61/L62 up, walk down.",
 "https://www.renfe.com/es/en",9,33,True),
("🕌 Mezquita del Cristo de la Luz",39.8607,-4.0247,13,"moorish","Toledo",
 "🕌 10:00 AM a mosque of 999 AD. Part of the Moorish/Mudéjar circuit with the Puerta del Sol gate. The €12 tourist wristband (toledomonumental.com) covers seven monuments.",
 "https://toledomonumental.com",10,45,False),
("🕌 Santa María la Blanca + El Tránsito",39.8563,-4.0296,13,"moorish","Toledo",
 "🕌 Mudéjar-built synagogues — Santa María la Blanca and the Sinagoga del Tránsito. The three-faith heart of medieval Toledo.",
 None,11,60,False),
("Bar Ludeña (lunch)",39.8578,-4.0237,13,"food","Toledo",
 "🍽 1:30 PM carcamusas or venison stew; Toledo marzipan for dessert. Bar Ludeña is THE carcamusas stop, €12–15.",
 None,13,60,False),
("⭐ Santo Tomé (El Greco) + Cathedral",39.8574,-4.0283,13,"attraction","Toledo",
 "⭐ 3:30 PM Santo Tomé (~€4): El Greco's Burial of the Count of Orgaz — one canvas, ten minutes, unmissable. Then the Cathedral (~€10–12) if energy allows. Golden-hour old town after the ~17:00 crowds leave; ~19:00 train back.",
 None,15,90,False),

# ---- Day 14: Madrid full day + farewell ----
("✊ Reina Sofía (Guernica)",40.4079,-3.6947,14,"museum","Madrid",
 "✊ 10:00 AM (€12) — built around Picasso's Guernica, the century's great anti-fascist painting. 🇪🇸 One friend rates it over the Prado; the Prado's Monday free window already covered that.",
 "https://www.museoreinasofia.es/en",10,105,False),
("📚 Cuesta de Moyano book stalls",40.4103,-3.6890,14,"history","Madrid",
 "📚 11:45 AM open-air secondhand book stalls (since 1925) on the rise between Atocha and Retiro — Madrid's classic radical-and-rare browse, 20 min, en route to the Muralla.",
 None,11,20,False),
("🕌 Muralla Árabe",40.4150,-3.7135,14,"moorish","Madrid",
 "🕌 12:30 PM the 9th-c. Arab wall below Almudena Cathedral, from Madrid's founding as Moorish Mayrit (free). 🇪🇸 From this low angle the cathedral finally shows real depth — the below-the-parks approach the friends recommend.",
 None,12,45,False),
("⭐ San Ginés churros",40.4165,-3.7065,14,"food","Madrid",
 "🍽⭐ 2:00 PM long lunch; San Ginés churros con chocolate (since 1894) for dessert, 12-min walk up Calle Mayor. Casa Revuelta (fried bacalao) 2 min from the Airbnb.",
 None,14,90,False),
("⭐🛍 Casa Hernanz → Gran Vía shops",40.4130,-3.7080,14,"shop","Madrid",
 "⭐🛍 4:30 PM Casa Hernanz (handmade espadrilles since 1845, from ~€15), then Gran Vía → Calle Fuencarral/Chueca for Spanish brands, or Calle de Serrano for leather (Loewe, Camper). Collect tax-free forms; refund at MAD DIVA kiosks tomorrow.",
 None,16,120,False),
("⭐ Templo de Debod (sunset) 🌄",40.4240,-3.7176,14,"attraction","Madrid",
 "⭐ 8:45 PM an actual 2nd-c. BC Egyptian temple — Madrid's best sunset spot, free, ~25 min on foot from the Airbnb and worth every step at dusk.",
 None,20,45,False),
("Botín — farewell dinner",40.4147,-3.7085,14,"food","Madrid",
 "🍽 9:30 PM farewell dinner (book ahead): Botín, the world's oldest restaurant — cochinillo ~€45–50 pp, the one splurge — now around the corner from your door. In-budget fallback: La Sanabresa, menú ~€15. Pack; pre-book tomorrow's taxi.",
 None,21,120,False),

# ---- Day 15: Fly home ----
("Free Madrid morning",40.4155,-3.7075,15,"attraction","Madrid",
 "☕ Plaza Mayor at 9 AM is empty and beautiful — coffee on the square, San Ginés churros 3 min away, pack up. The 2:35 PM departure leaves room for it.",
 None,9,90,True),
("MAD → DCA ✈️ (depart 2:35 PM)",40.4936,-3.5668,15,"flight","Transit",
 "✈️ 11:00 AM taxi to MAD (flat €33, ~30 min) — arrive ~11:35, 3 hrs before departure. Claim VAT refunds at the DIVA kiosks airside (Spain has no minimum spend). KLM/Delta 2:35 PM → connect Boston → land DCA 10:05 PM EDT. You land at DCA, not IAD.",
 "https://www.delta.com",11,0,True),
]

# ═══════════════════════ INTERCITY LEGS (route polylines) ═══════════════════
LEGS = [
 {"name":"Porto → Lisbon","mode":"train","day":4,"note":"Alfa Pendular · ~3h · cp.pt",
  "a":(41.1490,-8.5850),"b":(38.7139,-9.1224)},
 {"name":"Lisbon → Seville","mode":"flight","day":7,"note":"Ryanair FR3628 · 1h05",
  "a":(38.7742,-9.1342),"b":(37.4180,-5.8931)},
 {"name":"Seville ⇄ Cordoba","mode":"train","day":9,"note":"AVE/Avant · 45 min · renfe.com",
  "a":(37.3919,-5.9757),"b":(37.8918,-4.7908)},
 {"name":"Seville → Granada","mode":"train","day":10,"note":"Renfe direct · 2.5–3h",
  "a":(37.3919,-5.9757),"b":(37.1918,-3.6089)},
 {"name":"Granada → Madrid","mode":"train","day":12,"note":"AVE · ~3h20 · Renfe-only",
  "a":(37.1918,-3.6089),"b":(40.4067,-3.6906)},
 {"name":"Madrid ⇄ Toledo","mode":"train","day":13,"note":"Avant · 33 min · fixed fares",
  "a":(40.4067,-3.6906),"b":(39.8628,-4.0273)},
]

# ─── Transport modes: colour + line style + routing engine per mode ─────────
# walk/taxi/bus follow real streets (Valhalla/OSM, cached); metro/tram/train/
# flight run on rails or air, so they are drawn as clean direct hops.
MODE_STYLE = {
 "walk":  {"color":"#2E9B57","dash":"1 7","w":3,"label":"🚶 Walk","costing":"pedestrian"},
 "taxi":  {"color":"#E8952F","dash":None, "w":4,"label":"🚕 Taxi","costing":"auto"},
 "bus":   {"color":"#159C97","dash":None, "w":4,"label":"🚌 Bus","costing":"bus"},
 "metro": {"color":"#2D5BD0","dash":"7 6","w":4,"label":"🚇 Metro","costing":None},
 "tram":  {"color":"#8E44AD","dash":"7 6","w":4,"label":"🚊 Tram","costing":None},
 "train": {"color":"#C0392B","dash":None, "w":4,"label":"🚆 Train","costing":None},
 "flight":{"color":"#6C757D","dash":"10 8","w":4,"label":"✈️ Flight","costing":None},
}
# Mode used to REACH each stop from the previous stop that day (default = walk).
# Straight from the itinerary's stated transport for each hop.
MODE_TO = {
 "Ribeira riverfront":"taxi",
 "🍷 Graham's 1890 Port Lodge":"taxi",
 "O Valentim (dinner, Matosinhos)":"metro",
 "🕌 Alfama + Miradouro de Santa Luzia":"metro",
 "⭐ Pena Palace":"bus",
 "⭐ Oceanário de Lisboa":"taxi",
 "🕌 National Tile Museum (Azulejo)":"taxi",
 "⭐ Tram 28 / Ler Devagar 📚":"tram",
 "⭐🛍 Embaixada (Príncipe Real)":"metro",
 "Hotel Giralda Center 🏨":"taxi",
 "🕌 Albaicín → Mirador de San Nicolás 🌄":"bus",
 "Rest / pool 🏊":"taxi",
 "Sacromonte — carmen dinner 🌄":"taxi",
 "🕌 Muralla Árabe":"taxi",
 "⭐ Templo de Debod (sunset) 🌄":"taxi",
 "Botín — farewell dinner":"taxi",
}

def arrive_mode(day, name, first):
    if first: return None
    return MODE_TO.get(name, "walk")

# Named coordinates for transfer hops (hotels, stations, airports)
_C = {
 "OPO":(41.2481,-8.6814),"Sheraton":(41.1580,-8.6293),"Campanha":(41.1490,-8.5850),"Lello":(41.1470,-8.6146),
 "HFFenix":(38.7267,-9.1500),"SantaApolonia":(38.7139,-9.1224),"Rossio":(38.7143,-9.1400),
 "SintraSt":(38.7986,-9.3866),"Castelo":(38.7925,-9.3888),"Regaleira":(38.7963,-9.3963),
 "BairroAlto":(38.7118,-9.1447),"Jeronimos":(38.6979,-9.2065),"Gulbenkian":(38.7376,-9.1537),"LIS":(38.7742,-9.1342),
 "Giralda":(37.3833,-5.9822),"Alcazar":(37.3830,-5.9906),"SantaJusta":(37.3919,-5.9757),
 "CordobaSt":(37.8918,-4.7908),"Mezquita":(37.8790,-4.7794),
 "GranadaSt":(37.1918,-3.6089),"Melia":(37.1735,-3.5990),"Alhambra":(37.1760,-3.5881),
 "Atocha":(40.4067,-3.6906),"Airbnb":(40.4155,-3.7075),"ReinaSofia":(40.4079,-3.6947),
 "ToledoSt":(39.8628,-4.0273),"Cristo":(39.8607,-4.0247),"MAD":(40.4936,-3.5668),
}
# Connective hops the stop-to-stop logic can't derive: getting from the hotel to
# the station/airport (and from the arrival station to the first stop), plus the
# day-trip train legs. This is where the "gaps" were.
TRANSFERS = [
 (2,"taxi","OPO","Sheraton"),
 (3,"metro","Sheraton","Lello"),
 (4,"taxi","Sheraton","Campanha"),              # hotel → station, last day in Porto
 (4,"metro","SantaApolonia","HFFenix"),          # arrival station → hotel
 (5,"metro","HFFenix","Rossio"),
 (5,"train","Rossio","SintraSt"),
 (5,"bus","SintraSt","Castelo"),
 (5,"walk","Regaleira","SintraSt"),
 (5,"train","SintraSt","Rossio"),
 (5,"walk","Rossio","BairroAlto"),
 (6,"taxi","HFFenix","Jeronimos"),
 (7,"walk","HFFenix","Gulbenkian"),
 (7,"taxi","Gulbenkian","LIS"),                  # hotel-area → airport, last day in Lisbon
 (8,"walk","Giralda","Alcazar"),
 (9,"taxi","Giralda","SantaJusta"),
 (9,"walk","CordobaSt","Mezquita"),
 (10,"taxi","Giralda","SantaJusta"),             # hotel → station, last day in Seville
 (10,"taxi","GranadaSt","Melia"),
 (11,"bus","Melia","Alhambra"),
 (12,"taxi","Melia","GranadaSt"),                # hotel → station, last day in Granada
 (12,"walk","Atocha","Airbnb"),
 (13,"walk","Airbnb","Atocha"),
 (13,"bus","ToledoSt","Cristo"),
 (14,"walk","Airbnb","ReinaSofia"),
 (15,"taxi","Airbnb","MAD"),                     # hotel → airport, last day of the trip
]
_LABEL = {
 "OPO":"OPO Airport","Sheraton":"Sheraton Porto","Campanha":"Porto Campanhã","Lello":"Livraria Lello",
 "HFFenix":"HF Fénix Urban","SantaApolonia":"Santa Apolónia","Rossio":"Rossio station",
 "SintraSt":"Sintra station","Castelo":"Castelo dos Mouros","Regaleira":"Quinta da Regaleira",
 "BairroAlto":"Bairro Alto","Jeronimos":"Jerónimos, Belém","Gulbenkian":"Gulbenkian Museum","LIS":"LIS Airport",
 "Giralda":"Hotel Giralda","Alcazar":"Real Alcázar","SantaJusta":"Sevilla Santa Justa",
 "CordobaSt":"Córdoba station","Mezquita":"Mezquita-Catedral",
 "GranadaSt":"Granada station","Melia":"Meliá Granada","Alhambra":"The Alhambra",
 "Atocha":"Madrid Atocha","Airbnb":"Plaza Mayor Airbnb","ReinaSofia":"Reina Sofía",
 "ToledoSt":"Toledo station","Cristo":"Cristo de la Luz","MAD":"MAD Airport",
}

def _haversine(a, b):
    from math import radians, sin, cos, asin, sqrt
    la1,lo1,la2,lo2=map(radians,[a[0],a[1],b[0],b[1]])
    h=sin((la2-la1)/2)**2+cos(la1)*cos(la2)*sin((lo2-lo1)/2)**2
    return 2*6371*asin(sqrt(h))

def build_segments():
    """Ordered intra-day hops between consecutive place-stops, plus the explicit
    hotel↔station↔airport transfers. Skips hops into/out of a train/flight stop
    (those are the intercity legs) and any accidental >20 km teleport line."""
    segs=[]
    for d in range(1,16):
        ds=[s for s in S if s[3]==d]
        for i in range(1,len(ds)):
            prev,cur=ds[i-1],ds[i]
            if prev[4] in ("train","flight") or cur[4] in ("train","flight"): continue
            a,b=(prev[1],prev[2]),(cur[1],cur[2])
            if _haversine(a,b)>20: continue   # inter-city jump → handled by a leg/transfer
            segs.append({"day":d,"mode":MODE_TO.get(cur[0],"walk"),
                         "a":a,"b":b,"from":prev[0],"to":cur[0]})
    for d,mode,fa,fb in TRANSFERS:
        segs.append({"day":d,"mode":mode,"a":_C[fa],"b":_C[fb],
                     "from":_LABEL[fa],"to":_LABEL[fb],"transfer":True})
    return segs

def valhalla_route(a, b, costing):
    payload={"locations":[{"lat":a[0],"lon":a[1]},{"lat":b[0],"lon":b[1]}],
             "costing":costing,"directions_options":{"units":"km"}}
    try:
        r=requests.post(VALHALLA_URL,json=payload,timeout=30); r.raise_for_status(); d=r.json()
        if "trip" not in d: return None
        cc=[]
        for leg in d["trip"]["legs"]:
            c=pl_lib.decode(leg["shape"],6)
            if cc and c and cc[-1]==c[0]: c=c[1:]
            cc.extend(c)
        return cc or None
    except Exception:
        return None

def build_paths():
    cache={}
    if os.path.exists(ROUTE_CACHE):
        try: cache=json.load(open(ROUTE_CACHE))
        except Exception: cache={}
    legs=[(lg,[list(lg["a"]),list(lg["b"])]) for lg in LEGS]  # rail/air = direct
    print("Resolving intra-city paths…")
    segs=[]; routed=0
    for sg in build_segments():
        costing=MODE_STYLE[sg["mode"]]["costing"]
        straight=[list(sg["a"]),list(sg["b"])]
        if not costing:
            segs.append((sg,straight)); continue
        key=hashlib.md5(f'{sg["a"]}{sg["b"]}{costing}'.encode()).hexdigest()
        if key in cache:
            segs.append((sg,cache[key])); routed+=1; continue
        res=valhalla_route(sg["a"],sg["b"],costing)
        if res:
            cache[key]=res; segs.append((sg,res)); routed+=1
            time.sleep(0.4)
        else:
            segs.append((sg,straight))  # fallback NOT cached → upgraded on a networked run
    try: json.dump(cache,open(ROUTE_CACHE,"w"))
    except Exception: pass
    print(f"  {routed}/{len(segs)} intra-city hops street-routed (rest drawn direct)")
    return {"legs":legs,"segs":segs}

# ═══════════════════════ THEME / ICON HELPERS ═══════════════════════
TYPE_ICON = {  # (fa icon, override marker colour or None → use region colour)
 "hotel":("bed",None),"flight":("plane","gray"),"train":("train","gray"),
 "food":("utensils","purple"),"shop":("bag-shopping","pink"),
 "moorish":("mosque","darkred"),"history":("fist-raised","black"),
 "museum":("palette",None),"attraction":("camera",None),
 "viewpoint":("binoculars",None),"church":("church",None),"eclipse":("sun","black"),
}
TYPE_EMOJI = {"hotel":"🏨","flight":"✈️","train":"🚆","food":"🍽️","shop":"🛍️",
 "moorish":"🕌","history":"✊","museum":"🎨","attraction":"📷","viewpoint":"🌄",
 "church":"⛪","eclipse":"🌘"}

def is_moorish(notes): return "🕌" in notes
def is_history(notes): return "✊" in notes
def is_food(st):       return st=="food"

def climate_block(city, c):
    cl=CLIMATE.get(city, CLIMATE["Madrid"])
    warn=""
    if cl["warn"]:
        warn=('<div style="grid-column:1/-1;margin-top:4px;color:#b45309;font-weight:600;">'
              '🥵 Heat protocol: sights 8:30–12:00 · rest 14:00–18:00 · out after 19:00</div>')
    return (f'<div style="background:#fff8e6;border-radius:6px;padding:8px 10px;margin-bottom:8px;'
            f'font-size:12px;border-left:3px solid {c};">'
            f'<div style="font-weight:600;margin-bottom:4px;">{cl["emoji"]} Typical {city} in August · {cl["pat"]}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:11px;color:#555;">'
            f'<span>🌡️ Avg high {cl["hi"]}</span><span>🌙 Avg low {cl["lo"]}</span>{warn}</div></div>')

def _n0(v, unit=""):
    return "—" if v is None else f"{v:.0f}{unit}"

def wx_block(wx, c):
    """Live-forecast panel (mint tint) shown when Open-Meteo has data for the slot."""
    temp=f'{_n0(wx["tc"],"°C")} / {_n0(wx["tf"])}°F'
    feels='' if wx["fc"] is None else f'<span>🥶 Feels {_n0(wx["fc"],"°C")} / {_n0(wx["ff"])}°F</span>'
    precip='—' if wx["p"] is None else f'{wx["p"]:.1f} mm'
    return (f'<div style="background:#eef7f0;border-radius:6px;padding:8px 10px;margin-bottom:8px;'
            f'font-size:12px;border-left:3px solid {c};">'
            f'<div style="font-weight:600;margin-bottom:4px;">🔴 Live · {wx["emoji"]} {wx["desc"]} at ~{wx["hour"]:02d}:00</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:11px;color:#555;">'
            f'<span>🌡️ {temp}</span>{feels}'
            f'<span>💨 Wind {_n0(wx["w"]," km/h")}</span><span>💨 Gusts {_n0(wx["g"]," km/h")}</span>'
            f'<span>🌧️ Precip {precip}</span></div></div>')

# ═══════════════════════ POPUPS ═══════════════════════
def popup_html(name, day, st, city, notes, link, lat, lon, wx=None):
    c=rcolor(city)
    h=(f'<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Arial,sans-serif;'
       f'max-width:300px;width:calc(100vw - 80px);line-height:1.5;">'
       f'<div style="background:{c};color:white;padding:8px 12px;">'
       f'<strong style="font-size:14px;">{name}</strong><br>'
       f'<span style="font-size:11px;opacity:0.9;">{DAY_LABELS[day]} · {st.capitalize()}</span></div>'
       f'<div style="padding:10px 14px 12px 14px;">')
    if wx:
        h+=wx_block(wx, c)
    elif city in CLIMATE and city!="Transit":
        h+=climate_block(city, c)
    h+=f'<div style="font-size:12px;color:#333;white-space:pre-wrap;">{notes}</div>'
    parts=[]
    if link:
        parts.append(f'<a href="{link}" target="_blank" style="color:{c};text-decoration:none;font-size:13px;font-weight:600;">🔗 Book / Info →</a>')
    parts.append(f'<a href="https://www.google.com/maps?q={lat},{lon}" target="_blank" style="color:{c};text-decoration:none;font-size:13px;font-weight:600;">📍 Map</a>')
    if day in DAY_MAP:
        parts.append(f'<a href="{DAY_MAP[day]}" target="_blank" style="color:{c};text-decoration:none;font-size:13px;font-weight:600;">🗺 Day route</a>')
    h+=f'<div style="margin-top:8px;padding-top:8px;border-top:1px solid #eee;display:flex;gap:14px;flex-wrap:wrap;">{"".join(parts)}</div>'
    return h+"</div></div>"

# ═══════════════════════ MAP ═══════════════════════
DAY_LAYER = {d: f"Day {d} — {DAY_DATES[d][5:].replace('-','/')} · {DAY_CITY[d]}" for d in range(1,16)}

def build_map(paths, weather):
    m=folium.Map(location=MAP_CENTER, zoom_start=ZOOM_START, tiles=None, control_scale=True)
    folium.TileLayer("OpenStreetMap", name="🗺️ Street Map").add_to(m)
    folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",attr="© OpenStreetMap contributors © CARTO",name="🌙 Dark Matter").add_to(m)
    folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",attr="Esri",name="🏔️ Terrain").add_to(m)
    folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",attr="Esri",name="🛰️ Satellite").add_to(m)

    # One toggleable layer per day (markers + that day's paths)
    dg={d: FeatureGroup(name=DAY_LAYER[d], show=True) for d in range(1,16)}
    moor=FeatureGroup(name="🕌 Moorish & Mudéjar sites", show=False)
    hist=FeatureGroup(name="✊ Political & literary history", show=False)
    hotels=FeatureGroup(name="🏨 Hotels", show=False)

    # Intercity legs (rail/air) → their travel day's layer
    for lg,coords in paths["legs"]:
        stl=MODE_STYLE[lg["mode"]]
        PolyLine(locations=coords, color=stl["color"], weight=5, opacity=0.9, smooth_factor=1,
                 dash_array=stl["dash"],
                 tooltip=f"<b>{stl['label']}: {lg['name']}</b><br>{lg['note']}").add_to(dg[lg["day"]])

    # Intra-city hops (walk/taxi/metro/…) → their day's layer, styled by mode
    for sg,coords in paths["segs"]:
        stl=MODE_STYLE[sg["mode"]]
        PolyLine(locations=coords, color=stl["color"], weight=stl["w"], opacity=0.85, smooth_factor=1,
                 dash_array=stl["dash"],
                 tooltip=f"<b>{stl['label']}</b><br>{sg['from']} → {sg['to']}").add_to(dg[sg["day"]])

    # Stop markers
    for name,lat,lon,day,st,city,notes,link,hr,dur,anchor in S:
        ic,ocol=TYPE_ICON.get(st,("camera",None))
        col=ocol or REGION_MARKER[region(city)]
        wx=get_wx(weather, city, day, hr)
        ph=Popup(popup_html(name,day,st,city,notes,link,lat,lon,wx), max_width=340)
        Marker(location=[lat,lon], popup=ph,
               tooltip=f"<b>{TYPE_EMOJI.get(st,'📷')} {name}</b><br><small>{DAY_LABELS[day]}</small>",
               icon=Icon(color=col, icon=ic, prefix="fa")).add_to(dg[day])
        if is_moorish(notes):
            Marker(location=[lat,lon], popup=Popup(popup_html(name,day,st,city,notes,link,lat,lon,wx),max_width=340),
                   tooltip=f"<b>🕌 {name}</b>", icon=Icon(color="darkred",icon="mosque",prefix="fa")).add_to(moor)
        if is_history(notes):
            Marker(location=[lat,lon], popup=Popup(popup_html(name,day,st,city,notes,link,lat,lon,wx),max_width=340),
                   tooltip=f"<b>✊ {name}</b>", icon=Icon(color="black",icon="fist-raised",prefix="fa")).add_to(hist)
        if st=="hotel" and "🏨" in name:
            Marker(location=[lat,lon], popup=Popup(popup_html(name,day,st,city,notes,link,lat,lon,wx),max_width=340),
                   tooltip=f"<b>🏨 {name}</b>", icon=Icon(color="green",icon="bed",prefix="fa")).add_to(hotels)

    for d in range(1,16): dg[d].add_to(m)
    moor.add_to(m); hist.add_to(m); hotels.add_to(m)
    LayerControl(collapsed=True).add_to(m)
    LocateControl(position="topleft", strings={"title":"See my location"}).add_to(m)

    title="""<div id="map-title" style="position:fixed;top:10px;left:55px;z-index:1000;background:white;padding:10px 18px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.2);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;max-width:calc(100vw - 120px);">
    <div style="font-size:16px;font-weight:700;color:#B23A48;">🕌 Portugal &amp; Spain</div>
    <div class="title-sub" style="font-size:12px;color:#666;margin-top:2px;">Aug 6–20, 2026 · 15 Days · Porto → Lisbon → Seville → Granada → Madrid · all trains + one flight</div>
    <div class="title-legend" style="font-size:10px;color:#999;margin-top:4px;">🕌 Moorish  ✊ History  🏨 Hotel  🍽️ Food  🛍️ Shop  🌄 View  🌘 Eclipse</div>
    <div class="title-legend" style="font-size:10px;color:#999;margin-top:2px;">Paths: <span style="color:#2E9B57;font-weight:700">━ 🚶Walk</span>  <span style="color:#E8952F;font-weight:700">━ 🚕Taxi</span>  <span style="color:#2D5BD0;font-weight:700">┄ 🚇Metro</span>  <span style="color:#8E44AD;font-weight:700">┄ 🚊Tram</span>  <span style="color:#159C97;font-weight:700">━ 🚌Bus</span>  <span style="color:#C0392B;font-weight:700">━ 🚆Train</span>  <span style="color:#6C757D;font-weight:700">┄ ✈️Flight</span></div>
    <div class="title-credits" style="font-size:9px;color:#bbb;margin-top:3px;">Walk/taxi/bus paths follow streets (Valhalla/OSM); rail &amp; air are direct hops · Toggle days ↗</div></div>"""
    m.get_root().html.add_child(folium.Element(title))
    m.get_root().html.add_child(folium.Element(RESPONSIVE_CSS))
    m.get_root().html.add_child(folium.Element(build_agenda(weather)))
    m.get_root().html.add_child(folium.Element(build_scrubber()))
    m.get_root().html.add_child(folium.Element(build_theme()))
    return m

RESPONSIVE_CSS = """<style>
.leaflet-control-layers-overlays{max-height:400px;overflow-y:auto;-webkit-overflow-scrolling:touch;}
.leaflet-popup-content-wrapper{padding:0 !important;overflow:hidden;}
.leaflet-popup-content{margin:0 !important;-webkit-overflow-scrolling:touch;touch-action:pan-y;}
.leaflet-popup-close-button{font-size:22px !important;width:30px !important;height:30px !important;padding:4px !important;color:white !important;z-index:1;}
@media (max-width:600px){
 #map-title{left:10px !important;top:6px !important;padding:6px 12px !important;max-width:calc(100vw - 70px) !important;}
 #map-title > div:first-child{font-size:13px !important;}
 .title-sub{font-size:10px !important;} .title-legend,.title-credits{display:none !important;}
 .leaflet-control-layers{max-width:210px;} .leaflet-control-layers-overlays{max-height:250px;font-size:11px;}
 .leaflet-popup-content-wrapper{max-width:calc(100vw - 40px) !important;}
 .leaflet-popup-content{max-width:calc(100vw - 70px) !important;}
}
@media (min-width:601px) and (max-width:1024px){ #map-title{max-width:440px !important;} .title-credits{display:none !important;}}
</style>"""

# ═══════════════════════ AGENDA VIEW ═══════════════════════
def _trunc(notes, c):
    if len(notes) > 150:
        short=notes[:145].rsplit(" ",1)[0]+"…"
        short=short.replace("\n","<br>"); full=notes.replace("\n","<br>")
        return (f'<span style="display:inline">{short} </span>'
                f'<a href="#" onclick="this.previousElementSibling.style.display=\'none\';this.nextElementSibling.style.display=\'inline\';this.style.display=\'none\';return false;" style="color:{c};font-weight:600;text-decoration:none;">Read More ↓</a>'
                f'<span style="display:none">{full} '
                f'<a href="#" onclick="var p=this.parentElement;p.style.display=\'none\';p.previousElementSibling.style.display=\'inline\';p.previousElementSibling.previousElementSibling.style.display=\'inline\';return false;" style="color:#666;text-decoration:none;">Hide ↑</a></span>')
    return notes.replace("\n","<br>")

def _card(name,lat,lon,day,st,city,notes,link,hr,dur,anchor,wx=None,arrive=None):
    c=rcolor(city); reg=region(city)
    icon=TYPE_EMOJI.get(st,"📷"); tstr=f"{hr:02d}:00"
    sid=f"d{day}h{hr}s{st}"
    immune="true" if anchor else "false"
    mo="true" if is_moorish(notes) else "false"
    hi="true" if is_history(notes) else "false"
    h =f'<div class="sc" id="{sid}" data-id="{sid}" data-day="{day}" data-city="{reg}" data-type="{st}" data-hour="{hr}" data-moor="{mo}" data-hist="{hi}" data-immune="{immune}" data-dur="{dur}" style="border-left-color:{c}">'
    if arrive:
        stl=MODE_STYLE[arrive]
        h+=f'<div class="amode" style="color:{stl["color"]}">↳ {stl["label"]} from previous stop</div>'
    h+='<div style="display:flex;align-items:baseline;gap:10px;justify-content:space-between;width:100%">'
    h+=f'<div style="display:flex;align-items:baseline;gap:10px"><div class="st">{tstr}</div>'
    h+=f'<div><span class="sn">{icon} {name}</span><br><span class="stp">{st}</span></div></div>'
    if not anchor:
        h+=f'<button class="stog" onclick="togSkip(\'{sid}\', event)" style="background:transparent;border:1px solid #ddd;color:#666;border-radius:6px;padding:4px 8px;font-size:11px;cursor:pointer;height:24px;">➖ Remove</button>'
    h+='</div>'
    if wx:
        feels='' if wx["fc"] is None else f'<span>🥶 Feels {_n0(wx["fc"],"°C")} / {_n0(wx["ff"])}°F</span>'
        h+=f'<div class="sw sw-live" style="border-left:3px solid {c}">'
        h+=f'<div style="grid-column:1/-1;font-weight:600;margin-bottom:2px">🔴 Live · {wx["emoji"]} {wx["desc"]} at ~{wx["hour"]:02d}:00</div>'
        h+=f'<span>🌡️ {_n0(wx["tc"],"°C")} / {_n0(wx["tf"])}°F</span>{feels}'
        h+=f'<span>💨 Wind {_n0(wx["w"]," km/h")}</span><span>💨 Gusts {_n0(wx["g"]," km/h")}</span></div>'
    elif city in CLIMATE and city!="Transit":
        cl=CLIMATE[city]
        h+=f'<div class="sw" style="border-left:3px solid {c}">'
        h+=f'<div style="grid-column:1/-1;font-weight:600;margin-bottom:2px">{cl["emoji"]} Typical {city} · {cl["pat"]}</div>'
        h+=f'<span>🌡️ High {cl["hi"]}</span><span>🌙 Low {cl["lo"]}</span></div>'
    h+=f'<div class="snt">{_trunc(notes,c)}</div>'
    h+='<div class="sl">'
    if link: h+=f'<a href="{link}" target="_blank" style="color:{c}">🔗 Book / Info →</a>'
    h+=f'<a href="https://www.google.com/maps?q={lat},{lon}" target="_blank" style="color:{c}">📍 Map</a>'
    if day in DAY_MAP: h+=f'<a href="{DAY_MAP[day]}" target="_blank" style="color:{c}">🗺 Day route</a>'
    h+='</div></div>'
    return h

def build_agenda(weather):
    tl=""
    for i in range(1,16):
        city=DAY_CITY[i]; c=REGION_COLORS[region(city)]
        tl+=f'<div class="dh" data-day="{i}" data-city="{region(city)}"><div class="dd" style="background:{c}"></div>{DAY_LABELS[i]}</div>'
        day_stops=[stp for stp in S if stp[3]==i]
        for j,stp in enumerate(day_stops):
            wx=get_wx(weather, stp[5], stp[3], stp[8])  # city, day, hour
            # inbound transport mode (skip the day's first stop and rail/flight hops)
            arrive=None
            if j>0:
                prev=day_stops[j-1]
                if prev[4] not in ("train","flight") and stp[4] not in ("train","flight"):
                    arrive=MODE_TO.get(stp[0],"walk")
            tl+=_card(*stp, wx=wx, arrive=arrive)

    dd_js="{"+",".join(f'{k}:"{v}"' for k,v in DAY_DATES.items())+"}"
    day_opts="".join(f'<option value="{d}">Day {d} · {DAY_DATES[d][5:].replace("-","/")}</option>' for d in range(1,16))

    return f"""
    <div id="vtog">
      <button id="bm" onclick="sv('map')">🗺️ Map</button>
      <button id="ba" onclick="sv('agenda')">📋 Itinerary</button>
    </div>
    <div id="av">
      <div class="ah"><div style="font-size:22px;font-weight:700">🕌 Portugal &amp; Spain</div>
        <div style="font-size:13px;opacity:0.85;margin-top:4px">Aug 6–20, 2026 · 15 Days · Dad, Ihsan (21) &amp; Daughter (18)</div>
        <div style="font-size:11px;opacity:0.7;margin-top:6px">Porto → Lisbon → Seville → Granada → Madrid · all trains + one short flight, no car</div></div>
      <div id="af">
        <button class="fp active" data-f="all" onclick="tf(this)">All</button>
        <button class="fp active" data-f="Porto" onclick="tf(this)" style="border-color:#2A9D8F;color:#2A9D8F">Porto</button>
        <button class="fp active" data-f="Lisbon" onclick="tf(this)" style="border-color:#457B9D;color:#457B9D">Lisbon</button>
        <button class="fp active" data-f="Seville" onclick="tf(this)" style="border-color:#E63946;color:#E63946">Seville</button>
        <button class="fp active" data-f="Granada" onclick="tf(this)" style="border-color:#D4A017;color:#D4A017">Granada</button>
        <button class="fp active" data-f="Madrid" onclick="tf(this)" style="border-color:#7B2D8E;color:#7B2D8E">Madrid</button>
        <button class="fp active" data-f="moor" onclick="tf(this)">🕌 Moorish</button>
        <button class="fp active" data-f="food" onclick="tf(this)">🍽️ Food</button>
        <button class="fp active" data-f="hist" onclick="tf(this)">✊ History</button>
      </div>
      <div id="atl">{tl}
        <div style="max-width:700px;margin:8px auto 0;padding:0 4px">
          <div class="infocard">
            <b>☀️ August heat is the #1 hazard.</b> Porto &amp; Lisbon are comfortable; Andalusia (Aug 12–16) is the danger zone — Seville/Cordoba run 100–108°F. Heat protocol: sights 8:30–12:00, siesta 14:00–18:00, out after 19:00. Re-check <a href="https://www.aemet.es/en" target="_blank">aemet.es</a> (Spain) / <a href="https://www.ipma.pt/en/" target="_blank">ipma.pt</a> (Portugal) 48 h before each leg.<br><span style="color:#2e7d5b;font-weight:600">🔴 Live forecast:</span> each stop shows a live Open-Meteo reading once its day is within the ~16-day forecast window (refreshed hourly); until then it shows the August climate normal.
          </div>
          <div class="infocard">
            <b>🎟️ Locked bookings:</b> Alhambra General — morning Sun Aug 16 (non-changeable). Ryanair FR3628 Lisbon→Seville, Aug 12 5:20 PM. All hotels + Madrid Airbnb booked. Book the 5 rail legs now on <a href="https://www.cp.pt/passageiros/en" target="_blank">cp.pt</a> / <a href="https://www.renfe.com/es/en" target="_blank">renfe.com</a> — the Aug 15 holiday Granada train sells first.
          </div>
          <div class="infocard">
            <b>🌘 Aug 12 eclipse:</b> deep partial (~85–90%) over Seville, beginning minutes after you land. Pack 3 pairs of ISO 12312-2 glasses from the US.
          </div>
        </div>
      </div>
      <div style="padding:20px;text-align:center;font-size:11px;color:#999">Climate normals from the itinerary heat outlook · Routes: Valhalla/OSM · Times are local · Skip/delay state saved on this device</div>

      <div id="d-fab" onclick="togMenu()" style="position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:28px;background:#B23A48;color:white;display:flex;align-items:center;justify-content:center;font-size:32px;box-shadow:0 4px 16px rgba(178,58,72,0.4);cursor:pointer;z-index:100;">+</div>
      <div id="d-menu" style="display:none;position:fixed;bottom:90px;right:24px;background:white;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.15);padding:8px;z-index:99;flex-direction:column;gap:4px;">
        <button onclick="opAdd()" style="padding:12px 16px;border:none;background:transparent;text-align:left;font-size:14px;font-weight:600;cursor:pointer;border-radius:8px;color:#333;">⏱ Add Delay / Stop</button>
        <button onclick="opRem()" style="padding:12px 16px;border:none;background:transparent;text-align:left;font-size:14px;font-weight:600;cursor:pointer;border-radius:8px;color:#666;">Undo / Remove Delay</button>
      </div>

      <div id="d-add-mod" class="mod-ov" style="display:none;">
        <div class="mod-bx">
          <div style="font-size:18px;font-weight:700;margin-bottom:12px;">Add Delay / Extra Stop</div>
          <div style="font-size:13px;color:#666;margin-bottom:16px;">Shifts all later scheduled items that day downward.</div>
          <div style="display:flex;gap:12px;margin-bottom:12px;">
            <div style="flex:1"><label style="font-size:12px;font-weight:600;color:#555;">Day:</label>
              <select id="v-day" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-top:4px;">{day_opts}</select></div>
            <div style="flex:1"><label style="font-size:12px;font-weight:600;color:#555;">Start Time:</label>
              <select id="v-time" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-top:4px;">{"".join(f'<option value="{h}">{h:02d}:00</option>' for h in range(6,24))}</select></div>
          </div>
          <label style="font-size:12px;font-weight:600;color:#555;">Duration (minutes):</label><br>
          <div style="display:flex;gap:8px;margin-top:6px;margin-bottom:16px;">
            <button class="mbtn" onclick="setD(15)">15m</button><button class="mbtn" onclick="setD(30)">30m</button>
            <button class="mbtn" onclick="setD(45)">45m</button><button class="mbtn" onclick="setD(60)">1h</button>
            <input type="number" id="v-dur" style="width:70px;padding:8px;border:1px solid #ddd;border-radius:6px;font-size:14px;" value="15">
          </div>
          <label style="font-size:12px;font-weight:600;color:#555;">Reason (optional):</label>
          <input type="text" id="v-rsn" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-top:6px;margin-bottom:20px;" placeholder="e.g., long lunch, siesta ran over…">
          <div style="display:flex;justify-content:flex-end;gap:12px;">
            <button onclick="clsMod()" style="padding:10px 16px;border:none;background:transparent;color:#666;font-weight:600;cursor:pointer;">Cancel</button>
            <button onclick="svDel()" style="padding:10px 20px;border:none;background:#B23A48;color:white;border-radius:8px;font-weight:600;cursor:pointer;">Apply</button>
          </div>
        </div>
      </div>
      <div id="d-rem-mod" class="mod-ov" style="display:none;">
        <div class="mod-bx">
          <div style="font-size:18px;font-weight:700;margin-bottom:12px;">Remove a Delay</div>
          <div id="v-del-list" style="max-height:200px;overflow-y:auto;margin-bottom:16px;font-size:13px;"></div>
          <div style="display:flex;justify-content:flex-end;"><button onclick="clsMod()" style="padding:10px 16px;border:none;background:#B23A48;color:white;border-radius:8px;font-weight:600;cursor:pointer;">Close</button></div>
        </div>
      </div>
    </div>
    <style>
    #vtog{{position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:2000;display:flex;background:rgba(255,255,255,0.95);backdrop-filter:blur(12px);border-radius:24px;padding:3px;box-shadow:0 2px 12px rgba(0,0,0,0.15);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif}}
    #vtog button{{padding:8px 20px;border:none;border-radius:20px;font-size:13px;font-weight:600;cursor:pointer;transition:all 0.3s}}
    #vtog button:focus{{outline:none}}
    #bm{{background:#B23A48;color:white}} #ba{{background:transparent;color:#666}}
    #av{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;z-index:1500;background:#f8f6f2;overflow-y:auto;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif}}
    .ah{{padding:60px 20px 14px;background:linear-gradient(135deg,#7b1f2b,#B23A48,#D4A017);color:white;text-align:center}}
    #af{{padding:12px 16px;background:white;border-bottom:1px solid #e8eaed;display:flex;flex-wrap:wrap;gap:6px;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,0.06)}}
    .fp{{padding:6px 14px;border:1.5px solid #ddd;border-radius:16px;font-size:12px;font-weight:500;cursor:pointer;background:white;color:#888;transition:all 0.2s}}
    .fp.active{{background:#fdf3f4;border-color:currentColor;font-weight:600}}
    .fp[data-f="all"].active{{background:#e8eaed;border-color:#666;color:#333}}
    #atl{{padding:16px;max-width:700px;margin:0 auto}}
    .dh{{display:flex;align-items:center;gap:12px;padding:16px 0 8px;margin-top:8px;font-size:14px;font-weight:700;color:#333}}
    .dd{{width:14px;height:14px;border-radius:50%;flex-shrink:0}}
    .sc{{background:white;border-radius:12px;padding:14px 16px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,0.06);border-left:4px solid #ddd;transition:all 0.2s}}
    .sc:hover{{box-shadow:0 3px 12px rgba(0,0,0,0.1);transform:translateY(-1px)}}
    .sc.now{{box-shadow:0 0 0 2px #B23A48,0 3px 12px rgba(178,58,72,0.2)}}
    .st{{font-size:13px;font-weight:700;color:#333;font-variant-numeric:tabular-nums;min-width:48px}}
    .sn{{font-size:14px;font-weight:600;color:#111}} .stp{{font-size:11px;color:#888;text-transform:capitalize}}
    .snt{{font-size:12px;color:#555;margin-top:6px;line-height:1.5}}
    .amode{{font-size:11px;font-weight:600;margin-bottom:6px;opacity:0.9}}
    .sw{{background:#fff8e6;border-radius:8px;padding:8px 10px;margin-top:8px;font-size:11px;display:grid;grid-template-columns:1fr 1fr;gap:2px 10px}}
    .sw-live{{background:#eef7f0}}
    .sl{{display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;padding-top:8px;border-top:1px solid #f0f0f0}}
    .sl a{{font-size:12px;font-weight:600;text-decoration:none;padding:4px 0}}
    .infocard{{background:white;border-radius:12px;padding:14px 16px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,0.06);border-left:4px solid #D4A017;font-size:12px;color:#444;line-height:1.55}}
    .infocard a{{color:#B23A48;font-weight:600;text-decoration:none}}
    .mod-ov{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.4);z-index:3000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)}}
    .mod-bx{{background:white;border-radius:16px;padding:24px;width:90%;max-width:360px;box-shadow:0 10px 30px rgba(0,0,0,0.2)}}
    .mbtn{{padding:8px 12px;background:#fdf3f4;border:1px solid #f0d9dc;border-radius:6px;font-weight:600;color:#B23A48;cursor:pointer;flex:1}}
    .mbtn:hover{{background:#fbe7e9}}
    .d-itm{{display:flex;justify-content:space-between;align-items:center;background:#f9f9f9;padding:12px;border-radius:8px;margin-bottom:8px;border:1px solid #eee}}
    .rm-btn{{background:#ffebee;color:#c62828;border:none;padding:6px 12px;border-radius:6px;font-weight:600;cursor:pointer}}
    .time-adj{{color:#e63946;font-weight:700;font-size:11px;display:block;margin-top:2px}}
    .time-adj.time-sub{{color:#4caf50;}}
    .skip-rec{{background:#fff3cd;border-left:4px solid #ffc107;padding:10px 12px;border-radius:0 6px 6px 0;margin-bottom:12px;font-size:12px;font-weight:600;color:#856404;display:flex;align-items:center;gap:8px}}
    .sc.skipped{{opacity:0.5;filter:grayscale(1)}}
    .sc.skipped .sn,.sc.skipped .stp,.sc.skipped .snt{{text-decoration:line-through}}
    .sc.skipped .stog{{color:#111 !important;border-color:#111 !important}}
    @media(max-width:600px){{ #vtog{{top:auto;bottom:98px}} #vtog button{{padding:6px 14px;font-size:12px}} .sc{{padding:12px 14px}} #af{{padding:10px 12px}}}}
    </style>
    <script>
    var DD={dd_js};
    window.dels=JSON.parse(localStorage.getItem('sp_dels'))||[];
    window.skips=JSON.parse(localStorage.getItem('sp_skips'))||[];
    function togMenu(){{var m=document.getElementById('d-menu');m.style.display=m.style.display==='none'?'flex':'none';}}
    function togSkip(sid,e){{if(e)e.preventDefault();var i=window.skips.indexOf(sid);if(i===-1)window.skips.push(sid);else window.skips.splice(i,1);localStorage.setItem('sp_skips',JSON.stringify(window.skips));applyDelays();}}
    function opAdd(){{document.getElementById('d-menu').style.display='none';document.getElementById('d-add-mod').style.display='flex';var ad=1;var dhs=document.querySelectorAll('.dh');for(var i=0;i<dhs.length;i++){{if(dhs[i].style.display!=='none'){{ad=parseInt(dhs[i].getAttribute('data-day'));break;}}}}document.getElementById('v-day').value=ad;var h=new Date().getHours();if(h>=6&&h<=23)document.getElementById('v-time').value=h;}}
    function opRem(){{document.getElementById('d-menu').style.display='none';buildRemList();document.getElementById('d-rem-mod').style.display='flex';}}
    function clsMod(){{document.querySelectorAll('.mod-ov').forEach(function(m){{m.style.display='none';}});}}
    function setD(m){{document.getElementById('v-dur').value=m;}}
    function svDel(){{var mins=parseInt(document.getElementById('v-dur').value);var rsn=document.getElementById('v-rsn').value||'Delay/Overtime';var day=parseInt(document.getElementById('v-day').value);var hr=parseInt(document.getElementById('v-time').value);if(isNaN(mins)||mins<=0)return;window.dels.push({{id:Date.now(),day:day,hr:hr,mins:mins,rsn:rsn}});localStorage.setItem('sp_dels',JSON.stringify(window.dels));document.getElementById('v-dur').value=15;document.getElementById('v-rsn').value='';clsMod();applyDelays();}}
    function buildRemList(){{var h='';if(window.dels.length===0)h='<div style="color:#888;text-align:center;padding:20px;">No delays added yet.</div>';else{{window.dels.forEach(function(d){{h+='<div class="d-itm"><div><strong style="color:#B23A48">Day '+d.day+' @ '+d.hr+':00</strong>: '+d.mins+'m<br><span style="color:#666;font-size:11px">'+d.rsn+'</span></div><button class="rm-btn" onclick="rmDel('+d.id+')">Remove</button></div>';}});}}document.getElementById('v-del-list').innerHTML=h;}}
    function rmDel(id){{window.dels=window.dels.filter(function(d){{return d.id!==id;}});localStorage.setItem('sp_dels',JSON.stringify(window.dels));buildRemList();applyDelays();}}
    function applyDelays(){{
      document.querySelectorAll('.time-adj,.skip-rec,.injected-delay').forEach(function(e){{e.remove();}});
      var cards=document.querySelectorAll('.sc:not(.injected-delay)');
      cards.forEach(function(c){{c.classList.remove('skipped');var sid=c.getAttribute('data-id');var btn=c.querySelector('.stog');if(sid&&window.skips.includes(sid)){{c.classList.add('skipped');if(btn)btn.innerHTML='➕ Restore';}}else if(btn)btn.innerHTML='➖ Remove';var stEl=c.querySelector('.st');if(stEl&&stEl.dataset.orig)stEl.innerHTML=stEl.dataset.orig;}});
      if(window.dels.length===0&&window.skips.length===0)return;
      window.dels.forEach(function(d){{var dc=document.createElement('div');dc.className='sc injected-delay';dc.setAttribute('data-day',d.day);dc.setAttribute('data-hour',d.hr);dc.setAttribute('data-delay-id',d.id);dc.style.borderLeftColor='#B23A48';dc.style.backgroundColor='#fff0f1';var hrStr=String(d.hr).padStart(2,'0')+':00';dc.innerHTML='<div style="display:flex;align-items:baseline;gap:10px"><div class="st">'+hrStr+'</div><div><span class="sn" style="color:#B23A48">🛑 Added Stop / Delay</span><br><span class="stp">'+d.mins+' minutes ('+d.rsn+')</span></div></div>';var ins=false;for(var i=0;i<cards.length;i++){{var c=cards[i];var cd=parseInt(c.getAttribute('data-day'));var ch=parseInt(c.getAttribute('data-hour'));if(cd===d.day&&ch>=d.hr){{c.parentNode.insertBefore(dc,c);ins=true;break;}}else if(cd>d.day){{c.parentNode.insertBefore(dc,c);ins=true;break;}}}}if(!ins)document.getElementById('atl').appendChild(dc);}});
      var allCards=document.querySelectorAll('.sc');var dayShifts={{}};for(var k=1;k<=15;k++)dayShifts[k]=[];
      window.dels.forEach(function(d){{dayShifts[d.day].push({{type:'add',hr:d.hr,mins:d.mins,id:d.id}});}});
      cards.forEach(function(c){{var sid=c.getAttribute('data-id');if(sid&&window.skips.includes(sid)){{var cD=parseInt(c.getAttribute('data-day'));var cH=parseInt(c.getAttribute('data-hour'));var cDur=parseInt(c.getAttribute('data-dur')||60);if(dayShifts[cD])dayShifts[cD].push({{type:'sub',hr:cH,mins:cDur,id:sid}});}}}});
      allCards.forEach(function(c){{var dA=c.getAttribute('data-day');var hA=c.getAttribute('data-hour');if(!dA||!hA)return;var cardDay=parseInt(dA);var cardHr=parseInt(hA);var delayId=c.getAttribute('data-delay-id');var isImmune=c.getAttribute('data-immune')==='true';var mins=0;(dayShifts[cardDay]||[]).forEach(function(sh){{if(sh.type==='add'&&cardHr>=sh.hr&&String(sh.id)!==delayId)mins+=sh.mins;if(sh.type==='sub'&&cardHr>sh.hr)mins-=sh.mins;}});if(isImmune)return;if(mins===0)return;var stEl=c.querySelector('.st');if(!stEl)return;if(!stEl.dataset.orig)stEl.dataset.orig=stEl.innerHTML;var tot=cardHr*60+mins;var nh=Math.floor(tot/60);var nm=tot%60;if(nh<0){{nh=0;nm=0;}}if(nh>23){{nh=23;nm=59;}}var tStr=String(nh).padStart(2,'0')+':'+String(nm).padStart(2,'0');var sign=mins>0?'+':'';var tCls=mins<0?'time-adj time-sub':'time-adj';stEl.innerHTML=tStr+' <span class="'+tCls+'">'+sign+mins+'m</span>';if(nh>=19&&!delayId){{if(!c.querySelector('.skip-rec')&&c.getAttribute('data-immune')!=='true'){{var rec=document.createElement('div');rec.className='skip-rec';rec.innerHTML='⚠️ Running late — dinner is drifting past 21:30. Consider trimming a stop.';c.insertBefore(rec,c.firstChild);}}}}}});
      af();
    }}
    function sv(v){{var m=document.querySelector('.folium-map');var a=document.getElementById('av');var t=document.getElementById('map-title');var bm=document.getElementById('bm');var ba=document.getElementById('ba');if(v==='agenda'){{if(m)m.style.display='none';if(t)t.style.display='none';a.style.display='block';bm.style.background='transparent';bm.style.color='#666';ba.style.background='#B23A48';ba.style.color='white';asc();}}else{{if(m)m.style.display='block';if(t)t.style.display='block';a.style.display='none';bm.style.background='#B23A48';bm.style.color='white';ba.style.background='transparent';ba.style.color='#666';}}}}
    var CITIES=['Porto','Lisbon','Seville','Granada','Madrid'];
    var _f=new Set(['all'].concat(CITIES).concat(['moor','food','hist']));
    function tf(b){{var f=b.getAttribute('data-f');if(f==='all'){{_f=new Set(['all'].concat(CITIES).concat(['moor','food','hist']));document.querySelectorAll('.fp').forEach(function(p){{p.className='fp active';}});}}else{{if(b.className.indexOf('active')>=0){{b.className='fp';_f.delete(f);}}else{{b.className='fp active';_f.add(f);}}if(CITIES.indexOf(f)>=0){{var ok=CITIES.every(function(x){{return _f.has(x);}});var ab=document.querySelector('[data-f="all"]');if(ok){{ab.className='fp active';_f.add('all');}}else{{ab.className='fp';_f.delete('all');}}}}}}af();}}
    function af(){{var cs=document.querySelectorAll('#atl .sc');var hs=document.querySelectorAll('#atl .dh');for(var i=0;i<cs.length;i++){{var c=cs[i];var ci=c.getAttribute('data-city');var tp=c.getAttribute('data-type');var mo=c.getAttribute('data-moor');var hi=c.getAttribute('data-hist');if(!ci)continue;var cityOk=(ci==='Transit')||_f.has(ci);var tok=true;if(tp==='food'&&!_f.has('food'))tok=false;if(mo==='true'&&!_f.has('moor'))tok=false;if(hi==='true'&&!_f.has('hist'))tok=false;c.style.display=(cityOk&&tok)?'':'none';}}for(var j=0;j<hs.length;j++){{var h=hs[j];var hc=h.getAttribute('data-city');h.style.display=(hc==='Transit'||_f.has(hc))?'':'none';}}}}
    function asc(){{var n=new Date();var uh=n.getHours();var today=n.getFullYear()+'-'+String(n.getMonth()+1).padStart(2,'0')+'-'+String(n.getDate()).padStart(2,'0');var td=null;for(var k in DD){{if(DD[k]===today)td=parseInt(k);}}if(!td)return;var cs=document.querySelectorAll('.sc[data-hour]');for(var i=0;i<cs.length;i++){{var c=cs[i];var cd=parseInt(c.getAttribute('data-day'));var ch=parseInt(c.getAttribute('data-hour'));if((cd===td&&ch>=uh)||cd>td){{c.className+=' now';(function(el){{setTimeout(function(){{el.scrollIntoView({{behavior:'smooth',block:'center'}});}},200);}})(c);return;}}}}}}
    if('serviceWorker' in navigator){{window.addEventListener('load',function(){{navigator.serviceWorker.register('sw.js').catch(function(){{}});}});}}
    applyDelays();
    </script>
    """

def build_scrubber():
    days=[{"d":d,
           "date":f"{int(DAY_DATES[d][5:7])}/{int(DAY_DATES[d][8:10])}",
           "city":DAY_CITY[d],
           "color":REGION_COLORS[region(DAY_CITY[d])]} for d in range(1,16)]
    DAYS_JS=json.dumps(days)
    html=r"""
    <div id="scrub" role="group" aria-label="Trip day timeline">
      <div id="scrub-top">
        <button id="scrub-all" class="on" type="button">All 15 days</button>
        <span id="scrub-label">Aug 6–20 · whole trip</span>
      </div>
      <div id="scrub-track">
        <div id="scrub-line"></div>
        <div id="scrub-thumb"></div>
      </div>
    </div>
    <style>
    #scrub{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);z-index:1000;
      width:min(94vw,860px);background:rgba(255,255,255,0.97);backdrop-filter:blur(12px);
      border-radius:16px;box-shadow:0 4px 20px rgba(0,0,0,0.18);padding:10px 16px 14px;
      font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;box-sizing:border-box;touch-action:none;}
    #scrub-top{display:flex;align-items:center;gap:12px;margin-bottom:6px;}
    #scrub-all{border:1.5px solid #B23A48;background:white;color:#B23A48;border-radius:20px;
      padding:4px 12px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap;flex-shrink:0;}
    #scrub-all.on{background:#B23A48;color:white;}
    #scrub-label{font-size:13px;color:#333;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
    #scrub-label b{color:#B23A48;}
    #scrub-track{position:relative;height:40px;margin:0 12px;cursor:pointer;}
    #scrub-line{position:absolute;top:19px;left:0;right:0;height:5px;border-radius:3px;
      background:linear-gradient(90deg,#2A9D8F,#457B9D,#E63946,#D4A017,#7B2D8E);opacity:0.9;}
    .scrub-tick{position:absolute;top:9px;transform:translateX(-50%);background:transparent;border:none;
      padding:0;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:2px;width:22px;}
    .scrub-tick .tk-bar{width:3px;height:14px;border-radius:2px;background:var(--c);opacity:0.55;transition:all .15s;}
    .scrub-tick .tk-n{font-size:9px;color:#999;font-weight:600;transition:color .15s;}
    .scrub-tick.act .tk-bar{opacity:1;height:20px;width:4px;}
    .scrub-tick.act .tk-n{color:#333;}
    #scrub-thumb{position:absolute;top:11px;width:22px;height:22px;border-radius:50%;
      background:#B23A48;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);
      transform:translateX(-50%);transition:left .12s ease,opacity .12s;opacity:0;pointer-events:none;z-index:3;}
    @media(max-width:600px){
      #scrub{bottom:12px;padding:8px 12px 12px;width:96vw;}
      #scrub-label{font-size:12px;}
      .scrub-tick .tk-n{font-size:8px;}
    }
    </style>
    <script>
    (function(){
      var DAYS=__DAYS__, N=DAYS.length, sel='all', dragging=false;
      var track=document.getElementById('scrub-track');
      var thumb=document.getElementById('scrub-thumb');
      var line=document.getElementById('scrub-line');
      var lab=document.getElementById('scrub-label');
      var allb=document.getElementById('scrub-all');
      var GRAD='linear-gradient(90deg,#2A9D8F,#457B9D,#E63946,#D4A017,#7B2D8E)';
      function pos(i){return N<2?0:(i/(N-1))*100;}
      DAYS.forEach(function(o,i){
        var t=document.createElement('button');
        t.type='button';t.className='scrub-tick';t.style.left=pos(i)+'%';t.style.setProperty('--c',o.color);
        t.innerHTML='<span class="tk-bar"></span><span class="tk-n">'+o.d+'</span>';
        t.addEventListener('click',function(e){e.stopPropagation();pick(o.d);});
        track.appendChild(t);
      });
      function setDayLayers(s){
        var labs=document.querySelectorAll('.leaflet-control-layers-overlays label');
        labs.forEach(function(lb){
          var m=lb.textContent.trim().match(/^Day\s+(\d+)/); if(!m)return;
          var d=parseInt(m[1]), inp=lb.querySelector('input'); if(!inp)return;
          var want=(s==='all')||(d===s);
          if(inp.checked!==want) inp.click();
        });
      }
      function pick(s){
        sel=s;
        if(s==='all'){allb.classList.add('on');thumb.style.opacity=0;line.style.background=GRAD;
          lab.textContent='Aug 6–20 · whole trip';}
        else{allb.classList.remove('on');var o=DAYS[s-1];
          thumb.style.opacity=1;thumb.style.left=pos(s-1)+'%';thumb.style.background=o.color;
          line.style.background='#e6e6e6';
          lab.innerHTML='<b>Day '+s+'</b> · '+o.date+' · '+o.city;}
        var ticks=document.querySelectorAll('.scrub-tick');
        for(var k=0;k<ticks.length;k++){ticks[k].classList.toggle('act',sel!=='all'&&k===s-1);}
        setDayLayers(s);
      }
      function dayFromX(x){var r=track.getBoundingClientRect();var f=(x-r.left)/r.width;
        f=Math.max(0,Math.min(1,f));return Math.round(f*(N-1))+1;}
      track.addEventListener('pointerdown',function(e){dragging=true;
        try{track.setPointerCapture(e.pointerId);}catch(_){}pick(dayFromX(e.clientX));e.preventDefault();});
      track.addEventListener('pointermove',function(e){if(dragging)pick(dayFromX(e.clientX));});
      window.addEventListener('pointerup',function(){dragging=false;});
      allb.addEventListener('click',function(){pick('all');});
      pick('all');
    })();
    </script>
    """
    return html.replace("__DAYS__", DAYS_JS)

def build_theme():
    # Warm "Claude Code" dark palette: charcoal surfaces, clay/coral accent.
    return r"""
    <button id="theme-tog" type="button" aria-label="Toggle dark mode" title="Toggle dark mode">🌙</button>
    <style>
    #theme-tog{position:fixed;top:12px;right:12px;z-index:2600;width:40px;height:40px;border-radius:50%;
      border:none;background:rgba(255,255,255,0.95);box-shadow:0 2px 8px rgba(0,0,0,0.2);
      font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;line-height:1;padding:0;}
    #theme-tog:hover{transform:scale(1.06);}
    /* make room at top-right so the toggle doesn't cover the layer control */
    .leaflet-top.leaflet-right{margin-top:52px;}
    /* ═════════ DARK MODE (Claude Code colours) ═════════ */
    [data-theme="dark"] #theme-tog{background:#35322e;box-shadow:0 2px 8px rgba(0,0,0,0.55);}
    [data-theme="dark"] .leaflet-container{background:#1a1917;}
    [data-theme="dark"] #av{background:#1f1e1d;}
    [data-theme="dark"] .ah{filter:brightness(0.88);}
    [data-theme="dark"] #af{background:#2a2927;border-bottom-color:#3d3a35;box-shadow:0 2px 8px rgba(0,0,0,0.45);}
    [data-theme="dark"] .fp{background:#35322e;border-color:#3d3a35;color:#a8a49c;}
    [data-theme="dark"] .fp.active{background:rgba(217,119,87,0.18);}
    [data-theme="dark"] .fp[data-f="all"].active{background:#3d3a35;border-color:#a8a49c;color:#e8e6e1;}
    [data-theme="dark"] .sc{background:#2a2927;box-shadow:0 1px 4px rgba(0,0,0,0.45);}
    [data-theme="dark"] .sc:hover{box-shadow:0 3px 12px rgba(0,0,0,0.6);}
    [data-theme="dark"] .st,[data-theme="dark"] .sn{color:#ece9e4;}
    [data-theme="dark"] .stp,[data-theme="dark"] .snt{color:#a8a49c;}
    [data-theme="dark"] .dh{color:#ece9e4;}
    [data-theme="dark"] .sw{background:#35322e;}
    [data-theme="dark"] .sw div,[data-theme="dark"] .sw span{color:#cfccc5;}
    [data-theme="dark"] .sw-live{background:#22302a;}
    [data-theme="dark"] .sl{border-top-color:#3d3a35;}
    [data-theme="dark"] .infocard{background:#2a2927;color:#bdb9b1;}
    [data-theme="dark"] .mod-bx{background:#2a2927;color:#ece9e4;}
    [data-theme="dark"] .mod-bx input,[data-theme="dark"] .mod-bx select{background:#35322e;color:#ece9e4;border-color:#3d3a35;}
    [data-theme="dark"] .mod-bx [style*="color:#666"],[data-theme="dark"] .mod-bx [style*="color:#555"],
    [data-theme="dark"] .mod-bx label{color:#a8a49c !important;}
    [data-theme="dark"] .mbtn{background:#35322e;border-color:#3d3a35;color:#e08a6b;}
    [data-theme="dark"] .d-itm{background:#35322e;border-color:#3d3a35;}
    [data-theme="dark"] #vtog{background:rgba(42,41,39,0.95);}
    [data-theme="dark"] #ba{color:#a8a49c;}
    [data-theme="dark"] #map-title{background:#2a2927 !important;box-shadow:0 2px 8px rgba(0,0,0,0.55);}
    [data-theme="dark"] #map-title > div:first-child{color:#e08a6b !important;}
    [data-theme="dark"] #map-title .title-sub,[data-theme="dark"] #map-title .title-legend,
    [data-theme="dark"] #map-title .title-credits{color:#a8a49c !important;}
    [data-theme="dark"] #scrub{background:rgba(42,41,39,0.97);}
    [data-theme="dark"] #scrub-label{color:#ece9e4;}
    [data-theme="dark"] #scrub-label b{color:#e08a6b;}
    [data-theme="dark"] #scrub-all{background:#2a2927;border-color:#d97757;color:#e08a6b;}
    [data-theme="dark"] #scrub-all.on{background:#d97757;color:#fff;}
    [data-theme="dark"] .scrub-tick .tk-n{color:#8a867e;}
    [data-theme="dark"] .scrub-tick.act .tk-n{color:#ece9e4;}
    [data-theme="dark"] .leaflet-control-layers{background:#2a2927;color:#ece9e4;border-color:#3d3a35;}
    [data-theme="dark"] .leaflet-control-layers-toggle{filter:invert(0.88);}
    [data-theme="dark"] .leaflet-control-layers label{color:#ece9e4;}
    [data-theme="dark"] .leaflet-bar a{background:#2a2927;color:#ece9e4;border-bottom-color:#3d3a35;}
    [data-theme="dark"] .leaflet-bar a:hover{background:#35322e;}
    [data-theme="dark"] .leaflet-control-attribution{background:rgba(42,41,39,0.85) !important;color:#8a867e !important;}
    [data-theme="dark"] .leaflet-control-attribution a{color:#a8a49c !important;}
    </style>
    <script>
    (function(){
      var KEY='trip_theme';
      function basemap(dark){
        var labs=document.querySelectorAll('.leaflet-control-layers-base label');
        for(var i=0;i<labs.length;i++){
          var t=labs[i].textContent.trim(), inp=labs[i].querySelector('input'); if(!inp)continue;
          var want = dark ? /Dark/.test(t) : /Street/.test(t);
          if(want && !inp.checked){ inp.click(); }
        }
      }
      function apply(theme, switchmap){
        document.documentElement.setAttribute('data-theme', theme);
        var b=document.getElementById('theme-tog'); if(b) b.textContent = (theme==='dark')?'☀️':'🌙';
        if(switchmap) setTimeout(function(){ basemap(theme==='dark'); }, 60);
      }
      var saved=null; try{ saved=localStorage.getItem(KEY); }catch(_){}
      var sysDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      var theme = saved || (sysDark?'dark':'light');
      apply(theme, false);
      window.addEventListener('load', function(){ setTimeout(function(){ basemap(theme==='dark'); }, 500); });
      var btn=document.getElementById('theme-tog');
      if(btn) btn.addEventListener('click', function(){
        var next=(document.documentElement.getAttribute('data-theme')==='dark')?'light':'dark';
        try{ localStorage.setItem(KEY,next); }catch(_){}
        apply(next, true);
      });
    })();
    </script>
    """

if __name__=="__main__":
    paths=build_paths()
    weather=fetch_weather()
    print("\nBuilding interactive map…")
    m=build_map(paths, weather)
    out="spain.html"
    m.save(out)
    import re
    html=open(out,encoding="utf-8").read()
    html=re.sub(r'(<(meta|link|img|br|hr|input)[^>]*?)\s*/>', r'\1>', html)
    open(out,"w",encoding="utf-8").write(html)
    print(f"\n✓ Saved: {out} ({os.path.getsize(out)/1024:.0f} KB)")
