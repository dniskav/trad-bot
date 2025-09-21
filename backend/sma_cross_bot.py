import os
import time
import argparse
from dotenv import load_dotenv
import numpy as np
import logging
import datetime

from binance.um_futures import UMFutures  # Cliente oficial USDT-M Futures
from metrics_logger import MetricsLogger, Trade

# ------------------ CONFIG / PARÁMETROS OPTIMIZADOS ------------------
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

SYMBOL = "DOGEUSDT"  # Dogecoin - NOTIONAL mínimo $1.00
INTERVAL = "1m"
FAST_WINDOW = 8      # Optimizado para DOGE (era 5)
SLOW_WINDOW = 21     # Optimizado para DOGE (era 20)
CAPITAL = 1000
RISK_PER_TRADE = 0.005  # 0.5% - Más conservador para DOGE
THRESHOLD = 0.0005   # 0.05% - Menos sensible, más preciso (era -0.0001)

SLEEP_SECONDS = 5    # Verificación ultra-rápida para scalping agresivo

# Estado
POSITION = None
current_trade = None
VERSION = "v1-sma-cross"

# ------------------ SETUP ------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

if API_KEY is None or API_SECRET is None:
    logging.error("Faltan BINANCE_API_KEY / BINANCE_API_SECRET en .env. Salida.")
    exit(1)

client = UMFutures(key=API_KEY, secret=API_SECRET)
logger = MetricsLogger(filepath="logs/trades.csv")


# ------------------ FUNCIONES AUX ------------------
def get_klines(symbol, interval, limit=500):
    resp = client.klines(symbol=symbol, interval=interval, limit=limit)
    return resp  # Return full candlestick data


def get_closes(symbol, interval, limit=500):
    """Get only closing prices for signal generation"""
    resp = client.klines(symbol=symbol, interval=interval, limit=limit)
    closes = [float(candle[4]) for candle in resp]
    return np.array(closes)

def get_volumes(symbol, interval, limit=500):
    """Get volume data for signal confirmation"""
    resp = client.klines(symbol=symbol, interval=interval, limit=limit)
    volumes = [float(candle[5]) for candle in resp]
    return np.array(volumes)


def compute_sma(series, window):
    if len(series) < window:
        return None
    return np.convolve(series, np.ones(window) / window, mode="valid")


def align_smas(sma_fast, sma_slow):
    """
    Alinea las dos SMAs recortando la más larga para que tengan el mismo length.
    """
    if sma_fast is None or sma_slow is None:
        return None, None
    offset = len(sma_slow) - len(sma_fast)
    if offset > 0:
        # slow es más larga: recortamos el inicio de slow
        sma_slow = sma_slow[offset:]
    elif offset < 0:
        # fast es más larga: recortamos el inicio de fast
        sma_fast = sma_fast[-offset:]
    return sma_fast, sma_slow


def calculate_rsi(prices, window=14):
    """Calcula el RSI para filtrar señales"""
    if len(prices) < window + 1:
        return None
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gains = np.mean(gains[-window:])
    avg_losses = np.mean(losses[-window:])
    
    if avg_losses == 0:
        return 100
    
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_volume_ma(volumes, window=20):
    """Calcula la media móvil del volumen (VMA)"""
    if len(volumes) < window:
        return None
    return np.mean(volumes[-window:])

def is_volume_confirmed(current_volume, avg_volume, threshold=1.2):
    """Verifica si el volumen actual confirma la señal"""
    if avg_volume is None or avg_volume == 0:
        return True  # Si no hay datos de volumen, permitir la señal
    return current_volume > (avg_volume * threshold)

def generate_signal(closes, volumes=None):
    sma_fast = compute_sma(closes, FAST_WINDOW)
    sma_slow = compute_sma(closes, SLOW_WINDOW)

    sma_fast, sma_slow = align_smas(sma_fast, sma_slow)
    if sma_fast is None or sma_slow is None:
        return None

    if len(sma_fast) < 2 or len(sma_slow) < 2:
        return None

    prev_fast, curr_fast = sma_fast[-2], sma_fast[-1]
    prev_slow, curr_slow = sma_slow[-2], sma_slow[-1]

    # Normalizamos diferencias relativas para aplicar threshold
    prev_diff = (prev_fast - prev_slow) / prev_slow if prev_slow != 0 else 0
    curr_diff = (curr_fast - curr_slow) / curr_slow if curr_slow != 0 else 0

    # Calcular RSI para filtrar señales
    rsi = calculate_rsi(closes)
    if rsi is None:
        return "HOLD"

    # Calcular confirmación de volumen si está disponible
    volume_confirmed = True
    if volumes is not None and len(volumes) > 0:
        current_volume = volumes[-1]
        avg_volume = calculate_volume_ma(volumes, window=20)
        volume_confirmed = is_volume_confirmed(current_volume, avg_volume, threshold=1.2)

    # Cruce alcista con umbral, filtro RSI y confirmación de volumen
    if prev_diff <= 0 and curr_diff > THRESHOLD and rsi < 70 and volume_confirmed:
        return "BUY"
    # Cruce bajista con umbral, filtro RSI y confirmación de volumen
    if prev_diff >= 0 and curr_diff < -THRESHOLD and rsi > 30 and volume_confirmed:
        return "SELL"
    return "HOLD"


