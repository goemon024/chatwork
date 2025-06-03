import os
import requests
import json
from dotenv import load_dotenv
import supabase

load_dotenv()

API_TOKEN = os.getenv("CHATWORK_API_TOKEN")
ROOM_ID1 = "366697435"  # ← 実際のチャットAのルームIDに変更
ROOM_ID2 = "361855530"  # ← 実際のチャットBのルームIDに変更
ROOM_ID3 = "400639780"  # ← 実際のチャットBのルームIDに変更
API_URL1 = f"https://api.chatwork.com/v2/rooms/{ROOM_ID1}/messages"
API_URL2 = f"https://api.chatwork.com/v2/rooms/{ROOM_ID2}/messages"
API_URL3 = f"https://api.chatwork.com/v2/rooms/{ROOM_ID3}/messages"
HEADERS = {"X-ChatWorkToken": API_TOKEN}

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # or anon key for public
STORAGE_BUCKET = "chatwork-logs"
supabase = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
bucket = supabase.storage.from_(STORAGE_BUCKET)

SAVE_DIR1 = STORAGE_BUCKET + "/tax"
SAVE_DIR2 = STORAGE_BUCKET + "/repair"
SAVE_DIR3 = STORAGE_BUCKET + "/memo"

def get_saved_message_ids(save_directory):
    """既に保存されたmessage_idの一覧を取得"""
    url = f"{SUPABASE_URL}/storage/v1/object/public/{save_directory}"
    params = {
        "limit": 1000,
    }
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"❌ Supabase取得失敗: {response.status_code}: {response.text}")
        return set()
    
    data = response.json()
    files = data["data"]
    return {os.path.splitext(os.path.basename(file["name"]))[0] for file in files if file["name"].endswith(".json")}

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
            
            # JSONデータをバイト列に変換
            json_bytes = json.dumps(msg, ensure_ascii=False, indent=2).encode("utf-8")
            # Supabase上の保存パスを指定（例: "room1/12345.json"）
            supabase_path = f"{SUPABASE_URL}/storage/v1/object/public/{DIR_LIST[i]}/{msg_id}.json"
            # アップロード
            res = bucket.upload(supabase_path, json_bytes)
            print(f"✅ Supabaseにアップロード: {supabase_path} → {res}")
            print(f"✅ 保存: {msg['body'][:50]}...")
            
            # file_path = os.path.join(DIR_LIST[i], f"{msg_id}.json")
            # with open(file_path, "w", encoding="utf-8") as f:
            #     json.dump(msg, f, ensure_ascii=False, indent=2)

            count += 1

        print(f"🎉 合計 {count} 件を保存しました")

if __name__ == "__main__":
    fetch_and_store_messages()