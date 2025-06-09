# from fastapi import FastAPI, HTTPException, Request
# from pydantic import BaseModel
# from .rag_utils import answer_with_rag
# import os
# import requests

print("🚀 main.py 起動開始")
import fastapi_backend.rag_loader as rag_loader

print("📂 rag_loader import 完了")
from fastapi_backend.rag_utils import answer_with_rag
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import os
import requests

import fastapi_backend.fetch_chatwork_messages as fetch_messages
import fastapi_backend.rag_generate as rag_generate

app = FastAPI()

class AskRequest(BaseModel):
    question: str

## ask
# @app.post("/ask")
# async def ask_endpoint(body: AskRequest):
#     if not body.question:
#         raise HTTPException(status_code=400, detail="No question provided.")
#     answer = answer_with_rag(body.question)
#     return {"question": body.question, "answer": answer}

@app.get("/")
def read_root():
    return {"message": "FastAPIサーバーは動作中です"}

@app.on_event("startup")
def startup_event():
    print("📦 SupabaseからRAGデータを読み込み中...")
    try:
        rag_loader.load_index_and_documents()
        print("✅ RAGデータの読み込み完了")
    except Exception as e:
        print(f"❌ RAGデータ読み込み失敗: {e}")

## chatwork webhook
API_TOKEN_ANSWER = os.getenv("CHATWORK_API_TOKEN_ANSWER")
ROOM_OUTPUT_ID = os.getenv("CHATWORK_ROOM_OUTPUT_ID")
BOT_ACCOUNT_ID = os.getenv("BOT_ACCOUNT_ID")

@app.post("/chatwork-hook")
async def chatwork_webhook(request: Request):
    try:
        data = await request.json()
        # ChatworkのWebhook形式に合わせてパース（例）
        webhook_event = data.get("webhook_event")
        if not webhook_event:
            raise HTTPException(status_code=400, detail="Invalid payload")

        message = webhook_event.get("body")
        account_id = str(webhook_event.get("account_id"))

        print(f"📩 質問受信: {message}")
    
        # 自分のBotの投稿は無視
        if account_id == BOT_ACCOUNT_ID:
            return JSONResponse(content={"status": "ignored"})
        
        # chatworkからのコマンド
        if message =="ＲＡＧ更新":
            print("ＲＡＧ更新します")
            fetch_messages.fetch_and_store_messages()
            rag_generate.rag_generate()
            return
        
        # chatworkからのコマンド
        if message =="ＲＡＧ読み込み":
            print("ＲＡＧ読み込みます")
            rag_loader.load_index_and_documents()
            print("✅ RAGデータの読み込み完了")
            # startup_event()
            return 

        answer = answer_with_rag(message,rag_loader.index,rag_loader.documents)
        post_to_chatwork(answer)
        return JSONResponse(content={"status": "success", "answer": answer})

    except Exception as e:
        print(f"⚠️ エラー: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


def post_to_chatwork(message: str):
    url = f"https://api.chatwork.com/v2/rooms/{ROOM_OUTPUT_ID}/messages"
    headers = {"X-ChatWorkToken": API_TOKEN_ANSWER}
    data = {"body": message}
    
    response = requests.post(url, headers=headers, data=data)
    if not response.ok:
        print(f"❌ チャットワークへの投稿に失敗しました:{response.text}")
        response.raise_for_status()
    else:
        print(f"✅ チャットワークへの投稿に成功しました:{response.text}")