import time

import requests
from datetime import datetime, timezone


def print_banner():
    print("""
 _______   _______   _______  _______ .__   __.        .___  ___.      ___       ______  __    __   __  .__   __.  _______ 
|       \ |   ____| /  _____||   ____||  \ |  |        |   \/   |     /   \     /      ||  |  |  | |  | |  \ |  | |   ____|
|  .--.  ||  |__   |  |  __  |  |__   |   \|  |  ______|  \  /  |    /  ^  \   |  ,----'|  |__|  | |  | |   \|  | |  |__   
|  |  |  ||   __|  |  | |_ | |   __|  |  . `  | |______|  |\/|  |   /  /_\  \  |  |     |   __   | |  | |  . `  | |   __|  
|  '--'  ||  |____ |  |__| | |  |____ |  |\   |        |  |  |  |  /  _____  \ |  `----.|  |  |  | |  | |  |\   | |  |____ 
|_______/ |_______| \______| |_______||__| \__|        |__|  |__| /__/     \__\ \______||__|  |__| |__| |__| \__| |_______|
""")


failed_tokens = {}
last_failed_tokens_eviction_time = time.time()

active_trades = {}

deposit = 2.0


def get_tokens(min_number_holders,
               min_market_cap,
               max_market_cap,
               max_sniper_count,
               max_single_owner_percentage,
               max_top_5_owner_percentage):
    print(
        f"\nGET-TOKENS: Fetching information from pump.fun [{min_market_cap} < MC < {max_market_cap}, Sniper < {max_sniper_count}, 1TH% -> {max_single_owner_percentage}, 5TH% -> {max_top_5_owner_percentage}")

    url = f"https://advanced-api.pump.fun/coins/list?sortBy=creationTime&marketCapFrom={min_market_cap}&marketCapTo={max_market_cap}&numHoldersFrom={min_number_holders}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        filtered_tokens = []

        for token in data:

            token_addr = token["coinMint"]

            # Skip tokens already checked tokens
            if token_addr in failed_tokens:
                print(f"GET-TOKENS: Skipping {token['name']} - Already failed rug_check")
                failed_tokens[token_addr] += 1

                if failed_tokens[token_addr] >= 5:
                    print(f"GET-TOKENS: Removing {token_addr} from failed_tokens after 5 occurrences")
                    del failed_tokens[token_addr]

                continue

            if token["sniperCount"] < max_sniper_count:

                rug_check_result = rug_check(token_addr, max_single_owner_percentage, max_top_5_owner_percentage)
                if not rug_check_result:

                    if rug_check_result is None:
                        # Skip adding to failed_tokens if the request failed
                        print(f"ERROR-GET-TOKENS: {token['name']} with addr {token['coinMint']} skipped due to rugcheck API failure")
                        continue

                    print(f"ERROR-GET-TOKENS: {token['name']} with addr {token['coinMint']} fails on rugcheck!")
                    failed_tokens[token_addr] = 0
                    continue

                filtered_tokens.append(token)

                print(
                    f"Name: {token['name']}, Ticker: {token['ticker']}, "
                    f"Market Cap: {token['marketCap']}, "
                    f"Creation Time: {datetime.fromtimestamp(token['creationTime'] / 1000, timezone.utc)}, "
                    f"Num Holders: {token['numHolders']}, "
                    f"Sniper Count: {token['sniperCount']}, "
                    f"Address: {token['coinMint']}"
                )

        return filtered_tokens
    else:
        print(f"ERROR-GET-TOKENS: Failed to fetch data from pump.fun - status code: {response.status_code}")
        return []


# rugcheck.xyz
def rug_check(token_addr, max_single_owner_percentage, max_top_5_owner_percentage):
    url = f"https://api.rugcheck.xyz/v1/tokens/{token_addr}/report"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        if not check_risks(data["risks"]):
            print(f"ERROR-RUG-CHECK: {token_addr} -> risks array is not empty")
            return False

        if not check_top_holders_ownership(data["topHolders"], max_single_owner_percentage, max_top_5_owner_percentage):
            print(f"ERROR-RUG-CHECK: {token_addr} -> top holders validation fails")
            return False

        return True

    else:
        print(f"ERROR-RUG-CHECK: Failed to fetch data from rugcheck.xyz - status code: {response.status_code}")
        return None


def check_risks(risks):
    acceptable_risk = "Low amount of LP Providers"

    if not risks:
        return True

    for risk in risks:
        if risk["name"] != acceptable_risk:
            return False

    return True


def check_top_holders_ownership(top_holders, max_single_owner_percentage, max_top_5_owner_percentage):
    if (
            top_holders[0]["owner"] == "HahdWwA534mqfzzX27AJN4HcYC2t3kHj8Pp3uXChZTD6" or
            top_holders[0]["address"] == "AH2YeZ5YnXx9AUerg1J1iWKeCkG24SKeF35zefCNTDJy"
    ):
        top_5_holders = top_holders[1:6]  # Skip the Pump Fun Automated Market Maker
        top_holder = top_holders[1]
    else:
        top_5_holders = top_holders[:5]
        top_holder = top_holders[0]

    ownership_percentage = sum(holder.get("pct", 0) for holder in top_5_holders)

    return (top_holder["pct"] < max_single_owner_percentage and
            ownership_percentage < max_top_5_owner_percentage)


def fetch_price(token_addr):
    url = f"https://data.fluxbeam.xyz/tokens/{token_addr}/price"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return float(data.get("price", 0))
    else:
        print(f"FETCH-PRICE: Failed to fetch price for token {token_addr}")
        return None


def monitor_trades():
    global deposit
    for token_addr in list(active_trades.keys()):
        current_price = fetch_price(token_addr)
        if current_price is None:
            continue

        buy_price = active_trades[token_addr]["price"]

        if current_price >= 2 * buy_price:
            print(f"MONITOR-TRADES: Sell {token_addr} at price {current_price} (2x achieved!)")
            deposit += 0.2
            del active_trades[token_addr]


def evict_failed_tokens():
    global failed_tokens, last_failed_tokens_eviction_time

    current_time = time.time()
    if current_time - last_failed_tokens_eviction_time >= 300:  # 300 seconds = 5 minutes
        failed_tokens.clear()
        last_failed_tokens_eviction_time = current_time
        print("EVICT_FAILED_TOKENS: Cleared failed_tokens map")


def main():
    global deposit

    print_banner()
    print("Discovering meme coins...")

    while True:
        start_time = time.time()

        tokens = get_tokens(
            200,
            50_000,
            100_000,
            10,
            10,
            30
        )

        for token in tokens:
            token_addr = token["coinMint"]
            if token_addr not in active_trades and deposit >= 0.1:
                buy_price = fetch_price(token_addr)
                if buy_price:
                    print(f"MAIN: Buy {token['name']} at price {buy_price}")
                    active_trades[token_addr] = {"price": buy_price, "timestamp": time.time()}
                    deposit -= 0.1

        monitor_trades()

        end_time = time.time()
        print(f"MAIN: Found meme coins: {len(tokens)} (Time spent: {end_time - start_time})")

        evict_failed_tokens()


if __name__ == "__main__":
    main()
