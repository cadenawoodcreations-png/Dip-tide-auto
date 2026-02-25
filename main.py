"""
DIP & TIDE QUANT SYSTEM v13.0
Configurable Investigation Parameters + Live Data (Finnhub) + Groq AI integration
"""

import requests
import time
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import yfinance as yf  # kept for historical data & backup

# ============================================
# INVESTIGATION PARAMETERS – EDIT THESE
# ============================================

# ---------- TIDE SCORE FORMULA ----------
tide_roc_weight = 0.6
tide_min_weight = -0.4

tide_strong_buy = -1.5
tide_buy = -0.5
tide_sell = 0.5
tide_strong_sell = 1.5

# ---------- TECHNICAL INDICATORS ----------
rsi_oversold = 30
rsi_overbought = 70
adx_trending = 25
volume_ratio_min = 1.0
volume_ratio_daytrade = 1.2
sma_short = 20
sma_medium = 50
sma_long = 200
support_resistance_lookback = 20
near_level_percent = 2

# ---------- SECTOR STRENGTH ----------
max_sector_rank = 3

# ---------- OPTIONS FLOW / GAMMA ----------
gamma_multiplier_near_expiry = 5.0
gamma_multiplier_medium = 2.5
gamma_multiplier_normal = 1.0

# ---------- RISK MANAGEMENT ----------
default_risk_per_trade = 0.01
confidence_to_risk = {
    10: 0.02,
    9: 0.015,
    8: 0.01,
    7: 0.01,
    6: 0.005,
    5: 0.002,
    4: 0.001,
    3: 0.0,
    2: 0.0,
    1: 0.0
}
stop_loss_pct = 0.03
option_stop_loss_pct = 0.50
daily_loss_limit_pct = 0.03
weekly_loss_limit_pct = 0.06

# ---------- ALERTS ----------
email_enabled = False
email_sender = ""
email_password = ""
email_recipient = ""

telegram_enabled = False
telegram_bot_token = ""
telegram_chat_id = ""

# ============================================
# API KEYS (Provided by user)
# ============================================
FINNHUB_API_KEY = "d6f6ilpr01qvn4o20oagd6f6ilpr01qvn4o20ob0"
GROQ_API_KEY = "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"

# ============================================
# YOUR QUESTRADE HOLDINGS (as of 2026-02-24)
# ============================================
portfolio = {
    'ARG.TO': {'shares': 200, 'avg_cost': 6.12, 'sector': 'MATERIALS', 'stop': 5.50, 'targets': [6.50, 7.00, 8.00]},
    'CNQ.TO': {'shares': 25, 'avg_cost': 43.40, 'sector': 'ENERGY', 'trailing_stop': 55.00, 'trailing_pct': 5},
    'HBM.TO': {'shares': 30, 'avg_cost': 35.01, 'sector': 'MATERIALS', 'stop': 33.00, 'targets': [38.00, 42.00]},
    'MU.TO': {'shares': 21, 'avg_cost': 86.77, 'sector': 'TECHNOLOGY', 'stop': 85.00, 'targets': [95.00, 100.00]},
    'NVDA': {'shares': 25, 'avg_cost': 43.54, 'sector': 'TECHNOLOGY', 'stop': 40.00, 'targets': [45.00, 50.00]},
    'TMQ.TO': {'shares': 135, 'avg_cost': 8.42, 'sector': 'MATERIALS', 'stop': 4.50, 'targets': [6.50, 7.00, 8.00], 'notes': 'TD upgraded to BUY @ $8.00'},
    'VEE.TO': {'shares': 22, 'avg_cost': 47.03, 'sector': 'EMERGING', 'stop': 45.00, 'targets': [50.00, 55.00]},
    'XGD.TO': {'shares': 20, 'avg_cost': 58.70, 'sector': 'GOLD', 'stop': 60.00, 'targets': [70.00, 75.00]},
    'EWY': {'shares': 10, 'avg_cost': 117.61, 'sector': 'INTERNATIONAL', 'stop': 110.00, 'targets': [150.00], 'note': 'P/E 293x - overvalued'},
    'EWZ': {'shares': 15, 'avg_cost': 36.72, 'sector': 'INTERNATIONAL', 'stop': 35.00, 'targets': [42.00, 45.00]}
}

cash_balance = 23679.72

# ============================================
# MAIN BOT CLASS
# ============================================

