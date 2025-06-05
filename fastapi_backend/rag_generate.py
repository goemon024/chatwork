import os
import json
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
import openai
from janome.tokenizer import Tokenizer
import re
import faiss
import numpy as np
import pickle
from dotenv import load_dotenv
from datetime import datetime, date
from supabase import create_client
import fastapi_backend.rag_loader as rag_loader
import tempfile
import io

load_dotenv()
tokenizer = Tokenizer()

# 🔑 OpenAI APIキー（.envなどに置くとよい）
openai.api_key = os.getenv("OPENAI_API_KEY")

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
BUCKET_NAME_LOG = os.getenv("BUCKET_NAME_LOG")

BUCKET_NAME = os.getenv("BUCKET_NAME")
supabase = create_client(supabase_url, supabase_key)
bucket = supabase.storage.from_(BUCKET_NAME)
bucket_log = supabase.storage.from_(BUCKET_NAME_LOG)

def tokenize_japanese(text):
    return [token.surface for token in tokenizer.tokenize(text)]

# ストップワード。TFIDFによるバンドル処理で使う。
JAPANESE_STOP = ["これ", "それ", "あれ", "この", "その", "あの", "ここ",
                 "そこ", "あそこ","私", "あなた", "です","いる",
                 "ある", "する", "なる", "の", "に", "は", "を", "が", "と", "も", "で",
                  "しかし","吉井","樋口","西口","amahou","松下"]

# スキップ文。chatworkの運用メッセージ。
SKIP_PHRASES =[
    "アイコンを変更しました",
    "メッセージを編集しました",
]

def contains_japanese(text):
    # ひらがな・カタカナ・漢字のいずれかが含まれていればTrue
    return re.search(r'[\u3040-\u30FF\u4E00-\u9FFF]', text) is not None

def is_skip_phrase(text):
    return any(phrase in text for phrase in SKIP_PHRASES)

def extract_room_name(text):
    # 例: 「ルミナス伊丹101号室」「ルミナス伊丹101室」「伊丹101号室」「伊丹101室」「伊丹101」などを抽出
    pattern = r'([^\s]+?\d{1,4}(号室|室|号|階)?)'
    matches = re.findall(pattern, text)
    # matchesはタプルのリストになるので、最初の要素だけ取り出す
    return [m[0] for m in matches] if matches else []

# 🔹 ステップ1：メッセージ読み込み（想定フォルダ：./chatwork_logs）
def load_messages(folder_path):
    messages = []
    today = date.today()
    res = bucket_log.list(folder_path)
    for file_info in res:
        file_name = file_info["name"]
        if not file_name.endswith(".json"):
            continue
        
        file_path = f"{folder_path}/{file_name}"
        file_bytes = bucket_log.download(file_path)
        msg = json.loads(file_bytes.decode("utf-8"))
        body = msg["body"]
        send_time = datetime.fromtimestamp(msg["send_time"])
        if send_time.date() != today:
            continue  # 今日送信されたメッセージでなければスキップ
        if not contains_japanese(body):
            continue  # 日本語が含まれていなければスキップ
        if is_skip_phrase(body):
            continue
        messages.append({
            "id": msg["message_id"],
            "body": body,
            "timestamp": send_time
        })
    return messages


def keyword_overlap(tags1, tags2, threshold=3):
    return len(set(tags1) & set(tags2)) >= threshold

def is_valid_tag(tag, min_len=2, max_len=15):
    # ひらがな・カタカナ・漢字・英数字を含む2文字以上15文字以下
    return min_len <= len(tag) <= max_len

# ステップ2：バンドル処理（TFIDFタグ添付）
def bundle_by_tfidf(messages, top_k=3, threshold=2, mode="default"):
    texts = [msg["body"] for msg in messages]
    
    vectorizer = TfidfVectorizer(tokenizer=tokenize_japanese,
                                 stop_words=JAPANESE_STOP,
                                 ngram_range=(1, 4),
                                 token_pattern=None)
    tfidf = vectorizer.fit_transform(texts)
    features = vectorizer.get_feature_names_out()

    bundles = []
    last_bundle = None

    for i, msg in enumerate(messages):
        # タグ生成
        row = tfidf[i].toarray()[0]
        top_indices = row.argsort()[-top_k:][::-1]
        tfidf_tags = [features[idx] for idx in top_indices]
        room_tags = extract_room_name(msg["body"])
        all_tags = set(tfidf_tags + room_tags)
        filtered_tags = [tag for tag in all_tags if is_valid_tag(tag)]
        msg["tags"] = filtered_tags
        
        if mode == "memo":
            room_tags = ["memo"]

        if room_tags:
            # 部屋名タグがある場合は新しいバンドル
            bundle = {
                "id": [msg["id"]],
                "tags": filtered_tags,
                "messages": [msg],
                "timestamp": [msg["timestamp"]]
            }
            bundles.append(bundle)
            last_bundle = bundle
        else:
            # 部屋名タグがない場合は直前のバンドルに追加
            if last_bundle is not None:
                last_bundle["id"].append(msg["id"])
                last_bundle["messages"].append(msg)
                last_bundle["tags"] = list(set(last_bundle["tags"] + filtered_tags))
                last_bundle["timestamp"].append(msg["timestamp"])
            else:
                # 最初のメッセージが部屋名タグなしの場合は新規バンドル
                bundle = {
                    "id": [msg["id"]],
                    "tags": filtered_tags,
                    "messages": [msg],
                    "timestamp": [msg["timestamp"]]
                }
                bundles.append(bundle)
                last_bundle = bundle

    for bundle in bundles:
        bundle["combined_body"] = "\n".join([msg["body"] for msg in bundle["messages"]])
    return bundles


