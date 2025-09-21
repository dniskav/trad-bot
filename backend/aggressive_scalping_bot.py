#!/usr/bin/env python3
"""
SMA Cross Bot - Versión Agresiva para Scalping
Parámetros optimizados para trading de alta frecuencia
"""

import os
import time
import argparse
from dotenv import load_dotenv
import numpy as np
import logging
import datetime

from binance.um_futures import UMFutures  # Cliente oficial USDT-M Futures
from metrics_logger import MetricsLogger, Trade
from real_trading_manager import real_trading_manager
from trading_tracker import initialize_tracker
from colored_logger import get_colored_logger

# ------------------ CONFIG / PARÁMETROS AGRESIVOS ------------------
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

SYMBOL = "DOGEUSDT"  # Dogecoin - Optimizado para DOGE
INTERVAL = "1m"  # Mantenemos 1m como mínimo de Binance

# PARÁMETROS AGRESIVOS OPTIMIZADOS PARA SCALPING
FAST_WINDOW = 5      # SMA rápida optimizada (era 3)
SLOW_WINDOW = 13     # SMA lenta optimizada (era 8)
CAPITAL = 1000
RISK_PER_TRADE = 0.01  # 1.0% - Más conservador para DOGE (era 2%)
THRESHOLD = 0.0008   # 0.08% - Menos sensible, más preciso (era -0.0002)

SLEEP_SECONDS = 5    # Verificación ultra-rápida para scalping agresivo

# Estado
POSITION = None
current_trade = None
VERSION = "v2-aggressive-scalping"

# ------------------ SETUP ------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

if API_KEY is None or API_SECRET is None:
    logging.error("Faltan BINANCE_API_KEY / BINANCE_API_SECRET en .env. Salida.")
    exit(1)

client = UMFutures(key=API_KEY, secret=API_SECRET)
logger = MetricsLogger(filepath="logs/trades.csv")

# Inicializar trading tracker y logger con colores
trading_tracker = initialize_tracker(client)
colored_logger = get_colored_logger(__name__)


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


def compute_sma(prices, window):
    """Compute Simple Moving Average"""
    if len(prices) < window:
        return None
    return np.convolve(prices, np.ones(window)/window, mode='valid')


def align_smas(sma_fast, sma_slow):
    """Align SMAs to same length"""
    if sma_fast is None or sma_slow is None:
        return None, None
    
    # slow es más larga: recortamos el inicio de slow
    offset = len(sma_slow) - len(sma_fast)
    if offset > 0:
        sma_slow = sma_slow[offset:]
    # fast es más larga: recortamos el inicio de fast
    elif offset < 0:
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

def is_volume_confirmed(current_volume, avg_volume, threshold=1.1):
    """Verifica si el volumen actual confirma la señal (más permisivo para agresivo)"""
    if avg_volume is None or avg_volume == 0:
        return True  # Si no hay datos de volumen, permitir la señal
    return current_volume > (avg_volume * threshold)

def generate_signal(closes, volumes=None):
    """Genera señal de trading con parámetros agresivos optimizados"""
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
        volume_confirmed = is_volume_confirmed(current_volume, avg_volume, threshold=1.1)

    # Cruce alcista con umbral, filtro RSI y confirmación de volumen (más agresivo)
    if prev_diff <= 0 and curr_diff > THRESHOLD and rsi < 75 and volume_confirmed:
        return "BUY"
    # Cruce bajista con umbral, filtro RSI y confirmación de volumen (más agresivo)
    if prev_diff >= 0 and curr_diff < -THRESHOLD and rsi > 25 and volume_confirmed:
        return "SELL"
    return "HOLD"


def position_size(price):
    """Calcula el tamaño de la posición con mayor riesgo"""
    risk_amount = CAPITAL * RISK_PER_TRADE
    stop_distance = 0.005 * price  # Stop loss más ajustado (0.5% en lugar de 1%)
    qty = risk_amount / stop_distance
    return max(qty, 0)


def calculate_stop_loss(entry_price, signal):
    """Calcula stop loss más ajustado para scalping"""
    if signal == "BUY":
        return entry_price * 0.995  # Stop loss 0.5% abajo
    else:
        return entry_price * 1.005  # Stop loss 0.5% arriba


def calculate_take_profit(entry_price, signal):
    """Calcula take profit más conservador para scalping"""
    if signal == "BUY":
        return entry_price * 1.003  # Take profit 0.3% arriba
    else:
        return entry_price * 0.997  # Take profit 0.3% abajo


