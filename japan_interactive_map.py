#!/usr/bin/env python3
"""
Japan Family Trip — Interactive Map
July 28–August 14, 2023

Generates japan.html from the itinerary in
docs/Ihsan Japan Sharing Repo - Itenirary.csv.

Features mirror the existing trip pages:
  - Leaflet/Folium map with day layers and multiple basemaps
  - Rich stop popups, Google Maps links, and route lines
  - Map/itinerary views with filters, search, skip toggles, and delays
  - Horizontal and vertical day scrubbers, dark mode, geolocation, and PWA hooks
  - A separate ideas layer for every categorized place in the source document

Requires: pip install folium
Usage:    python japan_interactive_map.py
Output:   japan.html
"""

from datetime import date, timedelta
from html import escape
from math import asin, cos, radians, sin, sqrt
import json
import os
import re
from urllib.parse import quote_plus

import folium
from folium import FeatureGroup, Icon, LayerControl, Marker, PolyLine, Popup
from folium.plugins import LocateControl


MAP_CENTER = [36.15, 137.2]
ZOOM_START = 6
ROUTE_CACHE = "japan_route_cache.json"
OUTPUT = "japan.html"
DAY_COUNT = 18

CITY_OF = {
    "Washington": "Transit",
    "Tokyo": "Tokyo",
    "Fuji": "Tokyo",
    "Kanazawa": "Kanazawa",
    "Shirakawa-go": "Kanazawa",
    "Kyoto": "Kyoto",
    "Nara": "Kyoto",
    "Osaka": "Osaka",
    "Transit": "Transit",
}
CITY_COLORS = {
    "Tokyo": "#c8555f",
    "Kanazawa": "#3d877f",
    "Kyoto": "#8a63a8",
    "Osaka": "#d18435",
    "Transit": "#6f747b",
}
CITY_MARKERS = {
    "Tokyo": "red",
    "Kanazawa": "cadetblue",
    "Kyoto": "purple",
    "Osaka": "orange",
    "Transit": "gray",
}
CITY_ORDER = ["Tokyo", "Kanazawa", "Kyoto", "Osaka", "Transit"]


def city_group(city):
    return CITY_OF.get(city, city)


def city_color(city):
    return CITY_COLORS[city_group(city)]


start_date = date(2023, 7, 28)
DAY_DATES = {
    day: (start_date + timedelta(days=day - 1)).isoformat()
    for day in range(1, DAY_COUNT + 1)
}
DAY_CITY = {
    1: "Transit",
    2: "Tokyo",
    3: "Tokyo",
    4: "Tokyo",
    5: "Fuji",
    6: "Tokyo",
    7: "Tokyo",
    8: "Kanazawa",
    9: "Shirakawa-go",
    10: "Kyoto",
    11: "Kyoto",
    12: "Nara",
    13: "Kyoto",
    14: "Osaka",
    15: "Osaka",
    16: "Tokyo",
    17: "Tokyo",
    18: "Transit",
}
DAY_LABELS = {
    1: "Day 1 — Fri Jul 28: Depart Washington",
    2: "Day 2 — Sat Jul 29: Arrive Tokyo · Ginza · fireworks",
    3: "Day 3 — Sun Jul 30: Tsukiji · teamLab · Odaiba · Asakusa",
    4: "Day 4 — Mon Jul 31: Shibuya · Harajuku · Meiji Shrine",
    5: "Day 5 — Tue Aug 1: Mount Fuji day trip",
    6: "Day 6 — Wed Aug 2: Ghibli Museum · Kichijoji",
    7: "Day 7 — Thu Aug 3: Akihabara · Shinjuku",
    8: "Day 8 — Fri Aug 4: Tokyo → Kanazawa",
    9: "Day 9 — Sat Aug 5: Shirakawa-go day trip",
    10: "Day 10 — Sun Aug 6: Kenrokuen · Kanazawa → Kyoto",
    11: "Day 11 — Mon Aug 7: Fushimi Inari · Gion",
    12: "Day 12 — Tue Aug 8: Higashiyama · Nara",
    13: "Day 13 — Wed Aug 9: Arashiyama · central Kyoto",
    14: "Day 14 — Thu Aug 10: Kyoto → Osaka",
    15: "Day 15 — Fri Aug 11: Dotonbori",
    16: "Day 16 — Sat Aug 12: Osaka → Tokyo",
    17: "Day 17 — Sun Aug 13: Shinjuku",
    18: "Day 18 — Mon Aug 14: Fly home",
}

CLIMATE = {
    "Tokyo": ("88°F / 31°C", "76°F / 24°C", "Hot, humid, with summer showers", "🌦️"),
    "Fuji": ("73°F / 23°C", "59°F / 15°C", "Cooler by the lake; mountain visibility varies", "🗻"),
    "Kanazawa": ("88°F / 31°C", "75°F / 24°C", "Hot and humid; carry rain protection", "🌦️"),
    "Shirakawa-go": ("82°F / 28°C", "66°F / 19°C", "Warm days, cooler mountain evenings", "🌤️"),
    "Kyoto": ("91°F / 33°C", "76°F / 24°C", "Very hot and humid; start temple days early", "☀️"),
    "Nara": ("90°F / 32°C", "74°F / 23°C", "Hot and humid with limited midday shade", "☀️"),
    "Osaka": ("91°F / 33°C", "78°F / 26°C", "Hot, humid, and lively after dark", "☀️"),
    "Transit": ("—", "—", "Long-distance travel day", "✈️"),
}

TYPE_ICON = {
    "airport": ("plane", "gray"),
    "hotel": ("bed", None),
    "train": ("train", "darkblue"),
    "food": ("cutlery", "green"),
    "shop": ("shopping-bag", "pink"),
    "temple": ("institution", "darkred"),
    "museum": ("university", "purple"),
    "park": ("tree", "green"),
    "view": ("camera", "cadetblue"),
    "event": ("star", "red"),
    "attraction": ("map-marker", None),
    "cruise": ("ship", "blue"),
}
TYPE_EMOJI = {
    "airport": "✈️",
    "hotel": "🏨",
    "train": "🚆",
    "food": "🍽️",
    "shop": "🛍️",
    "temple": "⛩️",
    "museum": "🏛️",
    "park": "🌳",
    "view": "📸",
    "event": "🎆",
    "attraction": "📍",
    "cruise": "⛴️",
}
MODE_STYLE = {
    "walk": {"color": "#56875b", "dash": "2 7", "weight": 3, "label": "🚶 Walk"},
    "metro": {"color": "#4b70aa", "dash": "7 6", "weight": 4, "label": "🚇 Metro / local train"},
    "bus": {"color": "#338b88", "dash": None, "weight": 4, "label": "🚌 Bus / coach"},
    "train": {"color": "#b84f43", "dash": None, "weight": 4, "label": "🚆 Intercity train"},
    "flight": {"color": "#73767d", "dash": "11 8", "weight": 4, "label": "✈️ Flight"},
    "cruise": {"color": "#3f82b5", "dash": "6 5", "weight": 4, "label": "⛴️ Water bus"},
}


def stop(name, lat, lon, day, kind, city, notes, hour, duration=45,
         mode="walk", link=None, locked=False):
    return {
        "name": name,
        "lat": lat,
        "lon": lon,
        "day": day,
        "kind": kind,
        "city": city,
        "notes": notes,
        "hour": hour,
        "duration": duration,
        "mode": mode,
        "link": link,
        "locked": locked,
    }


