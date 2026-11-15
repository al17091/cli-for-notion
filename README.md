# Notion CLI (`notion` / `notion-cli`)

高速・軽量かつ依存関係ゼロ（Python 標準ライブラリのみで動作）の Notion 操作用 CLI ツールです。  
Notion MCP Server の代わりに CLI 経由で Markdown の読み書き、ページの作成・更新、データベースクエリ、検索を快適に行えます。

---

## 🌟 特徴

- **高速 & ゼロ依存**: Python 3.9+ の標準ライブラリ (`urllib.request`) のみで実装。外部ライブラリのインストール不要で起動が極めて高速。
- **ネイティブ Markdown サポート**: Notion API 2026-03-11 の Markdown エンドポイントに対応。ページ全体の一括取得 (`get`) や置換 (`update`)、末尾追記 (`append`)、部分置換 (`replace`) が可能。
- **パイプ & 標準入力対応**: `cat document.md | notion page update <PAGE_ID>` のようにパイプライン処理が可能。
- **URL / UUID 自動正規化**: Notion の Web URL（`https://notion.so/...` や `https://app.notion.com/p/...`）、ハイフンなし 32 桁 16 進数、ハイフン付き UUID のいずれを渡しても自動解決。
- **データベース & データソース自動解決**: 2026-03-11 仕様の Data Source と Database の関係を自動判定し、テーブル検索やプロパティの自動型変換（`select`, `rich_text`, `status`, `multi_select` 等）を実行。
- **レートリミット (429) 自動リトライ**: Notion API のレート制限を検知し、指数バックオフで自動再試行。

---

## 🚀 インストール & セットアップ

### 1. 認証トークンの設定
Notion インテグレーションの内部トークン（`ntn_...` または `secret_...`）を設定します。

```bash
# 方法 1: CLI から設定（~/.config/notion/config.json に 0600 で保存）
notion auth set-token "ntn_xxxxxxxxxxxxxxxxxxxx"

# 方法 2: 環境変数
export NOTION_API_KEY="ntn_xxxxxxxxxxxxxxxxxxxx"
# または
export NOTION_TOKEN="ntn_xxxxxxxxxxxxxxxxxxxx"
```

### 2. 接続確認
```bash
notion whoami
# または
notion auth status
```

出力例:
```text
Authenticated as: lab_enhance (ce00ee66-8ac5-460c-b5b4-4c7277f4d592)
Workspace:        Private Workspace
Status:           Active (Valid token)
```

---

## 📖 コマンドリファレンス

### 1. ページ操作 (`notion page`)

#### ページの Markdown 取得 (`get`)
```bash
# 標準出力へ表示
notion page get <PAGE_ID_OR_URL>

# ファイルへ保存
notion page get <PAGE_ID_OR_URL> -o page_backup.md

# ページメタデータ JSON を取得
notion page get <PAGE_ID_OR_URL> --json
```

#### 新規ページの作成 (`create`)
```bash
# 空ページ作成
notion page create --parent <PARENT_PAGE_OR_DB_ID> --title "新しいページ名"

# Markdown ファイルから一括初期化
notion page create --parent <PARENT_PAGE_OR_DB_ID> --title "議事録" -f notes.md

# インライン Markdown 文字列から作成
notion page create --parent <PARENT_PAGE_OR_DB_ID> --title "タスク一覧" -c "## 今日のタスク\n- [ ] タスク1\n- [ ] タスク2"

# 標準入力からパイプして作成
cat draft.md | notion page create --parent <PARENT_PAGE_OR_DB_ID> --title "ドラフト" -f -
```

#### ページ Markdown の全体置換 (`update`)
```bash
# ファイルでページ本文を上書き
notion page update <PAGE_ID_OR_URL> -f updated.md

# パイプから上書き
echo "# タイトル\n本文内容" | notion page update <PAGE_ID_OR_URL>

# 子要素削除を許可して完全上書き
notion page update <PAGE_ID_OR_URL> -f clean.md --allow-delete
```

#### ページ末尾への Markdown 追記 (`append`)
```bash
# 末尾に追記
notion page append <PAGE_ID_OR_URL> -c "\n### 追記事項\n- 新しい知見を追加しました。"

# ファイルの内容を追記
notion page append <PAGE_ID_OR_URL> -f additional_notes.md
```

#### ページ内の文字列置換 (`replace`)
```bash
# 特定の文字列を安全に置換（既存ブロック構造を壊さない）
notion page replace <PAGE_ID_OR_URL> --old "旧バージョン 1.0" --new "新バージョン 2.0"

# 全一致箇所を置換
notion page replace <PAGE_ID_OR_URL> --old "TODO" --new "DONE" --all
```

#### ページタイトルの変更 (`set-title`)
```bash
notion page set-title <PAGE_ID_OR_URL> "新しいタイトル"
```

#### ページの削除・ゴミ箱移動 (`delete`)
```bash
notion page delete <PAGE_ID_OR_URL> --force
```

---

### 2. データベース操作 (`notion db`)

#### データベース情報 & カラム構造取得 (`get`)
```bash
notion db get <DB_ID_OR_URL>
```

#### データベースのアイテム一覧取得 (`query`)
```bash
# 最新 50 件を表示
notion db query <DB_ID_OR_URL>

# フィルター指定（JSON）
notion db query <DB_ID_OR_URL> --filter '{"property": "Severity", "select": {"equals": "Critical"}}'

# 件数制限と JSON 出力
notion db query <DB_ID_OR_URL> --limit 10 --json
```

#### データベースへの新規アイテム起票 (`add-item`)
```bash
# タイトルのみ
notion db add-item <DB_ID_OR_URL> --title "[Alert] CPU 高負荷検知"

# プロパティ付き（select や rich_text などを自動変換）
notion db add-item <DB_ID_OR_URL> \
  --title "[Alert] Keycloak 503 エラー" \
  --props '{"Severity": "Critical", "Service": "keycloak", "Status": "Open"}'
```

---

### 3. 全体検索 (`notion search`)

```bash
# キーワード検索
notion search "自宅ラボ"

# ページのみに絞り込み
notion search "Kubernetes" --type page

# データベースのみに絞り込み
notion search "Incident" --type database
```

---

## 🛠️ トラブルシューティング & Tips

- **デバッグログの出力**: `--debug` オプションを付与すると、HTTP リクエスト URL や送受信ボディが stderr に出力されます。
  ```bash
  notion --debug page get <PAGE_ID>
  ```
- **トークンの優先順位**:
  1. コマンドライン引数 `--token`
  2. 環境変数 `NOTION_API_KEY` または `NOTION_TOKEN`
  3. 設定ファイル `~/.config/notion/config.json`
