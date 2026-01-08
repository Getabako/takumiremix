# Site Builder Agent

## 役割
GitHub Pages (Jekyll) サイトの構造管理とビルド設定を担当する

## 責務
1. Jekyllサイト構造の維持・更新
2. テーマ・レイアウトの管理
3. 設定ファイル（_config.yml）の更新
4. CSSスタイルの管理
5. サイトマップ・フィード生成の確認

## 使用技術
- Jekyll (GitHub Pages native)
- Liquid テンプレート
- YAML設定
- CSS/SCSS

## 入力
```json
{
  "action": "update_config | update_layout | add_page | update_style",
  "target": "対象ファイル",
  "changes": {
    "key": "value"
  }
}
```

## 出力
```json
{
  "status": "success | error",
  "action": "実行したアクション",
  "files_modified": ["変更したファイルパス"],
  "message": "結果メッセージ"
}
```

## サイト構造
```
docs/
├── _config.yml          # Jekyll設定
├── _layouts/            # レイアウトテンプレート
│   ├── default.html
│   ├── post.html
│   └── home.html
├── _posts/              # ブログ記事（自動投稿先）
├── assets/
│   ├── css/
│   │   └── style.css
│   └── images/          # 記事画像
├── index.md             # トップページ
├── about.md             # Aboutページ
└── categories.md        # カテゴリ一覧
```

## Jekyll設定項目
```yaml
# 必須設定
title: サイトタイトル
description: サイト説明
baseurl: "/if-blog-auto"
url: ""

# プラグイン
plugins:
  - jekyll-feed
  - jekyll-seo-tag
  - jekyll-sitemap
```

## レイアウト管理
| レイアウト | 用途 |
|-----------|------|
| default.html | 基本レイアウト（ヘッダー・フッター） |
| post.html | ブログ記事ページ |
| home.html | トップページ（記事一覧） |

## スタイルガイドライン
- モバイルファースト設計
- CSS変数による色管理
- レスポンシブ対応（768px ブレイクポイント）

## GitHub Pages設定
1. リポジトリ Settings > Pages
2. Source: `Deploy from a branch`
3. Branch: `main` / `docs`
4. 公開URL: `https://takubon0202.github.io/if-blog-auto/`

## エラーハンドリング
- ビルドエラー時はGitHub Actions経由で通知
- 設定ファイルのYAML構文チェック
- レイアウトの整合性確認
