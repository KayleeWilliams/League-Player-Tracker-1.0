import os
import requests
from dotenv import load_dotenv

# Get API Key for League/Riot API
load_dotenv()
API_KEY_2 = os.getenv("API_KEY_2")

# API Routing


def get_routing(platform):
    platform = platform.upper()

    if platform == "KR" or "JP":
        region = "asia"

        if platform == "KR":
            return "kr", region, "kr"

        elif platform == "JP":
            return "jp1", region, "jp"

    if platform == "EUW" or "EUNE" or "TR" or "RU":
        region = "europe"

        if platform == "EUW":
            return "euw1", region, "euw"

        elif platform == "EUNE":
            return "eun1", region, "eune"

        elif platform == "TR":
            return "tr1", region, "tr"

        elif platform == "RU":
            return "ru", region, "ru"

    if platform == "NA" or "BR" or "LAN" or "LAS" or "OCE":
        region = "americas"

        if platform == "NA":
            return "na1", region, "na"

        elif platform == "BR":
            return "br1", region, "br"

        elif platform == "LAN":
            return "la1", region, "lan"

        elif platform == "LAS":
            return "la2", region, "las"

        elif platform == "OCE":
            return "oc1", region, "oce"

# Get UUID


def get_puuid(NAME, platform):
    try:
        NAME = NAME.replace(' ', '%20')  # Replace the spaces
        res = requests.get(
            f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{NAME}?api_key={API_KEY_2}")
        res.raise_for_status()  # Check for HTTP Error
        res = res.json()  # Return response
        return False, res["puuid"]

    except requests.exceptions.HTTPError as err:
        status_code = err.response.status_code  # Error code  E.g. 404
        reason = err.response.reason  # Reason E.g. Not found
        print(f"[GET PUUID] {status_code}: {reason} Error!")
        return True, status_code, reason

# Get UUID latest matches


def latest_matches(puuid, region, start_time):
    try:
        res = requests.get(
            f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?startTime={start_time}&queue=420&api_key={API_KEY_2}")
        res.raise_for_status()  # Check for HTTP Error
        res = res.json()  # Return response
        return False, res

    except requests.exceptions.HTTPError as err:
        status_code = err.response.status_code  # Error code  E.g. 404
        reason = err.response.reason  # Reason E.g. Not found
        print(f"[LATEST MATCHES] {status_code}: {reason} Error!")
        return True, status_code, reason

# Get PUUID's username


def get_username(puuid, platform):
    res = requests.get(
        f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={API_KEY_2}")
    res = res.json()
    return res

# Summary of UUID games in past x


def accounts_summary(accounts, start_time):
    champs = []
    wins = []
    posistions = []
    average_cs = []
    average_csm = []
    cs_at_10 = []

    total_matches = 0
    kills = 0
    deaths = 0
    assists = 0

    for account in accounts:
        matches = latest_matches(account[0], account[3], start_time)
        total_matches += len(matches[1])
        for match in matches[1]:
            res = requests.get(
                f"https://{account[3]}.api.riotgames.com/lol/match/v5/matches/{match}?api_key={API_KEY_2}")
            res = res.json()

            for participant in res["info"]["participants"]:
                if participant["puuid"] == account[0]:
                    champs.append(participant["championName"])
                    wins.append(participant["win"])

                    posistions.append(participant["individualPosition"])

                    kills += participant["kills"]
                    deaths += participant["deaths"]
                    assists += participant["assists"]

                    minuites = res["info"]["gameDuration"] // 60
                    total_cs = participant["totalMinionsKilled"] + \
                        participant["neutralMinionsKilled"]
                    get_average = round(total_cs / minuites, 2)
                    average_cs.append(total_cs)
                    average_csm.append(get_average)

                    cs = round(participant["challenges"]["laneMinionsFirst10Minutes"] +
                               participant["challenges"]["jungleCsBefore10Minutes"], 2)
                    cs_at_10.append(cs)

    for i in range(len(posistions)):
        if posistions[i] == "UTILITY":
            posistions[i] = "SUPPORT"
        posistions[i] = posistions[i].title()

    kills = round(kills/total_matches, 1)

    deaths = round(deaths/total_matches, 1)
    assists = round(assists/total_matches, 1)
    average_cs = round(sum(average_cs)/total_matches)
    average_csm = round(sum(average_csm)/total_matches)
    average_cs_at_10 = round(sum(cs_at_10)/total_matches)

    response = {
        "total_matches": total_matches,
        "winrate": round(sum(wins)/len(wins)*100, 2),
        "champs": champs,
        "average_kda": [kills, deaths, assists],
        "posistions": posistions,
        "average_cs": average_cs,
        "average_csm": average_csm,
        "10min_cs": average_cs_at_10
    }

    return response

# Get PUUIDs latest match


def latest_match(puuid, region, matches):
    match = matches[0]  # First match on list, if there is multiple
    res = requests.get(
        f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match}?api_key={API_KEY_2}")
    res = res.json()

    for participant in res["info"]["participants"]:
        if participant["puuid"] == puuid:

            # Get game length
            seconds = res["info"]["gameDuration"]
            minute = res["info"]["gameDuration"] // 60
            seconds %= 60

            total_cs = participant["totalMinionsKilled"] + \
                participant["neutralMinionsKilled"]
            average_cs = round(total_cs / minute, 2)

            # Edit posistions and make them presentable
            if participant["individualPosition"] == "UTILITY":
                posistion = "Support"
            else:
                # "JUNGLE" -> "Jungle"
                posistion = participant["individualPosition"].title()

            # Return data as dictionry
            response = {
                "win": participant["win"],
                "champ": participant["championName"],
                "kda": [participant["kills"], participant["deaths"], participant["assists"]],
                "posistion": posistion,
                "total_cs": total_cs,
                "average_cs": average_cs,
                "game_lengh": [minute, seconds]
            }
            return response
