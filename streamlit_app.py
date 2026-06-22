import streamlit as st
import random
import math
from datetime import datetime, date

st.set_page_config(
    page_title="Belton AI Market Radar",
    page_icon="📈",
    layout="centered"
)

APP_NAME = "Belton AI Market Radar"

DEFAULT_WATCHLIST = [
    "SPY", "QQQ", "VTI", "AAPL", "MSFT", "NVDA", "TSLA", "BTC", "ETH"
]

def init_state():
    if "paper_cash" not in st.session_state:
        st.session_state.paper_cash = 100.00
    if "positions" not in st.session_state:
        st.session_state.positions = {}
    if "trade_log" not in st.session_state:
        st.session_state.trade_log = []
    if "daily_spent" not in st.session_state:
        st.session_state.daily_spent = {}
    if "weekly_spent" not in st.session_state:
        st.session_state.weekly_spent = 0.00

init_state()

def fake_market_data(symbol):
    seed = sum(ord(c) for c in symbol) + int(datetime.now().strftime("%Y%m%d"))
    random.seed(seed)

    base_price = random.uniform(20, 500)
    if symbol in ["BTC"]:
        base_price = random.uniform(60000, 75000)
    if symbol in ["ETH"]:
        base_price = random.uniform(2500, 4500)

    change_1d = random.uniform(-4.5, 5.5)
    change_5d = random.uniform(-8, 10)
    change_20d = random.uniform(-15, 18)
    rsi = random.uniform(25, 78)
    volume_score = random.uniform(0.5, 2.5)

    score = 50
    score += change_1d * 3
    score += change_5d * 1.5
    score += change_20d * 0.7

    if 45 <= rsi <= 68:
        score += 10
    elif rsi > 75:
        score -= 12
    elif rsi < 30:
        score -= 8

    if volume_score > 1.4:
        score += 8

    score = max(0, min(100, round(score)))

    if score >= 75:
        label = "🔥 Hot watch"
        action = "Watch closely"
    elif score >= 62:
        label = "🟢 Bullish watch"
        action = "Paper buy allowed"
    elif score >= 45:
        label = "🟡 Neutral"
        action = "Wait"
    else:
        label = "🔴 Avoid for now"
        action = "No buy"

    return {
        "symbol": symbol,
        "price": round(base_price * (1 + change_1d / 100), 2),
        "change_1d": round(change_1d, 2),
        "change_5d": round(change_5d, 2),
        "change_20d": round(change_20d, 2),
        "rsi": round(rsi, 1),
        "volume_score": round(volume_score, 2),
        "score": score,
        "label": label,
        "action": action,
    }

def scan_market(watchlist):
    rows = [fake_market_data(s.strip().upper()) for s in watchlist if s.strip()]
    return sorted(rows, key=lambda x: x["score"], reverse=True)

def paper_buy(symbol, price, amount):
    if st.session_state.paper_cash < amount:
        return False, "Not enough paper cash."

    qty = amount / price
    st.session_state.paper_cash -= amount

    if symbol not in st.session_state.positions:
        st.session_state.positions[symbol] = {"qty": 0.0, "spent": 0.0}

    st.session_state.positions[symbol]["qty"] += qty
    st.session_state.positions[symbol]["spent"] += amount

    st.session_state.trade_log.insert(0, {
        "time": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
        "symbol": symbol,
        "amount": amount,
        "price": price,
        "qty": qty,
        "type": "PAPER BUY"
    })

    today = str(date.today())
    st.session_state.daily_spent[today] = st.session_state.daily_spent.get(today, 0) + amount
    st.session_state.weekly_spent += amount

    return True, f"Paper bought ${amount:.2f} of {symbol}."

def make_price_path(price):
    values = []
    current = price * random.uniform(0.92, 1.05)
    for _ in range(30):
        current *= 1 + random.uniform(-0.018, 0.022)
        values.append(round(current, 2))
    return values

st.title("📈 Belton AI Market Radar")
st.caption("Phone-friendly paper trading assistant. This is not financial advice.")

with st.expander("⚠️ Safety note", expanded=True):
    st.write(
        "This app is built for education, alerts, and paper trading. "
        "Real trading always has risk, even with $10 or $20. "
        "This version does not place real-money trades."
    )

tabs = st.tabs(["🏠 Home", "📡 Radar", "🤖 Auto", "💵 Paper", "📊 Chart", "⚙️ Setup"])

with tabs[0]:
    st.subheader("Your market dashboard")
    st.write("Use this app to scan trends, test tiny paper trades, and learn before risking real money.")

    st.metric("Paper Cash", f"${st.session_state.paper_cash:.2f}")
    st.metric("Open Paper Positions", len(st.session_state.positions))
    st.metric("Trades Logged", len(st.session_state.trade_log))

    st.info("Start with the Radar tab. Then use Auto for a controlled paper autopilot test.")

