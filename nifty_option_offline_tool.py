import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config("📈 Nifty Option Analyzer", layout="wide")

st.title("📈 Offline Nifty Option Strategy Analyzer")
st.markdown("Upload a CSV or Excel file of Nifty Option Chain data to get trade suggestions based on popular trader strategies.")

# --- Sidebar Inputs ---
st.sidebar.header("📂 Upload Data & Budget")
uploaded_file = st.sidebar.file_uploader("Upload Option Chain File", type=["csv", "xlsx"])
budget = st.sidebar.number_input("💰 Budget (INR)", min_value=1000, value=10000, step=500)

# --- Data Processing Function ---
def fetch_option_chain_offline(uploaded_file, budget):
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()

        rename_map = {
            "strike price": "strikeprice", "strike": "strikeprice",
            "ltp": "ltp", "last traded price": "ltp",
            "oi": "oi", "open interest": "oi",
            "chng in oi": "chngoi", "change in oi": "chngoi",
            "volume": "volume",
            "iv": "iv", "implied volatility": "iv",
            "type": "type"
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        # Fill missing 'type'
        if "type" not in df.columns:
            if "ce" in uploaded_file.name.lower():
                df["type"] = "CE"
            elif "pe" in uploaded_file.name.lower():
                df["type"] = "PE"
            else:
                df["type"] = "CE"  # default fallback

        for col in ["strikeprice", "ltp", "oi", "chngoi", "volume", "iv"]:
            if col not in df.columns:
                st.error(f"❌ Missing required column: `{col}`")
                st.info(f"Available columns: {list(df.columns)}")
                return pd.DataFrame(), 0

        df["cost"] = df["ltp"] * 50
        df = df[df["cost"] <= budget]

        spot_price = df.loc[df["volume"].idxmax(), "strikeprice"] if not df.empty else 0
        return df, spot_price
    except Exception as e:
        st.error(f"⚠️ Error reading data: {e}")
        return pd.DataFrame(), 0

# --- Main Logic ---
if uploaded_file:
    df_chain, spot_price = fetch_option_chain_offline(uploaded_file, budget)
    if df_chain.empty:
        st.warning("📭 No eligible trades found under your budget.")
        st.stop()

    st.success(f"🧮 Estimated Spot Price: {spot_price}")

    # Strategy Rules
    st.subheader("📌 Trade Ideas Based on 5 Top Traders")
    ideas = []
    for _, row in df_chain.iterrows():
        reason, strategy, trader = "", "", ""
        if row["oi"] < df_chain["oi"].quantile(0.3) and row["volume"] > df_chain["volume"].quantile(0.7):
            trader, strategy, reason = "Sivakumar", "Scalping", "Low OI, High Volume"
        elif row["type"] == "CE" and abs(row["strikeprice"] - spot_price) < 200:
            trader, strategy, reason = "P. R. Sundar", "Neutral Selling", "Near Spot Range"
        elif row["type"] == "CE" and row["strikeprice"] > spot_price:
            trader, strategy, reason = "Ghanshyam Tech", "Breakout", "Price Action CE"
        elif row["type"] == "PE" and row["strikeprice"] < spot_price:
            trader, strategy, reason = "Subasish Pani", "Reversal", "Support/Resistance PE"
        elif row["iv"] > df_chain["iv"].quantile(0.7):
            trader, strategy, reason = "Anant Ladha", "Event Volatility", "High IV"
        if trader:
            ideas.append({
                "Trader": trader, "Strategy": strategy, "Reason": reason,
                "Strike": row["strikeprice"], "Type": row["type"],
                "LTP": row["ltp"], "IV": row["iv"], "Cost": row["cost"]
            })

    if ideas:
        st.dataframe(pd.DataFrame(ideas))
    else:
        st.info("No trade ideas matched the strategy filters.")

    # Spread Ideas
    st.subheader("📐 Bull Call & Bear Put Spread Strategies")
    spreads = []

    ce_df = df_chain[df_chain["type"] == "CE"].sort_values("strikeprice")
    for i in range(len(ce_df)-1):
        buy, sell = ce_df.iloc[i], ce_df.iloc[i+1]
        if buy["strikeprice"] < spot_price:
            spreads.append({
                "Strategy": "Bull Call Spread",
                "Buy CE": buy["strikeprice"], "Sell CE": sell["strikeprice"],
                "Net Cost": round((buy["ltp"] - sell["ltp"]) * 50, 2),
                "Max Profit": round((sell["strikeprice"] - buy["strikeprice"]) * 50 - (buy["ltp"] - sell["ltp"]) * 50, 2)
            })

    pe_df = df_chain[df_chain["type"] == "PE"].sort_values("strikeprice", ascending=False)
    for i in range(len(pe_df)-1):
        buy, sell = pe_df.iloc[i], pe_df.iloc[i+1]
        if buy["strikeprice"] > spot_price:
            spreads.append({
                "Strategy": "Bear Put Spread",
                "Buy PE": buy["strikeprice"], "Sell PE": sell["strikeprice"],
                "Net Cost": round((buy["ltp"] - sell["ltp"]) * 50, 2),
                "Max Profit": round((buy["strikeprice"] - sell["strikeprice"]) * 50 - (buy["ltp"] - sell["ltp"]) * 50, 2)
            })

    if spreads:
        st.dataframe(pd.DataFrame(spreads))
    else:
        st.warning("No spread trades found.")

    # Optional Chart
    st.subheader("📊 OI vs IV by Strike")
    for typ in ["CE", "PE"]:
        sub = df_chain[df_chain["type"] == typ]
        if not sub.empty:
            chart = alt.Chart(sub).mark_circle(size=60).encode(
                x="strikeprice", y="oi",
                color=alt.Color("iv", scale=alt.Scale(scheme="blueorange")),
                tooltip=["strikeprice", "oi", "volume", "ltp", "iv"]
            ).properties(title=f"{typ} - OI vs IV")
            st.altair_chart(chart, use_container_width=True)
else:
    st.info("📤 Please upload a CSV or Excel file to begin.")