class DipTideBot:
    def __init__(self):
        self.finnhub_key = FINNHUB_API_KEY
        self.groq_key = GROQ_API_KEY
        self.base_url = "https://finnhub.io/api/v1"
        self.cache = {}
        self.portfolio = portfolio
        self.cash = cash_balance
        self.daily_pnl = 0
        self.weekly_pnl = 0
        self.trades_log = []

    # ---------- LIVE DATA FROM FINNHUB ----------
    def get_quote(self, symbol):
        url = f"{self.base_url}/quote"
        params = {'symbol': symbol, 'token': self.finnhub_key}
        try:
            r = requests.get(url, params=params, timeout=10)
            data = r.json()
            if 'c' in data and data['c'] > 0:
                return {
                    'symbol': symbol,
                    'price': data['c'],
                    'change': data['d'],
                    'change_pct': data['dp'],
                    'high': data['h'],
                    'low': data['l'],
                    'open': data['o'],
                    'prev_close': data['pc'],
                    'timestamp': datetime.now()
                }
        except Exception as e:
            print(f"Finnhub error for {symbol}: {e}")
        return None

    def get_yahoo_quote(self, symbol):
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            if not data.empty:
                price = data['Close'].iloc[-1]
                return {'symbol': symbol, 'price': price, 'source': 'yahoo'}
        except:
            pass
        return None

    def get_price(self, symbol):
        quote = self.get_quote(symbol)
        if quote:
            return quote['price']
        yq = self.get_yahoo_quote(symbol)
        if yq:
            return yq['price']
        if symbol in self.cache:
            return self.cache[symbol]
        return None

    # ---------- TECHNICAL INDICATORS ----------
    def get_historical(self, symbol, period="3mo"):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            return df
        except:
            return None

    def calculate_rsi(self, df, period=14):
        if df is None or len(df) < period:
            return 50
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    def calculate_adx(self, df, period=14):
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
        if df is None or len(df) < sma_long:
            return {}
        close = df['Close']
        sma20 = close.rolling(sma_short).mean().iloc[-1]
        sma50 = close.rolling(sma_medium).mean().iloc[-1]
        sma200 = close.rolling(sma_long).mean().iloc[-1]
        return {'sma20': sma20, 'sma50': sma50, 'sma200': sma200}

    def get_support_resistance(self, df):
        if df is None or len(df) < support_resistance_lookback:
            return {}
        high = df['High'].iloc[-support_resistance_lookback:].max()
        low = df['Low'].iloc[-support_resistance_lookback:].min()
        return {'resistance': high, 'support': low}

    # ---------- SECTOR STRENGTH ----------
    def get_sector_strength(self):
        sector_etfs = {
            'MATERIALS': 'XMA.TO',
            'ENERGY': 'XEG.TO',
            'GOLD': 'XGD.TO',
            'SILVER': 'HUZ.TO',
            'TECHNOLOGY': 'XIT.TO',
            'FINANCIALS': 'XFN.TO',
            'HEALTHCARE': 'XHC.TO',
            'INDUSTRIALS': 'XIC.TO'
        }
        scores = {}
        for sector, etf in sector_etfs.items():
            price = self.get_price(etf)
            if price is None:
                continue
            hist = self.get_historical(etf, period="1mo")
            if hist is not None and len(hist) > 1:
                ret_1m = (price / hist['Close'].iloc[0] - 1) * 100
                scores[sector] = ret_1m
            else:
                scores[sector] = 0
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return {sector: rank+1 for rank, (sector, _) in enumerate(ranked)}

    # ---------- TIDE SCORE (placeholder) ----------
    def get_tide_score(self):
        # TODO: integrate your Amador Pacific tide data
        return -0.31

    # ---------- PORTFOLIO MANAGEMENT ----------
    def update_portfolio_prices(self):
        total_value = self.cash
        positions = []
        for symbol, data in self.portfolio.items():
            price = self.get_price(symbol)
            if price is None:
                print(f"  ⚠️ Could not get price for {symbol}, skipping")
                continue
            market_value = price * data['shares']
            cost = data['avg_cost'] * data['shares']
            pnl = market_value - cost
            pnl_pct = (pnl / cost) * 100 if cost else 0
            total_value += market_value
            positions.append({
                'symbol': symbol,
                'price': price,
                'shares': data['shares'],
                'market_value': market_value,
                'cost': cost,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'sector': data.get('sector', 'OTHER')
            })
        self.cache_prices = {p['symbol']: p['price'] for p in positions}
        return positions, total_value

    def check_alerts(self, positions):
        alerts = []
        for pos in positions:
            sym = pos['symbol']
            data = self.portfolio[sym]
            price = pos['price']
            if 'stop' in data and price <= data['stop']:
                alerts.append(f"🚨 STOP LOSS: {sym} at ${price:.2f} (stop ${data['stop']:.2f})")
            if 'trailing_stop' in data and price <= data['trailing_stop']:
                alerts.append(f"🛡️ TRAILING STOP: {sym} at ${price:.2f} (trailing stop hit)")
            if 'targets' in data:
                for t in data['targets']:
                    if price >= t * 0.98:
                        alerts.append(f"💰 TARGET: {sym} at ${price:.2f} (target ${t:.2f})")
            if 'prev_price' in self.cache and sym in self.cache['prev_price']:
                prev = self.cache['prev_price'][sym]
                change = (price - prev)/prev * 100
                if abs(change) > 5:
                    alerts.append(f"⚠️ UNUSUAL MOVE: {sym} {change:+.2f}%")
        return alerts

    # ---------- OPPORTUNITY SCANNER ----------
    def scan_opportunities(self):
        print("\n📈 SCANNING FOR OPPORTUNITIES...")
        sector_ranks = self.get_sector_strength()
        top_sectors = [s for s, r in sector_ranks.items() if r <= max_sector_rank]
        print(f"Top sectors: {', '.join(top_sectors)}")

        watchlist = [
            'TECK.B', 'CNQ.TO', 'SU.TO', 'AEM.TO', 'WPM.TO', 'FM.TO', 'LUN.TO',
            'FCX', 'NEM', 'GOLD', 'COP', 'XOM', 'RIO', 'BHP'
        ]
        opportunities = []
        for sym in watchlist:
            price = self.get_price(sym)
            if not price:
                continue
            df = self.get_historical(sym)
            if df is None:
                continue
            rsi = self.calculate_rsi(df)
            ma = self.get_moving_averages(df)
            sr = self.get_support_resistance(df)
            sector = ('MATERIALS' if sym in ['TECK.B','FM.TO','LUN.TO','FCX','RIO','BHP'] else
                      'ENERGY' if sym in ['CNQ.TO','SU.TO','COP','XOM'] else
                      'GOLD' if sym in ['AEM.TO','WPM.TO','NEM','GOLD'] else 'OTHER')
            if sector not in sector_ranks or sector_ranks[sector] > max_sector_rank:
                continue
            if rsi < rsi_oversold:
                signal = 'OVERSOLD'
                confidence = 7
                entry = sr.get('support', price * 0.95)
                reason = f"RSI {rsi:.1f} near support"
            elif price > ma.get('sma50', 0) and rsi < rsi_overbought and rsi > 40:
                signal = 'BUY'
                confidence = 8
                entry = price * 0.98
                reason = f"Uptrend, RSI {rsi:.1f}"
            else:
                continue
            opportunities.append({
                'symbol': sym,
                'price': price,
                'signal': signal,
                'confidence': confidence,
                'entry_zone': round(entry,2),
                'sector': sector,
                'reason': reason
            })
        opportunities.sort(key=lambda x: x['confidence'], reverse=True)
        return opportunities[:10]

    # ---------- GROQ AI INTEGRATION ----------
    def groq_analysis(self, prompt):
        if not self.groq_key:
            return "Groq API key not set."
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
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            return f"Groq API error: {e}"

    # ---------- MAIN ROUTINE ----------
    def run_morning_routine(self):
        print("\n" + "🚀"*40)
        print(" DIP & TIDE MORNING ROUTINE".center(60))
        print("🚀"*40)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        positions, total_value = self.update_portfolio_prices()
        print(f"\n💰 Portfolio Value: ${total_value:,.2f}")
        print(f"💵 Cash: ${self.cash:,.2f}")
        total_pnl = total_value - self.cash - sum(p['cost'] for p in positions)
        print(f"📈 Total P&L: ${total_pnl:+,.2f}")

        alerts = self.check_alerts(positions)
        if alerts:
            print("\n🔔 ALERTS:")
            for a in alerts:
                print(f"  {a}")

        opps = self.scan_opportunities()
        print("\n🎯 TOP OPPORTUNITIES:")
        for i, opp in enumerate(opps, 1):
            print(f"\n  {i}. {opp['symbol']} - {opp['signal']} (Conf: {opp['confidence']}/10)")
            print(f"     Price: ${opp['price']:.2f} | Entry Zone: ${opp['entry_zone']:.2f}")
            print(f"     {opp['reason']}")

        print("\n" + "="*60)
        print("✅ Morning routine complete.")
        return positions, opps

    def send_alert(self, message):
        if email_enabled and email_sender and email_password:
            try:
                msg = MIMEText(message)
                msg['Subject'] = 'DIP & TIDE Alert'
                msg['From'] = email_sender
                msg['To'] = email_recipient
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(email_sender, email_password)
                server.send_message(msg)
                server.quit()
            except Exception as e:
                print(f"Email failed: {e}")
        if telegram_enabled and telegram_bot_token and telegram_chat_id:
            try:
                url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
                data = {'chat_id': telegram_chat_id, 'text': message}
                requests.post(url, data=data)
            except:
                pass

# ============================================
# MAIN EXECUTION
# ============================================
if __name__ == "__main__":
    bot = DipTideBot()
    bot.run_morning_routine()
