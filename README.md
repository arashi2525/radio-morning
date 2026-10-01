# 朝のニュースラジオ

毎朝6時(JST)に GitHub Actions が RSS からニュースを集め、Claude API で約4分のラジオ原稿にし、
edge-tts で MP3 化して、GitHub Pages からポッドキャストとして配信します。

```
RSS (config.yaml) → Claude で原稿 → edge-tts で MP3 → docs/feed.xml を更新 → GitHub Pages
```

## セットアップ

1. このフォルダを GitHub リポジトリとして push する(Pages を無料で使うには public リポジトリ)。
2. **Settings → Secrets and variables → Actions** で `ANTHROPIC_API_KEY` を登録する。
3. **Settings → Pages** で Source を「Deploy from a branch」、Branch を `main` / `/docs` にする。
4. **Actions → Daily news podcast → Run workflow** で初回を手動実行する。
5. `https://<ユーザー名>.github.io/<リポジトリ名>/feed.xml` をポッドキャストアプリに登録する。

## カスタマイズ

すべて [config.yaml](config.yaml) で編集します。

- `genres`: ジャンルと RSS ソースの追加・削除・並べ替え
- `script`: 番組の長さ、口調、使用モデル
- `tts`: 声と話速
- `podcast`: 番組名、説明、保持する回数

配信時刻は [.github/workflows/daily.yml](.github/workflows/daily.yml) の `cron`(UTC)で変更します。

## ローカルで試す

```bash
pip install -r requirements.txt
python -m newscast --dry-run   # RSS取得のみ。APIキー不要
python -m newscast             # ANTHROPIC_API_KEY が必要。docs/ に出力
```

## 構成

| ファイル | 役割 |
|---|---|
| `newscast/fetch.py` | RSS 取得 |
| `newscast/script.py` | Claude API で原稿生成 |
| `newscast/tts.py` | 音声合成 |
| `newscast/feed.py` | `episodes.json` / `feed.xml` / `index.html` の更新 |
| `docs/` | GitHub Pages の公開ディレクトリ(MP3 と原稿テキストもここ) |
