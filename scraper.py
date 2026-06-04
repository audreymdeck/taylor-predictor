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
        section_name = section.get("name", "")
        for song in section.get("song", []):
            name = song.get("name", "")
            if not name:
                continue
            is_surprise = "Surprise" in section_name or song.get("info", "")
            entry = {
                "name": name,
                "encore": bool(is_encore),
                "surprise": bool(is_surprise),
                "info": song.get("info", "")
            }
            songs.append(entry)
            if is_surprise:
                surprise_songs.append(name)
    return songs, surprise_songs

def main():
    print("Fetching Eras Tour setlists...")
    raw = fetch_all_eras_tour()
    print(f"Found {len(raw)} Eras Tour shows")

    processed = []
    all_surprise = []

    for s in raw:
        date = s.get("eventDate", "")
        venue = s.get("venue", {})
        songs, surprises = extract_songs(s)
        processed.append({
            "date": date,
            "city": venue.get("city", {}).get("name", ""),
            "country": venue.get("city", {}).get("country", {}).get("name", ""),
            "venue": venue.get("name", ""),
            "songs": songs,
            "surprise_songs": surprises,
            "show_number": 0
        })
        all_surprise.extend(surprises)

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
    with open("data/surprise_songs.json", "w") as f:
        json.dump({
            "pulled_at": datetime.utcnow().isoformat(),
            "total_unique": len(surprise_counts),
            "songs": [{"name": k, "count": v} for k, v in surprise_counts.most_common()]
        }, f, indent=2)

    print(f"Done. Saved {len(processed)} shows.")
    print(f"Unique surprise songs: {len(surprise_counts)}")

if __name__ == "__main__":
    main()
