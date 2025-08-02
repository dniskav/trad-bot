import csv
import os
from collections import defaultdict
from datetime import datetime
import matplotlib.pyplot as plt

CSV_PATH = "logs/test_suite_summary.csv"
OUTPUT_PLOT = "logs/test_suite_passrate.png"
ALERT_THRESHOLD = 0.8  # 80%

def load_rows():
    if not os.path.exists(CSV_PATH):
        print(f"No existe el archivo de resultados: {CSV_PATH}")
        return []
    rows = []
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalizar
            row["pass"] = row["pass"].strip().lower() in ("true", "1", "yes", "y")
            try:
                row["timestamp"] = datetime.fromisoformat(row["timestamp"])
            except ValueError:
                # si tiene zona u otro formato
                row["timestamp"] = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            rows.append(row)
    return rows

def summarize(rows):
    stats = defaultdict(lambda: {"runs": 0, "passes": 0, "fails": 0})
    for row in rows:
        scenario = row["scenario"]
        passed = row["pass"]
        stats[scenario]["runs"] += 1
        if passed:
            stats[scenario]["passes"] += 1
        else:
            stats[scenario]["fails"] += 1
    print(f"\nResumen total de la suite de tests ({len(rows)} ejecuciones):\n")
    print(f"{'Escenario':25} {'#Ejecutados':>12} {'#Pasos':>8} {'#Fallos':>8} {'Tasa de pase':>14}")
    print("-" * 70)
    for scenario, data in stats.items():
        runs = data["runs"]
        passes = data["passes"]
        fails = data["fails"]
        rate = (passes / runs) if runs else 0.0
        print(f"{scenario:25} {runs:12d} {passes:8d} {fails:8d} {rate:13.2%}")
    print()

def compute_daily_passrates(rows):
    # estructura: scenario -> date -> {runs, passes}
    daily = defaultdict(lambda: defaultdict(lambda: {"runs": 0, "passes": 0}))
    for row in rows:
        scenario = row["scenario"]
        date = row["timestamp"].date()
        passed = row["pass"]
        daily[scenario][date]["runs"] += 1
        if passed:
            daily[scenario][date]["passes"] += 1
    # convertir a dict de listas ordenadas
    result = {}
    for scenario, dates in daily.items():
        sorted_dates = sorted(dates.keys())
        rates = []
        for d in sorted_dates:
            info = dates[d]
            rate = info["passes"] / info["runs"] if info["runs"] else 0
            rates.append((d, rate, info["runs"]))
        result[scenario] = rates  # list of (date, rate, runs)
    return result

def plot_passrates(daily_passrates):
    plt.figure()
    for scenario, data in daily_passrates.items():
        dates = [d for d, _, _ in data]
        rates = [r for _, r, _ in data]
        plt.plot(dates, rates, label=scenario)
        # marcar días con bajo pass rate
        low_dates = [d for d, r, _ in data if r < ALERT_THRESHOLD]
        low_rates = [r for d, r, _ in data if r < ALERT_THRESHOLD]
        if low_dates:
            plt.scatter(low_dates, low_rates, marker='x')
    plt.axhline(ALERT_THRESHOLD, linestyle='--', label=f"Threshold {ALERT_THRESHOLD:.0%}")
    plt.xlabel("Fecha")
    plt.ylabel("Tasa de pase diaria")
    plt.title("Evolución de pass rate por escenario")
    plt.legend()
    plt.grid(True)
    os.makedirs(os.path.dirname(OUTPUT_PLOT), exist_ok=True)
    plt.tight_layout()
    plt.savefig(OUTPUT_PLOT)
    print(f"Gráfico guardado en {OUTPUT_PLOT}")

def main():
    rows = load_rows()
    if not rows:
        return
    summarize(rows)
    daily = compute_daily_passrates(rows)
    plot_passrates(daily)

if __name__ == "__main__":
    main()