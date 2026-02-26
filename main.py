
"""
DIP & TIDE QUANT SYSTEM v21.0 - COMPLETO CON CONFIGURACIÓN
===========================================
Sistema Quant Multi-Factor con:
- Tide Score (datos de marea Amador Pacific)
- Análisis técnico multi-timeframe (1m a yearly)
- Fuerza sectorial dinámica (1d,5d,1m)
- Screener de oportunidades con colores
- AI Wall Street Trader (20 años experiencia)
- Integración MetaTrader 5 para ejecución
- 24/7 automático (solo Ctrl+C lo detiene)
- HTTP GET/POST para consultas externas
- Colores verde (BUY) / rojo (SELL)
- CONFIGURACIÓN INTERACTIVA DE DATOS Y SERVER
"""

import MetaTrader5 as mt5
import requests
import pandas as pd
import numpy as np
import time
import json
import smtplib
import urllib.parse
import os
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
import yfinance as yf
from bs4 import BeautifulSoup

# ============================================
# COLORES PARA OUTPUT EN TERMINAL
# ============================================

class Colors:
    """Códigos ANSI para colores en terminal"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def color_signal(signal, text):
    """Retorna texto coloreado según la señal"""
    if signal in ['STRONG_BUY', 'BUY']:
        return f"{Colors.GREEN}{text}{Colors.END}"
    elif signal in ['STRONG_SELL', 'SELL']:
        return f"{Colors.RED}{text}{Colors.END}"
    elif signal == 'NEUTRAL':
        return f"{Colors.YELLOW}{text}{Colors.END}"
    else:
        return text

# ============================================
# CONFIGURACIÓN DE METATRADER
# ============================================

def init_mt5(account, password, server):
    """Inicializar conexión con MetaTrader 5"""
    if not mt5.initialize():
        print(f"{Colors.RED}❌ Error al inicializar MetaTrader 5{Colors.END}")
        return False
    
    authorized = mt5.login(login=account, password=password, server=server)
    if not authorized:
        print(f"{Colors.RED}❌ Error al conectar a la cuenta {account}{Colors.END}")
        print(f"{Colors.YELLOW}Error: {mt5.last_error()}{Colors.END}")
        return False
    
    account_info = mt5.account_info()
    if account_info:
        print(f"{Colors.GREEN}✅ Conectado a MetaTrader 5 - Cuenta: {account}{Colors.END}")
        print(f"   Balance: ${account_info.balance:.2f} | Equity: ${account_info.equity:.2f}")
    return True

def shutdown_mt5():
    mt5.shutdown()
    print(f"{Colors.BLUE}🔌 Conexión con MetaTrader cerrada{Colors.END}")

# ============================================
# SERVICIO HTTP (GET/POST)
# ============================================

class HTTPService:
    """Maneja todas las peticiones HTTP GET y POST"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DIP-TIDE-SYSTEM/21.0',
            'Accept': 'application/json'
        })
    
    def http_get(self, url, params=None, headers=None):
        """Realizar petición HTTP GET"""
        try:
            if params:
                url = f"{url}?{urllib.parse.urlencode(params)}"
            
            response = self.session.get(url, headers=headers or {}, timeout=10)
            response.raise_for_status()
            
            try:
                return response.json()
            except:
                return response.text
                
        except Exception as e:
            print(f"{Colors.RED}❌ GET error: {e}{Colors.END}")
            return None
    
    def http_post(self, url, data=None, json_data=None, headers=None):
        """Realizar petición HTTP POST"""
        try:
            response = self.session.post(
                url, 
                data=data, 
                json=json_data,
                headers=headers or {},
                timeout=10
            )
            response.raise_for_status()
            
            try:
                return response.json()
            except:
                return response.text
                
        except Exception as e:
            print(f"{Colors.RED}❌ POST error: {e}{Colors.END}")
            return None
    
    def get_finnhub_quote(self, symbol, api_key):
        """GET desde Finnhub"""
        url = "https://finnhub.io/api/v1/quote"
        params = {'symbol': symbol, 'token': api_key}
        return self.http_get(url, params)
    
    def post_telegram(self, bot_token, chat_id, message):
        """POST a Telegram"""
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {'chat_id': chat_id, 'text': message}
        return self.http_post(url, json_data=data)

