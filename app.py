import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Recommender UI", layout="wide")
st.title("📈 Asset Recommender")

# ---- EDIT THIS if your FastAPI endpoint is different (check /docs) ----
API_URL = "http://127.0.0.1:8000/recommend"   # e.g. /recommend or /recommendations

@st.cache_data
def load_assets():
    df = pd.read_csv("asset_information.csv")
    df.columns = [c.strip() for c in df.columns]
    return df

assets = load_assets()

# Try to detect which column in CSV stores Asset IDs
possible_cols = ["asset_id", "Asset ID", "assetId", "ISIN", "isin", "id", "ID"]
asset_id_col = next((c for c in possible_cols if c in assets.columns), assets.columns[0])

st.subheader("Input")
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    user_id = st.text_input("User ID", placeholder="e.g. 12345")
with c2:
    risk_profile = st.selectbox("Risk Profile (for new users)", ["Conservative", "Balanced", "Aggressive"])
with c3:
    k = st.number_input("Top-K", min_value=1, max_value=50, value=10, step=1)

if st.button("Get Recommendations 🚀", type="primary"):
    if not user_id.strip():
        st.error("Please enter a User ID.")
        st.stop()

    payload = {"user_id": user_id.strip(), "risk_profile": risk_profile, "k": int(k)}

    try:
        with st.spinner("Calling backend..."):
            # Most common: POST JSON body. If your backend uses GET, tell me and I’ll switch it.
            r = requests.post(API_URL, json=payload, timeout=15)
            r.raise_for_status()
            rec_ids = r.json()  # expected: list of asset IDs
    except Exception as e:
        st.error(f"API call failed: {e}")
        st.stop()

    if not isinstance(rec_ids, list) or len(rec_ids) == 0:
        st.warning("No recommendations returned (or response format not list).")
        st.write("Raw response:")
        st.json(rec_ids)
        st.stop()

    st.success(f"Got {len(rec_ids)} recommendations.")
    st.caption("Returned Asset IDs:")
    st.code(rec_ids)

    # Filter assets by returned IDs + preserve order
    assets[asset_id_col] = assets[asset_id_col].astype(str)
    rec_ids = [str(x) for x in rec_ids]

    rec_df = assets[assets[asset_id_col].isin(rec_ids)].copy()
    order_map = {aid: i for i, aid in enumerate(rec_ids)}
    rec_df["__order"] = rec_df[asset_id_col].map(order_map)
    rec_df = rec_df.sort_values("__order").drop(columns="__order")

    if rec_df.empty:
        st.warning(
            f"API returned IDs, but none matched your CSV column `{asset_id_col}`.\n"
            f"Check your CSV ID column / values."
        )
        st.write("CSV columns:", list(assets.columns))
        st.stop()

    tab1, tab2 = st.tabs(["✨ Card View", "📋 Table View"])

    with tab1:
        for _, row in rec_df.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row.get('name', row.get('ticker', row[asset_id_col]))}**")
                st.caption(f"Asset ID: `{row[asset_id_col]}`")
                # show a few common fields if present
                for col in ["type", "Type", "asset_type", "currency", "Currency", "risk", "Risk", "sector", "Sector"]:
                    if col in rec_df.columns and pd.notna(row.get(col)):
                        st.write(f"{col}: {row[col]}")

    with tab2:
        st.dataframe(rec_df, use_container_width=True)

    st.download_button(
        "Download CSV",
        rec_df.to_csv(index=False).encode("utf-8"),
        file_name="recommended_assets.csv",
        mime="text/csv",
    )
