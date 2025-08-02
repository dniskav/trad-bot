import csv
from datetime import datetime
from test_scenarios import (
    flat_scenario,
    bullish_cross_scenario,
    bearish_cross_scenario,
    noisy_scenario,
    false_small_cross,
)

SCENARIOS = [
    ("Flat (sin cruce)", flat_scenario, "HOLD"),
    ("Cruce alcista", bullish_cross_scenario, "BUY"),
    ("Cruce bajista", bearish_cross_scenario, "SELL"),
    ("Ruido", noisy_scenario, "HOLD"),
    ("False small cross", false_small_cross, "HOLD"),
]

OUTFILE = "logs/test_scenarios_results.csv"

def run_and_log():
    results = []
    for name, func, expected in SCENARIOS:
        # Cada función imprime por sí misma; aquí la envolvemos para capturar señal
        # Se asume que esas funciones se adaptan para devolver (signal, expected)
        signal = func.__wrapped__() if hasattr(func, "__wrapped__") else None  # si no están adaptadas, refactoriza para que devuelvan
        passed = signal == expected
        results.append({
            "timestamp": datetime.utcnow().isoformat(),
            "scenario": name,
            "signal": signal,
            "expected": expected,
            "pass": passed,
        })

    # Asegura carpeta
    import os
    os.makedirs(os.path.dirname(OUTFILE), exist_ok=True)
    with open(OUTFILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "scenario", "signal", "expected", "pass"])
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    print(f"Resultados guardados en {OUTFILE}")

if __name__ == "__main__":
    run_and_log()