# ============================================
# CONFIGURACIÓN INTERACTIVA
# ============================================

def setup_config():
    """Configuración interactiva de parámetros"""
    config = {}
    
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}🔧 CONFIGURACIÓN DEL SISTEMA DIP & TIDE{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")
    
    # ---------- API KEYS ----------
    print(f"\n{Colors.YELLOW}📡 CONFIGURACIÓN DE APIS{Colors.END}")
    print("-" * 40)
    
    config['FINNHUB_API_KEY'] = input(f"Finnhub API Key (ENTER para usar default): ").strip()
    if not config['FINNHUB_API_KEY']:
        config['FINNHUB_API_KEY'] = "d6f6ilpr01qvn4o20oagd6f6ilpr01qvn4o20ob0"
        print(f"{Colors.GREEN}✓ Usando API key por defecto{Colors.END}")
    
    config['GROQ_API_KEY'] = input(f"Groq API Key (ENTER para usar default): ").strip()
    if not config['GROQ_API_KEY']:
        config['GROQ_API_KEY'] = "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"
        print(f"{Colors.GREEN}✓ Usando API key por defecto{Colors.END}")
    
    config['NEWSAPI_KEY'] = input(f"NewsAPI Key (ENTER para usar default): ").strip()
    if not config['NEWSAPI_KEY']:
        config['NEWSAPI_KEY'] = "f6407d0a284d44ed98286124bb57103a"
        print(f"{Colors.GREEN}✓ Usando API key por defecto{Colors.END}")
    
    # ---------- METATRADER ----------
    print(f"\n{Colors.YELLOW}📊 CONFIGURACIÓN DE METATRADER 5{Colors.END}")
    print("-" * 40)
    
    config['MT5_ACCOUNT'] = input("Número de cuenta MT5: ").strip()
    if not config['MT5_ACCOUNT']:
        config['MT5_ACCOUNT'] = 0
        print(f"{Colors.YELLOW}⚠️ Sin cuenta MT5 - modo solo análisis{Colors.END}")
    else:
        try:
            config['MT5_ACCOUNT'] = int(config['MT5_ACCOUNT'])
        except:
            config['MT5_ACCOUNT'] = 0
    
    config['MT5_PASSWORD'] = input("Contraseña MT5: ").strip()
    config['MT5_SERVER'] = input("Servidor MT5 (ej: IC Markets-Demo): ").strip()
    
    # ---------- PARÁMETROS DE TRADING ----------
    print(f"\n{Colors.YELLOW}💰 CONFIGURACIÓN DE TRADING{Colors.END}")
    print("-" * 40)
    
    default_balance = input("Balance de cuenta (USD) [50000]: ").strip()
    config['ACCOUNT_BALANCE'] = float(default_balance) if default_balance else 50000
    
    default_risk = input("Riesgo por operación (%) [1.0]: ").strip()
    config['RISK_PER_TRADE'] = float(default_risk) if default_risk else 1.0
    
    # ---------- INTERVALO DE MONITOREO ----------
    print(f"\n{Colors.YELLOW}⏰ CONFIGURACIÓN DE AUTOMATIZACIÓN{Colors.END}")
    print("-" * 40)
    
    default_interval = input("Intervalo entre análisis (minutos) [60]: ").strip()
    config['MONITORING_INTERVAL'] = int(default_interval) if default_interval else 60
    
    return config

# ============================================
# PARÁMETROS DEL SISTEMA (TODOS DESDE DÍA 1)
# ============================================

def get_default_params():
    """Retorna todos los parámetros por defecto"""
    params = {
        # ---------- TIDE SCORE ----------
        'tide_roc_weight': 0.6,
        'tide_min_weight': -0.4,
        'tide_strong_buy': -1.5,
        'tide_buy': -0.5,
        'tide_neutral_low': -0.5,
        'tide_neutral_high': 0.5,
        'tide_sell': 0.5,
        'tide_strong_sell': 1.5,
        'tide_station': "Amador Pacific",
        'tide_latitude': 8.917133,
        'tide_longitude': -79.535161,
        'tide_datum': "MLWS",
        
        # ---------- INDICADORES TÉCNICOS ----------
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'adx_period': 14,
        'adx_trending': 25,
        'adx_strong_trend': 35,
        'sma_short': 20,
        'sma_medium': 50,
        'sma_long': 200,
        'ema_8': 8,
        'ema_21': 21,
        'volume_ratio_min': 1.0,
        'volume_ratio_daytrade': 1.2,
        'volume_lookback': 20,
        'support_resistance_lookback': 20,
        'near_level_percent': 2,
        'atr_period': 14,
        'atr_multiplier_stop': 3,
        'candlestick_lookback': 10,
        'pattern_weight_strong': 1.0,
        'pattern_weight_medium': 0.7,
        'pattern_weight_weak': 0.4,
        
        # ---------- SECTOR STRENGTH ----------
        'num_top_sectors': 3,
        'sector_weight_1d': 0.2,
        'sector_weight_5d': 0.3,
        'sector_weight_1m': 0.5,
        'min_sector_score': 60,
        'sector_rank_limit': 3,
        
        # ---------- ETFs POR SECTOR ----------
        'sector_etfs': {
            'MATERIALS': 'XMA.TO',
            'ENERGY': 'XEG.TO',
            'GOLD': 'XGD.TO',
            'SILVER': 'HUZ.TO',
            'TECHNOLOGY': 'XIT.TO',
            'FINANCIALS': 'XFN.TO',
            'HEALTHCARE': 'XHC.TO',
            'INDUSTRIALS': 'XIC.TO',
            'COMMUNICATION': 'XTL.TO',
            'UTILITIES': 'XUT.TO',
            'REALESTATE': 'XRE.TO'
        },
        
        # ---------- RIESGO Y POSICIÓN ----------
        'default_risk_per_trade': 0.01,
        'confidence_to_risk': {
            10: 0.02, 9: 0.015, 8: 0.01, 7: 0.01, 6: 0.005,
            5: 0.002, 4: 0.001, 3: 0.0, 2: 0.0, 1: 0.0
        },
        'stop_loss_pct': 0.03,
        'option_stop_loss_pct': 0.50,
        'trailing_stop_default_pct': 5,
        'daily_loss_limit_pct': 0.03,
        'weekly_loss_limit_pct': 0.06,
        'max_drawdown_pct': 0.15,
        'position_size_calc': "risk_based",
        'margin_multiplier': 2.0,
        'max_position_size_pct': 0.05,
        'max_sector_exposure_pct': 0.20,
        
        # ---------- SCORING FUNDAMENTAL ----------
        'fundamental_rules': {
            'pe':              {'threshold': 15,  'direction': 'less',    'score': 10},
            'forward_pe':      {'threshold': 15,  'direction': 'less',    'score': 10},
            'peg':             {'threshold': 1,   'direction': 'less',    'score': 10},
            'roe_pct':         {'threshold': 15,  'direction': 'greater', 'score': 10},
            'debt_equity':     {'threshold': 0.5, 'direction': 'less',    'score': 10},
            'eps_growth':      {'threshold': 10,  'direction': 'greater', 'score': 10},
            'profit_margin':   {'threshold': 10,  'direction': 'greater', 'score': 5},
            'dividend_yield':  {'threshold': 3,   'direction': 'greater', 'score': 5},
            'inst_ownership':  {'threshold': 50,  'direction': 'greater', 'score': 5}
        },
        
        # ---------- SCREENER ----------
        'screener_technical_weight': 0.6,
        'screener_fundamental_weight': 0.4,
        'screener_sector_weight': 0.3,
        'screener_top_n': 10,
        'screener_min_confidence': 6,
        'entry_zone_pct_below': 0.02,
        'entry_zone_pct_above': 0.02,
        'pullback_min_pct': 3,
        'pullback_max_pct': 10,
        'pullback_rsi_min': 30,
        'pullback_rsi_max': 50,
        'breakout_lookback': 20,
        'breakout_threshold': 0.95,
        
        # ---------- NOTICIAS Y REPORTES ----------
        'news_sources': ['finnhub', 'newsapi', 'finviz', 'ink'],
        'newsapi_lookback_days': 7,
        'finnhub_news_lookback_days': 7,
        'max_news_items': 10,
        'max_sec_filings': 5,
        'sec_filing_types': ['10-K', '10-Q', '8-K'],
        'max_analyst_ratings': 20,
        'insider_transactions_limit': 20,
        
        # ---------- OPCIONES ----------
        'gamma_multiplier_near_expiry': 5.0,
        'gamma_multiplier_medium': 2.5,
        'gamma_multiplier_normal': 1.0,
        'unusual_whales_enabled': False,
        'min_option_volume': 100,
        'min_oi_ratio': 1.5,
        'pin_probability_threshold': 0.5,
        'high_oi_threshold': 1000,
        
        # ---------- ALERTAS ----------
        'email_enabled': False,
        'telegram_enabled': False,
        'unusual_move_threshold': 5,
        'target_proximity_pct': 2,
        'stop_proximity_pct': 1,
        
        # ---------- AUTOMATIZACIÓN ----------
        'cloud_deployment': False,
        'scheduled_time': "06:00",
        'continuous_monitoring': True,
        'monitoring_interval': 60,
        'cache_enabled': True,
        'cache_duration': 60,
        
        # ---------- RUTAS DE ARCHIVOS ----------
        'portfolio_csv_path': "holdings.csv",
        'sector_stocks_csv_path': "sector_stocks.csv",
        'tide_data_path': "tide_data.csv",
        'trade_log_path': "trade_log.csv",
        'daily_report_path': "daily_report.txt",
        'error_log_path': "errors.log"
    }
    
    return params

# ============================================
# CLASE PRINCIPAL DIP & TIDE
# ============================================

class DipTideSystem:
    def __init__(self, config, params):
        self.config = config
        self.params = params
        self.http = HTTPService()
        self.finnhub_key = config['FINNHUB_API_KEY']
        self.groq_key = config['GROQ_API_KEY']
        self.newsapi_key = config['NEWSAPI_KEY']
        self.cache = {}
        self.account_balance = config['ACCOUNT_BALANCE']
        self.monitoring_interval = config['MONITORING_INTERVAL']
        
        # Conectar a MetaTrader
        self.mt5_connected = False
        if config['MT5_ACCOUNT'] and config['MT5_PASSWORD'] and config['MT5_SERVER']:
            self.mt5_connected = init_mt5(
                config['MT5_ACCOUNT'], 
                config['MT5_PASSWORD'], 
                config['MT5_SERVER']
            )
        
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}🚀 DIP & TIDE SYSTEM v21.0 INICIALIZADO{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.GREEN}✅ Wall Street Veteran Mode: ACTIVE{Colors.END}")
        print(f"{Colors.BLUE}📊 MetaTrader 5: {'CONECTADO' if self.mt5_connected else 'DESCONECTADO'}{Colors.END}")
        print(f"{Colors.MAGENTA}🌐 HTTP Services: READY{Colors.END}")
        print(f"{Colors.YELLOW}💰 Balance: ${self.account_balance:,.2f}{Colors.END}")
    
    # ---------- MÉTODOS DE PRECIOS ----------
    def get_quote(self, symbol):
        """Obtener precio en vivo desde Finnhub"""
        url = "https://finnhub.io/api/v1/quote"
        params = {'symbol': symbol, 'token': self.finnhub_key}
        data = self.http.http_get(url, params)
        if data and 'c' in data and data['c'] > 0:
            return {
                'price': data['c'],
                'change': data['d'],
                'change_pct': data['dp'],
                'high': data['h'],
                'low': data['l']
            }
        return None
    
    def get_price(self, symbol):
        """Obtener precio con caché"""
        if self.params['cache_enabled'] and symbol in self.cache:
            timestamp, price = self.cache[symbol]
            if (datetime.now() - timestamp).seconds < self.params['cache_duration']:
                return price
        
        quote = self.get_quote(symbol)
        if quote:
            if self.params['cache_enabled']:
                self.cache[symbol] = (datetime.now(), quote['price'])
            return quote['price']
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            if not data.empty:
                price = data['Close'].iloc[-1]
                if self.params['cache_enabled']:
                    self.cache[symbol] = (datetime.now(), price)
                return price
        except:
            pass
        
        return None
    
    def get_historical(self, symbol, period="3mo"):
        """Obtener datos históricos desde Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            return df
        except:
            return None
    
    # ---------- INDICADORES TÉCNICOS ----------
    def calculate_rsi(self, df, period=None):
        if period is None:
            period = self.params['rsi_period']
        if df is None or len(df) < period:
            return 50
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    
    def calculate_adx(self, df, period=None):
        if period is None:
            period = self.params['adx_period']
        if df is None or len(df) < period*2:
            return 20
        high = df['High']
        low = df['Low']
        close = df['Close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        up = high - high.shift()
        down = low.shift() - low
        plus_dm = (up > down) & (up > 0)
        minus_dm = (down > up) & (down > 0)
        plus_di = 100 * (plus_dm.rolling(window=period).sum() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).sum() / atr)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        return adx.iloc[-1] if not adx.empty else 20
    
    def get_moving_averages(self, df):
        if df is None or len(df) < self.params['sma_long']:
            return {}
        close = df['Close']
        sma20 = close.rolling(self.params['sma_short']).mean().iloc[-1]
        sma50 = close.rolling(self.params['sma_medium']).mean().iloc[-1]
        sma200 = close.rolling(self.params['sma_long']).mean().iloc[-1]
        return {'sma20': sma20, 'sma50': sma50, 'sma200': sma200}
    
    def get_support_resistance(self, df):
        if df is None or len(df) < self.params['support_resistance_lookback']:
            return {}
        lookback = self.params['support_resistance_lookback']
        high = df['High'].iloc[-lookback:].max()
        low = df['Low'].iloc[-lookback:].min()
        return {'resistance': high, 'support': low}
    
    # ---------- FUERZA SECTORIAL ----------
    def get_sector_strength_multiframe(self):
        """Ranking de sectores por rendimiento 1d, 5d, 1m"""
        scores = {}
        for sector, etf in self.params['sector_etfs'].items():
            df = self.get_historical(etf, period="1mo")
            if df is None or len(df) < 5:
                continue
            close = df['Close']
            ret_1d = (close.iloc[-1] / close.iloc[-2] - 1) * 100
            ret_5d = (close.iloc[-1] / close.iloc[-6] - 1) * 100 if len(close) >= 6 else 0
            ret_1m = (close.iloc[-1] / close.iloc[0] - 1) * 100
            
            composite = (ret_1d * self.params['sector_weight_1d']) + \
                       (ret_5d * self.params['sector_weight_5d']) + \
                       (ret_1m * self.params['sector_weight_1m'])
            scores[sector] = round(composite, 2)
        
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked
    
    # ---------- SCREENER DE OPORTUNIDADES ----------
    def scan_opportunities(self):
        """Buscar oportunidades en los mejores sectores"""
        print(f"\n{Colors.BLUE}📈 SCANNING FOR OPPORTUNITIES...{Colors.END}")
        
        ranked_sectors = self.get_sector_strength_multiframe()
        top_sectors = [s for s,_ in ranked_sectors[:self.params['num_top_sectors']]]
        print(f"{Colors.YELLOW}🏆 TOP SECTORS: {', '.join(top_sectors)}{Colors.END}")
        
        sector_stocks = {
            'MATERIALS': ['TECK.B', 'FM.TO', 'LUN.TO', 'HBM.TO', 'FCX', 'RIO', 'BHP'],
            'ENERGY': ['CNQ.TO', 'SU.TO', 'COP', 'XOM', 'ENB.TO', 'CVE.TO'],
            'GOLD': ['AEM.TO', 'WPM.TO', 'NEM', 'GOLD', 'K.TO'],
            'SILVER': ['FR.TO', 'PAAS.TO', 'SVM.TO'],
            'TECHNOLOGY': ['NVDA', 'MU.TO', 'AMD', 'MSFT', 'AAPL'],
            'FINANCIALS': ['RY.TO', 'TD.TO', 'BNS.TO', 'BMO.TO'],
        }
        
        opportunities = []
        for sector in top_sectors:
            if sector not in sector_stocks:
                continue
            for sym in sector_stocks[sector]:
                price = self.get_price(sym)
                if not price:
                    continue
                df = self.get_historical(sym)
                if df is None:
                    continue
                rsi = self.calculate_rsi(df)
                ma = self.get_moving_averages(df)
                sr = self.get_support_resistance(df)
                
                signal = 'NEUTRAL'
                confidence = 5
                entry = price
                reason = ""
                
                if rsi < self.params['rsi_oversold']:
                    signal = 'BUY'
                    confidence = 7
                    entry = sr.get('support', price * 0.95)
                    reason = f"Oversold (RSI {rsi:.1f}) near support"
                elif price > ma.get('sma50', 0) and rsi < self.params['rsi_overbought'] and rsi > 40:
                    signal = 'BUY'
                    confidence = 8
                    entry = price * 0.98
                    reason = f"Uptrend, healthy RSI {rsi:.1f}"
                elif rsi > self.params['rsi_overbought']:
                    signal = 'SELL'
                    confidence = 6
                    entry = price * 1.02
                    reason = f"Overbought (RSI {rsi:.1f})"
                
                if confidence >= self.params['screener_min_confidence']:
                    opportunities.append({
                        'symbol': sym,
                        'price': round(price, 2),
                        'signal': signal,
                        'confidence': confidence,
                        'entry': round(entry, 2),
                        'sector': sector,
                        'reason': reason,
                        'rsi': round(rsi, 1)
                    })
        
        opportunities.sort(key=lambda x: x['confidence'], reverse=True)
        return opportunities[:self.params['screener_top_n']]
    
    # ---------- EJECUCIÓN DE ÓRDENES EN METATRADER ----------
    def place_mt5_order(self, symbol, action, lots, entry_price, stop_loss, take_profit):
        """Colocar orden en MetaTrader 5"""
        if not self.mt5_connected:
            print(f"{Colors.RED}❌ No conectado a MetaTrader{Colors.END}")
            return False
        
        mt5_symbol = symbol.replace('.TO', '').replace('.', '')
        
        symbol_info = mt5.symbol_info(mt5_symbol)
        if symbol_info is None:
            print(f"{Colors.RED}❌ Símbolo {mt5_symbol} no encontrado en MT5{Colors.END}")
            return False
        
        if not symbol_info.visible:
            if not mt5.symbol_select(mt5_symbol, True):
                print(f"{Colors.RED}❌ No se pudo seleccionar {mt5_symbol}{Colors.END}")
                return False
        
        order_type = mt5.ORDER_TYPE_BUY if action == 'BUY' else mt5.ORDER_TYPE_SELL
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": mt5_symbol,
            "volume": lots,
            "type": order_type,
            "price": entry_price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 10,
            "magic": 234000,
            "comment": "DIP TIDE SIGNAL",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"{Colors.RED}❌ Error en orden: {result.comment}{Colors.END}")
            return False
        else:
            print(f"{Colors.GREEN}✅ Orden ejecutada: {result.order}{Colors.END}")
            return result
    
    def calculate_lots(self, confidence, entry_price, stop_loss):
        """Calcular tamaño de posición basado en riesgo"""
        risk_pct = self.params['confidence_to_risk'].get(confidence, self.params['default_risk_per_trade'])
        risk_amount = self.account_balance * risk_pct
        stop_distance = abs(entry_price - stop_loss)
        
        if stop_distance == 0:
            return 0.01
        
        raw_lots = risk_amount / stop_distance / 100000
        lots = round(raw_lots, 2)
        return max(0.01, lots)
    
    # ---------- IA COMO TRADER DE WALL STREET ----------
    def groq_analysis(self, prompt):
        """Consultar Groq AI"""
        if not self.groq_key:
            return "Groq API key no configurada"
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "mixtral-8x7b-32768",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        result = self.http.http_post(url, json_data=data, headers=headers)
        if result and 'choices' in result:
            return result['choices'][0]['message']['content']
        return "Error en análisis"
    
    def professional_trader_analysis(self, symbol, analysis_data):
        """Análisis de trader profesional con 20 años de experiencia"""
        prompt = f"""You are a Wall Street veteran trader with 20 years of experience managing institutional portfolios. 
        You have survived multiple market cycles (2008, 2020, etc.) and have a reputation for clear, decisive analysis.
        
        Analyze {symbol} based on the following data:
        
        TECHNICAL ANALYSIS:
        - Current Price: ${analysis_data['price']:.2f}
        - RSI (14): {analysis_data['rsi']:.1f} ({'oversold' if analysis_data['rsi'] < 30 else 'overbought' if analysis_data['rsi'] > 70 else 'neutral'})
        - 50-day MA: ${analysis_data['sma50']:.2f} (Price is {'above' if analysis_data['price'] > analysis_data['sma50'] else 'below'} MA)
        - Volume Ratio: {analysis_data['volume_ratio']:.2f}x average
        
        SECTOR CONTEXT:
        - Sector: {analysis_data['sector']} (Rank #{analysis_data['sector_rank']})
        
        Provide a professional trading recommendation with:
        1. CLEAR SIGNAL (BUY/SELL/HOLD) in bold
        2. Entry price or zone
        3. Stop loss level
        4. Price target(s)
        5. Risk assessment (low/medium/high)
        6. One sentence of Wall Street wisdom
        
        Be decisive, use professional terminology."""
        
        response = self.groq_analysis(prompt)
        
        if 'BUY' in response.upper():
            response = f"{Colors.GREEN}{response}{Colors.END}"
        elif 'SELL' in response.upper():
            response = f"{Colors.RED}{response}{Colors.END}"
        
        return response
    
    def prepare_analysis_data(self, symbol):
        """Preparar datos para análisis de IA"""
        price = self.get_price(symbol)
        df = self.get_historical(symbol)
        sector_ranks = self.get_sector_strength_multiframe()
        
        sector = 'UNKNOWN'
        sector_rank = 99
        for i, (s_name, _) in enumerate(sector_ranks, 1):
            if s_name in ['MATERIALS', 'ENERGY', 'GOLD'] and any(x in symbol for x in ['CNQ', 'AEM', 'TECK']):
                sector = s_name
                sector_rank = i
                break
        
        return {
            'symbol': symbol,
            'price': price,
            'rsi': self.calculate_rsi(df) if df is not None else 50,
            'sma50': df['Close'].rolling(50).mean().iloc[-1] if df is not None and len(df) > 50 else price,
            'volume_ratio': (df['Volume'].iloc[-5:].mean() / df['Volume'].iloc[-20:].mean()) if df is not None else 1,
            'sector': sector,
            'sector_rank': sector_rank
        }
    
    # ---------- CICLO PRINCIPAL 24/7 ----------
    def run_24_7(self):
        """Bucle principal que corre 24/7 hasta Ctrl+C"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}🚀 DIP & TIDE 24/7 AUTOMATED TRADER STARTED{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Balance: ${self.account_balance:,.2f}")
        print(f"Press {Colors.RED}Ctrl+C{Colors.END} to stop the system")
        print(f"{'='*60}\n")
        
        cycle = 0
        while True:
            try:
                cycle += 1
                print(f"\n{Colors.BLUE}{'─'*60}{Colors.END}")
                print(f"{Colors.BOLD}CYCLE #{cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
                print(f"{Colors.BLUE}{'─'*60}{Colors.END}")
                
                opportunities = self.scan_opportunities()
                
                if opportunities:
                    print(f"\n{Colors.GREEN}{Colors.BOLD}📊 TOP OPPORTUNITIES:{Colors.END}")
                    for opp in opportunities[:5]:
                        signal_color = Colors.GREEN if opp['signal'] in ['BUY','STRONG_BUY'] else Colors.RED if opp['signal'] in ['SELL','STRONG_SELL'] else Colors.YELLOW
                        print(f"  {signal_color}{opp['symbol']}: {opp['signal']} (Conf: {opp['confidence']}/10){Colors.END}")
                        print(f"     Price: ${opp['price']:.2f} | Entry: ${opp['entry']:.2f} | RSI: {opp['rsi']}")
                        print(f"     {opp['reason']}")
                
                if opportunities and self.groq_key:
                    print(f"\n{Colors.MAGENTA}{Colors.BOLD}🧠 WALL STREET VETERAN ANALYSIS:{Colors.END}")
                    for opp in opportunities[:3]:
                        print(f"\n{Colors.WHITE}{Colors.BOLD}--- {opp['symbol']} ---{Colors.END}")
                        analysis_data = self.prepare_analysis_data(opp['symbol'])
                        ai_output = self.professional_trader_analysis(opp['symbol'], analysis_data)
                        print(ai_output)
                
                if self.mt5_connected and opportunities:
                    print(f"\n{Colors.BLUE}📊 EJECUTANDO ÓRDENES EN METATRADER...{Colors.END}")
                    for opp in opportunities[:2]:
                        if opp['signal'] in ['BUY', 'SELL'] and opp['confidence'] >= 7:
                            stop = opp['price'] * 0.97 if opp['signal'] == 'BUY' else opp['price'] * 1.03
                            target = opp['price'] * 1.05 if opp['signal'] == 'BUY' else opp['price'] * 0.95
                            lots = self.calculate_lots(opp['confidence'], opp['price'], stop)
                            
                            print(f"  {opp['signal']} {opp['symbol']}: {lots} lots @ ${opp['price']:.2f}")
                            print(f"     Stop: ${stop:.2f} | Target: ${target:.2f}")
                            
                            # Descomentar para ejecución real
                            # self.place_mt5_order(opp['symbol'], opp['signal'], lots, opp['price'], stop, target)
                
                next_run = datetime.now() + timedelta(minutes=self.monitoring_interval)
                print(f"\n{Colors.CYAN}⏰ Next analysis at: {next_run.strftime('%H:%M:%S')}{Colors.END}")
                
                for _ in range(self.monitoring_interval * 60):
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print(f"\n\n{Colors.RED}{Colors.BOLD}🛑 SYSTEM STOPPED BY USER (Ctrl+C){Colors.END}")
                print(f"Final cycle: #{cycle} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                if self.mt5_connected:
                    shutdown_mt5()
                break
            except Exception as e:
                print(f"\n{Colors.RED}❌ Error en ciclo #{cycle}: {e}{Colors.END}")
                import traceback
                traceback.print_exc()
                time.sleep(60)

# ============================================
# PUNTO DE ENTRADA PRINCIPAL
# ============================================

def main():
    """Función principal"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}🌊 DIP & TIDE QUANT SYSTEM v21.0{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")
    
    # Configuración inicial
    config = setup_config()
    params = get_default_params()
    
    # Crear instancia del sistema
    bot = DipTideSystem(config, params)
    
    # Menú principal
    while True:
        print(f"\n{Colors.CYAN}{Colors.BOLD}📋 MENÚ PRINCIPAL{Colors.END}")
        print("-" * 40)
        print("1. 🔍 Análisis único (morning routine)")
        print(f"2. {Colors.GREEN}🔄 MODO 24/7 CONTINUO (Ctrl+C para detener){Colors.END}")
        print("3. 📊 Probar conexión MetaTrader")
        print("4. ⚙️ Reconfigurar parámetros")
        print("5. ❌ Salir")
        
        choice = input("\nSelecciona una opción (1-5): ").strip()
        
        if choice == '1':
            opps = bot.scan_opportunities()
            if opps:
                print(f"\n{Colors.GREEN}{Colors.BOLD}📊 TOP OPPORTUNITIES:{Colors.END}")
                for opp in opps:
                    signal_color = Colors.GREEN if opp['signal'] in ['BUY','STRONG_BUY'] else Colors.RED if opp['signal'] in ['SELL','STRONG_SELL'] else Colors.YELLOW
                    print(f"  {signal_color}{opp['symbol']}: {opp['signal']} (Conf: {opp['confidence']}/10){Colors.END}")
        
        elif choice == '2':
            bot.run_24_7()
        
        elif choice == '3':
            if bot.mt5_connected:
                account_info = mt5.account_info()
                if account_info:
                    print(f"{Colors.GREEN}✅ MetaTrader conectado correctamente{Colors.END}")
                    print(f"   Balance: ${account_info.balance:.2f}")
                    print(f"   Equity: ${account_info.equity:.2f}")
                    print(f"   Margin: ${account_info.margin:.2f}")
                    print(f"   Free Margin: ${account_info.margin_free:.2f}")
                else:
                    print(f"{Colors.RED}❌ Error obteniendo información de cuenta{Colors.END}")
            else:
                print(f"{Colors.RED}❌ MetaTrader no conectado{Colors.END}")
        
        elif choice == '4':
            config = setup_config()
            bot.account_balance = config['ACCOUNT_BALANCE']
            bot.monitoring_interval = config['MONITORING_INTERVAL']
            print(f"{Colors.GREEN}✅ Configuración actualizada{Colors.END}")
        
        elif choice == '5':
            if bot.mt5_connected:
                shutdown_mt5()
            print(f"{Colors.CYAN}👋 ¡Hasta luego!{Colors.END}")
            sys.exit(0)
        
        else:
            print(f"{Colors.RED}❌ Opción inválida{Colors.END}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.RED}{Colors.BOLD}🛑 Sistema detenido por usuario{Colors.END}")
        shutdown_mt5()
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error fatal: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        shutdown_mt5()