STOPS = [
    stop("Washington Dulles (IAD) — depart", 38.9531, -77.4565, 1, "airport", "Transit",
         "12:15 PM EST departure for Haneda. The itinerary calls out the Turkish Airlines Lounge before the flight.",
         12, 60, "flight", locked=True),

    stop("Tokyo Haneda (HND) — arrive", 35.5494, 139.7798, 2, "airport", "Tokyo",
         "Arrive 3:20 PM JST. Set up the eSIM, then pick up Suica cards at the JR East Travel Service Center.",
         15, 60, "flight",
         "https://www.jreast.co.jp/e/customer_support/service_center_haneda.html#section", True),
    stop("The Blossom Hibiya", 35.6695, 139.7568, 2, "hotel", "Tokyo",
         "Keikyu Airport Line to Shimbashi, then check in from 3 PM. Buffet breakfast is included.",
         17, 45, "metro",
         "https://www.rome2rio.com/map/Tokyo-Haneda-Airport-HND/THE-BLOSSOM-HIBIYA-Tokyo#r/Train", True),
    stop("Ginza · Itoya · ancōra · MARUZEN", 35.6717, 139.7650, 2, "shop", "Tokyo",
         "Walk from Shimbashi to explore Ginza. The itinerary highlights Itoya Ginza, ancōra Ginza, and MARUZEN Nihombashi.",
         18, 90),
    stop("Sumida River Fireworks Festival", 35.7206, 139.8065, 2, "event", "Tokyo",
         "7:00–8:30 PM in the Asakusa and Mukojima areas along the Sumida River.",
         19, 90, "metro", locked=True),

    stop("Tsukiji Outer Market", 35.6655, 139.7707, 3, "food", "Tokyo",
         "Arrive 8:30 AM for brunch. Options in the itinerary: Sushizanmai, Kitsuneya, Yonemoto Coffee, and Marutoyo.",
         8, 150, "metro"),
    stop("teamLab Planets", 35.6491, 139.7898, 3, "museum", "Tokyo",
         "Take the bus from Tsukiji around 11:20 AM. Check-in window is 12:00–12:30 PM; leave around 2 PM.",
         12, 120, "bus", locked=True),
    stop("Odaiba · DiverCity · Gundam Base", 35.6251, 139.7755, 3, "attraction", "Tokyo",
         "Train to Odaiba around 2:15 PM; explore the mall and Gundam Base.",
         14, 30, "metro"),
    stop("Tokyo Water Cruise — Odaiba pier", 35.6273, 139.7710, 3, "cruise", "Tokyo",
         "Check in at 3 PM for the 3:10 PM cruise toward Asakusa.",
         15, 70, "walk", locked=True),
    stop("Senso-ji & Asakusa", 35.7148, 139.7967, 3, "temple", "Tokyo",
         "Explore Senso-ji and Asakusa after the water cruise, then return to the hotel by train.",
         17, 120, "cruise"),

    stop("Shibuya Crossing", 35.6595, 139.7005, 4, "attraction", "Tokyo",
         "Explore Shibuya, including the crossing and nearby shopping streets.",
         10, 120, "metro"),
    stop("Harajuku · Takeshita Street", 35.6702, 139.7027, 4, "shop", "Tokyo",
         "Explore Harajuku and its fashion, character shops, and vintage shopping.",
         13, 120),
    stop("Meiji Shrine", 35.6764, 139.6993, 4, "temple", "Tokyo",
         "Walk through the wooded grounds and visit Meiji Shrine.",
         15, 90),

    stop("Shinjuku LOVE Object — tour meet-up", 35.6914, 139.6960, 5, "attraction", "Fuji",
         "8:00 AM departure. Arrive 15 minutes before the tour leaves.",
         7, 30, "metro", locked=True),
    stop("Oishi Park · Lake Kawaguchi", 35.5210, 138.7465, 5, "view", "Fuji",
         "Mount Fuji day trip stop at Oishi Park, with lunch and the tour's included attractions and experiences.",
         11, 180, "bus"),
    stop("Tokyo Mode Gakuen — tour return", 35.6917, 139.6968, 5, "attraction", "Tokyo",
         "Scheduled return around 6:30 PM.",
         18, 15, "bus", locked=True),

    stop("Inokashira Park", 35.7004, 139.5740, 6, "park", "Tokyo",
         "Walk through Inokashira Park before the museum.",
         11, 75, "metro"),
    stop("Ghibli Museum, Mitaka", 35.6962, 139.5704, 6, "museum", "Tokyo",
         "1:00 PM timed entry. Keep the ticket/reservation handy.",
         13, 120, "walk", locked=True),
    stop("Kichijoji", 35.7032, 139.5796, 6, "food", "Tokyo",
         "Lunch and neighborhood exploration, then return to the hotel. The source leaves space for an additional activity.",
         15, 150),

    stop("Akihabara", 35.6984, 139.7731, 7, "shop", "Tokyo",
         "Ihsan's solo day: anime, manga, electronics, and hobby shopping around Akihabara.",
         10, 180, "metro"),
    stop("Haruki Murakami Library · Waseda", 35.7070, 139.7197, 7, "museum", "Tokyo",
         "A practical anchor for the itinerary's Murakami pilgrimage link.",
         14, 90, "metro", "https://murakamipilgrimage.com/"),
    stop("Shinjuku", 35.6938, 139.7034, 7, "attraction", "Tokyo",
         "Continue the solo day in Shinjuku.",
         17, 180, "metro"),

    stop("The Blossom Hibiya — check out", 35.6695, 139.7568, 8, "hotel", "Tokyo",
         "Check out at 11 AM. Store luggage at the hotel and be back by 2 PM.",
         11, 30, locked=True),
    stop("Aoyama Flower Market Tea House", 35.6635, 139.7122, 8, "food", "Tokyo",
         "Tea-house stop while luggage is stored at the hotel.",
         12, 75, "metro"),
    stop("Tokyo Station — Kagayaki 511", 35.6812, 139.7671, 8, "train", "Tokyo",
         "Depart 4:24 PM in Ordinary Car 10, seats 1A, 1B, 1C, and 2E.",
         16, 15, "metro", locked=True),
    stop("Kanazawa Station — arrive", 36.5781, 136.6486, 8, "train", "Kanazawa",
         "Arrive 6:52 PM on Kagayaki 511.",
         18, 15, "train", locked=True),
    stop("Mitsui Garden Hotel Kanazawa", 36.5667, 136.6552, 8, "hotel", "Kanazawa",
         "Check in from 3 PM. Address: 1-22 Kamitsutsumicho, Kanazawa 920-0869.",
         19, 30, "bus", locked=True),

    stop("Kanazawa Station — tour meet-up", 36.5781, 136.6486, 9, "bus", "Kanazawa",
         "Gather at 9:20 AM at the Kanazawa Port/West Exit group-bus boarding area; depart at 9:30 AM.",
         9, 30, "bus", locked=True),
    stop("Roadside Station Shirakawa-go", 36.2643, 136.9066, 9, "attraction", "Shirakawa-go",
         "Scheduled stop from 10:50 to 11:10 AM.",
         10, 20, "bus"),
    stop("Shirakawa-go lunch", 36.2570, 136.9065, 9, "food", "Shirakawa-go",
         "Tour lunch from 11:15 AM to noon.",
         11, 45),
    stop("Shirakawa-go village", 36.2606, 136.9060, 9, "view", "Shirakawa-go",
         "Free walk from noon to 2:10 PM through the historic gassho-zukuri village.",
         12, 130),
    stop("Kanazawa Station — tour return", 36.5781, 136.6486, 9, "bus", "Kanazawa",
         "Tour arrives back around 3:40 PM.",
         15, 20, "bus", locked=True),
    stop("Higashi Chaya District", 36.5725, 136.6666, 9, "shop", "Kanazawa",
         "5 PM shopping-district time. Higashi Chaya is used as the map anchor because the source does not name a district.",
         17, 120, "bus"),

    stop("Mitsui Garden Hotel — check out", 36.5667, 136.6552, 10, "hotel", "Kanazawa",
         "Check out at 11 AM and store luggage.",
         11, 20, locked=True),
    stop("Kenrokuen Garden", 36.5621, 136.6625, 10, "park", "Kanazawa",
         "Walk to Kenrokuen Garden after storing luggage.",
         11, 180),
    stop("Kanazawa Station — Thunderbird 40", 36.5781, 136.6486, 10, "train", "Kanazawa",
         "Depart 5:31 PM in Ordinary Car 11, seats 1A–1D.",
         17, 15, "bus", locked=True),
    stop("Kyoto Station — arrive", 34.9858, 135.7588, 10, "train", "Kyoto",
         "Arrive 7:38 PM on Thunderbird 40.",
         19, 15, "train", locked=True),
    stop("Kyoto Airbnb · Gion", 35.0032, 135.7784, 10, "hotel", "Kyoto",
         "Check in from 4 PM. Address: 559-4 Karatohanachō, Higashiyama Ward, Kyoto 605-0069.",
         20, 30, "metro", locked=True),

    stop("Fushimi Inari Taisha", 34.9671, 135.7727, 11, "temple", "Kyoto",
         "Go very early — the itinerary emphasizes a 6 AM start.",
         6, 180, "metro"),
    stop("Gion", 35.0037, 135.7786, 11, "attraction", "Kyoto",
         "Explore Gion after Fushimi Inari.",
         11, 240, "metro"),

    stop("Higashiyama · % Arabica", 34.9969, 135.7808, 12, "food", "Kyoto",
         "Morning exploration in Higashiyama with a coffee stop at % Arabica.",
         8, 90),
    stop("Yasaka Shrine", 35.0037, 135.7785, 12, "temple", "Kyoto",
         "Visit Yasaka Shrine while moving through Higashiyama.",
         10, 60),
    stop("Kiyomizu-dera", 34.9949, 135.7850, 12, "temple", "Kyoto",
         "Visit Kiyomizu-dera before traveling to Nara.",
         11, 120),
    stop("Kyoto Station — Aoniyoshi", 34.9858, 135.7588, 12, "train", "Kyoto",
         "Train to Nara at 2:40 PM on the Aoniyoshi sightseeing train.",
         14, 20, "metro", locked=True),
    stop("Tōdai-ji", 34.6890, 135.8398, 12, "temple", "Nara",
         "The source says “Temple”; Tōdai-ji is used as the Nara temple map anchor.",
         16, 75, "train"),
    stop("Nara Park", 34.6851, 135.8430, 12, "park", "Nara",
         "Walk through Nara Park and see the deer.",
         17, 75),
    stop("Nara dinner options", 34.6825, 135.8275, 12, "food", "Nara",
         "Dinner idea from the itinerary: kakimase udon or Maguro Koya, then return via the JR Nara Line.",
         18, 75),
    stop("Philosopher's Path · optional", 35.0267, 135.7956, 12, "park", "Kyoto",
         "The source also lists Philosopher's Path and Kinkaku-ji on this day; treat these as optional because they conflict with the Nara timing.",
         20, 60, "train"),
    stop("Kinkaku-ji · optional", 35.0394, 135.7292, 12, "temple", "Kyoto",
         "Optional item from the source itinerary. Confirm opening hours before attempting it after Nara.",
         20, 60, "bus"),

    stop("Shoraian", 35.0150, 135.6718, 13, "food", "Kyoto",
         "11:30 AM reservation in Arashiyama.",
         11, 120, "metro", locked=True),
    stop("Kyoto Imperial Palace", 35.0254, 135.7621, 13, "attraction", "Kyoto",
         "Visit the palace grounds in the evening.",
         15, 75, "metro"),
    stop("Ippodo Tea Kyoto Main Store", 35.0176, 135.7674, 13, "shop", "Kyoto",
         "Tea stop near the palace.",
         16, 45),
    stop("Kyoto International Manga Museum", 35.0119, 135.7594, 13, "museum", "Kyoto",
         "Museum option in central Kyoto.",
         14, 90),
    stop("Honke Owariya", 35.0137, 135.7596, 13, "food", "Kyoto",
         "The itinerary calls for a 3 PM stop at Kyoto's historic soba restaurant.",
         15, 60),
    stop("Kamo River bridge sunset", 35.0088, 135.7710, 13, "view", "Kyoto",
         "Finish at a Kamo River bridge for sunset.",
         18, 75),

    stop("Heian Jingū", 35.0159, 135.7824, 14, "temple", "Kyoto",
         "Morning shrine visit before checkout.",
         9, 90),
    stop("Kyoto Airbnb — check out", 35.0032, 135.7784, 14, "hotel", "Kyoto",
         "Check out at 11 AM.",
         11, 20, locked=True),
    stop("Kyoto Station — Thunderbird 18", 34.9858, 135.7588, 14, "train", "Kyoto",
         "Depart 1:11 PM in Ordinary Car 2, seats 1A–1D.",
         13, 15, "metro", locked=True),
    stop("Osaka Station — arrive", 34.7025, 135.4959, 14, "train", "Osaka",
         "Arrive 1:27 PM.",
         13, 15, "train", locked=True),
    stop("Osaka Airbnb · Dōtonbori", 34.6686, 135.5064, 14, "hotel", "Osaka",
         "Check in from 4 PM. Address: Residence Namba East 304, 1-chōme Higashi 6-24, Dōtonbori.",
         16, 30, "metro", locked=True),

    stop("Dōtonbori", 34.6687, 135.5013, 15, "attraction", "Osaka",
         "Open day to explore Dōtonbori, its food stalls, signs, canalside walk, and nearby shopping.",
         11, 480),

    stop("Osaka Airbnb — check out", 34.6686, 135.5064, 16, "hotel", "Osaka",
         "Check out at 11 AM.",
         11, 20, locked=True),
    stop("Shin-Osaka Station", 34.7335, 135.5002, 16, "train", "Osaka",
         "The source lists Haruka 22 departing 12:43 PM and arriving Shin-Osaka at 12:45 PM; verify the origin and timing before travel.",
         12, 20, "metro", locked=True),
    stop("Shin-Osaka — Hikari 652", 34.7335, 135.5002, 16, "train", "Osaka",
         "Depart 12:52 PM in Ordinary Car 15, seats 1A, 1B, 1D, 1E with oversized-baggage area.",
         12, 10, locked=True),
    stop("Tokyo Station — arrive", 35.6812, 139.7671, 16, "train", "Tokyo",
         "Arrive 4:12 PM.",
         16, 15, "train", locked=True),
    stop("The Knot Tokyo Shinjuku", 35.6896, 139.6918, 16, "hotel", "Tokyo",
         "Check in from 3 PM. Address: 4 Chome-31-1 Nishishinjuku, Shinjuku City.",
         17, 30, "metro", locked=True),

    stop("Shinjuku", 35.6938, 139.7034, 17, "attraction", "Tokyo",
         "JR Pass has expired; use Suica. Explore Shinjuku.",
         10, 360),
    stop("Kingdom Note Shinjuku", 35.6909, 139.6981, 17, "shop", "Tokyo",
         "Specialty stationery and fountain-pen stop from the itinerary.",
         14, 90),

    stop("The Knot Tokyo Shinjuku — check out", 35.6896, 139.6918, 18, "hotel", "Tokyo",
         "Check out at 10 AM.",
         8, 20, locked=True),
    stop("Tokyo Haneda (HND) — depart", 35.5494, 139.7798, 18, "airport", "Transit",
         "Depart 10:55 AM JST for Washington Dulles.",
         10, 90, "metro", locked=True),
    stop("Washington Dulles (IAD) — arrive", 38.9531, -77.4565, 18, "airport", "Transit",
         "Scheduled return at 10:35 AM EST.",
         10, 30, "flight", locked=True),
]


