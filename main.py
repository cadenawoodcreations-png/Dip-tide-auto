import yfinance as yf
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os

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

def check_prices():
    """Check current prices for all symbols"""
    print(f"\n📊 Checking prices at {datetime.now().strftime('%H:%M:%S')}")
    
    for symbol, levels in WATCHLIST.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1d', interval='1m')
            
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                change = ((price - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100 if len(hist) > 1 else 0
                
                print(f"  {symbol}: ${price:.2f} ({change:+.2f}%)")
                
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
                        
        except Exception as e:
            print(f"  ❌ Error checking {symbol}: {e}")

def main():
    """Main loop"""
    print("\n" + "="*50)
    print(f"🚀 DIP & TIDE BOT STARTED at {datetime.now()}")
    print("="*50)
    
    while True:
        try:
            check_prices()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            break
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            time.sleep(60)

# ============================================
# START THE BOT
# ============================================

if __name__ == "__main__":
    main()
