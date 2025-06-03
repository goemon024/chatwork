# fastapi_backend/rag_utils.py

import openai, faiss, pickle, numpy as np
from typing import List
from dotenv import load_dotenv
import os

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

index = faiss.read_index("rag_engine/index.faiss")
with open("rag_engine/doc_store.pkl", "rb") as f:
    documents = pickle.load(f)


def embed_with_openai(text:str) ->list[float]:
    res = openai.Embedding.create(
        input=[text],
        model="text-embedding-3-small"
    )
    return res["data"][0]["embedding"]


def retrieve_relevant_context(query: str,
                              index,
                              documents,
                              top_k: int = 3) -> List[str]:
    emb = embed_with_openai(query)
    emb_np = np.array([emb]).astype(np.float32)
    _, I = index.search(emb_np, top_k)
    return [documents[i] for i in I[0]]


def answer_with_rag(query: str,index,documents) -> str:
    context_docs = retrieve_relevant_context(query,index,documents,top_k=3)
    
    context_text = "\n\n---\n\n".join(
        f"[{doc['metadata']['timestamp']}] {doc['original']['summary']}\n{doc['original']['content']}"
        for doc in context_docs
    )

    prompt = f"""以下は過去の業務連絡です：
    {context_text}
    質問：{query}
    上記質問に沿って前向きな口調で回答してください。
    """
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
    except Exception as e:
        print(f"❌ 回答生成中にエラーが発生しました: {e}")
        return "回答生成中にエラーが発生しました。"

    return completion["choices"][0]["message"]["content"]




# def query_index(query: str) -> str:
#     embedding = embed_with_openai(query)
#     embedding_np = np.array([embedding]).astype(np.float32)
#     D, I = index.search(embedding_np, top_k=3)
#     top_idx = I[0][0]
#     return documents[top_idx]


