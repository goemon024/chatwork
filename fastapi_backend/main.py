from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from .rag_utils import answer_with_rag
import os
import requests

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



## chatwork webhook
API_TOKEN_ANSWER = os.getenv("CHATWORK_API_TOKEN_ANSWER")
ROOM_OUTPUT_ID = os.getenv("CHATWORK_ROOM_OUTPUT_ID")
BOT_ACCOUNT_ID = os.getenv("BOT_ACCOUNT_ID")


@app.post("/chatwork-hook")
async def chatwork_webhook(request: Request):
    data = await request.json()

    try:
        # ChatworkのWebhook形式に合わせてパース（例）
        webhook_event = data.get("webhook_event")
        if not webhook_event:
            raise HTTPException(status_code=400, detail="Invalid payload")

        message = webhook_event.get("body")
        account_id = str(webhook_event.get("account_id"))

        print(f"📩 質問受信: {webhook_event}")
        print(f"📩 送信元: {account_id}")
    
        # 自分のBotの投稿は無視
        if account_id == BOT_ACCOUNT_ID:
            return {"status": "ignored"}

        print(f"📩 質問受信: {message}")
        answer = answer_with_rag(message)
        post_to_chatwork(answer)
        return {"status": "ok"}

    except Exception as e:
        print(f"⚠️ エラー: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


def post_to_chatwork(message: str):
    url = f"https://api.chatwork.com/v2/rooms/{ROOM_OUTPUT_ID}/messages"
    headers = {"X-ChatWorkToken": API_TOKEN_ANSWER}
    data = {"body": message}
    res = requests.post(url, headers=headers, data=data)
    res.raise_for_status()
