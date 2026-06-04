import requests
import json
import os
import time
from datetime import datetime

API_KEY = os.environ.get("SETLIST_API_KEY")
HEADERS = {
    "x-api-key": API_KEY,
    "Accept": "application/json"
}
BASE_URL = "https://api.setlist.fm/rest/1.0"
TAYLOR_MBID = "20244d07-534f-4eff-b4d4-930878889970"

def get_setlists(page=1):
    url = f"{BASE_URL}/artist/{TAYLOR_MBID}/setlists?p={page}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 429:
        print("Rate limited, waiting 10 seconds...")
        time.sleep(10)
        r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()

def fetch_all_eras_tour():
    all_setlists = []
    page = 1
    while True:
        print(f"Fetching page {page}...")
        data = get_setlists(page)
        setlists = data.get("setlist", [])
        if not setlists:
            break
        for s in setlists:
            tour = s.get("tour", {})
            if tour and "Eras" in tour.get("name", ""):
                all_setlists.append(s)
        total = int(data.get("total", 0))
        items_per_page = int(data.get("itemsPerPage", 20))
        if page * items_per_page >= total:
            break
        page += 1
        time.sleep(2)
    return all_setlists

def extract_songs(setlist):
    songs = []
    surprise_songs = []
    for section in setlist.get("sets", {}).get("set", []):
        is_encore = section.get("encore", 0)
        section_name = section.get("name", "").lower()
        is_surprise_section = "surprise" in section_name
        for song in section.get("song", []):
            name = song.get("name", "")
            if not name:
                continue
            parts = [p.strip() for p in name.replace(" + ", " / ").replace(" with ", " / ").split(" / ")]
            for part in parts:
                if not part:
                    continue
                entry = {
                    "name": part,
                    "encore": bool(is_encore),
                    "surprise": is_surprise_section,
                    "mashup": len(parts) > 1,
                    "original_entry": name,
                    "info": song.get("info", "")
                }
                songs.append(entry)
                if is_surprise_section:
                    surprise_songs.append(part)
    return songs, surprise_songs

def main():
    print("Fetching Eras Tour setlists...")
    raw = fetch_all_eras_tour()
    print(f"Found {len(raw)} Eras Tour shows")

    processed = []
    all_surprise = []
    all_surprise_standalone = []
    all_surprise_mashup = []

    for s in raw:
        date = s.get("eventDate", "")
        venue = s.get("venue", {})
        songs, surprises = extract_songs(s)

        standalone = [song["name"] for song in songs if song["surprise"] and not song["mashup"]]
        mashup = [song["name"] for song in songs if song["surprise"] and song["mashup"]]

        processed.append({
            "date": date,
            "city": venue.get("city", {}).get("name", ""),
            "country": venue.get("city", {}).get("country", {}).get("name", ""),
            "venue": venue.get("name", ""),
            "songs": songs,
            "surprise_songs": surprises,
            "surprise_standalone": standalone,
            "surprise_mashup": mashup,
            "show_number": 0
        })
        all_surprise.extend(surprises)
        all_surprise_standalone.extend(standalone)
        all_surprise_mashup.extend(mashup)

    processed.sort(key=lambda x: datetime.strptime(x["date"], "%d-%m-%Y") if x["date"] else datetime.min)
    for i, show in enumerate(processed):
        show["show_number"] = i + 1

    os.makedirs("data", exist_ok=True)
    with open("data/setlists.json", "w") as f:
        json.dump({
            "pulled_at": datetime.utcnow().isoformat(),
            "total_shows": len(processed),
            "shows": processed
        }, f, indent=2)

    from collections import Counter
    surprise_counts = Counter(all_surprise)
    standalone_counts = Counter(all_surprise_standalone)
    mashup_counts = Counter(all_surprise_mashup)

    with open("data/surprise_songs.json", "w") as f:
        json.dump({
            "pulled_at": datetime.utcnow().isoformat(),
            "total_unique": len(surprise_counts),
            "songs": [
                {
                    "name": k,
                    "total_count": v,
                    "standalone_count": standalone_counts.get(k, 0),
                    "mashup_count": mashup_counts.get(k, 0)
                }
                for k, v in surprise_counts.most_common()
            ]
        }, f, indent=2)

    print(f"Done. Saved {len(processed)} shows.")
    print(f"Unique surprise songs: {len(surprise_counts)}")
    print("Top 10 surprise songs:")
    for song, count in surprise_counts.most_common(10):
        print(f"  {song}: {count} total ({standalone_counts.get(song,0)} standalone, {mashup_counts.get(song,0)} mashup)")

if __name__ == "__main__":
    main()
