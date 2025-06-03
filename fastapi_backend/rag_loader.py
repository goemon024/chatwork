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
    try:
        print(f"📥 {filename} を {dest_path} にダウンロード中...")
        res = supabase.storage.from_(BUCKET_NAME).download(filename)
        with open(dest_path, "wb") as f:
            f.write(res)
        print(f"✅ {filename} のダウンロード完了")
    except Exception as e:
        print(f"❌ {filename} のダウンロード失敗: {e}")
        raise

def load_index_and_documents():
    os.makedirs("./tmp", exist_ok=True)

    try:
        print("=== インデックスとドキュメントのダウンロード開始 ===")
        download_file("index.faiss", LOCAL_INDEX_PATH)
        download_file("doc_store.pkl", LOCAL_PKL_PATH)
        
        print(os.path.getsize("./tmp/index.faiss")) 
        print(os.path.getsize("./tmp/doc_store.pkl")) 
        print("=== ダウンロード完了 ===")
    except Exception as e:
        print(f"❌ ファイルのダウンロード中にエラー: {e}")
        raise

    global index, documents
    try:
        print("🔄 FAISSインデックスをメモリにロード中...")
        index = faiss.read_index(LOCAL_INDEX_PATH)
        print(type(index))
        print("✅ FAISSインデックスのロード完了")
    except Exception as e:
        print(f"❌ FAISSインデックスのロード失敗: {e}")
        index = None
        raise

    try:
        print("🔄 ドキュメント（pickle）をメモリにロード中...")
        with open(LOCAL_PKL_PATH, "rb") as f:
            documents = pickle.load(f)
        print(type(documents))
        print("✅ ドキュメントのロード完了")
    except Exception as e:
        print(f"❌ ドキュメントのロード失敗: {e}")
        documents = None
        raise