def idea(name, lat, lon, category, city, notes="", link=None):
    return {
        "name": name, "lat": lat, "lon": lon, "category": category,
        "city": city, "notes": notes, "link": link,
    }


IDEAS = [
    idea("Mode Off", 35.6704, 139.7050, "Clothes", "Tokyo", "Clothes-shopping idea from the source."),
    idea("2nd Street Harajuku", 35.6695, 139.7062, "Clothes", "Tokyo", "4 Chome-26-4 Jingumae."),
    idea("Treasure Factory Style", 35.6900, 139.7000, "Clothes", "Tokyo", "Secondhand fashion."),
    idea("Sunshine City", 35.7290, 139.7197, "Clothes", "Tokyo", "Large Ikebukuro shopping complex."),
    idea("Shibuya 109", 35.6596, 139.6996, "Clothes", "Tokyo", "2 Chome-29-1 Dogenzaka."),
    idea("UNIQLO Ginza", 35.6712, 139.7647, "Clothes", "Tokyo", "Multi-floor UNIQLO flagship."),
    idea("BOOKOFF PLUS", 35.6900, 139.7020, "Clothes", "Tokyo", "Secondhand books, media, and clothing."),
    idea("Rilakkuma Tea House", 35.0166, 135.6765, "Souvenirs", "Kyoto", "15 Sagatenryuji Kitatsukurimichicho."),
    idea("Shiro-Hige's Cream Puff Factory", 35.6586, 139.6616, "Souvenirs", "Tokyo", "First floor: souvenirs and cream puffs; second floor: café."),
    idea("Radio Kaikan", 35.6979, 139.7711, "Souvenirs", "Tokyo", "Akihabara hobby and character shopping."),
    idea("Animate Ikebukuro", 35.7324, 139.7156, "Souvenirs", "Tokyo", "1 Chome-20-7 Higashiikebukuro."),
    idea("Donguri Kyowakoku Osaka", 34.6684, 135.5046, "Souvenirs", "Osaka", "Studio Ghibli shop in Namba Walk."),
    idea("Shibuya Loft", 35.6613, 139.7006, "Souvenirs", "Tokyo", "21-1 Udagawacho."),
    idea("Don Quijote", 35.6608, 139.6987, "Souvenirs", "Tokyo", "Snacks, souvenirs, and skincare."),
    idea("7-Eleven", 35.6810, 139.7670, "Souvenirs", "Tokyo", "Convenience-store snack stop."),
    idea("Akihabara shopping district", 35.6984, 139.7731, "Souvenirs", "Tokyo", "Anime- and manga-related shopping."),
    idea("@cosme TOKYO", 35.6698, 139.7038, "Beauty", "Tokyo", "Skincare and makeup; 1 Chome-14-27 Jingumae."),
    idea("Miffy Sakura Kitchen", 35.0169, 135.6772, "Cafés", "Kyoto", "Miffy bakery in Arashiyama."),
    idea("Starbucks Reserve Roastery Tokyo", 35.6490, 139.6922, "Cafés", "Tokyo"),
    idea("Kōri Bake Shinjuku", 35.6957, 139.7000, "Cafés", "Tokyo", "1-28-2 Kabukicho."),
    idea("Nakatanidou", 34.6815, 135.8283, "Cafés", "Nara", "Fresh mochi at 29 Hashimotocho."),
    idea("Kichijoji Petit Mura", 35.7061, 139.5790, "Cafés", "Tokyo", "Tea house and cat café near the Ghibli Museum."),
    idea("Aoyama Flower Market Tea House", 35.6635, 139.7122, "Cafés", "Tokyo"),
    idea("Ogawa Coffee Laboratory", 35.6312, 139.6460, "Cafés", "Tokyo", "Sakurashinmachi coffee stop."),
    idea("Atelier Matcha", 35.6860, 139.7824, "Cafés", "Tokyo", "1 Chome-5-8 Nihonbashiningyocho."),
    idea("Rikuro's Namba Main Branch", 34.6666, 135.5011, "Cafés", "Osaka", "Japanese soufflé cheesecake."),
    idea("Honke Owariya", 35.0137, 135.7596, "Food", "Kyoto", "Historic Kyoto soba restaurant."),
    idea("Kuromon Ichiba Market", 34.6653, 135.5064, "Food", "Osaka"),
    idea("Tavelt grocery store", 35.0050, 135.7640, "Food", "Kyoto", "Listed as being at the end of Nishiki Market."),
    idea("Arashiyama", 35.0094, 135.6668, "Places", "Kyoto", "River, shops, cafés, and nearby sights."),
    idea("Arashiyama Monkey Park", 35.0114, 135.6760, "Places", "Kyoto"),
    idea("Shimokitazawa", 35.6615, 139.6680, "Places", "Tokyo", "Neighborhood for thrifting."),
    idea("Nara", 34.6851, 135.8048, "Places", "Nara", "About one hour from the Kyoto Airbnb."),
    idea("Kiyomizu-dera", 34.9949, 135.7850, "Places", "Kyoto"),
    idea("Okochi Sanso Garden", 35.0170, 135.6670, "Places", "Kyoto", "Quieter Arashiyama views and complimentary matcha; source notes a $10 admission."),
    idea("Uji", 34.8892, 135.8077, "Places", "Kyoto", "Matcha city."),
    idea("Nakamise-dori", 35.7121, 139.7965, "Places", "Tokyo", "Shopping street inside the Asakusa/Senso-ji approach."),
    idea("Harajuku", 35.6702, 139.7027, "Places", "Tokyo", "Takeshita Street, Kiddy Land, and vintage shopping."),
    idea("Thermae-Yu", 35.6951, 139.7057, "Relax", "Tokyo", "Spa/relaxation idea."),
    idea("Sumidagawa Fireworks Festival", 35.7206, 139.8065, "Events", "Tokyo", "Summer fireworks event from the itinerary."),
    idea("Kyoto kimono / yukata rental", 35.0037, 135.7786, "Events", "Kyoto",
         "Compare rental plans and reserve ahead.",
         "https://www.okamoto-kimono-en.com/kimono/setPlan.html"),
]

IDEA_ICON = {
    "Clothes": ("shopping-bag", "pink"),
    "Souvenirs": ("gift", "purple"),
    "Beauty": ("heart", "red"),
    "Cafés": ("coffee", "cadetblue"),
    "Food": ("cutlery", "green"),
    "Places": ("star", "blue"),
    "Relax": ("tint", "lightblue"),
    "Events": ("calendar", "orange"),
}


