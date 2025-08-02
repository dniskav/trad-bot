import numpy as np
from sma_cross_bot import generate_signal, FAST_WINDOW, SLOW_WINDOW, THRESHOLD

def make_series_from_smas(prev_fast, prev_slow, curr_fast, curr_slow, total_length=50):
    """
    Reconstruye una serie de precios artificial donde las SMAs rápida/lenta previas y actuales
    sean las dadas, aproximando con dos pasos: antes y después del cruce.
    Esto es heurístico: construye una base plana y luego empuja los últimos valores para
    inducir las medias.
    """
    base = np.ones(total_length) * 100.0

    # Ajustamos los últimos valores para que las SMAs encajen aproximadamente:
    # Hacemos que en el bloque anterior fast <= slow, y luego fast > slow (cruce alcista), etc.
    # Simplificación: modificamos los últimos SLOW_WINDOW+2 valores
    for i in range(total_length - SLOW_WINDOW - 2, total_length):
        if i < total_length - 2:
            # antes del "corte", mantenemos fast < slow si prev_fast < prev_slow
            if prev_fast < prev_slow:
                base[i] = 99.0
            else:
                base[i] = 101.0
        else:
            # después, reflejamos curr_fast vs curr_slow
            if curr_fast > curr_slow:
                base[i] = 102.0
            else:
                base[i] = 98.0
    return base

def run_scenario(name, series, expected):
    signal = generate_signal(series)
    result = "PASS" if signal == expected else "FAIL"
    print(f"[{result}] {name}: señal={signal} expected={expected}")

def flat_scenario():
    # Sin cruce, todo igual
    series = np.ones(100) * 100
    run_scenario("Flat (sin cruce)", series, "HOLD")

def bullish_cross_scenario():
    # Forzamos cruce alcista: prev_fast <= prev_slow, curr_fast > curr_slow
    series = make_series_from_smas(prev_fast=99, prev_slow=100, curr_fast=101, curr_slow=100)
    run_scenario("Cruce alcista", series, "BUY")

def bearish_cross_scenario():
    # Cruce bajista: prev_fast >= prev_slow, curr_fast < curr_slow
    series = make_series_from_smas(prev_fast=101, prev_slow=100, curr_fast=99, curr_slow=100)
    run_scenario("Cruce bajista", series, "SELL")

def noisy_scenario():
    # Ruido aleatorio sin cruce sostenido
    np.random.seed(42)
    base = np.cumsum(np.random.normal(0, 0.1, 200)) + 100
    run_scenario("Ruido", base, "HOLD")  # puede ser HOLD o falso cruce; aceptamos HOLD como ideal

def false_small_cross():
    # Cruce muy pequeño que debería filtrarse si THRESHOLD > 0
    global THRESHOLD
    original_threshold = THRESHOLD
    # aquí simulamos umbral pequeño; si THRESHOLD=0 en tu config, se verá como BUY/SELL
    # para este test se asume que THRESHOLD está en 0.005 (0.5%)
    setattr(__import__("sma_cross_bot"), "THRESHOLD", 0.005)
    series = make_series_from_smas(prev_fast=100, prev_slow=100, curr_fast=100.3, curr_slow=100)
    expected = "HOLD"  # porque la diferencia es 0.3% < 0.5%
    signal = generate_signal(series)
    result = "PASS" if signal == expected else "FAIL"
    print(f"[{result}] False small cross (threshold=0.5%): señal={signal} expected={expected}")
    setattr(__import__("sma_cross_bot"), "THRESHOLD", original_threshold)

if __name__ == "__main__":
    print("=== Ejecutando escenarios sintéticos ===")
    flat_scenario()
    bullish_cross_scenario()
    bearish_cross_scenario()
    noisy_scenario()
    # Si usas threshold > 0, habilita esto; de lo contrario puedes comentarlo
    false_small_cross()