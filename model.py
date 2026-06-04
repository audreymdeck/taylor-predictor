import json
from datetime import datetime
from collections import defaultdict

def load_data():
    with open("data/setlists.json") as f:
        setlists = json.load(f)
    return setlists["shows"]

def score_songs(shows_so_far, all_songs):
    total_shows = len(shows_so_far)
    last_played = {}
    play_count = defaultdict(int)
    standalone_count = defaultdict(int)

    for i, show in enumerate(shows_so_far):
        for song in show["surprise_songs"]:
            last_played[song] = i
            play_count[song] += 1
        for song in show.get("surprise_standalone", []):
            standalone_count[song] += 1

    scores = {}
    for song in all_songs:
        if song not in last_played:
            days_since = total_shows
        else:
            days_since = total_shows - last_played[song] - 1

        frequency_score = 1 / (play_count.get(song, 0) + 1)
        recency_score = days_since / total_shows
        standalone_penalty = standalone_count.get(song, 0) * 0.1

        scores[song] = (recency_score * 0.6) + (frequency_score * 0.4) - standalone_penalty

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

def backtest(shows):
    all_songs = list(set(
        song for show in shows for song in show["surprise_songs"]
    ))

    results = []
    correct_top5 = 0
    correct_top10 = 0
    total_predictions = 0

    for i in range(10, len(shows)):
        shows_so_far = shows[:i]
        actual = shows[i]["surprise_songs"]
        if not actual:
            continue

        predictions = score_songs(shows_so_far, all_songs)
        top5 = [s for s, _ in predictions[:5]]
        top10 = [s for s, _ in predictions[:10]]

        hit_top5 = any(song in top5 for song in actual)
        hit_top10 = any(song in top10 for song in actual)

        if hit_top5:
            correct_top5 += 1
        if hit_top10:
            correct_top10 += 1
        total_predictions += 1

        results.append({
            "show_number": shows[i]["show_number"],
            "date": shows[i]["date"],
            "city": shows[i]["city"],
            "actual": actual,
            "predicted_top10": top10,
            "hit_top5": hit_top5,
            "hit_top10": hit_top10
        })

    accuracy_top5 = correct_top5 / total_predictions if total_predictions > 0 else 0
    accuracy_top10 = correct_top10 / total_predictions if total_predictions > 0 else 0

    print(f"Total shows evaluated: {total_predictions}")
    print(f"Top 5 accuracy: {accuracy_top5:.1%}")
    print(f"Top 10 accuracy: {accuracy_top10:.1%}")

    return results, accuracy_top5, accuracy_top10

def main():
    shows = load_data()
    print(f"Loaded {len(shows)} shows")

    results, acc5, acc10 = backtest(shows)

    all_songs = list(set(
        song for show in shows for song in show["surprise_songs"]
    ))
    final_predictions = score_songs(shows, all_songs)

    import os
    os.makedirs("data", exist_ok=True)
    with open("data/predictions.json", "w") as f:
        json.dump({
            "accuracy_top5": round(acc5, 4),
            "accuracy_top10": round(acc10, 4),
            "total_shows_evaluated": len(results),
            "backtest_results": results,
            "most_overdue": [
                {"name": s, "score": round(sc, 4)}
                for s, sc in final_predictions[:20]
            ]
        }, f, indent=2)

    print("\nTop 20 most overdue songs at end of tour:")
    for song, score in final_predictions[:20]:
        print(f"  {song}: {score:.4f}")

if __name__ == "__main__":
    main()
