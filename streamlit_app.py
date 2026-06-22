import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
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

SYMBOL_MAP = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "DOGE": "DOGE-USD",
    "SOL": "SOL-USD",
    "ADA": "ADA-USD",
}

def normalize_symbol(symbol):
    symbol = symbol.strip().upper()
    return SYMBOL_MAP.get(symbol, symbol)

def display_symbol(symbol):
    reverse_map = {v: k for k, v in SYMBOL_MAP.items()}
    return reverse_map.get(symbol, symbol)

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

@st.cache_data(ttl=300)
def get_market_history(symbol):
    real_symbol = normalize_symbol(symbol)

    try:
        data = yf.Ticker(real_symbol).history(period="6mo", interval="1d", auto_adjust=True)

        if data is None or data.empty:
            return None

        data = data.dropna()

        if len(data) < 30:
            return None

        return data

    except Exception:
        return None

def calculate_rsi(close, period=14):
    delta = close.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    latest_rsi = rsi.iloc[-1]

    if pd.isna(latest_rsi) or np.isinf(latest_rsi):
        return 50.0

    return round(float(latest_rsi), 1)

def pct_change(close, days):
    if len(close) <= days:
        return 0.0

    old = close.iloc[-days - 1]
    new = close.iloc[-1]

    if old == 0:
        return 0.0

    return round(((new - old) / old) * 100, 2)

def volume_ratio(volume):
    if volume is None or len(volume) < 21:
        return 1.0

    recent_volume = volume.iloc[-1]
    avg_volume = volume.iloc[-21:-1].mean()

    if avg_volume == 0 or pd.isna(avg_volume):
        return 1.0

    return round(float(recent_volume / avg_volume), 2)

def score_symbol(symbol):
    data = get_market_history(symbol)

    if data is None:
        return {
            "symbol": symbol.upper(),
            "real_symbol": normalize_symbol(symbol),
            "price": None,
            "change_1d": None,
            "change_5d": None,
            "change_20d": None,
            "rsi": None,
            "volume_score": None,
            "score": 0,
            "label": "⚪ No data",
            "action": "No data available",
            "reason": "Market data could not be loaded for this symbol."
        }

    close = data["Close"]
    volume = data["Volume"] if "Volume" in data.columns else None

    price = round(float(close.iloc[-1]), 2)
    change_1d = pct_change(close, 1)
    change_5d = pct_change(close, 5)
    change_20d = pct_change(close, 20)
    change_60d = pct_change(close, 60)
    rsi = calculate_rsi(close)
    vol_ratio = volume_ratio(volume)

    ma20 = close.rolling(20).mean().iloc[-1]
    ma50 = close.rolling(50).mean().iloc[-1]

    above_ma20 = price > ma20 if not pd.isna(ma20) else False
    above_ma50 = price > ma50 if not pd.isna(ma50) else False

    score = 50

    score += change_5d * 1.2
    score += change_20d * 0.8
    score += change_60d * 0.25

    if above_ma20:
        score += 8
    else:
        score -= 6

    if above_ma50:
        score += 8
    else:
        score -= 6

    if 45 <= rsi <= 68:
        score += 10
    elif 68 < rsi <= 75:
        score += 2
    elif rsi > 75:
        score -= 12
    elif rsi < 30:
        score -= 8

    if vol_ratio >= 1.5 and change_1d > 0:
        score += 8
    elif vol_ratio >= 1.5 and change_1d < 0:
        score -= 8

    score = int(max(0, min(100, round(score))))

    if score >= 78:
        label = "🔥 Hot watch"
        action = "Strong paper-watch only"
    elif score >= 65:
        label = "🟢 Bullish watch"
        action = "Paper buy allowed"
    elif score >= 45:
        label = "🟡 Neutral"
        action = "Wait"
    else:
        label = "🔴 Avoid for now"
        action = "No buy"

    reasons = []

    if change_20d > 5:
        reasons.append("positive 20-day momentum")
    elif change_20d < -5:
        reasons.append("weak 20-day momentum")

    if above_ma20:
        reasons.append("above 20-day moving average")
    else:
        reasons.append("below 20-day moving average")

    if above_ma50:
        reasons.append("above 50-day moving average")
    else:
        reasons.append("below 50-day moving average")

    if rsi > 75:
        reasons.append("RSI looks overheated")
    elif rsi < 30:
        reasons.append("RSI looks oversold")
    else:
        reasons.append("RSI is in a healthier range")

    if vol_ratio >= 1.5:
        reasons.append("unusual volume")

    reason_text = ", ".join(reasons)

    return {
        "symbol": symbol.upper(),
        "real_symbol": normalize_symbol(symbol),
        "price": price,
        "change_1d": change_1d,
        "change_5d": change_5d,
        "change_20d": change_20d,
        "change_60d": change_60d,
        "rsi": rsi,
        "volume_score": vol_ratio,
        "score": score,
        "label": label,
        "action": action,
        "reason": reason_text
    }

def scan_market(watchlist):
    rows = []
    for symbol in watchlist:
        if symbol.strip():
            rows.append(score_symbol(symbol.strip().upper()))

    return sorted(rows, key=lambda x: x["score"], reverse=True)