def haversine(a, b):
    lat1, lon1, lat2, lon2 = map(radians, [a[0], a[1], b[0], b[1]])
    value = (
        sin((lat2 - lat1) / 2) ** 2
        + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371 * asin(sqrt(value))


def flight_arc(a, b, points=42):
    # Keep trans-Pacific flights on the short side of the antimeridian.
    end_lon = b[1]
    if end_lon - a[1] > 180:
        end_lon -= 360
    elif end_lon - a[1] < -180:
        end_lon += 360
    adjusted_b = [b[0], end_lon]
    midpoint_lat = (a[0] + adjusted_b[0]) / 2
    midpoint_lon = (a[1] + adjusted_b[1]) / 2
    chord = sqrt((adjusted_b[0] - a[0]) ** 2 + (adjusted_b[1] - a[1]) ** 2)
    control = [midpoint_lat + 0.10 * chord, midpoint_lon]
    result = []
    for index in range(points + 1):
        t = index / points
        u = 1 - t
        result.append([
            round(u * u * a[0] + 2 * u * t * control[0] + t * t * adjusted_b[0], 4),
            round(u * u * a[1] + 2 * u * t * control[1] + t * t * adjusted_b[1], 4),
        ])
    return result


RAIL_VIA = {
    ("Tokyo Station — Kagayaki 511", "Kanazawa Station — arrive"): [
        [35.9063, 139.6239], [36.6433, 138.1887], [36.6953, 137.2137]
    ],
    ("Kanazawa Station — Thunderbird 40", "Kyoto Station — arrive"): [
        [36.0617, 136.2236], [35.6452, 136.0769], [35.3145, 136.2908],
        [35.0972, 136.0730], [35.0522, 135.7566],
    ],
    ("Kyoto Station — Aoniyoshi", "Tōdai-ji"): [
        [34.9534, 135.7698], [34.8820, 135.7994], [34.6937, 135.8008]
    ],
    ("Kyoto Station — Thunderbird 18", "Osaka Station — arrive"): [
        [34.8915, 135.8078], [34.8020, 135.5610]
    ],
    ("Shin-Osaka — Hikari 652", "Tokyo Station — arrive"): [
        [35.1709, 136.8815], [34.9716, 138.3890], [35.1036, 138.8590],
        [35.2564, 139.1549], [35.6302, 139.7404],
    ],
}


def build_routes():
    routes = [{
        "day": 1,
        "from": "Washington Dulles (IAD)",
        "to": "Tokyo Haneda (HND)",
        "mode": "flight",
        "km": round(haversine([38.9531, -77.4565], [35.5494, 139.7798]), 1),
        "coords": flight_arc([38.9531, -77.4565], [35.5494, 139.7798]),
        "far": True,
    }]
    for day in range(1, DAY_COUNT + 1):
        day_stops = [item for item in STOPS if item["day"] == day]
        for previous, current in zip(day_stops, day_stops[1:]):
            a = [previous["lat"], previous["lon"]]
            b = [current["lat"], current["lon"]]
            mode = current["mode"]
            if mode == "flight":
                coords = flight_arc(a, b)
            elif (previous["name"], current["name"]) in RAIL_VIA:
                coords = [a] + RAIL_VIA[(previous["name"], current["name"])] + [b]
            else:
                coords = [a, b]
            routes.append({
                "day": day,
                "from": previous["name"],
                "to": current["name"],
                "mode": mode,
                "km": round(haversine(a, b), 1),
                "coords": coords,
                "far": haversine(a, b) > 1500,
            })
    with open(ROUTE_CACHE, "w", encoding="utf-8") as cache_file:
        json.dump(routes, cache_file, ensure_ascii=False, indent=2)
    return routes


def climate_html(city):
    high, low, pattern, emoji = CLIMATE.get(city, CLIMATE["Transit"])
    return (
        '<div class="climate">'
        f'<div class="climate-icon">{emoji}</div>'
        '<div><b>Typical late Jul / early Aug</b><br>'
        f'<span>{escape(high)} high · {escape(low)} low</span><br>'
        f'<small>{escape(pattern)}</small></div></div>'
    )


def google_maps_url(lat, lon):
    return f"https://www.google.com/maps?q={lat},{lon}"


def popup_html(item):
    color = city_color(item["city"])
    links = []
    if item.get("link"):
        links.append(
            f'<a href="{escape(item["link"], quote=True)}" target="_blank">🔗 Info</a>'
        )
    links.append(
        f'<a href="{google_maps_url(item["lat"], item["lon"])}" target="_blank">📍 Map</a>'
    )
    locked = '<span class="locked">Booked / timed</span>' if item["locked"] else ""
    time_text = format_time(item["hour"])
    return f"""
    <div class="popup-card" style="--place:{color}">
      <div class="popup-kicker">Day {item["day"]} · {time_text} · {escape(item["city"])}</div>
      <div class="popup-title">{escape(item["name"])}</div>
      {locked}
      <div class="popup-notes">{escape(item["notes"])}</div>
      {climate_html(item["city"])}
      <div class="popup-links">{''.join(links)}</div>
    </div>
    """


def idea_popup_html(item):
    icon = TYPE_EMOJI.get("shop", "💡")
    links = [
        f'<a href="{google_maps_url(item["lat"], item["lon"])}" target="_blank">📍 Map</a>'
    ]
    if item.get("link"):
        links.insert(0, f'<a href="{escape(item["link"], quote=True)}" target="_blank">🔗 Info</a>')
    return f"""
    <div class="popup-card" style="--place:#947348">
      <div class="popup-kicker">{icon} Itinerary idea · {escape(item["category"])}</div>
      <div class="popup-title">{escape(item["name"])}</div>
      <div class="popup-notes">{escape(item["notes"] or "Saved from the ideas section of the itinerary.")}</div>
      <div class="popup-links">{''.join(links)}</div>
    </div>
    """


def format_time(hour):
    suffix = "AM" if hour < 12 else "PM"
    shown = hour if 1 <= hour <= 12 else (12 if hour in (0, 12) else hour - 12)
    return f"{shown}:00 {suffix}"


def marker_icon(item):
    icon_name, override = TYPE_ICON.get(item["kind"], ("map-marker", None))
    return Icon(
        color=override or CITY_MARKERS[city_group(item["city"])],
        icon=icon_name,
        prefix="fa",
    )


def build_map(routes):
    trip_map = folium.Map(
        location=MAP_CENTER,
        zoom_start=ZOOM_START,
        tiles=None,
        control_scale=False,
        prefer_canvas=True,
    )
    folium.TileLayer("OpenStreetMap", name="🗺️ Street Map").add_to(trip_map)
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
        attr="© OpenStreetMap contributors © CARTO",
        name="🌙 Dark Matter",
    ).add_to(trip_map)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="🏔️ Terrain",
    ).add_to(trip_map)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="🛰️ Satellite",
    ).add_to(trip_map)

    day_layers = {}
    for day in range(1, DAY_COUNT + 1):
        date_label = DAY_DATES[day][5:].replace("-", "/")
        layer = FeatureGroup(
            name=f"Day {day} — {date_label} · {DAY_CITY[day]}",
            show=True,
        )
        layer.add_to(trip_map)
        day_layers[day] = layer

    for route in routes:
        style = MODE_STYLE[route["mode"]]
        classes = "farflight" if route["far"] else ""
        line = PolyLine(
            route["coords"],
            color=style["color"],
            weight=style["weight"],
            opacity=0.84,
            dash_array=style["dash"],
            tooltip=(
                f'<b>{style["label"]}</b><br>'
                f'{escape(route["from"])} → {escape(route["to"])}'
            ),
        )
        line.options["className"] = classes
        line.add_to(day_layers[route["day"]])

    for item in STOPS:
        Marker(
            [item["lat"], item["lon"]],
            popup=Popup(popup_html(item), max_width=390),
            tooltip=f'<b>{escape(item["name"])}</b><br><small>{DAY_LABELS[item["day"]]}</small>',
            icon=marker_icon(item),
        ).add_to(day_layers[item["day"]])

    ideas_layer = FeatureGroup(name=f"💡 Saved ideas ({len(IDEAS)})", show=False)
    ideas_layer.add_to(trip_map)
    for item in IDEAS:
        icon_name, color = IDEA_ICON[item["category"]]
        Marker(
            [item["lat"], item["lon"]],
            popup=Popup(idea_popup_html(item), max_width=360),
            tooltip=f'<b>{escape(item["name"])}</b><br><small>{escape(item["category"])}</small>',
            icon=Icon(color=color, icon=icon_name, prefix="fa"),
        ).add_to(ideas_layer)

    LayerControl(collapsed=True, position="topright").add_to(trip_map)
    LocateControl(
        position="topleft",
        strings={"title": "Show my location"},
        flyTo=True,
        keepCurrentZoomLevel=False,
    ).add_to(trip_map)

    title = """
    <div id="map-title">
      <a class="home-link" href="index.html" aria-label="All trips">← Trips</a>
      <div class="map-heading">🇯🇵 Japan Family Trip</div>
      <div class="title-sub">Jul 28–Aug 14, 2023 · 18 days<span class="title-route"> · Tokyo → Kanazawa → Kyoto → Osaka → Tokyo</span></div>
      <div class="title-legend">Tap a marker · use the timeline below · toggle layers ↗</div>
    </div>
    """
    trip_map.get_root().html.add_child(folium.Element(title))
    trip_map.get_root().html.add_child(folium.Element(build_agenda(routes)))
    trip_map.get_root().html.add_child(folium.Element(build_scrubber()))
    trip_map.get_root().html.add_child(folium.Element(build_location_editor()))
    trip_map.get_root().html.add_child(folium.Element(build_theme()))
    trip_map.get_root().html.add_child(folium.Element(build_touch_cleanup()))
    return trip_map


def agenda_card(item):
    color = city_color(item["city"])
    locked = '<span class="card-lock">● timed</span>' if item["locked"] else ""
    link = ""
    if item.get("link"):
        link = f'<a href="{escape(item["link"], quote=True)}" target="_blank">Info</a>'
    maps = f'<a href="{google_maps_url(item["lat"], item["lon"])}" target="_blank">Map</a>'
    searchable = escape(
        f'{item["name"]} {item["notes"]} {item["city"]} {item["kind"]}',
        quote=True,
    ).lower()
    return f"""
    <article class="stop-card" id="jp-{item["day"]}-{slug(item["name"])}"
      data-day="{item["day"]}" data-city="{city_group(item["city"])}"
      data-search="{searchable}" style="--city:{color}">
      <button class="skip" type="button" aria-label="Skip {escape(item["name"], quote=True)}"
        data-skip="jp-{item["day"]}-{slug(item["name"])}">✓</button>
      <div class="card-time" data-hour="{item["hour"]}" data-day="{item["day"]}">{format_time(item["hour"])}</div>
      <div class="card-main">
        <div class="card-title">{TYPE_EMOJI.get(item["kind"], "📍")} {escape(item["name"])} {locked}</div>
        <div class="card-meta">{escape(item["city"])} · {item["duration"]} min · {MODE_STYLE[item["mode"]]["label"]}</div>
        <div class="card-notes">{escape(item["notes"])}</div>
        <div class="card-links">{link}{maps}</div>
      </div>
    </article>
    """


def slug(value):
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:54]


