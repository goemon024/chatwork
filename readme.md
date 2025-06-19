## 起動時の実行順序
fetch_chatwork_messages.pyにより当日のメッセージを取得する。
rag_generate.pyにより当日メッセージのRAGを形成。
rag_chatwork_bot.pyを起動させることで、chatworkからのメッセージを受け入れてＡＰＩで返答。

### 1.chatworkからの取込
・fetch_chatwork_messages.py
　charworkでの書き込み（3フォルダ内）をjsonファイルでchatwork_logsに保存。
・rag_generate.py
　取り込まれたjsonを、RAGデータに変換。この際、「tfidfでタグ付け」、「前後メッセージのタグの一致性で束ねる（バンドル処理）」、「要約生成」を行い、summaryとcombined_body、metadataを生成している（format_for_rag参照）。
### 2. 各種出力用スクリプト
~~（試作）rag_answer.py~~
~~ターミナルでの出力用スクリプト~~

（試作）rag_chatwork_bot.pyとmy_rag_core.py 　chatwork上での入力・出力用のスクリプト

### ~~3.fastapi_backdend（localhost、render）~~
~~fastapi_backend/main.py,rag_utils.py~~
~~rag_engine/index.faiss, doc_store.pkl~~
~~ローカルでのfastapiサーバ構築。データはrag_engineのファイルから読みだす。renderではsupabaseにrag-filesを記録して読みだすようにする。~~