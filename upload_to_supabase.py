# upload_to_supabase.py
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# 環境変数または直書き（環境変数推奨）
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

BUCKET_NAME = "rag-files"
LOCAL_FILES = {
    "index.faiss": "./rag_engine/index.faiss",
    "doc_store.pkl": "./rag_engine/doc_store.pkl"
}

# クライアント作成
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# アップロード処理
for remote_name, local_path in LOCAL_FILES.items():
    with open(local_path, "rb") as f:
        print(f"Uploading {remote_name}...")
        res = supabase.storage.from_(BUCKET_NAME).upload(remote_name, f, {"content-type": "application/octet-stream"})
        print(res)
