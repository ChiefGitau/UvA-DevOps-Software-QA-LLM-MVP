#!/usr/bin/env python3
import argparse, json, sys

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def count_bandit_high_or_medium(bandit):
    results = bandit.get("results", []) or []
    return sum(1 for r in results if (r.get("issue_severity") or "").upper() in ("HIGH", "MEDIUM"))

def max_radon_cc(radon):
    mx = 0
    for _, items in (radon or {}).items():
        for it in items or []:
            c = it.get("complexity")
            if isinstance(c, int):
                mx = max(mx, c)
    return mx

def count_secrets(trufflehog_jsonl_path):
    try:
        n = 0
        with open(trufflehog_jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    n += 1
        return n
    except Exception:
        return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bandit", required=True)
    ap.add_argument("--radon", required=True)
    ap.add_argument("--secrets", required=True)

    ap.add_argument("--max_bandit_high", type=int, default=0)
    ap.add_argument("--max_cc", type=int, default=15)
    ap.add_argument("--max_secrets", type=int, default=0)
    args = ap.parse_args()

    bandit = load_json(args.bandit, {})
    radon = load_json(args.radon, {})

    b = count_bandit_high_or_medium(bandit)
    cc = max_radon_cc(radon)
    s = count_secrets(args.secrets)

    print(f"[gate] bandit_high_or_medium={b} (max {args.max_bandit_high})")
    print(f"[gate] max_cc={cc} (max {args.max_cc})")
    print(f"[gate] secrets={s} (max {args.max_secrets})")

    failed = (b > args.max_bandit_high) or (cc > args.max_cc) or (s > args.max_secrets)
    if failed:
        print("[gate] FAILED")
        sys.exit(1)
    print("[gate] PASSED")
    sys.exit(0)

if __name__ == "__main__":
    main()
