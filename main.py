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


def get_tokens(min_number_holders,
               min_market_cap,
               max_market_cap,
               max_sniper_count,
               max_single_owner_percentage,
               max_top_5_owner_percentage):

    print(f"Fetching information from pump.fun [{min_market_cap} < MC < {max_market_cap}, Sniper < {max_sniper_count}, 1TH% -> {max_single_owner_percentage}, 5TH% -> {max_top_5_owner_percentage}")

    url = f"https://advanced-api.pump.fun/coins/list?sortBy=creationTime&marketCapFrom={min_market_cap}&marketCapTo={max_market_cap}&numHoldersFrom={min_number_holders}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        filtered_tokens = []

        for token in data:

            if token["sniperCount"] < max_sniper_count:

                token_addr = token["coinMint"]

                if not rug_check(token_addr, max_single_owner_percentage, max_top_5_owner_percentage):
                    print(f"GET-TOKENS: {token['name']} with addr {token['coinMint']} fails on rugcheck!")
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
        print(f"Failed to fetch data from pump.fun - status code: {response.status_code}")
        return []


# rugcheck.xyz
def rug_check(token_addr, max_single_owner_percentage, max_top_5_owner_percentage):
    url = f"https://api.rugcheck.xyz/v1/tokens/{token_addr}/report"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        if not check_risks(data["risks"]):
            print(f"RUG-CHECK: {token_addr} -> risks array is not empty")
            return False

        if not check_top_holders_ownership(data["topHolders"], max_single_owner_percentage, max_top_5_owner_percentage):
            print(f"RUG-CHECK: {token_addr} -> top holders validation fails")
            return False

        return True

    else:
        print(f"RUG-CHECK: Failed to fetch data from rugcheck.xyz - status code: {response.status_code}")
        return False


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
            top_holders[0]["owner"] == "HahdWwA534mqfzzX27AJN4HcYC2t3kHj8Pp3uXChZTD6" and
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


def main():
    print_banner()
    print("Discovering meme coins...")

    while True:
        start_time = time.time()

        tokens = get_tokens(
            200,
            50_000,
            100_000,
            10,
            5,
            15
        )

        end_time = time.time()

        print(f"Found meme coins: {len(tokens)} (Time spent: {end_time - start_time})")


if __name__ == "__main__":
    main()
