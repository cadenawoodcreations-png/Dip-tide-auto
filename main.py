
import yfinance as yf
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
import random
from groq import Groq

# ============================================
# CONFIGURATION - EDIT THESE
# ============================================

# GROQ API Configuration (pon tu API key aquí o en variable de entorno)
GROQ_API_KEY = "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"
# O mejor: os.environ.get('GROQ_API_KEY', '')

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# Your watchlist with price levels
WATCHLIST = {
    'TECK-B.TO': {'buy': 78.97, 'sell': 83.76, 'stop': 84.56},
    'HUZ.TO': {'buy': 33.50, 'sell': 36.50, 'stop': 31.50},
    'AEM.TO': {'buy': 320.00, 'sell': 345.00, 'stop': 315.00},
    'TMQ.TO': {'sell': [6.50, 7.00, 8.00], 'stop': 4.50},
}

# Email settings (get these from environment variables)
EMAIL_ENABLED = False
EMAIL_SENDER = os.environ.get('EMAIL_SENDER', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
EMAIL_RECIPIENT = os.environ.get('EMAIL_RECIPIENT', '')

# AI Analysis settings
AI_ENABLED = True  # Set to False to disable AI analysis
AI_ANALYSIS_INTERVAL = 6  # Run AI analysis every N cycles (6 ciclos = ~15 minutos)

# ============================================
# ANTI-RATE-LIMITING CONFIG
# ============================================
DELAY_BETWEEN_TICKERS = 5
DELAY_BETWEEN_CYCLES = 120
MAX_RETRIES = 3
RETRY_DELAY = 30

# ============================================
# AI ANALYSIS FUNCTIONS
# ============================================

def get_ai_market_insight():
    """Get market insight from Groq AI"""
    prompt = f"""You are a professional stock market analyst. Provide a brief analysis of the current market situation for TSX stocks.
    Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    Please provide:
    1. A general market sentiment (Bullish/Bearish/Neutral)
    2. One key insight for today's trading
    3. A cautionary note for traders
    
    Keep it concise, maximum 3 sentences."""
    
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",  # or "mixtral-8x7b-32768" for faster response
            messages=[
                {"role": "system", "content": "You are a professional stock market analyst providing concise, accurate insights."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_completion_tokens=300,
            top_p=1,
            stream=False  # False para respuesta completa
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        print(f"❌ AI Analysis Error: {e}")
        return None

def analyze_stock_with_ai(symbol, price, change, historical_data):
    """Get AI analysis for a specific stock"""
    
    # Crear resumen de datos históricos
    recent_prices = historical_data['Close'].tail(10).tolist() if not historical_data.empty else []
    recent_changes = historical_data['Close'].pct_change().tail(10).tolist() if not historical_data.empty else []
    
    prompt = f"""Analyze this stock:
    
    Symbol: {symbol}
    Current Price: ${price:.2f}
    Daily Change: {change:+.2f}%
    
    Recent prices (last 10 periods): {[f'${p:.2f}' for p in recent_prices]}
    
    Based on this data, provide:
    1. A BUY/SELL/HOLD recommendation
    2. Confidence level (1-10)
    3. Brief reasoning (1 sentence)
    
    Format: RECOMMENDATION|CONFIDENCE|REASONING"""
    
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are a technical analyst. Provide stock recommendations based on price action."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_completion_tokens=150,
            stream=False
        )
        
        result = completion.choices[0].message.content
        parts = result.split('|')
        
        if len(parts) == 3:
            return {
                'recommendation': parts[0].strip(),
                'confidence': parts[1].strip(),
                'reasoning': parts[2].strip()
            }
        else:
            return None
            
    except Exception as e:
        print(f"❌ Stock AI Analysis Error: {e}")
        return None

def stream_ai_analysis(prompt):
    """Stream AI response in real-time (like your example)"""
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are a helpful trading assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=1,
            max_completion_tokens=8192,
            top_p=1,
            reasoning_effort="medium",
            stream=True,
            stop=None
        )

        print("\n🤖 AI Assistant: ", end="")
        full_response = ""
        for chunk in completion:
            content = chunk.choices[0].delta.content or ""
            print(content, end="", flush=True)
            full_response += content
        print("\n")
        
        return full_response
        
    except Exception as e:
        print(f"❌ AI Stream Error: {e}")
        return None

# ============================================
# CORE FUNCTIONS (originales modificadas)
# ============================================

def send_alert(message):
    """Send email alert (if configured)"""
    print(f"🔔 {message}")
    
    if EMAIL_ENABLED and EMAIL_SENDER and EMAIL_PASSWORD:
        try:
            msg = MIMEText(message)
            msg['Subject'] = 'DIP & TIDE ALERT'
            msg['From'] = EMAIL_SENDER
            msg['To'] = EMAIL_RECIPIENT
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            print("  📧 Email sent")
        except Exception as e:
            print(f"  ❌ Email failed: {e}")

def get_price_with_retry(symbol, retries=0):
    """Get price with retry logic for rate limiting"""
    try:
        ticker = yf.Ticker(symbol)
        time.sleep(random.uniform(1, 3))
        hist = ticker.history(period='1d', interval='5m')
        
        if hist.empty:
            hist = ticker.history(period='1d', interval='30m')
            
        return hist
        
    except Exception as e:
        error_str = str(e)
        if "Too Many Requests" in error_str and retries < MAX_RETRIES:
            wait_time = RETRY_DELAY * (retries + 1)
            print(f"  ⏳ Rate limited on {symbol}. Waiting {wait_time}s...")
            time.sleep(wait_time)
            return get_price_with_retry(symbol, retries + 1)
        else:
            raise e

def check_prices(cycle_number):
    """Check current prices for all symbols with AI analysis"""
    print(f"\n📊 Checking prices at {datetime.now().strftime('%H:%M:%S')}")
    
    for i, (symbol, levels) in enumerate(WATCHLIST.items()):
        try:
            if i > 0:
                time.sleep(DELAY_BETWEEN_TICKERS)
            
            print(f"  🔍 Fetching {symbol}...")
            hist = get_price_with_retry(symbol)
            
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                open_price = hist['Close'].iloc[0] if len(hist) > 1 else price
                change = ((price - open_price) / open_price) * 100
                
                print(f"  ✅ {symbol}: ${price:.2f} ({change:+.2f}%)")
                
                # AI Analysis for this stock (every 3 cycles)
                if AI_ENABLED and cycle_number % 3 == 0:
                    ai_analysis = analyze_stock_with_ai(symbol, price, change, hist)
                    if ai_analysis:
                        print(f"  🤖 AI: {ai_analysis['recommendation']} (Confidence: {ai_analysis['confidence']}/10)")
                        print(f"     💡 {ai_analysis['reasoning']}")
                
                # Check buy zones
                if 'buy' in levels and price <= levels['buy'] * 1.01:
                    msg = f"✅ BUY ZONE: {symbol} at ${price:.2f} (target ${levels['buy']:.2f})"
                    send_alert(msg)
                
                # Check sell zones
                if 'sell' in levels:
                    if isinstance(levels['sell'], list):
                        for target in levels['sell']:
                            if price >= target * 0.99:
                                msg = f"💰 SELL TARGET: {symbol} at ${price:.2f} (target ${target:.2f})"
                                send_alert(msg)
                    elif price >= levels['sell'] * 0.99:
                        msg = f"💰 SELL ZONE: {symbol} at ${price:.2f} (target ${levels['sell']:.2f})"
                        send_alert(msg)
                
                # Check stop loss
                if 'stop' in levels and price <= levels['stop']:
                    msg = f"🚨 STOP LOSS: {symbol} at ${price:.2f} (stop ${levels['stop']:.2f})"
                    send_alert(msg)
            else:
                print(f"  ⚠️ No data for {symbol}")
                        
        except Exception as e:
            print(f"  ❌ Error checking {symbol}: {e}")

def main():
    """Main loop with AI integration"""
    print("\n" + "="*60)
    print(f"🚀 DIP & TIDE BOT WITH AI STARTED at {datetime.now()}")
    print("="*60)
    print(f"📈 Watching {len(WATCHLIST)} symbols")
    print(f"🤖 AI Analysis: {'ENABLED' if AI_ENABLED else 'DISABLED'}")
    
    # Test AI connection
    if AI_ENABLED:
        print("\n🔄 Testing AI connection...")
        test = get_ai_market_insight()
        if test:
            print(f"✅ AI Connected: {test}")
        else:
            print("⚠️ AI connection failed, but bot will continue without AI")
    
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            print(f"\n{'='*60}")
            print(f"🔄 CYCLE #{cycle_count} at {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*60}")
            
            # Regular price checking
            check_prices(cycle_count)
            
            # Market-wide AI analysis every AI_ANALYSIS_INTERVAL cycles
            if AI_ENABLED and cycle_count % AI_ANALYSIS_INTERVAL == 0:
                print("\n🤖 Running AI Market Analysis...")
                
                # Stream a market insight
                prompt = f"Give me a quick market update for TSX stocks. Current time: {datetime.now().strftime('%H:%M')}"
                stream_ai_analysis(prompt)
            
            # Long pause between cycles
            next_check = datetime.fromtimestamp(time.time() + DELAY_BETWEEN_CYCLES)
            print(f"\n⏸️  Cycle #{cycle_count} complete. Next check at: {next_check.strftime('%H:%M:%S')}")
            time.sleep(DELAY_BETWEEN_CYCLES)
            
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            break
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            time.sleep(DELAY_BETWEEN_CYCLES)

# ============================================
# START THE BOT
# ============================================

if __name__ == "__main__":
    main()
