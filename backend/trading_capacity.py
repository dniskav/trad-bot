#!/usr/bin/env python3
"""
Función auxiliar para filtrar señales según balance disponible
"""

import os
from dotenv import load_dotenv
from binance.client import Client

def get_trading_capacity():
    """Obtiene la capacidad de trading actual"""
    load_dotenv('config_real_trading.env')
    client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'))
    
    # Verificar si estamos usando margin trading
    leverage = int(os.getenv('LEVERAGE', '1'))
    
    if leverage > 1:
        # Usar cuenta de margen
        margin_account = client.get_margin_account()
        
        # Buscar balances en la cuenta de margen
        usdt_balance = 0.0
        doge_balance = 0.0
        
        for asset in margin_account.get('userAssets', []):
            if asset['asset'] == 'USDT':
                usdt_balance = float(asset['free']) + float(asset['locked'])
            elif asset['asset'] == 'DOGE':
                doge_balance = float(asset['free']) + float(asset['locked'])
    else:
        # Usar cuenta spot normal
        account = client.get_account()
        balances = {balance['asset']: float(balance['free']) for balance in account['balances']}
        
        usdt_balance = balances.get('USDT', 0.0)
        doge_balance = balances.get('DOGE', 0.0)
    
    return {
        'can_buy': usdt_balance >= 1.0,  # Mínimo $1.00 USDT para BUY
        'can_sell': doge_balance >= 1.0,  # Reducido a 1.0 DOGE para operaciones rentables
        'usdt_balance': usdt_balance,
        'doge_balance': doge_balance
    }

def filter_signal_by_capacity(signal, bot_type='conservative'):
    """Filtra una señal según la capacidad de trading actual"""
    if signal == "HOLD":
        return signal
    
    capacity = get_trading_capacity()
    
    if signal == "BUY" and not capacity['can_buy']:
        return "HOLD"  # No puede hacer BUY, mantener HOLD
    elif signal == "SELL" and not capacity['can_sell']:
        return "HOLD"  # No puede hacer SELL, mantener HOLD
    
    return signal  # Puede ejecutar la señal
