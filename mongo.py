import certifi
import pymongo
import os
from http import server
from dotenv import load_dotenv
from pymongo import MongoClient

# Get mongodb credentials 
load_dotenv()
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
DATABASE = os.getenv("DATABASE")

uri = f"mongodb+srv://{USERNAME}:{PASSWORD}@cluster0.x9xg5.mongodb.net/{DATABASE}?retryWrites=true&w=majority"

client = MongoClient(uri, tlsCAFile=certifi.where())
db = client["lolTracker"]
users_client = db["users"]
servers_client = db["servers"]

# Add user to database
def add_user(userid, puuid, routing, serverid):
    query = {"user_id": userid, "server_id": serverid}
    res = users_client.find_one(query)

    if res is not None: 
        accounts = res["accounts"]
        if len(accounts) != 0:
            for account in accounts:
                if account[0] == puuid: # If PUUID already exists...
                    found = True
                    break
                else: 
                    found = False
        else:
            found = False
    
        if not found:
            accounts.append([puuid, "placeholder", routing[0], routing[1], routing[2]])

        update = {"$set": {"accounts": accounts} }  
        users_client.update_one(query, update)

    if res is None: 
        user = {"user_id": userid,
                "accounts": [[puuid, "placeholder", routing[0], routing[1], routing[2]]],
                "server_id": serverid}
        users_client.insert_one(user)

# Get list of users from a server
def get_users(server_id):
    query = {"server_id": server_id}
    res = users_client.find(query)
    return res

# Get a users accounts
def get_accounts(user_id, server_id):
    query = {"user_id": user_id, "server_id": server_id}
    res = users_client.find_one(query)
    return res['accounts']

# Remove a user from a server
def remove_account(userid, puuid, serverid):
    query = {"user_id": userid, "server_id": serverid}
    res = users_client.find_one(query)

    if res is not None:
        accounts = res["accounts"]
        for account in accounts:
            if account[0] == puuid:
                accounts.remove(account)
                update = {"$set": {"accounts": accounts}}
                users_client.update_one(query, update)

# Update an users latest match
def update_match(userid, puuid, latest_match, serverid):
    query = {"user_id": userid, "server_id": serverid}
    res = users_client.find_one(query)

    if res is not None: 
        accounts = res["accounts"]
        for account in accounts:
            if account[0] == puuid:
                account[1] = (latest_match)
                update = {"$set": {"accounts": accounts}}
                users_client.update_one(query, update)

    if res is None:
        print(res)
        print(userid, puuid, serverid)

# Create a new sever, when a new one is joined
def new_server(serverid, channel):
    query = {"server_id": serverid}
    res = servers_client.find_one(query)

    if res is not None:
        update = {"$set": {"channel": channel}}
        servers_client.update_one(query, update)

    if res is None:
        server = {"server_id": serverid, "channel": channel}
        servers_client.insert_one(server)
        
# Get channels 
def get_channels():
    res = servers_client.find({})
    return res

