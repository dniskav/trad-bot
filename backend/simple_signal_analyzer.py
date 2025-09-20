#!/usr/bin/env python3
"""
Analizador de Señales del Trading Bot (Versión Simplificada)
Monitorea las señales del bot en tiempo real
"""

import os
import time
import logging
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
from binance.um_futures import UMFutures
from sma_cross_bot import generate_signal, get_closes, SYMBOL, INTERVAL

# Configuración
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class SimpleSignalAnalyzer:
    def __init__(self):
        self.client = UMFutures(key=API_KEY, secret=API_SECRET, base_url="https://testnet.binancefuture.com")
        self.signals_history = []
        
    def get_current_signal(self):
        """Obtiene la señal actual del bot"""
        try:
            closes = get_closes(SYMBOL, INTERVAL, limit=100)
            if len(closes) < 20:  # Necesitamos al menos 20 datos para SMA
                return None, None
                
            signal = generate_signal(closes)
            current_price = closes[-1]
            
            return signal, current_price
        except Exception as e:
            logger.error(f"Error obteniendo señal: {e}")
            return None, None
    
    def calculate_signal_strength(self):
        """Calcula la fuerza de la señal basada en la diferencia entre SMAs"""
        try:
            closes = get_closes(SYMBOL, INTERVAL, limit=100)
            if len(closes) < 20:
                return 0
                
            # Calcular SMAs
            sma_fast = np.mean(closes[-5:])  # SMA 5
            sma_slow = np.mean(closes[-20:])  # SMA 20
            
            # Calcular diferencia relativa
            if sma_slow != 0:
                strength = (sma_fast - sma_slow) / sma_slow
                return strength
            return 0
        except:
            return 0
    
    def run_analysis(self, duration_minutes=5):
        """Ejecuta el análisis por un tiempo determinado"""
        logger.info(f"🤖 Iniciando análisis de señales por {duration_minutes} minutos...")
        logger.info(f"📊 Símbolo: {SYMBOL} | Intervalo: {INTERVAL}")
        logger.info("=" * 50)
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        signal_counts = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        while datetime.now() < end_time:
            signal, price = self.get_current_signal()
            
            if signal and price:
                strength = self.calculate_signal_strength()
                
                # Registrar señal
                signal_data = {
                    'timestamp': datetime.now(),
                    'signal': signal,
                    'price': price,
                    'strength': strength
                }
                self.signals_history.append(signal_data)
                signal_counts[signal] += 1
                
                # Mostrar información
                logger.info(f"📈 Señal: {signal} | Precio: ${price:.2f} | Fuerza: {strength:.4f}")
                
                # Mostrar estadísticas cada 5 señales
                if len(self.signals_history) % 5 == 0:
                    total = len(self.signals_history)
                    logger.info(f"📊 Estadísticas: BUY: {signal_counts['BUY']} | SELL: {signal_counts['SELL']} | HOLD: {signal_counts['HOLD']} | Total: {total}")
            
            time.sleep(30)  # Verificar cada 30 segundos
        
        # Mostrar estadísticas finales
        logger.info("=" * 50)
        logger.info("📊 ESTADÍSTICAS FINALES")
        logger.info("=" * 50)
        
        total_signals = len(self.signals_history)
        if total_signals > 0:
            logger.info(f"Total de señales: {total_signals}")
            logger.info(f"Señales BUY: {signal_counts['BUY']} ({signal_counts['BUY']/total_signals*100:.1f}%)")
            logger.info(f"Señales SELL: {signal_counts['SELL']} ({signal_counts['SELL']/total_signals*100:.1f}%)")
            logger.info(f"Señales HOLD: {signal_counts['HOLD']} ({signal_counts['HOLD']/total_signals*100:.1f}%)")
            
            # Calcular fuerza promedio
            if self.signals_history:
                avg_strength = sum(s['strength'] for s in self.signals_history) / len(self.signals_history)
                logger.info(f"Fuerza promedio de señal: {avg_strength:.4f}")
                
                # Mostrar última señal
                last_signal = self.signals_history[-1]
                logger.info(f"Última señal: {last_signal['signal']} a ${last_signal['price']:.2f}")
        else:
            logger.info("No se obtuvieron señales durante el análisis")

if __name__ == "__main__":
    analyzer = SimpleSignalAnalyzer()
    analyzer.run_analysis(duration_minutes=3)  # Análisis de 3 minutos
