import requests

user_key = "upy5sdbfmzcokcnywxhzi9va91v5uo"
api_token = "anjxf411x6dw6bqcg1td6b7r9i7j7t"


def alert(message):
    url = "https://api.pushover.net/1/messages.json"
    payload = {"token": api_token, "user": user_key, "message": message}
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print("Failed to send notification.")
