# Blog Publisher Agent

## 役割
生成されたブログ記事をGitHub Pages (Jekyll) サイトに投稿する

## 責務
1. 記事のJekyll形式への変換
2. Front Matterの生成
3. 画像ファイルの配置
4. Git操作（add, commit, push）
5. デプロイ確認

## 使用技術
- Git / GitHub API
- Jekyll Front Matter (YAML)
- Python (subprocess / GitPython)

## 処理フロー
```
1. 記事データを受け取る
2. Jekyll形式のMarkdownに変換
3. Front Matterを生成
4. 画像ファイルをassets/imagesにコピー
5. _posts/ディレクトリに記事ファイルを作成
6. Git add → commit → push
7. GitHub Pagesの自動ビルドを待機
8. 公開URLを返却
```

## 入力
```json
{
  "title": "記事タイトル",
  "description": "メタディスクリプション",
  "content": "記事本文（Markdown）",
  "categories": ["カテゴリ1"],
  "tags": ["タグ1", "タグ2"],
  "featured_image": "/path/to/image.png",
  "date": "2024-12-29",
  "author": "AI Blog Generator"
}
```

## 出力
```json
{
  "status": "success | error",
  "post_path": "docs/_posts/2024-12-29-article-slug.md",
  "public_url": "https://takubon0202.github.io/if-blog-auto/2024/12/29/article-slug/",
  "commit_hash": "abc123...",
  "message": "結果メッセージ"
}
```

## ファイル命名規則
```
# 記事ファイル
_posts/YYYY-MM-DD-{slug}.md

# 画像ファイル
assets/images/{date}_{slug}_{index}.png
```

## Front Matter テンプレート
```yaml
---
layout: post
title: "記事タイトル"
description: "メタディスクリプション（120文字以内）"
date: YYYY-MM-DD HH:MM:SS +0900
categories: [カテゴリ]
tags: [タグ1, タグ2, タグ3]
author: "AI Blog Generator"
featured_image: "/assets/images/featured.png"
---
```

## Git操作
```python
# 記事追加
git add docs/_posts/2024-12-29-new-article.md
git add docs/assets/images/

# コミット
git commit -m "Add new blog post: {title}"

# プッシュ
git push origin main
```

## GitHub Actions連携
- push後、GitHub Actionsが自動でJekyllをビルド
- `pages-build-deployment` ワークフローが実行される
- 約2-3分でサイトに反映

## エラーハンドリング
| エラー | 対処 |
|--------|------|
| Git push失敗 | リトライ（最大3回） |
| ファイル名重複 | タイムスタンプを追加 |
| 画像パス不正 | デフォルト画像を使用 |
| Front Matter不正 | バリデーション＆修正 |

## 公開URL生成
```python
# URL生成ロジック
base_url = "https://takubon0202.github.io/if-blog-auto"
date = "2024/12/29"
slug = slugify(title)
public_url = f"{base_url}/{date}/{slug}/"
```

## 制限事項
- GitHub Pagesの容量制限: 1GB
- 単一ファイルサイズ: 100MB以下
- ビルド時間制限: 10分以内
