import time

import requests
from datetime import datetime, timezone


def print_banner():
    print("""
    ,------.  ,------. ,----.   ,------.,--.  ,--. ,--.   ,--.  ,---.   ,---.,--------.,------.,------.  ,-----.,--.     ,---.   ,---.   ,---.
    |  .-.  \ |  .---''  .-./   |  .---'|  ,'.|  | |   `.'   | /  O  \ '   .-'--.  .--'|  .---'|  .--. ''  .--./|  |    /  O  \ '   .-' '   .-'
    |  |  \  :|  `--, |  | .---.|  `--, |  |' '  | |  |'.'|  ||  .-.  |`.  `-.  |  |   |  `--, |  '--'.'|  |    |  |   |  .-.  |`.  `-. `.  `-.
    |  '--'  /|  `---.'  '--'  ||  `---.|  | `   | |  |   |  ||  | |  |.-'    | |  |   |  `---.|  |\  \ '  '--'\|  '--.|  | |  |.-'    |.-'    |
    `-------' `------' `------' `------'`--'  `--' `--'   `--'`--' `--'`-----'  `--'   `------'`--' '--' `-----'`-----'`--' `--'`-----' `-----'
""")


def get_tokens(min_number_holders,
               min_market_cap,
               max_market_cap,
               max_sniper_count,
               max_single_owner_percentage,
               max_top_3_owner_percentage):
    url = f"https://advanced-api.pump.fun/coins/list?sortBy=creationTime&marketCapFrom={min_market_cap}&marketCapTo={max_market_cap}&numHoldersFrom={min_number_holders}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()

        filtered_tokens = []

        for token in data:

            top_holder_percentage = token["holders"][0]["ownedPercentage"]
            top_3_holders_percentage = sum(holder["ownedPercentage"] for holder in token["holders"][:3])
            if (token["sniperCount"] < max_sniper_count and
                    top_3_holders_percentage <= max_top_3_owner_percentage and
                    top_holder_percentage <= max_single_owner_percentage):
                filtered_tokens.append(token)

                print(
                    f"Name: {token['name']}, Ticker: {token['ticker']}, "
                    f"Market Cap: {token['marketCap']}, "
                    f"Creation Time: {datetime.fromtimestamp(token['creationTime'] / 1000, timezone.utc)}, "
                    f"Num Holders: {token['numHolders']}, "
                    f"Sniper Count: {token['sniperCount']}, "
                    f"Address: {token['coinMint']}"
                    f"Top Holder Ownership: {top_holder_percentage:.2f}%, "
                    f"Top 3 Holders Ownership: {top_3_holders_percentage:.2f}%"
                )

        return filtered_tokens
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return []


def main():
    print_banner()
    print("Discovering meme coins...")
    while True:
        START_TIME = time.time()
        tokens = get_tokens(200, 50_000, 100_000, 10, 10, 20)
        END_TIME = time.time()

        print(f"Found meme coins: {len(tokens)} (Time spent: {END_TIME - START_TIME})")


if __name__ == "__main__":
    main()
