import requests
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from collections import defaultdict

# === CONFIG ===
RPC_URL = "https://mainnet.helius-rpc.com/?api-key=YOUR_HELIUS_API_KEY"
DEPOSIT_AUTHORITY = "Ewb5s8pgcWgcuWeat6qzS2r3BKLHiQn61iohnYtVUzyW"
DZ_MINT = "Gekfj7SL2fVpTDxJZmeC46cTYxinjB6gkAnb6EGT6mnn"
TX_LIMIT = 200

# dzSOL buckets
BUCKETS = {
    "<1": (0,1),
    "1-5": (1,5),
    "5-20": (5,20),
    "20-100": (20,100),
    ">100": (100,float('inf'))
}

# === Fetch recent transactions to deposit authority ===
def fetch_stake_txs(limit=TX_LIMIT):
    payload = {
        "jsonrpc": "2.0",
        "id": "dzsol",
        "method": "getSignaturesForAddress",
        "params": [DEPOSIT_AUTHORITY, {"limit": limit}]
    }
    res = requests.post(RPC_URL, json=payload).json()
    return res.get("result", [])

# === Fetch transaction details ===
def fetch_tx_details(sig):
    payload = {
        "jsonrpc": "2.0",
        "id": "dzsol",
        "method": "getTransaction",
        "params": [sig, {"encoding": "jsonParsed"}]
    }
    res = requests.post(RPC_URL, json=payload).json()
    return res.get("result")

# === Extract dzSOL staked from transaction ===
def extract_dzsol(tx):
    try:
        timestamp = tx["blockTime"]
        post_balances = tx["meta"]["postTokenBalances"]
        for bal in post_balances:
            if bal["mint"] == DZ_MINT:
                dzsol_amt = int(bal["uiTokenAmount"]["amount"]) / (10 ** int(bal["uiTokenAmount"]["decimals"]))
                owner = bal["owner"]
                return owner, dzsol_amt, timestamp
    except Exception:
        return None
    return None

# === MAIN ===
def main():
    print("Fetching recent dzSOL staking transactions...")
    txs = fetch_stake_txs(TX_LIMIT)

    wallets_seen = set()
    daily_stakers = defaultdict(list)
    dzsol_amounts = []
    bucket_counts = {k:0 for k in BUCKETS}

    for tx in txs:
        sig = tx["signature"]
        details = fetch_tx_details(sig)
        result = extract_dzsol(details)
        if result:
            owner, dzsol, ts = result
            date = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            if owner not in wallets_seen:
                wallets_seen.add(owner)
                dzsol_amounts.append(dzsol)
                daily_stakers[date].append(dzsol)
                for bucket,(low,high) in BUCKETS.items():
                    if low <= dzsol < high:
                        bucket_counts[bucket] += 1
                        break

    if not dzsol_amounts:
        print("⚠️ No dzSOL staking transactions found. Check deposit authority or mint.")
        return

    # Median & Mean
    median_val = np.median(dzsol_amounts)
    mean_val = np.mean(dzsol_amounts)

    print(f"\nOverall Median dzSOL: {median_val:.2f}")
    print(f"Overall Mean dzSOL: {mean_val:.2f}")
    print(f"Total unique wallets: {len(wallets_seen)}")

    print("\nWallet distribution by bucket:")
    for b,c in bucket_counts.items():
        print(f"{b}: {c} wallets")

    print("\nNew stakers per day:")
    for d in sorted(daily_stakers):
        vals = daily_stakers[d]
        print(f"{d}: {len(vals)} wallets, median dzSOL = {np.median(vals):.2f}")

    # === Charts ===
    plt.hist(dzsol_amounts, bins=[0,1,5,20,100,max(dzsol_amounts)], edgecolor="black")
    plt.title("Distribution of dzSOL staked by new wallets")
    plt.xlabel("dzSOL staked")
    plt.ylabel("Number of wallets")
    plt.show()

    plt.boxplot(dzsol_amounts, vert=False)
    plt.title("Boxplot of dzSOL staked")
    plt.xlabel("dzSOL staked")
    plt.show()

    dates = sorted(daily_stakers)
    counts = [len(daily_stakers[d]) for d in dates]
    plt.plot(dates, counts, marker='o')
    plt.title("New dzSOL stakers per day")
    plt.xlabel("Date")
    plt.ylabel("Wallets")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    main()
