#!/usr/bin/env python3
"""
Analizador del Bot Agresivo para Scalping
Compara rendimiento entre bot conservador vs agresivo
"""

import os
import time
import logging
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
from binance.um_futures import UMFutures
from sma_cross_bot import generate_signal as conservative_signal, get_closes, SYMBOL, INTERVAL
from aggressive_scalping_bot import generate_signal as aggressive_signal

# Configuración
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class ScalpingAnalyzer:
    def __init__(self):
        self.client = UMFutures(key=API_KEY, secret=API_SECRET, base_url="https://testnet.binancefuture.com")
        self.conservative_signals = []
        self.aggressive_signals = []
        
    def get_signals_comparison(self):
        """Compara señales entre bot conservador y agresivo"""
        try:
            closes = get_closes(SYMBOL, INTERVAL, limit=100)
            if len(closes) < 20:
                return None, None, None
                
            conservative_sig = conservative_signal(closes)
            aggressive_sig = aggressive_signal(closes)
            current_price = closes[-1]
            
            return conservative_sig, aggressive_sig, current_price
        except Exception as e:
            logger.error(f"Error obteniendo señales: {e}")
            return None, None, None
    
    def calculate_signal_strength(self, closes, fast_window, slow_window):
        """Calcula la fuerza de la señal"""
        try:
            if len(closes) < slow_window:
                return 0
                
            # Calcular SMAs
            sma_fast = np.mean(closes[-fast_window:])
            sma_slow = np.mean(closes[-slow_window:])
            
            # Calcular diferencia relativa
            if sma_slow != 0:
                strength = (sma_fast - sma_slow) / sma_slow
                return strength
            return 0
        except:
            return 0
    
    def run_comparison_analysis(self, duration_minutes=5):
        """Ejecuta análisis comparativo"""
        logger.info("🚀 Iniciando análisis comparativo de bots...")
        logger.info("📊 Bot Conservador: SMA 5 vs 20, Threshold 0.0")
        logger.info("⚡ Bot Agresivo: SMA 3 vs 8, Threshold 0.0001")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        conservative_counts = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        aggressive_counts = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        while datetime.now() < end_time:
            cons_signal, agg_signal, price = self.get_signals_comparison()
            
            if cons_signal and agg_signal and price:
                # Registrar señales
                cons_data = {
                    'timestamp': datetime.now(),
                    'signal': cons_signal,
                    'price': price,
                    'strength': self.calculate_signal_strength(get_closes(SYMBOL, INTERVAL, limit=100), 5, 20)
                }
                self.conservative_signals.append(cons_data)
                conservative_counts[cons_signal] += 1
                
                agg_data = {
                    'timestamp': datetime.now(),
                    'signal': agg_signal,
                    'price': price,
                    'strength': self.calculate_signal_strength(get_closes(SYMBOL, INTERVAL, limit=100), 3, 8)
                }
                self.aggressive_signals.append(agg_data)
                aggressive_counts[agg_signal] += 1
                
                # Mostrar comparación
                logger.info(f"💰 Precio: ${price:.2f}")
                logger.info(f"🐌 Conservador: {cons_signal} | ⚡ Agresivo: {agg_signal}")
                
                # Mostrar estadísticas cada 5 señales
                if len(self.conservative_signals) % 5 == 0:
                    logger.info("📊 Estadísticas:")
                    logger.info(f"🐌 Conservador - BUY: {conservative_counts['BUY']} | SELL: {conservative_counts['SELL']} | HOLD: {conservative_counts['HOLD']}")
                    logger.info(f"⚡ Agresivo - BUY: {aggressive_counts['BUY']} | SELL: {aggressive_counts['SELL']} | HOLD: {aggressive_counts['HOLD']}")
                    logger.info("-" * 40)
            
            time.sleep(30)  # Verificar cada 30 segundos
        
        # Mostrar estadísticas finales
        self.show_final_stats(conservative_counts, aggressive_counts)
    
    def show_final_stats(self, cons_counts, agg_counts):
        """Muestra estadísticas finales"""
        logger.info("=" * 60)
        logger.info("📊 ESTADÍSTICAS FINALES COMPARATIVAS")
        logger.info("=" * 60)
        
        cons_total = sum(cons_counts.values())
        agg_total = sum(agg_counts.values())
        
        if cons_total > 0:
            logger.info("🐌 BOT CONSERVADOR:")
            logger.info(f"   Total señales: {cons_total}")
            logger.info(f"   BUY: {cons_counts['BUY']} ({cons_counts['BUY']/cons_total*100:.1f}%)")
            logger.info(f"   SELL: {cons_counts['SELL']} ({cons_counts['SELL']/cons_total*100:.1f}%)")
            logger.info(f"   HOLD: {cons_counts['HOLD']} ({cons_counts['HOLD']/cons_total*100:.1f}%)")
            
            if self.conservative_signals:
                cons_avg_strength = sum(s['strength'] for s in self.conservative_signals) / len(self.conservative_signals)
                logger.info(f"   Fuerza promedio: {cons_avg_strength:.4f}")
        
        if agg_total > 0:
            logger.info("⚡ BOT AGRESIVO:")
            logger.info(f"   Total señales: {agg_total}")
            logger.info(f"   BUY: {agg_counts['BUY']} ({agg_counts['BUY']/agg_total*100:.1f}%)")
            logger.info(f"   SELL: {agg_counts['SELL']} ({agg_counts['SELL']/agg_total*100:.1f}%)")
            logger.info(f"   HOLD: {agg_counts['HOLD']} ({agg_counts['HOLD']/agg_total*100:.1f}%)")
            
            if self.aggressive_signals:
                agg_avg_strength = sum(s['strength'] for s in self.aggressive_signals) / len(self.aggressive_signals)
                logger.info(f"   Fuerza promedio: {agg_avg_strength:.4f}")
        
        # Comparación
        if cons_total > 0 and agg_total > 0:
            logger.info("🔄 COMPARACIÓN:")
            logger.info(f"   Señales agresivas vs conservadoras: {agg_total/cons_total:.2f}x")
            
            # Calcular actividad (no HOLD)
            cons_activity = (cons_counts['BUY'] + cons_counts['SELL']) / cons_total * 100
            agg_activity = (agg_counts['BUY'] + agg_counts['SELL']) / agg_total * 100
            
            logger.info(f"   Actividad conservador: {cons_activity:.1f}%")
            logger.info(f"   Actividad agresivo: {agg_activity:.1f}%")
            logger.info(f"   Incremento de actividad: {agg_activity/cons_activity:.2f}x")

if __name__ == "__main__":
    analyzer = ScalpingAnalyzer()
    analyzer.run_comparison_analysis(duration_minutes=3)
