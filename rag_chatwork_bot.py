import os
import time
import requests
# import openai
# import faiss
# import pickle
import numpy as np
import dotenv

dotenv.load_dotenv()

# 読み込み
from my_rag_core import (
    load_index, retrieve_relevant_context,
    answer_with_rag  # ← RAG機能（前提：定義済み）
)

API_TOKEN_QUESTION = os.getenv("CHATWORK_API_TOKEN_QUESTION")
API_TOKEN_ANSWER = os.getenv("CHATWORK_API_TOKEN_ANSWER")
# ROOM_INPUT_ID = os.getenv("CHATWORK_ROOM_INPUT_ID")
ROOM_OUTPUT_ID = os.getenv("CHATWORK_ROOM_OUTPUT_ID")
HEADERS_QUESTION = {"X-ChatWorkToken": API_TOKEN_QUESTION}
HEADERS_ANSWER = {"X-ChatWorkToken": API_TOKEN_ANSWER}

BOT_ACCOUNT_ID = os.getenv("BOT_ACCOUNT_ID")

def get_latest_messages():
    url = f"https://api.chatwork.com/v2/rooms/{ROOM_OUTPUT_ID}/messages"
    return requests.get(url, headers=HEADERS_QUESTION).json()

def post_reply(message):
    url = f"https://api.chatwork.com/v2/rooms/{ROOM_OUTPUT_ID}/messages"
    return requests.post(url, headers=HEADERS_ANSWER, data={"body": message})

def main():
    # index, doc_store = load_index()
    seen_ids = set()

    while True:
        try:
            messages = get_latest_messages()
            print(messages)

            for msg in messages:
                # 自分の投稿はスキップ
                if str(msg["account"]["account_id"]) == BOT_ACCOUNT_ID:
                    continue
                mid = msg["message_id"]
                if mid in seen_ids:
                    continue
                query = msg["body"]
                answer = answer_with_rag(query)
                post_reply(answer)
                seen_ids.add(mid)

            time.sleep(10)
        except Exception as e:
            print(f"⚠️ エラー発生: {e}")
            time.sleep(15)

if __name__ == "__main__":
    main()
