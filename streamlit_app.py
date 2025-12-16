

import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="FinPro Recommender", layout="wide")
st.title("💼 FinPro Asset Recommender System")

# -----------------------------
# CONFIG
# -----------------------------
API_BASE = "http://127.0.0.1:8000"
RECOMMEND_ENDPOINT = "/recommend"
API_URL = API_BASE.rstrip("/") + RECOMMEND_ENDPOINT

ASSET_CSV_PATH = "asset_information.csv"

# Put some sample IDs here that are known to exist in the SVD trainset.
# If you don't know them yet, leave as placeholders and test once you get 1-3 real IDs.
SAMPLE_AI_USERS = ["U1001", "U2049", "U3302"]  # <-- replace with real existing user_ids


# -----------------------------
# DATA LOAD
# -----------------------------
@st.cache_data
def load_assets(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    return df


try:
    assets_df = load_assets(ASSET_CSV_PATH)
except Exception as e:
    st.error(f"Failed to load {ASSET_CSV_PATH}: {e}")
    st.stop()

if "ISIN" not in assets_df.columns:
    st.warning("asset_information.csv has no 'ISIN' column. Table matching may fail.")


# -----------------------------
# UI: Account / identity
# -----------------------------
st.subheader("1) Account")

colA, colB = st.columns([2, 1])

with colB:
    use_sample_ai = st.toggle("Use sample AI user", value=False)

with colA:
    if use_sample_ai:
        selected_sample = st.selectbox("Sample existing user (AI mode)", SAMPLE_AI_USERS)
        entered_identity = selected_sample
        st.caption("This should trigger **AI Model (SVD)** if the ID exists in the training data.")
    else:
        entered_identity = st.text_input(
            "Email / Username",
            placeholder="e.g. grace@demo.com or grace_wang",
        )
        st.caption("New users will trigger **Rule-Based** recommendations (cold start).")

# Demo “account creation”
create_btn = st.button("Create account / Continue ✅", type="primary")

if create_btn:
    if not entered_identity.strip():
        st.error("Please enter an Email/Username OR choose a sample AI user.")
        st.stop()

    # In demo: we use email/username directly as user_id (stable + simple)
    st.session_state["user_id"] = entered_identity.strip().lower()
    st.success(f"Logged in as: **{st.session_state['user_id']}**")

st.divider()

# -----------------------------
# UI: Preferences
# -----------------------------
st.subheader("2) Preferences")
c1, c2 = st.columns([1, 1])

with c1:
    risk_profile = st.selectbox(
        "Risk Profile (used for cold start)",
        ["Conservative", "Balanced", "Aggressive"],
        index=1,
    )

with c2:
    top_k = st.number_input("Top-K recommendations", min_value=1, max_value=50, value=5, step=1)

st.divider()

# -----------------------------
# Call API
# -----------------------------
st.subheader("3) Recommendations")

if "user_id" not in st.session_state:
    st.info("Click **Create account / Continue ✅** above to proceed.")
    st.stop()

if st.button("Get Recommendations 🚀"):
    payload = {
        "user_id": st.session_state["user_id"],
        "risk_profile": risk_profile,
        "top_k": int(top_k),
    }

    try:
        with st.spinner("Calling FastAPI backend..."):
            resp = requests.post(API_URL, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
    except requests.HTTPError:
        st.error(f"API error {resp.status_code}: {resp.text}")
        st.stop()
    except Exception as e:
        st.error(f"Failed to call API: {e}")
        st.stop()

    # Expecting: { user_id, source, recommendations: [ISIN...] }
    rec_ids = data.get("recommendations", [])
    source = data.get("source", "Unknown")

    if not isinstance(rec_ids, list) or len(rec_ids) == 0:
        st.warning("No recommendations returned (or unexpected response format).")
        st.json(data)
        st.stop()

    st.success(f"✅ Got {len(rec_ids)} recommendations")
    st.write(f"**Source:** {source}")
    st.code(rec_ids)

    # -----------------------------
    # Join with assets metadata
    # -----------------------------
    if "ISIN" in assets_df.columns:
        tmp = assets_df.copy()
        tmp["ISIN"] = tmp["ISIN"].astype(str)
        rec_ids = [str(x) for x in rec_ids]

        rec_df = tmp[tmp["ISIN"].isin(rec_ids)].copy()

        # preserve API order
        order_map = {isin: i for i, isin in enumerate(rec_ids)}
        rec_df["__order"] = rec_df["ISIN"].map(order_map)
        rec_df = rec_df.sort_values("__order").drop(columns="__order")

        if rec_df.empty:
            st.warning("Returned ISINs did not match any rows in asset_information.csv.")
            st.write("Tip: Check that the CSV column is named 'ISIN' and values match.")
            st.json(data)
            st.stop()
    else:
        rec_df = pd.DataFrame({"ISIN": rec_ids})

    # -----------------------------
    # Display: Cards + Table
    # -----------------------------
    tab1, tab2 = st.tabs(["✨ Card View", "📋 Table View"])

    with tab1:
        # Pick a nice title column if available
        title_cols = ["assetName", "name", "ticker", "Ticker"]
        for _, row in rec_df.iterrows():
            with st.container(border=True):
                title = None
                for tc in title_cols:
                    if tc in rec_df.columns and pd.notna(row.get(tc)):
                        title = row.get(tc)
                        break

                st.markdown(f"### {title if title else row.get('ISIN', '-')}")
                st.caption(f"ISIN: `{row.get('ISIN', '-')}`")

                # show common fields if present
                fields = ["assetCategory", "currency", "risk", "sector"]
                cols = st.columns(4)
                for i, f in enumerate(fields):
                    if f in rec_df.columns and pd.notna(row.get(f)):
                        cols[i].metric(f, str(row.get(f)))
                    else:
                        cols[i].metric(f, "-")

    with tab2:
        st.dataframe(rec_df, use_container_width=True)

    st.download_button(
        "Download Recommendations CSV",
        rec_df.to_csv(index=False).encode("utf-8"),
        file_name="recommended_assets.csv",
        mime="text/csv",
    )
