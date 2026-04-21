import json
import os


def validate_lab():
    print("Checking submission format...")

    required_files = [
        "reports/summary.json",
        "reports/benchmark_results.json",
        "analysis/failure_analysis.md",
    ]

    missing = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"[OK] Found: {file_path}")
        else:
            print(f"[MISSING] {file_path}")
            missing.append(file_path)

    if missing:
        print(f"\nMissing {len(missing)} required file(s). Please generate them before submission.")
        return

    try:
        with open("reports/summary.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"summary.json is not valid JSON: {exc}")
        return

    if "metrics" not in data or "metadata" not in data:
        print("summary.json is missing the 'metrics' or 'metadata' field.")
        return

    metrics = data["metrics"]
    print("\nQuick stats")
    print(f"Total cases: {data['metadata'].get('total', 'N/A')}")
    print(f"Average score: {metrics.get('avg_score', 0):.2f}")

    if "hit_rate" in metrics:
        print(f"[OK] Retrieval metrics present (Hit Rate: {metrics['hit_rate'] * 100:.1f}%)")
    else:
        print("[WARN] Missing retrieval metric 'hit_rate'.")

    if "agreement_rate" in metrics:
        print(f"[OK] Multi-judge metrics present (Agreement Rate: {metrics['agreement_rate'] * 100:.1f}%)")
    else:
        print("[WARN] Missing multi-judge metric 'agreement_rate'.")

    if data["metadata"].get("version"):
        print("[OK] Agent version metadata present.")

    print("\nThe lab package is ready for grading.")


if __name__ == "__main__":
    validate_lab()
