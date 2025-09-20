#!/usr/bin/env python3
"""
Analizador de Señales del Trading Bot
Monitorea las señales del bot en tiempo real y analiza su rendimiento
"""

import os
import time
import logging
import pandas as pd
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

class SignalAnalyzer:
    def __init__(self):
        self.client = UMFutures(key=API_KEY, secret=API_SECRET, base_url="https://testnet.binancefuture.com")
        self.signals_history = []
        self.last_signal = None
        self.last_price = None
        
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
    
    def analyze_signal_quality(self, signal, price):
        """Analiza la calidad de la señal"""
        if signal is None:
            return
            
        # Registrar señal
        signal_data = {
            'timestamp': datetime.now(),
            'signal': signal,
            'price': price,
            'signal_strength': self.calculate_signal_strength()
        }
        
        self.signals_history.append(signal_data)
        
        # Mantener solo las últimas 100 señales
        if len(self.signals_history) > 100:
            self.signals_history = self.signals_history[-100:]
            
        logger.info(f"Señal: {signal} | Precio: ${price:.2f} | Fuerza: {signal_data['signal_strength']:.4f}")
        
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
    
    def get_performance_stats(self):
        """Calcula estadísticas de rendimiento"""
        if len(self.signals_history) < 2:
            return "No hay suficientes datos"
            
        df = pd.DataFrame(self.signals_history)
        
        # Contar señales
        buy_signals = len(df[df['signal'] == 'BUY'])
        sell_signals = len(df[df['signal'] == 'SELL'])
        hold_signals = len(df[df['signal'] == 'HOLD'])
        
        # Calcular frecuencia de señales
        total_signals = len(df)
        signal_frequency = {
            'BUY': buy_signals / total_signals * 100,
            'SELL': sell_signals / total_signals * 100,
            'HOLD': hold_signals / total_signals * 100
        }
        
        return {
            'total_signals': total_signals,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'hold_signals': hold_signals,
            'signal_frequency': signal_frequency,
            'avg_signal_strength': df['signal_strength'].mean(),
            'last_signal': df.iloc[-1]['signal'] if len(df) > 0 else 'N/A'
        }
    
    def run_analysis(self, duration_minutes=10):
        """Ejecuta el análisis por un tiempo determinado"""
        logger.info(f"Iniciando análisis de señales por {duration_minutes} minutos...")
        logger.info(f"Símbolo: {SYMBOL} | Intervalo: {INTERVAL}")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        while datetime.now() < end_time:
            signal, price = self.get_current_signal()
            
            if signal and price:
                self.analyze_signal_quality(signal, price)
                
                # Mostrar estadísticas cada 5 señales
                if len(self.signals_history) % 5 == 0:
                    stats = self.get_performance_stats()
                    logger.info(f"Estadísticas: {stats}")
            
            time.sleep(30)  # Verificar cada 30 segundos
        
        # Mostrar estadísticas finales
        final_stats = self.get_performance_stats()
        logger.info("=== ESTADÍSTICAS FINALES ===")
        logger.info(f"Total de señales: {final_stats['total_signals']}")
        logger.info(f"Señales BUY: {final_stats['buy_signals']} ({final_stats['signal_frequency']['BUY']:.1f}%)")
        logger.info(f"Señales SELL: {final_stats['sell_signals']} ({final_stats['signal_frequency']['SELL']:.1f}%)")
        logger.info(f"Señales HOLD: {final_stats['hold_signals']} ({final_stats['signal_frequency']['HOLD']:.1f}%)")
        logger.info(f"Fuerza promedio de señal: {final_stats['avg_signal_strength']:.4f}")

if __name__ == "__main__":
    analyzer = SignalAnalyzer()
    analyzer.run_analysis(duration_minutes=5)  # Análisis de 5 minutos
