import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("CHATWORK_API_TOKEN")
ROOM_ID1 = "366697435"  # ← 実際のチャットAのルームIDに変更
ROOM_ID2 = "361855530"  # ← 実際のチャットBのルームIDに変更
ROOM_ID3 = "400639780"  # ← 実際のチャットBのルームIDに変更
API_URL1 = f"https://api.chatwork.com/v2/rooms/{ROOM_ID1}/messages"
API_URL2 = f"https://api.chatwork.com/v2/rooms/{ROOM_ID2}/messages"
API_URL3 = f"https://api.chatwork.com/v2/rooms/{ROOM_ID3}/messages"
HEADERS = {"X-ChatWorkToken": API_TOKEN}

SAVE_DIR1 = "./chatwork_logs/tax"
SAVE_DIR2 = "./chatwork_logs/repair"
SAVE_DIR3 = "./chatwork_logs/memo"

os.makedirs(SAVE_DIR1, exist_ok=True)
os.makedirs(SAVE_DIR2, exist_ok=True)
os.makedirs(SAVE_DIR3, exist_ok=True)

def get_saved_message_ids(save_directory):
    """既に保存されたmessage_idの一覧を取得"""
    files = os.listdir(save_directory)
    return {f.split(".")[0] for f in files if f.endswith(".json")}

def fetch_and_store_messages():
    URL_LIST = [API_URL1, API_URL2, API_URL3]
    DIR_LIST = [SAVE_DIR1, SAVE_DIR2, SAVE_DIR3]
    
    print("📥 メッセージ取得開始...")
    for i, API_URL in enumerate(URL_LIST):
        print(API_URL, URL_LIST[i])
        response = requests.get(URL_LIST[i], headers=HEADERS)

        if response.status_code != 200:
            print("❌ エラー:", response.status_code, response.text)
            continue

        messages = response.json()
        saved_ids = get_saved_message_ids(DIR_LIST[i])
        count = 0
        
        for msg in messages:
            msg_id = msg["message_id"]
            
            if msg_id in saved_ids:
                continue  # すでに保存済みならスキップ
            
            file_path = os.path.join(DIR_LIST[i], f"{msg_id}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(msg, f, ensure_ascii=False, indent=2)
                
            print(f"✅ 保存: {msg['body'][:50]}...")
            count += 1

        print(f"🎉 合計 {count} 件を保存しました")

if __name__ == "__main__":
    fetch_and_store_messages()