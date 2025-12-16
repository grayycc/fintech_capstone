from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pickle
import pandas as pd
from typing import List, Optional

app = FastAPI(title="FinPro Robo-Advisor API")

# --- 1. GLOBAL STATE (Load Model & Data on Startup) ---
# Ensure these files are in the same folder as main.py
try:
    with open('model_svd.pkl', 'rb') as f:
        MODEL_SVD = pickle.load(f)
    print("✅ SVD Model Loaded")
except FileNotFoundError:
    print("❌ ERROR: model_svd.pkl not found. API will fail for existing users.")
    MODEL_SVD = None

# Load Asset Metadata (needed for filtering/Cold Start)
try:
    df_assets = pd.read_csv('asset_information.csv')
    ALL_ASSET_IDS = df_assets['ISIN'].unique()
    print("✅ Asset Data Loaded")
except Exception as e:
    print(f"❌ Error loading assets: {e}")
    df_assets = pd.DataFrame()
    ALL_ASSET_IDS = []

# --- 2. DATA MODELS ---
class RecommendationRequest(BaseModel):
    user_id: str
    risk_profile: Optional[str] = "Balanced" 
    top_k: int = 5

class RecommendationResponse(BaseModel):
    user_id: str
    source: str 
    recommendations: List[str]

# --- 3. HELPER FUNCTIONS ---
def get_cold_start_recs(risk_profile: str, top_k: int) -> List[str]:
    """Fallback logic for new users"""
    if 'Conservative' in risk_profile:
        target_cats = ['Bond']
    elif 'Aggressive' in risk_profile:
        target_cats = ['Stock']
    else:
        target_cats = ['Stock', 'MTF'] 
    
    candidates = df_assets[df_assets['assetCategory'].isin(target_cats)]
    return candidates.head(top_k)['ISIN'].tolist()

def get_warm_start_recs(user_id: str, top_k: int) -> List[str]:
    """SVD Logic for existing users"""
    predictions = []
    for asset_id in ALL_ASSET_IDS:
        pred = MODEL_SVD.predict(user_id, asset_id)
        predictions.append((asset_id, pred.est))
    
    predictions.sort(key=lambda x: x[1], reverse=True)
    return [x[0] for x in predictions[:top_k]]

# --- 4. API ENDPOINT ---
@app.post("/recommend", response_model=RecommendationResponse)
def recommend(request: RecommendationRequest):
    use_ai = False
    if MODEL_SVD:
        try:
            MODEL_SVD.trainset.to_inner_uid(request.user_id)
            use_ai = True
        except ValueError:
            use_ai = False 

    if use_ai:
        recs = get_warm_start_recs(request.user_id, request.top_k)
        source = "AI Model (SVD)"
    else:
        recs = get_cold_start_recs(request.risk_profile, request.top_k)
        source = f"Rule-Based ({request.risk_profile})"

    return {
        "user_id": request.user_id,
        "source": source,
        "recommendations": recs
    }

@app.get("/")
def health_check():
    return {"status": "ok", "message": "FinPro Robo-Advisor is Live"}
