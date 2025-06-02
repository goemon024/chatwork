import os
# import time
# import requests
import openai
import faiss
import pickle
import numpy as np

DIM = 1536

# from my_rag_core import (
#     load_index, add_to_index, save_index_and_store,
# )

def load_index():
    # rag_generate.py と同様。
    if os.path.exists("index.faiss") and os.path.exists("doc_store.pkl"):
        index = faiss.read_index("index.faiss")
        with open("doc_store.pkl", "rb") as f:
            doc_store = pickle.load(f)
    else:
        index = faiss.IndexFlatL2(DIM)
        doc_store = []
    return index, doc_store


def retrieve_relevant_context(query, top_k=2):
    index, doc_store = load_index() # 追加
    query_embedding = openai.Embedding.create(
        model="text-embedding-3-small",
        input=query
    )["data"][0]["embedding"]

    # top_kは取得するデータ数、Dは距離の配列、Iはインデックスの配列
    D, I = index.search(np.array([query_embedding]).astype('float32'), top_k)
    
    results = []
    for idx in I[0]:
        doc = doc_store[idx]
        results.append(doc)
    
    return results



def answer_with_rag(query):
    context_docs = retrieve_relevant_context(query, top_k=3)
    
    context_text = "\n\n---\n\n".join(
        f"[{doc['metadata']['timestamp']}] {doc['original']['summary']}\n{doc['original']['content']}"
        for doc in context_docs
    )

    prompt = f"""以下は過去の業務連絡です：
    {context_text}
    質問：{query}
    上記質問に沿って、上品な関西弁で回答してください。
    """
    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    return completion["choices"][0]["message"]["content"]