"""Unit tests for the find_players ranking formula.

These lock in today's design decisions so a future change
that silently breaks them gets caught:
- Salah must rank first among attackers (MF label must not hide him)
- Muniz must not crack the top 10 (small-sample shrinkage works)
- goalkeepers must never appear in outfield searches

No LLM, no API calls — runs in milliseconds.
Run from project root: python -m eval.test_ranking
"""

from data.loader import find_players, get_player_stats

THRESHOLD_TOP = 10


def run():
    results = []
    top = find_players(position="FW", limit=THRESHOLD_TOP)
    names = [p["name"] for p in top]

    # 1. Salah is the best attacker despite his MF label
    results.append(("salah_ranks_first", names[0] == "Mohamed Salah"))

    # 2. Muniz (964 min) stays out of the top 10 after shrinkage
    results.append(("muniz_out_of_top10", "Rodrigo Muniz" not in names))

    # 3. no goalkeeper leaks into an attacker search
    results.append(("no_gk_in_results", all("GK" not in p["position"] for p in top)))

    # 4. goalkeeper lookup returns keeper stats, not outfield zeros
    v = get_player_stats("Vicario")
    stats = v["records"][0]["stats"]
    results.append(("gk_lookup_has_saves", stats.get("save_pct") is not None))

    # 5. score must be built from npg, not goals.
    # Recompute Salah's score from his own DB row and compare.
    # If someone swaps npg back to goals, the values diverge (0.81 vs ~0.90).
    salah = next(p for p in top if p["name"] == "Mohamed Salah")
    s = get_player_stats("Salah")["records"][0]["stats"]
    expected = round((s["npg"] + s["assists"] + 0.315 * 15) / (s["nineties"] + 15), 2)
    results.append(("score_uses_npg_not_goals", salah["score"] == expected))

    passed = 0
    for name, ok in results:
        mark = "✅" if ok else "❌"
        print(f"{mark} {name}")
        passed += ok
    print(f"Pass rate: {passed}/{len(results)}")
    return passed == len(results)


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)