# 🔹 ステップ3：GPTで要約生成
def generate_summary(text):
    prompt = f"以下のメッセージの要点を1〜2文で要約してください。挨拶などの形式的文面は省略すること。：\n{text}"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response["choices"][0]["message"]["content"].strip()


# 🔹 ステップ4：RAG形式で出力（page_content + metadata）
def format_for_rag(bundle, summary):
    return {
        "summary": summary,
        "content": bundle["combined_body"],
        "metadata": {
            "id": bundle["id"],
            "timestamp": bundle["timestamp"],
            "tags": bundle["tags"]
        }
    }

#  ステップ5：summary+contentのベクトル化
def embed_rag_doc(rag_doc):
    embedding_input = rag_doc["summary"] + "\n\n" + rag_doc["content"]
    response = openai.Embedding.create(
        model="text-embedding-3-small",
        input=embedding_input
    )
    vector = response["data"][0]["embedding"]
    
    return {
        "embedding": vector,
        "metadata": rag_doc["metadata"],
        "original": {
            "summary": rag_doc["summary"],
            "content": rag_doc["content"]
        }
    }




DIM = 1536

# def load_index():
#     if os.path.exists("index.faiss") and os.path.exists("doc_store.pkl"):
#         index = faiss.read_index("index.faiss")
#         with open("doc_store.pkl", "rb") as f:
#             doc_store = pickle.load(f)
#     else:
#         index = faiss.IndexFlatL2(DIM)
#         doc_store = []
#     return index, doc_store

# 単純なFAISSインデックス（実用ではID管理やHNSW使用を推奨）
# dimension = 1536  # OpenAI embedding の次元数（モデルによって異なる）
# index = faiss.IndexFlatL2(dimension)
# doc_store = []  # メタ情報をここに保持（embeddingとインデックスを分離）

def add_to_index(doc_vector, index, doc_store):
    existing_ids = {d["metadata"]["id"][0] for d in doc_store}
    if doc_vector["metadata"]["id"][0] in existing_ids:
        print(f"⚠️ 既に存在するためスキップ: {doc_vector['metadata']['id'][0]}")
        return
    
    vector = np.array([doc_vector["embedding"]]).astype('float32')
    index.add(vector)
    doc_store.append(doc_vector)

def save_index_to_supabase(index, doc_store):
    # index.faissをバイト列で保存
    # faiss_bytes = io.BytesIO()
    # faiss.write_index(index, faiss_bytes)
    # faiss_bytes.seek(0)
    
    with tempfile.NamedTemporaryFile(suffix=".faiss", delete=False) as tmp:
        faiss.write_index(index, tmp.name)
        tmp.seek(0)
        content = tmp.read()
        bucket.upload("index2.faiss", content)
        


    # doc_store.pklをバイト列で保存
    pkl_bytes = io.BytesIO()
    pickle.dump(doc_store, pkl_bytes)
    pkl_bytes.seek(0)
    bucket.upload("doc_store2.pkl", pkl_bytes.read())
    print("✅ Supabaseにindex2.faissとdoc_store2.pklをアップロードしました")



# 🔹 実行部分
# if __name__ == "__main__":
    
def rag_generate():
    folders = ["tax",
               "repair",
               "memo"]
    # folders = ["memo",
    #            "memo/",
    #            "/memo",
    #            "/memo/"]

    
    messages = []
    for folder in folders:
        messages.extend(load_messages(folder))
    
    if len(messages) == 0:
        print("❌ 新規メッセージが見つかりませんでした。")
        exit()
        
    bundles = bundle_by_tfidf(messages)
    

    rag_data = []
    for bundle in bundles:
        summary = generate_summary(bundle["combined_body"])
        rag_doc = format_for_rag(bundle, summary)
        rag_data.append(rag_doc)

    embedded_rag_data = [embed_rag_doc(doc) for doc in rag_data]
    
    try:
        rag_loader.load_index_and_documents()
        print("✅ RAGデータの読み込み完了")
    except Exception as e:
        print(f"❌ RAGデータ読み込み失敗: {e}")
    
    for doc in embedded_rag_data:
        add_to_index(doc, rag_loader.index, rag_loader.documents)
    save_index_to_supabase(rag_loader.index, rag_loader.documents)

    for i in range(len(embedded_rag_data)):
        print(embedded_rag_data[i]["metadata"]["id"])
        print("--------------------------------")

    # # 結果を保存
    # with open("rag_documents.json", "w", encoding="utf-8") as f:
    #     json.dump(rag_data, f, ensure_ascii=False, indent=2)

    # print("✅ RAGデータ構築完了！件数:", len(rag_data))


if __name__ == "__main__":
    rag_generate()