def paper_buy(symbol, price, amount):
    if price is None:
        return False, "No real market price available."

    if st.session_state.paper_cash < amount:
        return False, "Not enough paper cash."

    qty = amount / price
    st.session_state.paper_cash -= amount

    if symbol not in st.session_state.positions:
        st.session_state.positions[symbol] = {
            "qty": 0.0,
            "spent": 0.0
        }

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

    return True, f"Paper bought ${amount:.2f} of {symbol} at ${price:.2f}."

def get_chart_data(symbol):
    data = get_market_history(symbol)

    if data is None:
        return None

    chart = data[["Close"]].copy()
    chart = chart.rename(columns={"Close": display_symbol(normalize_symbol(symbol))})
    return chart

st.title("📈 Belton AI Market Radar")
st.caption("Real market data scanner with paper trading only. This is not financial advice.")

with st.expander("⚠️ Important safety note", expanded=True):
    st.write(
        "This version uses real market data from Yahoo Finance through yfinance. "
        "It is still for education, trend scanning, and paper trading only. "
        "It does not place real-money trades. Real investing can lose money, even with $10 or $20."
    )

tabs = st.tabs(["🏠 Home", "📡 Radar", "🤖 Auto", "💵 Paper", "📊 Chart", "⚙️ Setup"])

with tabs[0]:
    st.subheader("Your real-data market dashboard")

    st.write(
        "This app now pulls real recent market history and calculates trend scores using momentum, "
        "moving averages, RSI, and volume."
    )

    col1, col2 = st.columns(2)
    col1.metric("Paper Cash", f"${st.session_state.paper_cash:.2f}")
    col2.metric("Open Positions", len(st.session_state.positions))

    st.metric("Trades Logged", len(st.session_state.trade_log))

    st.info("Start with the Radar tab. The app refreshes market data every 5 minutes.")

with tabs[1]:
    st.subheader("📡 Real Trend Radar")

    watchlist_text = st.text_area(
        "Watchlist",
        value=", ".join(DEFAULT_WATCHLIST),
        help="Separate symbols with commas. Crypto can be BTC or BTC-USD."
    )

    watchlist = [s.strip().upper() for s in watchlist_text.split(",") if s.strip()]

    if st.button("Refresh Radar"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Loading real market data..."):
        scan = scan_market(watchlist)

    for item in scan:
        with st.container(border=True):
            st.markdown(f"### {item['symbol']} — {item['label']}")

            if item["price"] is None:
                st.warning(item["reason"])
                continue

            col1, col2, col3 = st.columns(3)
            col1.metric("Score", item["score"])
            col2.metric("Price", f"${item['price']}")
            col3.metric("1D", f"{item['change_1d']}%")

            st.write(f"**Action:** {item['action']}")
            st.write(
                f"5D: {item['change_5d']}% | "
                f"20D: {item['change_20d']}% | "
                f"60D: {item['change_60d']}% | "
                f"RSI: {item['rsi']} | "
                f"Volume: {item['volume_score']}x"
            )
            st.caption(f"Why: {item['reason']}")

with tabs[2]:
    st.subheader("🤖 Paper Autopilot")

    st.write(
        "This chooses the highest-scoring symbol from your watchlist and only paper buys "
        "if the score passes your minimum."
    )

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

    if st.button("Refresh Auto Data"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Scanning real market data..."):
        auto_scan = scan_market(auto_watchlist)

    valid_scan = [x for x in auto_scan if x["price"] is not None]

    if not valid_scan:
        st.error("No valid market data loaded. Try checking your symbols.")
    else:
        best = valid_scan[0]

        st.write("Best current setup:")
        st.success(
            f"{best['symbol']} | Score: {best['score']} | "
            f"{best['label']} | Price: ${best['price']}"
        )

        st.caption(f"Why: {best['reason']}")

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
            current = score_symbol(symbol)

            if current["price"] is None:
                st.warning(f"No current price available for {symbol}.")
                continue

            value = pos["qty"] * current["price"]
            pnl = value - pos["spent"]

            with st.container(border=True):
                st.markdown(f"### {symbol}")
                st.write(f"Quantity: {pos['qty']:.6f}")
                st.write(f"Spent: ${pos['spent']:.2f}")
                st.write(f"Current price: ${current['price']:.2f}")
                st.write(f"Estimated value: ${value:.2f}")
                st.write(f"Estimated paper P/L: ${pnl:.2f}")

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
    st.subheader("📊 Real Trend Chart")

    symbol = st.text_input("Symbol to chart", value="SPY").upper()

    if st.button("Refresh Chart"):
        st.cache_data.clear()
        st.rerun()

    chart_data = get_chart_data(symbol)

    if chart_data is None:
        st.error("No chart data available. Try another symbol.")
    else:
        st.line_chart(chart_data)
        current = score_symbol(symbol)

        st.write(f"Current price: **${current['price']}**")
        st.write(f"Current score: **{current['score']}**")
        st.write(f"Status: **{current['label']}**")
        st.caption(f"Why: {current['reason']}")

with tabs[5]:
    st.subheader("⚙️ Setup")

    st.write("Your live app link is:")
    st.code("https://belton-ai-radar.streamlit.app")

    st.write("To add this to your iPhone Home Screen:")
    st.write("1. Open the link in Safari.")
    st.write("2. Tap the Share button.")
    st.write("3. Tap Add to Home Screen.")
    st.write("4. Name it Belton AI Radar.")

    st.write("Real data source:")
    st.code("Yahoo Finance through yfinance")

    st.warning(
        "This is still paper-only. It does not trade real money. "
        "Do not treat the score as a guaranteed buy signal."
    )