def build_agenda(routes):
    cards = []
    for day in range(1, DAY_COUNT + 1):
        date_value = date.fromisoformat(DAY_DATES[day])
        city = DAY_CITY[day]
        cards.append(
            f'<section class="day-section" data-day="{day}" data-city="{city_group(city)}">'
            f'<div class="day-head" data-day="{day}" style="--city:{city_color(city)}">'
            f'<span>Day {day}</span><div><b>{escape(date_value.strftime("%a %b %-d") if os.name != "nt" else date_value.strftime("%a %b %d").replace(" 0", " "))}</b>'
            f'<small>{escape(DAY_LABELS[day].split(": ", 1)[1])}</small></div></div>'
        )
        cards.extend(agenda_card(item) for item in STOPS if item["day"] == day)
        cards.append("</section>")
    city_chips = "".join(
        f'<button type="button" data-city="{city}">{city}</button>'
        for city in CITY_ORDER
    )
    route_count = len(routes)
    template = r"""
    <div id="view-toggle" role="group" aria-label="Choose view">
      <button id="map-button" class="on" type="button">🗺️ Map</button>
      <button id="agenda-button" type="button">📋 Itinerary</button>
    </div>
    <div id="agenda-view">
      <header class="agenda-hero">
        <a href="index.html">← All trips</a>
        <div>🇯🇵</div>
        <h1>Japan Family Trip</h1>
        <p>Jul 28–Aug 14, 2023 · 18 days · Tokyo → Kanazawa → Kyoto → Osaka</p>
      </header>
      <div id="agenda-filter">
        <div class="filter-row"><button class="on" type="button" data-city="all">All</button>__CHIPS__</div>
        <input id="agenda-search" type="search" placeholder="Search stops, notes, food…" aria-label="Search itinerary">
      </div>
      <main id="agenda-list">__CARDS__</main>
      <footer>
        Source: <code>docs/Ihsan Japan Sharing Repo - Itenirary.csv</code> ·
        __ROUTES__ route segments · skip and delay state stays on this device.
      </footer>
    </div>
    <div id="day-rail" aria-label="Jump to a day"><div id="day-rail-label"></div><div id="day-rail-buttons"></div></div>
    <button id="delay-fab" type="button">⏱ Delays</button>
    <div id="delay-modal" hidden>
      <div class="delay-card">
        <button id="delay-close" type="button" aria-label="Close">×</button>
        <h2>Trip delays</h2>
        <p>Add a delay from a day onward. Displayed times update; the original itinerary is unchanged.</p>
        <div class="delay-form">
          <label>From day <select id="delay-day"></select></label>
          <label>Minutes <input id="delay-minutes" type="number" min="-180" max="480" step="5" value="15"></label>
          <button id="delay-add" type="button">Add delay</button>
        </div>
        <div id="delay-list"></div>
      </div>
    </div>
    <style>
    #view-toggle{position:fixed;left:50%;top:12px;transform:translateX(-50%);z-index:2500;
      display:flex;padding:3px;border:1px solid var(--line);border-radius:24px;background:var(--panel);
      box-shadow:var(--shadow);font-family:var(--sans)}
    #view-toggle button{border:0;background:transparent;color:var(--ink2);padding:8px 14px;border-radius:20px;
      font-size:13px;font-weight:700;cursor:pointer}
    #view-toggle button.on{background:var(--brand);color:white}
    #agenda-view{display:none;position:fixed;inset:0;z-index:1500;background:var(--bg);color:var(--ink);
      overflow:auto;font-family:var(--sans)}
    body.agenda-on #agenda-view{display:block}
    body.agenda-on #map-title,body.agenda-on #scrubber{display:none}
    body.agenda-on #view-toggle{top:auto;bottom:18px}
    .agenda-hero{padding:70px 24px 30px;text-align:center;background:linear-gradient(145deg,#8d2432,#c94e5d 55%,#e6a247);color:#fff}
    .agenda-hero>a{position:absolute;left:18px;top:18px;color:#fff;text-decoration:none;font-size:13px;font-weight:700}
    .agenda-hero>div{font-size:48px}.agenda-hero h1{font-family:var(--serif);font-size:36px;margin:4px 0}
    .agenda-hero p{margin:0;opacity:.9;font-size:14px}
    #agenda-filter{position:sticky;top:0;z-index:100;padding:10px 66px 10px 14px;background:color-mix(in srgb,var(--bg) 90%,transparent);
      backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
    .filter-row{display:flex;gap:6px;overflow:auto;padding-bottom:8px;scrollbar-width:none}
    .filter-row button{border:1px solid var(--line);background:var(--panel);color:var(--ink2);border-radius:18px;
      padding:6px 11px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap}
    .filter-row button.on{background:var(--brand);color:#fff;border-color:var(--brand)}
    #agenda-search{width:100%;border:1px solid var(--line);background:var(--panel);color:var(--ink);
      border-radius:10px;padding:9px 11px;font-size:14px;outline:none}
    #agenda-list{max-width:820px;margin:0 auto;padding:14px 54px 120px 18px}
    .day-section{margin-bottom:26px}.day-section.hidden,.stop-card.hidden{display:none}
    .day-head{display:flex;align-items:center;gap:12px;padding:14px 4px 8px;border-bottom:2px solid var(--city)}
    .day-head>span{background:var(--city);color:#fff;border-radius:8px;padding:6px 9px;font-size:12px;font-weight:800}
    .day-head b{display:block;font-family:var(--serif);font-size:18px}.day-head small{display:block;color:var(--ink2);margin-top:2px}
    .stop-card{position:relative;display:grid;grid-template-columns:78px 1fr;gap:12px;padding:15px 40px 15px 12px;
      margin:10px 0;background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--city);
      border-radius:12px;box-shadow:var(--shadow)}
    .stop-card.skipped{opacity:.48;filter:grayscale(.8)}.stop-card.skipped .card-title{text-decoration:line-through}
    .skip{position:absolute;right:10px;top:10px;width:26px;height:26px;border:1px solid var(--line);border-radius:50%;
      background:transparent;color:var(--ink3);cursor:pointer}.stop-card.skipped .skip{background:#4d8d66;color:#fff;border-color:#4d8d66}
    .card-time{font-size:12px;font-weight:800;color:var(--city);padding-top:3px}.card-title{font-family:var(--serif);font-weight:600;font-size:17px}
    .card-lock{font-family:var(--sans);font-size:10px;color:#a34a38;background:#f5e1d9;border-radius:10px;padding:2px 6px;white-space:nowrap}
    :root[data-theme="dark"] .card-lock{background:#35231e;color:#ee9a7f}
    .card-meta{font-size:11px;color:var(--ink3);margin:4px 0 8px}.card-notes{font-size:13px;line-height:1.55;color:var(--ink2)}
    .card-links{display:flex;gap:14px;margin-top:9px}.card-links a{color:var(--city);font-size:12px;font-weight:700;text-decoration:none}
    #agenda-view footer{text-align:center;color:var(--ink3);font-size:11px;padding:22px 20px 100px}
    #day-rail{display:none;position:fixed;right:8px;top:50%;transform:translateY(-50%);z-index:1800}
    body.agenda-on #day-rail{display:flex;align-items:center}
    #day-rail-buttons{display:flex;flex-direction:column;gap:2px;padding:7px 5px;border:1px solid var(--line);
      border-radius:15px;background:color-mix(in srgb,var(--panel) 88%,transparent);backdrop-filter:blur(10px)}
    #day-rail-buttons button{width:25px;height:13px;border:0;background:transparent;padding:0;cursor:pointer}
    #day-rail-buttons i{display:block;width:11px;height:3px;margin:auto;border-radius:3px;background:var(--c);opacity:.48}
    #day-rail-buttons button.on i{width:20px;height:5px;opacity:1}
    #day-rail-label{position:absolute;right:42px;white-space:nowrap;background:var(--brand);color:#fff;
      border-radius:8px;padding:5px 9px;font-size:11px;font-weight:700;opacity:0;pointer-events:none}
    #day-rail:hover #day-rail-label{opacity:1}
    #delay-fab{display:none;position:fixed;right:18px;bottom:20px;z-index:2600;border:0;border-radius:22px;
      padding:10px 14px;background:var(--brand);color:#fff;font-weight:800;box-shadow:var(--shadow);cursor:pointer}
    body.agenda-on #delay-fab{display:block}
    #delay-modal{position:fixed;inset:0;z-index:4000;background:rgba(15,15,16,.55);backdrop-filter:blur(4px);
      align-items:center;justify-content:center;padding:18px}
    #delay-modal:not([hidden]){display:flex}.delay-card{position:relative;width:min(92vw,480px);background:var(--panel);
      color:var(--ink);border:1px solid var(--line);border-radius:16px;padding:22px;box-shadow:0 18px 60px rgba(0,0,0,.3)}
    .delay-card h2{font-family:var(--serif);margin:0 0 6px}.delay-card p{font-size:13px;color:var(--ink2);line-height:1.5}
    #delay-close{position:absolute;right:12px;top:10px;border:0;background:transparent;color:var(--ink2);font-size:24px;cursor:pointer}
    .delay-form{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:15px}.delay-form label{font-size:11px;color:var(--ink2)}
    .delay-form select,.delay-form input{display:block;width:100%;margin-top:4px;padding:8px;border:1px solid var(--line);
      border-radius:8px;background:var(--bg);color:var(--ink)}#delay-add{grid-column:1/-1;border:0;border-radius:9px;padding:10px;background:var(--brand);color:#fff;font-weight:800}
    .delay-row{display:flex;justify-content:space-between;align-items:center;margin-top:10px;padding:9px;background:var(--bg);border-radius:8px;font-size:13px}
    .delay-row button{border:0;background:transparent;color:#b24c43;cursor:pointer;font-weight:800}
    @media(max-width:600px){
      #view-toggle{top:calc(10px + env(safe-area-inset-top))}
      body.agenda-on #view-toggle{bottom:calc(10px + env(safe-area-inset-bottom))}
      .agenda-hero{padding-top:calc(66px + env(safe-area-inset-top))}
      #agenda-list{padding-left:10px;padding-right:34px}.stop-card{grid-template-columns:66px 1fr;padding-left:9px}
      #day-rail{right:2px}#day-rail-buttons button{width:21px;height:12px}
      #delay-fab{bottom:calc(64px + env(safe-area-inset-bottom));right:12px}
      .agenda-hero h1{font-size:30px}
    }
    </style>
    <script>
    (function(){
      var body=document.body,av=document.getElementById('agenda-view');
      var mapButton=document.getElementById('map-button'),agendaButton=document.getElementById('agenda-button');
      function setView(view){
        var agenda=view==='agenda';body.classList.toggle('agenda-on',agenda);
        mapButton.classList.toggle('on',!agenda);agendaButton.classList.toggle('on',agenda);
        try{localStorage.setItem('jp_view',view);}catch(e){}
        if(!agenda){setTimeout(function(){window.dispatchEvent(new Event('resize'));},80);}
      }
      mapButton.addEventListener('click',function(){setView('map')});
      agendaButton.addEventListener('click',function(){setView('agenda')});
      try{if(localStorage.getItem('jp_view')==='agenda')setView('agenda')}catch(e){}

      var selected='all',query='';
      function applyFilters(){
        document.querySelectorAll('.day-section').forEach(function(section){
          var cityMatch=selected==='all'||section.dataset.city===selected, visible=0;
          section.querySelectorAll('.stop-card').forEach(function(card){
            var match=cityMatch&&(!query||card.dataset.search.indexOf(query)>-1);
            card.classList.toggle('hidden',!match);if(match)visible++;
          });
          section.classList.toggle('hidden',visible===0);
        });
      }
      window.addEventListener('jp-custom-changed',applyFilters);
      document.querySelectorAll('.filter-row button').forEach(function(button){
        button.addEventListener('click',function(){
          selected=button.dataset.city;
          document.querySelectorAll('.filter-row button').forEach(function(b){b.classList.toggle('on',b===button)});
          applyFilters();
        });
      });
      document.getElementById('agenda-search').addEventListener('input',function(){query=this.value.trim().toLowerCase();applyFilters()});

      var skipped={};try{skipped=JSON.parse(localStorage.getItem('jp_skips')||'{}')}catch(e){}
      document.querySelectorAll('.skip').forEach(function(button){
        var id=button.dataset.skip,card=button.closest('.stop-card');
        card.classList.toggle('skipped',!!skipped[id]);
        button.addEventListener('click',function(){
          skipped[id]=!skipped[id];if(!skipped[id])delete skipped[id];
          card.classList.toggle('skipped',!!skipped[id]);
          try{localStorage.setItem('jp_skips',JSON.stringify(skipped))}catch(e){}
        });
      });

      var rail=document.getElementById('day-rail-buttons'),railLabel=document.getElementById('day-rail-label');
      var cityColors=__CITY_COLORS__,labels=__DAY_LABELS__;
      for(var day=1;day<=18;day++){
        var button=document.createElement('button');button.type='button';button.dataset.day=day;
        var city=document.querySelector('.day-section[data-day="'+day+'"]').dataset.city;
        button.innerHTML='<i style="--c:'+cityColors[city]+'"></i>';
        button.addEventListener('mouseenter',function(){railLabel.textContent=labels[this.dataset.day]});
        button.addEventListener('click',function(){
          var section=document.querySelector('.day-section[data-day="'+this.dataset.day+'"]');
          if(section){av.scrollTop=Math.max(0,av.scrollTop+section.getBoundingClientRect().top-av.getBoundingClientRect().top-104)}
        });
        rail.appendChild(button);
      }
      function markRail(){
        var limit=av.getBoundingClientRect().top+115,current=1;
        document.querySelectorAll('.day-section:not(.hidden)').forEach(function(section){
          if(section.getBoundingClientRect().top<=limit)current=+section.dataset.day;
        });
        rail.querySelectorAll('button').forEach(function(button){button.classList.toggle('on',+button.dataset.day===current)});
        railLabel.textContent=labels[current];
      }
      av.addEventListener('scroll',markRail,{passive:true});markRail();

      var modal=document.getElementById('delay-modal'),daySelect=document.getElementById('delay-day');
      for(var d=1;d<=18;d++){var option=document.createElement('option');option.value=d;option.textContent='Day '+d;daySelect.appendChild(option)}
      var delays=[];try{delays=JSON.parse(localStorage.getItem('jp_delays')||'[]')}catch(e){}
      function totalDelay(day){return delays.reduce(function(total,item){return total+(day>=item.day?item.minutes:0)},0)}
      function timeLabel(hour,minutes){
        var total=hour*60+minutes,totalDay=((total%1440)+1440)%1440,h=Math.floor(totalDay/60),m=totalDay%60;
        var suffix=h<12?'AM':'PM',shown=h%12||12;
        return shown+':'+String(m).padStart(2,'0')+' '+suffix;
      }
      function applyDelays(){
        document.querySelectorAll('.card-time').forEach(function(el){el.textContent=timeLabel(+el.dataset.hour,totalDelay(+el.dataset.day))});
        var list=document.getElementById('delay-list');list.innerHTML='';
        if(!delays.length){list.innerHTML='<div class="delay-row">No delays saved.</div>';return}
        delays.forEach(function(item,index){
          var row=document.createElement('div');row.className='delay-row';
          row.innerHTML='<span>Day '+item.day+' onward: '+(item.minutes>=0?'+':'')+item.minutes+' min</span><button type="button" data-index="'+index+'">Remove</button>';
          list.appendChild(row);
        });
        list.querySelectorAll('button').forEach(function(button){button.onclick=function(){delays.splice(+this.dataset.index,1);saveDelays()}});
      }
      function saveDelays(){try{localStorage.setItem('jp_delays',JSON.stringify(delays))}catch(e){}applyDelays()}
      document.getElementById('delay-fab').onclick=function(){modal.hidden=false;applyDelays()};
      document.getElementById('delay-close').onclick=function(){modal.hidden=true};
      modal.addEventListener('click',function(e){if(e.target===modal)modal.hidden=true});
      document.getElementById('delay-add').onclick=function(){
        var minutes=+document.getElementById('delay-minutes').value;if(!minutes)return;
        delays.push({day:+daySelect.value,minutes:minutes});saveDelays();
      };
      applyDelays();
      if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('sw.js',{updateViaCache:'none'}).catch(function(){})})}
    })();
    </script>
    """
    windows_colors = dict(CITY_COLORS)
    return (
        template.replace("__CHIPS__", city_chips)
        .replace("__CARDS__", "".join(cards))
        .replace("__ROUTES__", str(route_count))
        .replace("__CITY_COLORS__", json.dumps(windows_colors))
        .replace("__DAY_LABELS__", json.dumps(DAY_LABELS))
    )


