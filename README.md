### localのみの場合
- rag_chatwork_bot.pyを起動させてメッセージの待ち受け状態に出来る。  
（webhookではなくlocalから定期的に問い合わせて拾ってくる）
- fetch_chatwork_messages.py及びrag_generate.pyにてメッセージをローカルに保存してragファイルをローカルに構築する。

### localのfastapi
`uvicorn fastapi_backend.main:app --reload`
によりfastAPIをローカルで公開。  
`ngrok http 8000`  
にて、インターネットに公開。こちらのコマンドは適当なターミナル・カレントフォルダで可。  
また、chatworkの設定は毎回変更する必要がある（ngrokのコマンドで表示されたForwarding）  

- ragの構築等はlocalの場合と同様。


