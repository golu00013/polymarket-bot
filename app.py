import time, json, requests, threading
from datetime import datetime
from flask import Flask, render_template_string

TELEGRAM_TOKEN   = "8399826357:AAFw3sGXnFAwfkAoFsJ1pJVdiabJNC93wy4"
TELEGRAM_CHAT_ID = "6211724721"
GAMMA            = "https://gamma-api.polymarket.com"

app = Flask(__name__)
market_data = {}

def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
        timeout=10
    )

def get_markets():
    try:
        r = requests.get(f"{GAMMA}/markets",
            params={"limit": 20, "active": "true", "closed": "false",
                    "order": "volume24hr", "ascending": "false"}, timeout=10)
        data = r.json()
        return data if isinstance(data, list) else data.get("markets", [])
    except:
        return []

def monitor():
    history = {}
    alerted = set()
    while True:
        markets = get_markets()
        for m in markets:
            mid  = m.get("id") or m.get("conditionId", "")
            name = m.get("question", "?")[:55]
            vol  = float(m.get("volume", 0))
            if vol < 50000: continue
            try:
                prices = m.get("outcomePrices", "[0.5,0.5]")
                if isinstance(prices, str): prices = json.loads(prices)
                yes = round(float(prices[0]) * 100, 1)
            except: continue
            d = "UP" if yes > 52 else ("DOWN" if yes < 48 else "NEUTRAL")
            market_data[mid] = {
                "name": name, "yes": yes,
                "direction": d, "vol": vol,
                "time": datetime.now().strftime("%H:%M:%S")
            }
            if d == "NEUTRAL": continue
            if mid not in history: history[mid] = []
            history[mid].append(d)
            if len(history[mid]) > 3: history[mid].pop(0)
            h = history[mid]
            if len(h) == 3 and len(set(h)) == 1:
                key = f"{mid}_{d}"
                if key not in alerted:
                    alerted.add(key)
                    e = "🟢" if d == "UP" else "🔴"
                    send(f"{e}{e}{e} <b>3x {d} SIGNAL!</b>\n\n📊 {name}\n💰 YES: {yes}¢\n⏰ {datetime.now().strftime('%H:%M:%S')}")
            else:
                alerted.discard(f"{mid}_UP")
                alerted.discard(f"{mid}_DOWN")
        time.sleep(5 * 60)

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Polymarket Live</title>
<meta http-equiv="refresh" content="300">
<style>
body{background:#0d0d0d;color:#fff;font-family:Arial;padding:20px}
h1{color:#00d4aa}
table{width:100%;border-collapse:collapse}
th{background:#1a1a2e;padding:10px;text-align:left}
td{padding:10px;border-bottom:1px solid #222}
.up{color:#00ff88}
.down{color:#ff4444}
.dot{width:12px;height:12px;border-radius:50%;display:inline-block;margin-right:8px}
.dot-up{background:#00ff88}
.dot-down{background:#ff4444}
.dot-neutral{background:#888}
</style>
</head>
<body>
<h1>🤖 Polymarket Live Dashboard</h1>
<p style="color:#888">Auto refresh: har 5 min | {{ time }}</p>
<table>
<tr><th>Market</th><th>Direction</th><th>YES Price</th><th>Volume</th><th>Time</th></tr>
{% for mid, m in markets %}
<tr>
<td>{{ m.name }}</td>
<td>
  <span class="dot dot-{{ m.direction.lower() }}"></span>
  <span class="{{ 'up' if m.direction == 'UP' else 'down' if m.direction == 'DOWN' else '' }}">
    {{ m.direction }}
  </span>
</td>
<td>{{ m.yes }}¢</td>
<td>${{ "{:,.0f}".format(m.vol) }}</td>
<td>{{ m.time }}</td>
</tr>
{% endfor %}
</table>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML,
        markets=list(market_data.items()),
        time=datetime.now().strftime("%H:%M:%S")
    )

if __name__ == "__main__":
    t = threading.Thread(target=monitor, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=8080)  
