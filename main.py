import yfinance as yf
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
import random

# ============================================
# CONFIGURATION - EDIT THESE
# ============================================

# Your watchlist with price levels
WATCHLIST = {
    'TECK-B.TO': {'buy': 78.97, 'sell': 83.76, 'stop': 84.56},
    'HUZ.TO': {'buy': 33.50, 'sell': 36.50, 'stop': 31.50},
    'AEM.TO': {'buy': 320.00, 'sell': 345.00, 'stop': 315.00},
    'TMQ.TO': {'sell': [6.50, 7.00, 8.00], 'stop': 4.50},
}

# Email settings (get these from environment variables)
EMAIL_ENABLED = False  # Set to True when you add email credentials
EMAIL_SENDER = os.environ.get('EMAIL_SENDER', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
EMAIL_RECIPIENT = os.environ.get('EMAIL_RECIPIENT', '')

# ============================================
# ANTI-RATE-LIMITING CONFIG
# ============================================
DELAY_BETWEEN_TICKERS = 5  # Seconds between each ticker (5-8 is safe)
DELAY_BETWEEN_CYCLES = 120  # Seconds between complete cycles (2 minutes)
MAX_RETRIES = 3  # Max retries if rate limited
RETRY_DELAY = 30  # Seconds to wait if rate limited

# ============================================
# CORE FUNCTIONS
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
        # Add random delay to appear more human
        time.sleep(random.uniform(1, 3))
        
        # Use 5m interval instead of 1m to reduce requests
        hist = ticker.history(period='1d', interval='5m')
        
        if hist.empty:
            # Try with different interval if empty
            hist = ticker.history(period='1d', interval='30m')
            
        return hist
        
    except Exception as e:
        error_str = str(e)
        if "Too Many Requests" in error_str and retries < MAX_RETRIES:
            wait_time = RETRY_DELAY * (retries + 1)
            print(f"  ⏳ Rate limited on {symbol}. Waiting {wait_time}s before retry {retries + 1}/{MAX_RETRIES}...")
            time.sleep(wait_time)
            return get_price_with_retry(symbol, retries + 1)
        else:
            raise e

def check_prices():
    """Check current prices for all symbols with delays between requests"""
    print(f"\n📊 Checking prices at {datetime.now().strftime('%H:%M:%S')}")
    print(f"⏱️  Using {DELAY_BETWEEN_TICKERS}s delay between tickers")
    
    for i, (symbol, levels) in enumerate(WATCHLIST.items()):
        try:
            # Add delay between tickers (skip delay for first ticker)
            if i > 0:
                print(f"  ⏳ Waiting {DELAY_BETWEEN_TICKERS} seconds before next ticker...")
                time.sleep(DELAY_BETWEEN_TICKERS)
            
            print(f"  🔍 Fetching {symbol}...")
            hist = get_price_with_retry(symbol)
            
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                open_price = hist['Close'].iloc[0] if len(hist) > 1 else price
                change = ((price - open_price) / open_price) * 100
                
                print(f"  ✅ {symbol}: ${price:.2f} ({change:+.2f}%)")
                
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
            # Continue with next ticker even if this one failed

def main():
    """Main loop"""
    print("\n" + "="*50)
    print(f"🚀 DIP & TIDE BOT STARTED at {datetime.now()}")
    print("="*50)
    print(f"📈 Watching {len(WATCHLIST)} symbols")
    print(f"⏱️  Cycle time: ~{len(WATCHLIST) * DELAY_BETWEEN_TICKERS + 10}s + {DELAY_BETWEEN_CYCLES}s pause")
    
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            print(f"\n{'='*50}")
            print(f"🔄 CYCLE #{cycle_count} starting at {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*50}")
            
            check_prices()
            
            # Long pause between complete cycles
            print(f"\n⏸️  Cycle #{cycle_count} complete. Waiting {DELAY_BETWEEN_CYCLES} seconds before next cycle...")
            print(f"🕒 Next check at: {(datetime.fromtimestamp(time.time() + DELAY_BETWEEN_CYCLES)).strftime('%H:%M:%S')}")
            time.sleep(DELAY_BETWEEN_CYCLES)
            
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            break
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            print(f"⏳ Waiting {DELAY_BETWEEN_CYCLES} seconds before retry...")
            time.sleep(DELAY_BETWEEN_CYCLES)

# ============================================
# START THE BOT
# ============================================

if __name__ == "__main__":
    main()