def build_scrubber():
    days = []
    for day in range(1, DAY_COUNT + 1):
        day_stops = [item for item in STOPS if item["day"] == day]
        local = [
            [round(item["lat"], 5), round(item["lon"], 5)]
            for item in day_stops
            if day == 1 or -20 < item["lon"] < 170
        ]
        days.append({
            "day": day,
            "date": DAY_DATES[day][5:].replace("-", "/"),
            "city": DAY_CITY[day],
            "color": city_color(DAY_CITY[day]),
            "points": local,
            "stops": [
                {"lat": item["lat"], "lon": item["lon"], "name": item["name"]}
                for item in day_stops
            ],
        })
    template = r"""
    <div id="scrubber" role="group" aria-label="Trip day timeline">
      <div class="scrubber-top">
        <button id="all-days" class="on" type="button">All 18 days</button>
        <span id="scrubber-label">Jul 28–Aug 14 · whole trip</span>
        <div id="stop-steps">
          <button id="previous-stop" type="button" aria-label="Previous stop">‹</button>
          <button id="focus-stops" type="button" aria-label="Focus first stop">◎</button>
          <button id="next-stop" type="button" aria-label="Next stop">›</button>
        </div>
      </div>
      <div id="scrubber-track"><div id="scrubber-line"></div><div id="scrubber-thumb"></div></div>
    </div>
    <style>
    #scrubber{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:1000;width:min(94vw,900px);
      box-sizing:border-box;padding:10px 16px 13px;border:1px solid var(--line);border-radius:16px;background:var(--panel);
      box-shadow:var(--shadow);font-family:var(--sans);touch-action:none}
    .scrubber-top{display:flex;align-items:center;gap:10px;margin-bottom:5px}
    #all-days{border:1px solid var(--line);border-radius:18px;background:transparent;color:var(--ink2);padding:5px 11px;font-size:12px;font-weight:800}
    #all-days.on{background:var(--brand);border-color:var(--brand);color:#fff}
    #scrubber-label{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;color:var(--ink)}
    #stop-steps{display:flex;gap:4px}#stop-steps button{width:26px;height:26px;padding:0;border:1px solid var(--line);border-radius:8px;
      background:transparent;color:var(--brand);font-size:17px;cursor:pointer}#stop-steps button:disabled{opacity:.28}
    #scrubber-track{position:relative;height:39px;margin:0 12px;cursor:pointer}
    #scrubber-line{position:absolute;left:0;right:0;top:18px;height:5px;border-radius:3px;background:linear-gradient(90deg,#c8555f,#3d877f,#8a63a8,#d18435,#c8555f)}
    .day-tick{position:absolute;top:8px;transform:translateX(-50%);border:0;background:transparent;padding:0;width:19px;cursor:pointer}
    .day-tick i{display:block;width:3px;height:14px;margin:auto;border-radius:3px;background:var(--c);opacity:.55}.day-tick span{font-size:8px;color:var(--ink3)}
    .day-tick.on i{width:4px;height:20px;opacity:1}.day-tick.on span{color:var(--ink)}
    #scrubber-thumb{position:absolute;top:9px;width:22px;height:22px;border-radius:50%;transform:translateX(-50%);
      background:var(--brand);border:3px solid var(--panel);box-shadow:0 2px 8px rgba(0,0,0,.3);opacity:0;pointer-events:none}
    body.hide-far path.farflight{display:none!important}
    @media(max-width:600px){ #scrubber{bottom:calc(8px + env(safe-area-inset-bottom));padding:8px 10px 10px;width:97vw}
      #scrubber-track{margin:0 7px}.day-tick{width:16px}.day-tick span{font-size:7px}}
    </style>
    <script>
    (function(){
      var days=__DAYS__,selected='all',stopIndex=-1,map=null,dragging=false;
      var track=document.getElementById('scrubber-track'),thumb=document.getElementById('scrubber-thumb');
      var label=document.getElementById('scrubber-label'),all=document.getElementById('all-days');
      var previous=document.getElementById('previous-stop'),next=document.getElementById('next-stop'),focus=document.getElementById('focus-stops');
      function getMap(){if(map)return map;if(!window.L)return null;for(var key in window){try{if(window[key] instanceof L.Map){map=window[key];break}}catch(e){}}return map}
      function position(index){return index/(days.length-1)*100}
      days.forEach(function(item,index){
        var button=document.createElement('button');button.type='button';button.className='day-tick';
        button.style.left=position(index)+'%';button.style.setProperty('--c',item.color);
        button.innerHTML='<i></i><span>'+item.day+'</span>';button.onclick=function(e){e.stopPropagation();pick(item.day)};
        track.appendChild(button);
      });
      function setLayers(day){
        document.querySelectorAll('.leaflet-control-layers-overlays label').forEach(function(label){
          var match=label.textContent.trim().match(/^Day\s+(\d+)/);if(!match)return;
          var input=label.querySelector('input'),want=day==='all'||+match[1]===day;
          if(input&&input.checked!==want)input.click();
        });
      }
      function fitDay(day){
        var mapInstance=getMap();if(!mapInstance)return;
        if(day==='all'){mapInstance.setView([36.15,137.2],6);return}
        var points=days[day-1].points;if(!points.length)return;
        if(points.length===1){mapInstance.setView(points[0],13);return}
        try{mapInstance.fitBounds(L.latLngBounds(points),{paddingTopLeft:[55,95],paddingBottomRight:[55,145],maxZoom:14})}catch(e){}
      }
      function updateButtons(){
        var active=selected!=='all',stops=active?days[selected-1].stops:[];
        previous.disabled=!active||!(stopIndex>0||selected>1);
        next.disabled=!active||!(stopIndex<stops.length-1||selected<days.length);
        focus.disabled=!active;
      }
      function pick(day){
        selected=day;stopIndex=-1;var mapInstance=getMap();if(mapInstance)mapInstance.closePopup();
        all.classList.toggle('on',day==='all');thumb.style.opacity=day==='all'?0:1;
        document.body.classList.toggle('hide-far',day==='all');
        document.querySelectorAll('.day-tick').forEach(function(tick,index){tick.classList.toggle('on',day!=='all'&&index===day-1)});
        if(day==='all'){label.textContent='Jul 28–Aug 14 · whole trip'}
        else{var item=days[day-1];thumb.style.left=position(day-1)+'%';thumb.style.background=item.color;label.textContent='Day '+day+' · '+item.date+' · '+item.city}
        setLayers(day);fitDay(day);updateButtons();
      }
      function focusStop(){
        if(selected==='all')return;var stops=days[selected-1].stops,item=stops[stopIndex],mapInstance=getMap();if(!item||!mapInstance)return;
        mapInstance.setView([item.lat,item.lon],15);label.textContent='Day '+selected+' · '+(stopIndex+1)+'/'+stops.length+' · '+item.name;
        var best=null,distance=Infinity;mapInstance.eachLayer(function(layer){if(layer.getLatLng&&layer.getPopup&&layer.getPopup()){
          var ll=layer.getLatLng(),d=Math.abs(ll.lat-item.lat)+Math.abs(ll.lng-item.lon);if(d<distance){distance=d;best=layer}}});
        if(best&&distance<.001)best.openPopup();updateButtons();
      }
      focus.onclick=function(){stopIndex=0;focusStop()};
      next.onclick=function(){if(selected==='all')return;var stops=days[selected-1].stops;if(stopIndex<stops.length-1){stopIndex++;focusStop()}else if(selected<days.length)pick(selected+1)};
      previous.onclick=function(){if(selected==='all')return;if(stopIndex>0){stopIndex--;focusStop()}else if(selected>1)pick(selected-1)};
      all.onclick=function(){pick('all')};
      function dayAt(x){var rect=track.getBoundingClientRect(),fraction=Math.max(0,Math.min(1,(x-rect.left)/rect.width));return Math.round(fraction*(days.length-1))+1}
      track.addEventListener('pointerdown',function(e){dragging=true;try{track.setPointerCapture(e.pointerId)}catch(_){}pick(dayAt(e.clientX));e.preventDefault()});
      track.addEventListener('pointermove',function(e){if(dragging)pick(dayAt(e.clientX))});window.addEventListener('pointerup',function(){dragging=false});
      pick('all');
    })();
    </script>
    """
    return template.replace("__DAYS__", json.dumps(days, ensure_ascii=False))


