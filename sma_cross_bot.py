import os
import time
import argparse
from dotenv import load_dotenv
import numpy as np
import logging
import datetime

from binance.um_futures import UMFutures  # Cliente oficial USDT-M Futures
from metrics_logger import MetricsLogger, Trade

# ------------------ CONFIG / PARÁMETROS ------------------
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# Estrategia
SYMBOL = "BTCUSDT"
INTERVAL = "1m"
FAST_WINDOW = 5
SLOW_WINDOW = 20
CAPITAL = 1000  # capital ficticio
RISK_PER_TRADE = 0.01  # 1% por operación

# Timing
SLEEP_SECONDS = 30  # espera entre evaluaciones

# Estado global
POSITION = None  # "LONG" o None
current_trade = None  # instancia abierta

# Versión para comparar
VERSION = "v1-sma-cross"

# ------------------ SETUP ------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

if API_KEY is None or API_SECRET is None:
    logging.error("Faltan BINANCE_API_KEY / BINANCE_API_SECRET en .env. Salida.")
    exit(1)

# Cliente apuntando a testnet. Asegúrate que tus keys son de testnet.
client = UMFutures(key=API_KEY, secret=API_SECRET, base_url="https://testnet.binancefuture.com")

# Logger de métricas
logger = MetricsLogger(filepath="logs/trades.csv")


# ------------------ FUNCIONES AUX ------------------
def get_klines(symbol, interval, limit=100):
    """
    Baja las últimas velas y devuelve array de precios de cierre.
    """
    resp = client.klines(symbol=symbol, interval=interval, limit=limit)
    closes = [float(candle[4]) for candle in resp]
    return np.array(closes)


def compute_sma(series, window):
    if len(series) < window:
        return None
    return np.convolve(series, np.ones(window) / window, mode="valid")


def align_smas(sma_fast, sma_slow):
    """Alinea tamaños para comparar cruces."""
    if sma_fast is None or sma_slow is None:
        return None, None
    offset = len(sma_slow) - len(sma_fast)
    if offset > 0:
        sma_fast = sma_fast[offset:]
    elif offset < 0:
        sma_slow = sma_slow[-offset:]
    return sma_fast, sma_slow


def generate_signal(closes):
    sma_fast = compute_sma(closes, FAST_WINDOW)
    sma_slow = compute_sma(closes, SLOW_WINDOW)

    sma_fast, sma_slow = align_smas(sma_fast, sma_slow)
    if sma_fast is None or sma_slow is None:
        return None

    if len(sma_fast) < 2 or len(sma_slow) < 2:
        return None

    prev_fast, curr_fast = sma_fast[-2], sma_fast[-1]
    prev_slow, curr_slow = sma_slow[-2], sma_slow[-1]

    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return "BUY"
    if prev_fast >= prev_slow and curr_fast < curr_slow:
        return "SELL"
    return "HOLD"


def position_size(price):
    risk_amount = CAPITAL * RISK_PER_TRADE
    stop_distance = 0.01 * price  # stop a 1% fijo por ahora
    qty = risk_amount / stop_distance
    return max(qty, 0)


def debug_print(closes):
    """
    Imprime valores recientes para entender qué pasa con las SMAs y cruces.
    """
    sma_fast = compute_sma(closes, FAST_WINDOW)
    sma_slow = compute_sma(closes, SLOW_WINDOW)
    aligned_fast, aligned_slow = align_smas(sma_fast, sma_slow)

    logging.info(f"Últimos cierres: {closes[-6:]}")
    if aligned_fast is None or aligned_slow is None:
        logging.info("No hay suficientes datos para calcular ambas SMAs aún.")
        return
    logging.info(f"SMA fast recientes: {aligned_fast[-3:]}")
    logging.info(f"SMA slow recientes: {aligned_slow[-3:]}")


def synthetic_test():
    """
    Genera datos sintéticos donde la rápida cruza la lenta para validar la lógica.
    """
    base = np.ones(30) * 100
    for i in range(10, 15):
        base[i] += (i - 9) * 2  # simula subida corta para forzar cruce
    signal = generate_signal(base)
    print("=== TEST SINTÉTICO ===")
    print("Serie (últimos):", base[-15:])
    print("Señal generada (debería ser BUY):", signal)
    print("=====================")


# ------------------ LOOP PRINCIPAL ------------------
def main_loop(use_synthetic=False):
    global POSITION, current_trade

    if use_synthetic:
        synthetic_test()
        return

    while True:
        try:
            closes = get_klines(SYMBOL, INTERVAL, limit=100)
            signal = generate_signal(closes)
            last_price = closes[-1]
            now = datetime.datetime.utcnow().isoformat()

            # Debug
            debug_print(closes)

            logging.info(f"Señal: {signal} | Precio: {last_price:.2f} | Posición: {POSITION}")

            # Entrada LONG
            if signal == "BUY" and POSITION != "LONG":
                qty = position_size(last_price)
                logging.info(f"[acción] Entrando LONG (simulado) con qty≈{qty:.4f}")
                POSITION = "LONG"
                current_trade = Trade(
                    entry_time=now,
                    exit_time=None,
                    entry_price=last_price,
                    exit_price=None,
                    position="LONG",
                    quantity=qty,
                    pnl=None,
                    return_pct=None,
                    version=VERSION,
                )

            # Cierre LONG
            elif signal == "SELL" and POSITION == "LONG":
                qty = position_size(last_price)
                logging.info("[acción] Cerrando LONG (simulado)")
                exit_price = last_price
                pnl = (exit_price - current_trade.entry_price) * current_trade.quantity
                return_pct = pnl / (CAPITAL * RISK_PER_TRADE) if (CAPITAL * RISK_PER_TRADE) != 0 else None

                current_trade.exit_time = now
                current_trade.exit_price = exit_price
                current_trade.pnl = pnl
                current_trade.return_pct = return_pct
                logger.record_trade(current_trade)

                POSITION = None
                current_trade = None

        except Exception:
            logging.exception("Error en el loop:")
        time.sleep(SLEEP_SECONDS)


# ------------------ ENTRY POINT ------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SMA Cross Bot para Binance Futures Testnet con métricas y debug.")
    parser.add_argument("--synthetic", action="store_true", help="Ejecuta test sintético en lugar del loop real.")
    args = parser.parse_args()

    main_loop(use_synthetic=args.synthetic)