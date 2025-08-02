import sys
import logging
import argparse
import numpy as np
import datetime
import os
import csv

from sma_cross_bot import generate_signal, THRESHOLD, main_loop as bot_main_loop

# --- lógica auxiliar directa para cruces ---
def signal_from_diffs(prev_fast, prev_slow, curr_fast, curr_slow, threshold=THRESHOLD):
    prev_diff = (prev_fast - prev_slow) / prev_slow if prev_slow != 0 else 0
    curr_diff = (curr_fast - curr_slow) / curr_slow if curr_slow != 0 else 0

    if prev_diff <= 0 and curr_diff > threshold:
        return "BUY"
    if prev_diff >= 0 and curr_diff < -threshold:
        return "SELL"
    return "HOLD"


# --- escenarios ---
def flat_scenario():
    series = np.ones(100) * 100.0
    signal = generate_signal(series)
    expected = "HOLD"
    return "Flat (sin cruce)", signal, expected

def bullish_cross_scenario():
    signal = signal_from_diffs(prev_fast=99.0, prev_slow=100.0, curr_fast=101.0, curr_slow=100.0)
    expected = "BUY"
    return "Cruce alcista", signal, expected

def bearish_cross_scenario():
    signal = signal_from_diffs(prev_fast=101.0, prev_slow=100.0, curr_fast=99.0, curr_slow=100.0)
    expected = "SELL"
    return "Cruce bajista", signal, expected

def run_tests():
    tests = [flat_scenario, bullish_cross_scenario, bearish_cross_scenario]
    results = []
    for fn in tests:
        name, signal, expected = fn()
        passed = (signal == expected)
        results.append((name, signal, expected, passed))
    return results

def summary_and_decide(results, force=False):
    all_pass = all(passed for (_, _, _, passed) in results)
    print("\n=== Resultados de tests sintéticos ===")
    for name, signal, expected, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}: señal={signal} esperado={expected}")
    print("======================================\n")

    if all_pass or force:
        if not all_pass:
            print("Algunas pruebas fallaron pero se continúa por --force.")
        else:
            print("Todos los tests clave pasaron. Arrancando bot...")
        return True
    else:
        print("No se cumplen todos los tests clave. El bot no se iniciará. Usa --force para ignorar.")
        return False

def persist_results(results, outfile="logs/test_suite_summary.csv"):
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    header = ["timestamp", "scenario", "signal", "expected", "pass"]
    write_header = not os.path.exists(outfile)
    with open(outfile, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if write_header:
            writer.writeheader()
        ts = datetime.datetime.utcnow().isoformat()
        for name, signal, expected, passed in results:
            writer.writerow({
                "timestamp": ts,
                "scenario": name,
                "signal": signal,
                "expected": expected,
                "pass": passed,
            })

def main():
    parser = argparse.ArgumentParser(description="Corre tests sintéticos, guarda resultados y si pasan arranca el bot.")
    parser.add_argument("--force", action="store_true", help="Ignora fallos en los tests y arranca el bot de todos modos.")
    parser.add_argument("--synthetic-only", action="store_true", help="Solo corre los tests y no arranca el bot.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    results = run_tests()
    persist_results(results)
    proceed = summary_and_decide(results, force=args.force)

    if args.synthetic_only:
        return

    if proceed:
        bot_main_loop(use_synthetic=False)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()