def build_location_editor():
    """Client-side custom pins.

    User additions intentionally live in localStorage instead of mutating the
    checked-in itinerary. This keeps the source trip safe and makes removal
    reversible without requiring a server or account.
    """
    return r"""
    <button id="location-fab" type="button">＋ Add place</button>
    <button id="share-fab" type="button">↗ Share</button>
    <div id="share-toast" role="status"></div>
    <div id="pick-hint" hidden>Tap the map where you want to add a place · <button type="button">Cancel</button></div>
    <div id="location-modal" hidden>
      <div class="location-card">
        <button id="location-close" type="button" aria-label="Close">×</button>
        <h2>Add a location</h2>
        <p>Place a personal pin without changing the original itinerary.</p>
        <form id="location-form">
          <label class="location-wide">Name
            <input id="location-name" maxlength="100" required placeholder="Restaurant, temple, shop…">
          </label>
          <label>Day
            <select id="location-day"></select>
          </label>
          <label>City
            <select id="location-city">
              <option>Tokyo</option><option>Kanazawa</option><option>Kyoto</option>
              <option>Osaka</option><option>Transit</option>
            </select>
          </label>
          <label>Latitude
            <input id="location-lat" type="number" min="-90" max="90" step="any" required>
          </label>
          <label>Longitude
            <input id="location-lon" type="number" min="-180" max="180" step="any" required>
          </label>
          <button id="pick-location" class="secondary location-wide" type="button">◎ Pick a point on the map</button>
          <label class="location-wide">Notes
            <textarea id="location-notes" maxlength="500" rows="3" placeholder="Reservation, opening time, what to order…"></textarea>
          </label>
          <button class="primary location-wide" type="submit">Save location</button>
        </form>
        <div class="saved-heading">Your saved locations</div>
        <div id="custom-location-list"></div>
      </div>
    </div>
    <style>
    #location-fab,#share-fab{position:fixed;z-index:2650;border:1px solid var(--line);border-radius:22px;
      background:var(--panel);color:var(--ink);box-shadow:var(--shadow);padding:10px 14px;font:800 12px var(--sans);cursor:pointer}
    #location-fab{right:16px;bottom:72px;background:var(--brand);border-color:var(--brand);color:#fff}
    #share-fab{right:62px;top:12px}
    body.agenda-on #location-fab{right:112px;bottom:20px}
    body.agenda-on #share-fab{display:none}
    #share-toast{position:fixed;z-index:5200;left:50%;bottom:28px;transform:translate(-50%,20px);
      padding:9px 13px;border-radius:9px;background:#232326;color:#fff;font:700 12px var(--sans);
      opacity:0;pointer-events:none;transition:.2s}
    #share-toast.show{opacity:1;transform:translate(-50%,0)}
    #pick-hint{position:fixed;z-index:5100;left:50%;top:68px;transform:translateX(-50%);white-space:nowrap;
      border-radius:22px;background:#232326;color:#fff;padding:10px 14px;font:700 12px var(--sans);box-shadow:var(--shadow)}
    #pick-hint:not([hidden]){display:block}#pick-hint button{border:0;background:transparent;color:#f4a0a7;font-weight:800;cursor:pointer}
    #location-modal{position:fixed;inset:0;z-index:5000;background:rgba(15,15,17,.58);backdrop-filter:blur(5px);
      align-items:center;justify-content:center;padding:18px;font-family:var(--sans)}
    #location-modal:not([hidden]){display:flex}.location-card{position:relative;width:min(94vw,520px);max-height:90vh;overflow:auto;
      box-sizing:border-box;border:1px solid var(--line);border-radius:17px;background:var(--panel);color:var(--ink);
      padding:22px;box-shadow:0 20px 70px rgba(0,0,0,.35)}
    .location-card h2{font:600 25px var(--serif);margin:0 0 4px}.location-card>p{font-size:12px;color:var(--ink2);margin:0 0 15px}
    #location-close{position:absolute;right:11px;top:8px;border:0;background:transparent;color:var(--ink2);font-size:26px;cursor:pointer}
    #location-form{display:grid;grid-template-columns:1fr 1fr;gap:10px}
    #location-form label{font-size:11px;font-weight:700;color:var(--ink2)}
    #location-form input,#location-form select,#location-form textarea{display:block;width:100%;box-sizing:border-box;margin-top:5px;
      padding:9px;border:1px solid var(--line);border-radius:9px;background:var(--bg);color:var(--ink);font:13px var(--sans)}
    #location-form textarea{resize:vertical}.location-wide{grid-column:1/-1}
    #location-form button{border-radius:10px;padding:10px;font-weight:800;cursor:pointer}
    #location-form .primary{border:0;background:var(--brand);color:#fff}
    #location-form .secondary{border:1px solid var(--line);background:var(--panel2);color:var(--ink)}
    .saved-heading{margin:18px 0 7px;padding-top:14px;border-top:1px solid var(--line);font-size:12px;font-weight:800;color:var(--ink2)}
    .custom-list-row{display:flex;align-items:center;gap:9px;padding:8px 0;border-bottom:1px solid var(--line);font-size:12px}
    .custom-list-row span{flex:1}.custom-list-row small{color:var(--ink3)}.custom-list-row button{border:0;background:transparent;color:#c0524a;font-weight:800;cursor:pointer}
    .custom-empty{font-size:12px;color:var(--ink3);padding:4px 0}.custom-pin{filter:hue-rotate(325deg) saturate(1.2)}
    @media(max-width:600px){
      #location-fab{bottom:calc(112px + env(safe-area-inset-bottom));right:9px}
      #share-fab{top:calc(10px + env(safe-area-inset-top));right:58px;padding:10px 11px}
      body.agenda-on #location-fab{right:108px;bottom:calc(62px + env(safe-area-inset-bottom))}
      #location-modal{padding:8px}.location-card{max-height:94vh;padding:18px}
      #pick-hint{top:calc(58px + env(safe-area-inset-top));font-size:11px;max-width:94vw;white-space:normal;text-align:center}
    }
    </style>
    <script>
    (function(){
      var STORAGE='jp_custom_locations',items=[],map=null,group=null,picking=false;
      var modal=document.getElementById('location-modal'),form=document.getElementById('location-form');
      var latInput=document.getElementById('location-lat'),lonInput=document.getElementById('location-lon');
      var hint=document.getElementById('pick-hint'),list=document.getElementById('custom-location-list');
      var colors={Tokyo:'#c8555f',Kanazawa:'#3d877f',Kyoto:'#8a63a8',Osaka:'#d18435',Transit:'#6f747b'};
      function esc(value){return String(value||'').replace(/[&<>"']/g,function(ch){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]})}
      function load(){try{items=JSON.parse(localStorage.getItem(STORAGE)||'[]');if(!Array.isArray(items))items=[]}catch(e){items=[]}}
      function save(){try{localStorage.setItem(STORAGE,JSON.stringify(items))}catch(e){}render()}
      function getMap(){
        if(map)return map;if(!window.L)return null;
        for(var key in window){try{if(window[key] instanceof L.Map){map=window[key];break}}catch(e){}}
        return map;
      }
      function mapLink(item){return 'https://www.google.com/maps?q='+item.lat+','+item.lon}
      function remove(id){items=items.filter(function(item){return item.id!==id});save()}
      window.jpRemoveLocation=remove;
      function renderMap(){
        var instance=getMap();if(!instance)return false;
        if(group)group.clearLayers();else group=L.featureGroup().addTo(instance);
        items.forEach(function(item){
          var icon=null;
          try{icon=L.AwesomeMarkers.icon({icon:'plus',prefix:'fa',markerColor:'lightred'})}catch(e){}
          var marker=L.marker([item.lat,item.lon],icon?{icon:icon}:{});
          marker.bindPopup('<div class="popup-card" style="--place:'+colors[item.city]+'"><div class="popup-kicker">Your location · Day '+item.day+'</div>'+
            '<div class="popup-title">'+esc(item.name)+'</div><div class="popup-notes">'+esc(item.notes||'Personal itinerary addition')+'</div>'+
            '<div class="popup-links"><a target="_blank" href="'+mapLink(item)+'">📍 Map</a>'+
            '<a href="#" onclick="jpRemoveLocation(\''+item.id+'\');return false">Remove</a></div></div>');
          marker.bindTooltip('<b>'+esc(item.name)+'</b><br><small>Your location · Day '+item.day+'</small>');
          marker.addTo(group);
        });
        return true;
      }
      function renderAgenda(){
        document.querySelectorAll('.custom-stop-card').forEach(function(card){card.remove()});
        items.forEach(function(item){
          var section=document.querySelector('.day-section[data-day="'+item.day+'"]');if(!section)return;
          var card=document.createElement('article');card.className='stop-card custom-stop-card';
          card.dataset.day=item.day;card.dataset.city=item.city;
          card.dataset.search=(item.name+' '+item.notes+' '+item.city+' custom').toLowerCase();
          card.style.setProperty('--city',colors[item.city]);
          card.innerHTML='<button class="skip custom-remove" type="button" title="Remove location">×</button>'+
            '<div class="card-time">Custom</div><div class="card-main"><div class="card-title">＋ '+esc(item.name)+'</div>'+
            '<div class="card-meta">'+esc(item.city)+' · added on this device</div><div class="card-notes">'+esc(item.notes||'Personal itinerary addition')+'</div>'+
            '<div class="card-links"><a target="_blank" href="'+mapLink(item)+'">Map</a><a href="#" class="custom-remove-link">Remove</a></div></div>';
          card.querySelector('.custom-remove').onclick=function(){remove(item.id)};
          card.querySelector('.custom-remove-link').onclick=function(e){e.preventDefault();remove(item.id)};
          section.appendChild(card);
        });
      }
      function renderList(){
        list.innerHTML='';
        if(!items.length){list.innerHTML='<div class="custom-empty">No personal locations yet.</div>';return}
        items.slice().sort(function(a,b){return a.day-b.day}).forEach(function(item){
          var row=document.createElement('div');row.className='custom-list-row';
          row.innerHTML='<span><b>'+esc(item.name)+'</b><br><small>Day '+item.day+' · '+esc(item.city)+'</small></span><button type="button">Remove</button>';
          row.querySelector('button').onclick=function(){remove(item.id)};list.appendChild(row);
        });
      }
      function render(){
        renderMap();renderAgenda();renderList();window.dispatchEvent(new Event('jp-custom-changed'));
      }
      function show(){modal.hidden=false;renderList()}
      function hide(){modal.hidden=true}
      document.getElementById('location-fab').onclick=show;
      document.getElementById('location-close').onclick=hide;
      modal.addEventListener('click',function(e){if(e.target===modal)hide()});
      var daySelect=document.getElementById('location-day');
      for(var day=1;day<=18;day++){var option=document.createElement('option');option.value=day;option.textContent='Day '+day;daySelect.appendChild(option)}
      form.addEventListener('submit',function(e){
        e.preventDefault();var lat=+latInput.value,lon=+lonInput.value;
        if(!Number.isFinite(lat)||!Number.isFinite(lon))return;
        items.push({id:Date.now().toString(36)+Math.random().toString(36).slice(2,7),
          name:document.getElementById('location-name').value.trim(),day:+daySelect.value,
          city:document.getElementById('location-city').value,lat:lat,lon:lon,
          notes:document.getElementById('location-notes').value.trim()});
        form.reset();latInput.value='35.6812';lonInput.value='139.7671';save();hide();
      });
      function endPick(){picking=false;hint.hidden=true}
      document.getElementById('pick-location').onclick=function(){
        var instance=getMap();if(!instance)return;
        if(document.body.classList.contains('agenda-on'))document.getElementById('map-button').click();
        hide();picking=true;hint.hidden=false;
        instance.once('click',function(event){if(!picking)return;latInput.value=event.latlng.lat.toFixed(6);
          lonInput.value=event.latlng.lng.toFixed(6);endPick();show()});
      };
      hint.querySelector('button').onclick=endPick;
      function toast(message){var el=document.getElementById('share-toast');el.textContent=message;el.classList.add('show');setTimeout(function(){el.classList.remove('show')},1800)}
      function encodedShareUrl(){
        var base=location.href.split('#')[0];if(!items.length)return base;
        try{return base+'#places='+encodeURIComponent(btoa(unescape(encodeURIComponent(JSON.stringify(items)))))}
        catch(e){return base}
      }
      function importSharedLocations(){
        if(location.hash.indexOf('#places=')!==0)return;
        try{
          var raw=decodeURIComponent(location.hash.slice(8));
          var shared=JSON.parse(decodeURIComponent(escape(atob(raw))));
          if(!Array.isArray(shared))return;
          shared.forEach(function(item){
            if(!item||!item.name||!Number.isFinite(+item.lat)||!Number.isFinite(+item.lon))return;
            var duplicate=items.some(function(saved){return saved.name===item.name&&saved.day===+item.day&&Math.abs(saved.lat-(+item.lat))<.000001&&Math.abs(saved.lon-(+item.lon))<.000001});
            if(!duplicate)items.push({id:Date.now().toString(36)+Math.random().toString(36).slice(2,7),
              name:String(item.name).slice(0,100),day:Math.max(1,Math.min(18,+item.day||1)),
              city:colors[item.city]?item.city:'Tokyo',lat:+item.lat,lon:+item.lon,
              notes:String(item.notes||'').slice(0,500)});
          });
          try{localStorage.setItem(STORAGE,JSON.stringify(items));history.replaceState(null,'',location.pathname+location.search)}catch(e){}
          setTimeout(function(){toast('Shared locations added')},250);
        }catch(e){}
      }
      document.getElementById('share-fab').onclick=async function(){
        var url=encodedShareUrl();
        var data={title:'Japan Family Trip',text:'Our interactive Japan itinerary'+(items.length?' with '+items.length+' added location'+(items.length===1?'':'s'):''),url:url};
        try{if(navigator.share){await navigator.share(data)}else if(navigator.clipboard){await navigator.clipboard.writeText(url);toast('Japan link copied')}else{prompt('Copy this link',url)}}catch(e){}
      };
      load();importSharedLocations();latInput.value='35.6812';lonInput.value='139.7671';
      if(!renderMap()){var attempts=0,timer=setInterval(function(){if(renderMap()||++attempts>50){clearInterval(timer);render()}},100)}
      render();
    })();
    </script>
    """


