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

# ------------------ CONFIG / PARÁMETROS AGRESIVOS ------------------
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

SYMBOL = "ADAUSDT"  # Cardano - Mayor volatilidad (0.78%)
INTERVAL = "1m"  # Mantenemos 1m como mínimo de Binance

# PARÁMETROS AGRESIVOS PARA SCALPING
FAST_WINDOW = 3      # SMA rápida más corta (era 5)
SLOW_WINDOW = 8      # SMA lenta más corta (era 20)
CAPITAL = 1000
RISK_PER_TRADE = 0.01  # 1.0% - Más conservador para DOGE (era 2%)
THRESHOLD = -0.0002  # Muy sensible para generar más señales

SLEEP_SECONDS = 15   # Verificar más frecuentemente (era 30)

# Estado
POSITION = None
current_trade = None
VERSION = "v2-aggressive-scalping"

# ------------------ SETUP ------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

if API_KEY is None or API_SECRET is None:
    logging.error("Faltan BINANCE_API_KEY / BINANCE_API_SECRET en .env. Salida.")
    exit(1)

client = UMFutures(key=API_KEY, secret=API_SECRET, base_url="https://testnet.binancefuture.com")
logger = MetricsLogger(filepath="logs/trades.csv")


# ------------------ FUNCIONES AUX ------------------
def get_klines(symbol, interval, limit=100):
    resp = client.klines(symbol=symbol, interval=interval, limit=limit)
    return resp  # Return full candlestick data


def get_closes(symbol, interval, limit=100):
    """Get only closing prices for signal generation"""
    resp = client.klines(symbol=symbol, interval=interval, limit=limit)
    closes = [float(candle[4]) for candle in resp]
    return np.array(closes)


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


def generate_signal(closes):
    """Genera señal de trading con parámetros agresivos"""
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

    # Cruce alcista con umbral muy bajo (más agresivo)
    if prev_diff <= 0 and curr_diff > THRESHOLD:
        return "BUY"
    # Cruce bajista con umbral muy bajo (más agresivo)
    if prev_diff >= 0 and curr_diff < -THRESHOLD:
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
            # Obtener datos de precio
            closes = get_closes(SYMBOL, INTERVAL, limit=100)
            if len(closes) < SLOW_WINDOW:
                logging.warning("No hay suficientes datos históricos")
                time.sleep(SLEEP_SECONDS)
                continue

            current_price = closes[-1]
            signal = generate_signal(closes)
            
            if signal is None:
                logging.warning("No se pudo generar señal")
                time.sleep(SLEEP_SECONDS)
                continue

            # Log de estado actual
            sma_fast = compute_sma(closes, FAST_WINDOW)
            sma_slow = compute_sma(closes, SLOW_WINDOW)
            sma_fast, sma_slow = align_smas(sma_fast, sma_slow)
            
            if sma_fast is not None and sma_slow is not None:
                strength = (sma_fast[-1] - sma_slow[-1]) / sma_slow[-1] if sma_slow[-1] != 0 else 0
                logging.info(f"💰 Precio: ${current_price:.2f} | Señal: {signal} | Fuerza: {strength:.4f}")

            # Lógica de trading
            if POSITION is None and signal in ["BUY", "SELL"]:
                # Abrir nueva posición
                qty = position_size(current_price)
                stop_loss = calculate_stop_loss(current_price, signal)
                take_profit = calculate_take_profit(current_price, signal)
                
                logging.info(f"🎯 ABRIENDO POSICIÓN: {signal}")
                logging.info(f"📊 Cantidad: {qty:.4f} | Precio: ${current_price:.2f}")
                logging.info(f"🛑 Stop Loss: ${stop_loss:.2f} | Take Profit: ${take_profit:.2f}")
                
                # Simular apertura de posición (paper trading)
                current_trade = Trade(
                    entry_time=datetime.now(),
                    entry_price=current_price,
                    position=signal,
                    quantity=qty,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    version=VERSION
                )
                POSITION = signal
                
            elif POSITION is not None:
                # Verificar condiciones de cierre
                should_close = False
                close_reason = ""
                
                if POSITION == "BUY":
                    if current_price <= current_trade.stop_loss:
                        should_close = True
                        close_reason = "Stop Loss"
                    elif current_price >= current_trade.take_profit:
                        should_close = True
                        close_reason = "Take Profit"
                    elif signal == "SELL":
                        should_close = True
                        close_reason = "Señal Contraria"
                        
                elif POSITION == "SELL":
                    if current_price >= current_trade.stop_loss:
                        should_close = True
                        close_reason = "Stop Loss"
                    elif current_price <= current_trade.take_profit:
                        should_close = True
                        close_reason = "Take Profit"
                    elif signal == "BUY":
                        should_close = True
                        close_reason = "Señal Contraria"
                
                if should_close:
                    # Cerrar posición
                    pnl = (current_price - current_trade.entry_price) * current_trade.quantity
                    if POSITION == "SELL":
                        pnl = -pnl  # Invertir para posiciones cortas
                    
                    return_pct = (pnl / (current_trade.entry_price * current_trade.quantity)) * 100
                    
                    logging.info(f"🔚 CERRANDO POSICIÓN: {close_reason}")
                    logging.info(f"📊 PnL: ${pnl:.2f} | Retorno: {return_pct:.2f}%")
                    
                    # Guardar trade
                    current_trade.exit_time = datetime.now()
                    current_trade.exit_price = current_price
                    current_trade.pnl = pnl
                    current_trade.return_pct = return_pct
                    
                    logger.log_trade(current_trade)
                    
                    # Resetear estado
                    POSITION = None
                    current_trade = None

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
