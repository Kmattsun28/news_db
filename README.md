# api ディレクトリ

このディレクトリは、為替コンペティション2025のAPI関連のコードや設定ファイルを格納しています。

## 構成

- `app/` : FastAPI等のアプリケーション本体
- `data/` : データファイル
- `db/` : SQLite等のデータベース
- `models_cache/` : モデルキャッシュ
- `docker-compose.yml`, `Dockerfile` : Docker関連
- `requirements.txt` : Python依存パッケージ

## 使い方

1. 必要なPythonパッケージをインストール
   ```bash
   pip install -r requirements.txt
   ```
2. サーバーの起動例（FastAPIの場合）
   ```bash
   uvicorn app.main:app --reload
   ```
3. Dockerを使う場合
   ```bash
   docker-compose up --build
   ```

## 備考
- 各サブディレクトリやスクリプトの詳細は個別のREADMEやコメントを参照してください。
# news_db