with tabs[1]:
    st.subheader("📡 Trend Radar")

    watchlist_text = st.text_area(
        "Watchlist",
        value=", ".join(DEFAULT_WATCHLIST),
        help="Separate symbols with commas."
    )

    watchlist = [s.strip().upper() for s in watchlist_text.split(",") if s.strip()]
    scan = scan_market(watchlist)

    for item in scan:
        with st.container(border=True):
            st.markdown(f"### {item['symbol']} — {item['label']}")
            col1, col2, col3 = st.columns(3)
            col1.metric("Score", item["score"])
            col2.metric("Price", f"${item['price']}")
            col3.metric("1D", f"{item['change_1d']}%")

            st.write(f"**Action:** {item['action']}")
            st.write(
                f"5D: {item['change_5d']}% | 20D: {item['change_20d']}% | "
                f"RSI: {item['rsi']} | Volume: {item['volume_score']}x"
            )

with tabs[2]:
    st.subheader("🤖 Paper Autopilot")

    st.write("This chooses the highest-scoring symbol from your watchlist and only paper buys if the score is strong enough.")

    amount = st.number_input("Paper order size", min_value=1.0, max_value=25.0, value=10.0, step=1.0)
    daily_cap = st.number_input("Daily paper cap", min_value=1.0, max_value=50.0, value=10.0, step=1.0)
    weekly_cap = st.number_input("Weekly paper cap", min_value=1.0, max_value=100.0, value=20.0, step=1.0)
    min_score = st.slider("Minimum score to paper buy", 50, 95, 65)

    watchlist_text_auto = st.text_area(
        "Autopilot watchlist",
        value=", ".join(DEFAULT_WATCHLIST),
        key="auto_watchlist"
    )

    auto_watchlist = [s.strip().upper() for s in watchlist_text_auto.split(",") if s.strip()]
    auto_scan = scan_market(auto_watchlist)
    best = auto_scan[0]

    st.write("Best current setup:")
    st.success(f"{best['symbol']} | Score: {best['score']} | {best['label']} | Price: ${best['price']}")

    today = str(date.today())
    spent_today = st.session_state.daily_spent.get(today, 0.0)

    st.write(f"Spent today: ${spent_today:.2f} / ${daily_cap:.2f}")
    st.write(f"Spent this week: ${st.session_state.weekly_spent:.2f} / ${weekly_cap:.2f}")

    if st.button("Run Paper Autopilot Now"):
        if best["score"] < min_score:
            st.warning(f"No paper buy. {best['symbol']} score is below your minimum.")
        elif spent_today + amount > daily_cap:
            st.warning("No paper buy. Daily cap reached.")
        elif st.session_state.weekly_spent + amount > weekly_cap:
            st.warning("No paper buy. Weekly cap reached.")
        else:
            ok, msg = paper_buy(best["symbol"], best["price"], amount)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

with tabs[3]:
    st.subheader("💵 Paper Portfolio")

    st.metric("Paper Cash", f"${st.session_state.paper_cash:.2f}")

    if not st.session_state.positions:
        st.info("No paper positions yet.")
    else:
        for symbol, pos in st.session_state.positions.items():
            current = fake_market_data(symbol)
            value = pos["qty"] * current["price"]
            pnl = value - pos["spent"]

            with st.container(border=True):
                st.markdown(f"### {symbol}")
                st.write(f"Quantity: {pos['qty']:.6f}")
                st.write(f"Spent: ${pos['spent']:.2f}")
                st.write(f"Estimated value: ${value:.2f}")
                st.write(f"Estimated P/L: ${pnl:.2f}")

    st.subheader("Trade log")
    if not st.session_state.trade_log:
        st.write("No trades yet.")
    else:
        for trade in st.session_state.trade_log[:10]:
            st.write(
                f"{trade['time']} | {trade['type']} | "
                f"{trade['symbol']} | ${trade['amount']:.2f} at ${trade['price']:.2f}"
            )

with tabs[4]:
    st.subheader("📊 Trend Chart")

    symbol = st.text_input("Symbol to chart", value="SPY").upper()
    data = fake_market_data(symbol)
    chart_data = make_price_path(data["price"])

    st.write(f"{symbol} simulated trend path")
    st.line_chart(chart_data)

    st.write(f"Current simulated score: **{data['score']}**")
    st.write(f"Status: **{data['label']}**")

with tabs[5]:
    st.subheader("⚙️ Setup")

    st.write("Your live app link is:")
    st.code("https://belton-ai-radar.streamlit.app")

    st.write("To add this to your iPhone Home Screen:")
    st.write("1. Open the link in Safari.")
    st.write("2. Tap the Share button.")
    st.write("3. Tap Add to Home Screen.")
    st.write("4. Name it Belton AI Radar.")

    st.warning(
        "This one-file version is paper-only. "
        "Do not connect real money until you fully understand brokerage risk, taxes, and losses."
    )