def position_size(price):
    risk_amount = CAPITAL * RISK_PER_TRADE
    stop_distance = 0.01 * price
    qty = risk_amount / stop_distance
    return max(qty, 0)


def debug_print(closes):
    if len(closes) >= 6:
        print(f"Últimos cierres: {closes[-6:]}")
        sma_fast = compute_sma(closes, FAST_WINDOW)
        sma_slow = compute_sma(closes, SLOW_WINDOW)
        if sma_fast is not None and sma_slow is not None:
            sma_fast, sma_slow = align_smas(sma_fast, sma_slow)
            if sma_fast is not None and len(sma_fast) >= 3:
                print(f"SMA fast recientes: {sma_fast[-3:]}")
            if sma_slow is not None and len(sma_slow) >= 3:
                print(f"SMA slow recientes: {sma_slow[-3:]}")


def synthetic_test():
    """Test sintético con datos controlados"""
    print("=== Resultados de tests sintéticos ===")
    
    # Test 1: Flat (sin cruce)
    flat_data = np.array([100, 100, 100, 100, 100, 100, 100, 100, 100, 100])
    signal = generate_signal(flat_data)
    print(f"[{'PASS' if signal == 'HOLD' else 'FAIL'}] Flat (sin cruce): señal={signal} esperado=HOLD")
    
    # Test 2: Cruce alcista
    bullish_data = np.array([95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115])
    signal = generate_signal(bullish_data)
    print(f"[{'PASS' if signal == 'BUY' else 'FAIL'}] Cruce alcista: señal={signal} esperado=BUY")
    
    # Test 3: Cruce bajista
    bearish_data = np.array([115, 114, 113, 112, 111, 110, 109, 108, 107, 106, 105, 104, 103, 102, 101, 100, 99, 98, 97, 96, 95])
    signal = generate_signal(bearish_data)
    print(f"[{'PASS' if signal == 'SELL' else 'FAIL'}] Cruce bajista: señal={signal} esperado=SELL")
    
    print("======================================")
    
    # Verificar que todos los tests clave pasaron
    flat_signal = generate_signal(flat_data)
    bullish_signal = generate_signal(bullish_data)
    bearish_signal = generate_signal(bearish_data)
    
    return (flat_signal == 'HOLD' and bullish_signal == 'BUY' and bearish_signal == 'SELL')


# ------------------ LOOP PRINCIPAL ------------------
def main_loop(use_synthetic=False):
    global POSITION, current_trade
    
    if use_synthetic:
        print("Modo sintético activado - no se ejecutarán trades reales")
    
    while True:
        try:
            closes = get_closes(SYMBOL, INTERVAL, limit=500)
            volumes = get_volumes(SYMBOL, INTERVAL, limit=500)
            signal = generate_signal(closes, volumes)
            last_price = closes[-1]
            now = datetime.datetime.utcnow().isoformat()

            # Mostrar indicadores técnicos
            sma_fast = compute_sma(closes, FAST_WINDOW)
            sma_slow = compute_sma(closes, SLOW_WINDOW)
            sma_fast, sma_slow = align_smas(sma_fast, sma_slow)
            
            if sma_fast is not None and sma_slow is not None:
                rsi = calculate_rsi(closes)
                strength = (sma_fast[-1] - sma_slow[-1]) / sma_slow[-1] if sma_slow[-1] != 0 else 0
                
                # Calcular datos de volumen
                current_volume = volumes[-1] if len(volumes) > 0 else 0
                avg_volume = calculate_volume_ma(volumes, window=20)
                volume_ratio = current_volume / avg_volume if avg_volume and avg_volume > 0 else 1.0
                
                logging.info(f"📊 Indicadores: SMA Fast: {sma_fast[-1]:.5f} | SMA Slow: {sma_slow[-1]:.5f} | RSI: {rsi:.1f} | Fuerza: {strength:.4f}")
                logging.info(f"📈 Volumen: Actual: {current_volume:.0f} | Promedio: {avg_volume:.0f} | Ratio: {volume_ratio:.2f}x")
                logging.info(f"🎯 Señal: {signal} | Precio: ${last_price:.5f} | Posición: {POSITION}")
            else:
                logging.info(f"🎯 Señal: {signal} | Precio: ${last_price:.5f} | Posición: {POSITION}")

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