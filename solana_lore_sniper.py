import asyncio
import json
import os
import time
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import RpcLogsFilter
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from dotenv import load_dotenv
import requests
import tweepy
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
nltk.download('vader_lexicon', quiet=True)

load_dotenv()

# ========================= CONFIG =========================
RPC_URL = os.getenv("SOLANA_RPC")
WSS_URL = os.getenv("SOLANA_WSS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
BUY_AMOUNT_SOL = 0.5
MIN_SCORE = 75
PUMP_PROGRAM = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
JITO_TIP = 0.001

client = AsyncClient(RPC_URL)
kp = Keypair.from_base58_string(PRIVATE_KEY)

# X API
x_client = tweepy.Client(
    bearer_token=os.getenv("X_BEARER"),
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

sia = SentimentIntensityAnalyzer()

# ====================== HELPER FUNCTIONS ======================
async def get_token_metadata(mint: str):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
    try:
        resp = requests.get(url).json()
        pair = resp.get('pairs', [{}])[0] if resp.get('pairs') else {}
        return {
            "name": pair.get('baseToken', {}).get('name', 'Unknown'),
            "twitter": pair.get('info', {}).get('socials', [{}])[0].get('url') if pair.get('info', {}).get('socials') else None,
            "liquidity_sol": pair.get('liquidity', {}).get('usd', 0) / 150,  # rough
            "dev_holdings_pct": 5.0  # placeholder
        }
    except:
        return {"name": mint[:8], "liquidity_sol": 0, "dev_holdings_pct": 15}

def check_rug_params(metadata):
    if metadata["liquidity_sol"] < 10: return False
    if metadata["dev_holdings_pct"] > 10: return False
    return True

async def detect_bundlers_clusters(mint: str):
    print(f"[{mint}] Checking for bundler clusters...")
    return True  # placeholder

def analyze_lore_twitter(ticker_or_ca: str):
    query = f"{ticker_or_ca} OR ${ticker_or_ca} lang:en since:{int(time.time())-3600}"
    try:
        tweets = x_client.search_recent_tweets(query=query, max_results=30)
        if not tweets.data:
            return 0, 0
        texts = [t.text for t in tweets.data]
        sentiments = [sia.polarity_scores(text)['compound'] for text in texts]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        return len(texts), avg_sentiment
    except:
        return 0, 0

def calculate_score(metadata, cluster_ok, mention_vol, sentiment):
    score = 0
    if check_rug_params(metadata): score += 40
    if cluster_ok: score += 25
    if mention_vol > 15: score += 15
    if sentiment > 0.3: score += 20
    return min(score, 100)

async def buy_token(mint: str):
    print(f"🚀 SNIPING {mint} with {BUY_AMOUNT_SOL} SOL")
    # TODO: Implement full buy with Jito
    pass

# ====================== MAIN ======================
async def main():
    print("🔥 Real-time Solana Lore Sniper Bot STARTED")
    async for log_response in client.logs_subscribe(
        RpcLogsFilter(mentions=[str(PUMP_PROGRAM)]),
        commitment=Confirmed
    ):
        try:
            logs = log_response.value.logs
            if any("Create" in line for line in logs):
                mint = "PLACEHOLDER_MINT"  # TODO: proper parsing
                print(f"🆕 New pair: {mint}")
                metadata = await get_token_metadata(mint)
                cluster_ok = await detect_bundlers_clusters(mint)
                mention_vol, sentiment = analyze_lore_twitter(metadata.get("name", mint))
                score = calculate_score(metadata, cluster_ok, mention_vol, sentiment)
                print(f"Score: {score}/100")
                if score >= MIN_SCORE:
                    await buy_token(mint)
        except:
            continue

if __name__ == "__main__":
    asyncio.run(main())