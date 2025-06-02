import os
import pickle
import faiss
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME", "rag-files")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ローカルキャッシュパス
LOCAL_INDEX_PATH = "./tmp/index.faiss"
LOCAL_PKL_PATH = "./tmp/doc_store.pkl"

index = None
documents = None

def download_file(filename: str, dest_path: str):
    res = supabase.storage.from_(BUCKET_NAME).download(filename)
    with open(dest_path, "wb") as f:
        f.write(res)

def load_index_and_documents():
    os.makedirs("./tmp", exist_ok=True)

    # DL
    download_file("index.faiss", LOCAL_INDEX_PATH)
    download_file("doc_store.pkl", LOCAL_PKL_PATH)

    # メモリ展開
    global index, documents
    index = faiss.read_index(LOCAL_INDEX_PATH)
    with open(LOCAL_PKL_PATH, "rb") as f:
        documents = pickle.load(f)
