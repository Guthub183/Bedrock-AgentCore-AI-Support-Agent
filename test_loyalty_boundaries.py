import json
import main

test_cases = [
    {
        "name": "Below 500 boundary (450 pts, $100 order)",
        "pts": 450,
        "tier": "Silver",
        "order": 100.0,
        "cat": "standard",
        "exp_redeemed": 0,
        "rationale": "Eligible points (450) < 500 minimum block; 0 points redeemed."
    },
    {
        "name": "Just below 500 boundary (499 pts, $100 order)",
        "pts": 499,
        "tier": "Silver",
        "order": 100.0,
        "cat": "standard",
        "exp_redeemed": 0,
        "rationale": "Eligible points (499) < 500 minimum block; 0 points redeemed."
    },
    {
        "name": "Exactly at 500 boundary (500 pts, $100 order)",
        "pts": 500,
        "tier": "Silver",
        "order": 100.0,
        "cat": "standard",
        "exp_redeemed": 500,
        "rationale": "Eligible points exactly 500; 1 block of 500 redeemed ($5.00 discount)."
    },
    {
        "name": "Just above 500 boundary (550 pts, $100 order)",
        "pts": 550,
        "tier": "Silver",
        "order": 100.0,
        "cat": "standard",
        "exp_redeemed": 500,
        "rationale": "Eligible points (550) floored to nearest 500-point block (500)."
    },
    {
        "name": "Above 1000 boundary (1499 pts, $100 order)",
        "pts": 1499,
        "tier": "Gold",
        "order": 100.0,
        "cat": "standard",
        "exp_redeemed": 1000,
        "rationale": "Eligible points (1499) floored to nearest 500-point block (1000)."
    },
    {
        "name": "50% order cap exact (4000 pts, $50 order)",
        "pts": 4000,
        "tier": "Silver",
        "order": 50.0,
        "cat": "standard",
        "exp_redeemed": 2500,
        "rationale": "50% of $50 = $25 (2500 pts). 2500 is multiple of 500; exactly 2500 redeemed."
    },
    {
        "name": "50% order cap flooring (4000 pts, $55 order)",
        "pts": 4000,
        "tier": "Silver",
        "order": 55.0,
        "cat": "standard",
        "exp_redeemed": 2500,
        "rationale": "50% of $55 = $27.50 (2750 pts). Floored to nearest 500 block = 2500 pts."
    },
    {
        "name": "Small order below 500 pts cap (5000 pts, $8 order)",
        "pts": 5000,
        "tier": "Silver",
        "order": 8.0,
        "cat": "standard",
        "exp_redeemed": 0,
        "rationale": "50% of $8 = $4.00 (400 pts max). 400 < 500; 0 points redeemed."
    },
]

print("=" * 85)
print("LOYALTY DISCOUNT BOUNDARY & 50% CAP TEST SUITE (AGENTCORE CODE INTERPRETER)")
print("=" * 85)

all_passed = True
results = []
for i, tc in enumerate(test_cases, 1):
    raw = main.calculate_loyalty_discount(tc["pts"], tc["tier"], tc["order"], tc["cat"])
    parsed = json.loads(raw)
    if "structuredContent" in parsed:
        result = json.loads(parsed["structuredContent"]["stdout"])
    else:
        result = parsed

    actual_redeemed = result["points_redeemed"]
    passed = (actual_redeemed == tc["exp_redeemed"])
    all_passed = all_passed and passed
    status = "PASS" if passed else "FAIL"

    print(f"[{status}] Case {i}: {tc['name']}")
    print(f"       Rationale: {tc['rationale']}")
    print(f"       Points Redeemed: {actual_redeemed} (Expected: {tc['exp_redeemed']})")
    print(f"       Order: ${tc['order']} | Final Total: ${result['final_total']} | Remaining Points: {result['remaining_points']}")
    print("-" * 85)
    results.append({
        "case": tc["name"],
        "status": status,
        "result": result,
        "expected_redeemed": tc["exp_redeemed"],
    })

print("=" * 85)
print(f"OVERALL RESULT: {'ALL 8 BOUNDARY TESTS PASSED!' if all_passed else 'SOME TESTS FAILED'}")
print("=" * 85)

with open("loyalty_boundary_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