def build_theme():
    return r"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&display=swap" rel="stylesheet">
    <button id="theme-toggle" type="button" aria-label="Toggle dark mode">🌙</button>
    <style>
    :root{--sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;--serif:'Fraunces',Georgia,serif;
      --bg:#f5f1e9;--panel:#fffdf8;--panel2:#eee8dc;--line:#e3ddcf;--ink:#211e1a;--ink2:#6d675d;
      --ink3:#999083;--brand:#c34f5b;--shadow:0 2px 14px rgba(40,30,24,.10)}
    :root[data-theme="dark"]{--bg:#111113;--panel:#1a1a1d;--panel2:#242428;--line:#303035;--ink:#eeeeef;
      --ink2:#aaa7a2;--ink3:#747379;--brand:#e06e78;--shadow:0 2px 14px rgba(0,0,0,.45)}
    html,body{height:100vh;margin:0;background:var(--bg);overscroll-behavior:none}.folium-map{position:fixed!important;inset:0;width:100vw!important;height:100vh!important}
    @supports(height:100lvh){html,body,.folium-map{height:100lvh!important}}
    #theme-toggle{position:fixed;right:12px;top:12px;z-index:2700;width:40px;height:40px;border-radius:50%;border:1px solid var(--line);
      background:var(--panel);color:var(--ink);box-shadow:var(--shadow);font-size:17px;cursor:pointer}
    #map-title{position:fixed;left:50px;top:10px;z-index:900;background:var(--panel);color:var(--ink);border:1px solid var(--line);
      border-radius:12px;padding:9px 13px;box-shadow:var(--shadow);font-family:var(--sans)}
    .home-link{font-size:10px;font-weight:800;color:var(--brand);text-decoration:none}.map-heading{font-family:var(--serif);font-size:18px;font-weight:600}
    .title-sub{font-size:12px;color:var(--ink2);margin-top:2px}.title-legend{font-size:10px;color:var(--ink3);margin-top:4px}
    .leaflet-top.leaflet-right{margin-top:52px}.leaflet-control-layers{background:var(--panel)!important;color:var(--ink)!important;border:1px solid var(--line)!important;
      border-radius:12px!important;box-shadow:var(--shadow)!important}.leaflet-control-layers label{color:var(--ink);font-size:12px}
    :root[data-theme="dark"] .leaflet-control-layers-toggle{filter:invert(.85)}:root[data-theme="dark"] .leaflet-bar a{background:var(--panel);color:var(--ink);border-color:var(--line)}
    :root[data-theme="dark"] .leaflet-control-attribution{background:rgba(26,26,29,.88)!important;color:var(--ink3)!important}
    .leaflet-popup-content-wrapper{background:var(--panel)!important;color:var(--ink)!important;border:1px solid var(--line);border-radius:15px!important}
    .leaflet-popup-tip{background:var(--panel)!important}.leaflet-popup-content{margin:15px 17px!important}
    .popup-kicker{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--place);font-weight:800}.popup-title{font-family:var(--serif);font-size:17px;font-weight:600;margin:3px 0 8px}
    .popup-notes{font-size:12.5px;line-height:1.52;color:var(--ink2)}.locked{display:inline-block;font-size:10px;font-weight:800;color:#a14438;background:#f4dfd7;padding:3px 7px;border-radius:10px;margin-bottom:8px}
    :root[data-theme="dark"] .locked{background:#38231e;color:#ef9e85}.climate{display:flex;gap:8px;margin-top:11px;padding:9px;border-radius:9px;background:var(--panel2);font-size:11px;color:var(--ink2)}
    .climate-icon{font-size:23px}.climate b{color:var(--ink)}.climate small{color:var(--ink3)}.popup-links{display:flex;gap:14px;margin-top:10px}
    .popup-links a{font-size:12px;font-weight:800;text-decoration:none;color:var(--place)}.leaflet-tooltip{background:var(--panel)!important;color:var(--ink)!important;border:1px solid var(--line)!important;border-radius:8px!important}
    @media(max-width:600px){ #map-title{left:8px;top:calc(58px + env(safe-area-inset-top));max-width:calc(100vw - 85px)}.title-route,.title-legend{display:none}
      .leaflet-top.leaflet-left{margin-top:calc(55px + env(safe-area-inset-top))}#theme-toggle{top:calc(10px + env(safe-area-inset-top))}
      .leaflet-control-attribution{font-size:8px!important;opacity:.7}.leaflet-popup-content{margin:13px!important}}
    @media all and (display-mode:standalone){ #theme-toggle{top:calc(12px + env(safe-area-inset-top))}}
    </style>
    <script>
    (function(){
      var key='trip_theme';
      function switchBase(dark){
        document.querySelectorAll('.leaflet-control-layers-base label').forEach(function(label){
          var input=label.querySelector('input'),want=dark?/Dark/.test(label.textContent):/Street/.test(label.textContent);
          if(input&&want&&!input.checked)input.click();
        });
      }
      function apply(theme,switchMap){
        document.documentElement.dataset.theme=theme;var button=document.getElementById('theme-toggle');
        button.textContent=theme==='dark'?'☀️':'🌙';var meta=document.querySelector('meta[name="theme-color"]');
        if(meta)meta.content=theme==='dark'?'#111113':'#f5f1e9';if(switchMap)setTimeout(function(){switchBase(theme==='dark')},80);
      }
      var saved=null;try{saved=localStorage.getItem(key)}catch(e){}var system=matchMedia&&matchMedia('(prefers-color-scheme:dark)').matches;
      var theme=saved||(system?'dark':'light');apply(theme,false);window.addEventListener('load',function(){setTimeout(function(){switchBase(theme==='dark')},400)});
      document.getElementById('theme-toggle').onclick=function(){theme=document.documentElement.dataset.theme==='dark'?'light':'dark';try{localStorage.setItem(key,theme)}catch(e){}apply(theme,true)};
    })();
    </script>
    """


def build_touch_cleanup():
    return r"""
    <script>
    (function(){
      function clean(){
        if(!window.L||!matchMedia('(hover:none)').matches)return false;var map=null;
        for(var key in window){try{if(window[key] instanceof L.Map){map=window[key];break}}catch(e){}}
        if(!map)return false;function strip(layer){try{if(layer.getLatLng&&layer.unbindTooltip)layer.unbindTooltip();if(layer.eachLayer)layer.eachLayer(strip)}catch(e){}}
        map.eachLayer(strip);map.on('layeradd',function(e){strip(e.layer)});return true;
      }
      if(!clean()){var count=0,timer=setInterval(function(){if(clean()||++count>40)clearInterval(timer)},100)}
    })();
    </script>
    """


def postprocess(path):
    with open(path, encoding="utf-8") as source:
        html = source.read()
    html = re.sub(r'(<(meta|link|img|br|hr|input)[^>]*?)\s*/>', r"\1>", html)
    html = re.sub(
        r'<meta\s+name="viewport"[^>]*>',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, '
        'maximum-scale=1.0, user-scalable=no, viewport-fit=cover">',
        html,
        count=1,
    )
    metadata = (
        '    <meta name="theme-color" content="#111113">\n'
        '    <meta name="apple-mobile-web-app-capable" content="yes">\n'
        '    <meta name="mobile-web-app-capable" content="yes">\n'
        '    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
        '    <meta name="apple-mobile-web-app-title" content="Japan Trip">\n'
        '    <link rel="manifest" href="manifest.json">\n'
    )
    html = html.replace("</head>", metadata + "</head>", 1)
    with open(path, "w", encoding="utf-8") as output:
        output.write(html)


if __name__ == "__main__":
    print("Building Japan routes…")
    trip_routes = build_routes()
    print(f"  OK: {len(trip_routes)} route segments cached in {ROUTE_CACHE}")
    print("Building interactive map…")
    generated_map = build_map(trip_routes)
    generated_map.save(OUTPUT)
    postprocess(OUTPUT)
    print(f"  OK: Saved {OUTPUT} ({os.path.getsize(OUTPUT) / 1024:.0f} KB)")
