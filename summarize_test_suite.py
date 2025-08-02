import csv
import os
from collections import defaultdict

CSV_PATH = "logs/test_suite_summary.csv"

def summarize():
    if not os.path.exists(CSV_PATH):
        print(f"No existe el archivo de resultados: {CSV_PATH}")
        return

    stats = defaultdict(lambda: {"runs": 0, "passes": 0, "fails": 0})

    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scenario = row["scenario"]
            passed = row["pass"].strip().lower() in ("true", "1", "yes", "y")
            stats[scenario]["runs"] += 1
            if passed:
                stats[scenario]["passes"] += 1
            else:
                stats[scenario]["fails"] += 1

    print(f"\nResumen de la suite de tests (revisando {CSV_PATH}):\n")
    print(f"{'Escenario':25} {'#Ejecutados':>12} {'#Pasos':>8} {'#Fallos':>8} {'Tasa de pase':>14}")
    print("-" * 70)
    for scenario, data in stats.items():
        runs = data["runs"]
        passes = data["passes"]
        fails = data["fails"]
        rate = (passes / runs * 100) if runs else 0.0
        print(f"{scenario:25} {runs:12d} {passes:8d} {fails:8d} {rate:13.2f}%")
    print()

if __name__ == "__main__":
    summarize()