def main_loop():
    """Loop principal del bot agresivo"""
    global POSITION, current_trade
    
    logging.info(f"🚀 Iniciando Bot Agresivo v{VERSION}")
    logging.info(f"📊 Símbolo: {SYMBOL} | Intervalo: {INTERVAL}")
    logging.info(f"⚡ SMA Rápida: {FAST_WINDOW} | SMA Lenta: {SLOW_WINDOW}")
    logging.info(f"🎯 Threshold: {THRESHOLD} | Riesgo: {RISK_PER_TRADE*100}%")
    logging.info(f"⏱️ Verificación cada: {SLEEP_SECONDS}s")
    logging.info("=" * 60)
    
    while True:
        try:
            # Obtener datos de precio y volumen
            closes = get_closes(SYMBOL, INTERVAL, limit=500)
            volumes = get_volumes(SYMBOL, INTERVAL, limit=500)
            if len(closes) < SLOW_WINDOW:
                logging.warning("No hay suficientes datos históricos")
                time.sleep(SLEEP_SECONDS)
                continue

            current_price = closes[-1]
            signal = generate_signal(closes, volumes)
            
            if signal is None:
                logging.warning("No se pudo generar señal")
                time.sleep(SLEEP_SECONDS)
                continue

            # Log de indicadores técnicos
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
                logging.info(f"🎯 Señal: {signal} | Precio: ${current_price:.5f} | Posición: {POSITION}")
            else:
                logging.info(f"🎯 Señal: {signal} | Precio: ${current_price:.5f} | Posición: {POSITION}")

            # Lógica de trading REAL
            if POSITION is None and signal in ["BUY", "SELL"]:
                # Verificar si el bot está activo en el sistema
                if not real_trading_manager.bot_status.get('aggressive', False):
                    colored_logger.info(f"⚠️ Bot agresivo desactivado, saltando señal {signal}")
                    time.sleep(SLEEP_SECONDS)
                    continue
                
                # Abrir nueva posición REAL
                try:
                    # Usar el sistema de trading real
                    success, order_id, message = real_trading_manager.place_order(
                        symbol=SYMBOL,
                        side=signal,
                        quantity=None,  # Se calcula automáticamente
                        bot_type='aggressive',
                        trading_tracker=trading_tracker
                    )
                    
                    if success:
                        colored_logger.info(f"🚀 NUEVA POSICIÓN AGRESIVA: {signal}")
                        colored_logger.info(f"📊 Orden ID: {order_id} | Precio: ${current_price:.5f}")
                        colored_logger.info(f"✅ {message}")
                        POSITION = signal
                    else:
                        colored_logger.warning(f"❌ Error abriendo posición: {message}")
                        
                except Exception as e:
                    colored_logger.error(f"❌ Error en trading real: {e}")
                    time.sleep(SLEEP_SECONDS)
                    continue
                
            elif POSITION is not None:
                # Verificar condiciones de cierre usando el sistema real
                try:
                    # Obtener posiciones activas del sistema real
                    active_positions = real_trading_manager.active_positions.get('aggressive', {})
                    
                    if active_positions:
                        # Hay posiciones activas, verificar condiciones de cierre
                        for position_id, position_data in active_positions.items():
                            # El sistema real maneja automáticamente stop loss y take profit
                            # Solo verificamos señales contrarias
                            should_close = False
                            close_reason = ""
                            
                            if POSITION == "BUY" and signal == "SELL":
                                should_close = True
                                close_reason = "Señal Contraria"
                            elif POSITION == "SELL" and signal == "BUY":
                                should_close = True
                                close_reason = "Señal Contraria"
                            
                            if should_close:
                                # Cerrar posición usando el sistema real
                                success, message = real_trading_manager.close_position(
                                    position_id=position_id,
                                    bot_type='aggressive',
                                    trading_tracker=trading_tracker
                                )
                                
                                if success:
                                    colored_logger.info(f"🔒 CERRANDO POSICIÓN AGRESIVA: {close_reason}")
                                    colored_logger.info(f"✅ {message}")
                                    POSITION = None
                                else:
                                    colored_logger.warning(f"❌ Error cerrando posición: {message}")
                    else:
                        # No hay posiciones activas en el sistema real, resetear estado local
                        POSITION = None
                        colored_logger.info("🔄 Posición local reseteada (no hay posiciones activas en sistema real)")
                        
                except Exception as e:
                    colored_logger.error(f"❌ Error verificando cierre de posición: {e}")
                    time.sleep(SLEEP_SECONDS)
                    continue

            time.sleep(SLEEP_SECONDS)
            
        except KeyboardInterrupt:
            logging.info("🛑 Bot detenido por usuario")
            break
        except Exception as e:
            logging.error(f"❌ Error en main loop: {e}")
            time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot Agresivo para Scalping")
    parser.add_argument("--paper", action="store_true", help="Modo paper trading (solo simulación)")
    args = parser.parse_args()
    
    if args.paper:
        logging.info("📄 Modo Paper Trading activado")
    
    main_loop()
