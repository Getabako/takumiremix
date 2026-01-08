# CMS Integration Skill

## 概要
ブログ記事をCMS（GitHub Pages）に投稿するスキル

## 対応プラットフォーム

### Primary: GitHub Pages (Jekyll)
- **状態**: アクティブ
- **URL**: https://takubon0202.github.io/if-blog-auto/
- **方式**: Git push → 自動ビルド&デプロイ

### Secondary: WordPress (無効)
- **状態**: 無効化
- **理由**: WordPressを使用しないため

## GitHub Pages投稿フロー

```
記事データ受け取り
    ↓
Jekyll形式に変換
    ↓
画像をassets/imagesにコピー
    ↓
_posts/にMarkdownファイル作成
    ↓
git add → commit → push
    ↓
GitHub Actionsが自動ビルド
    ↓
公開URL生成
```

## 使用方法

### Python API
```python
from scripts.publish import publish_to_github_pages

article = {
    "title": "記事タイトル",
    "content": "記事本文（Markdown）",
    "description": "メタディスクリプション",
    "categories": ["カテゴリ"],
    "tags": ["タグ1", "タグ2"],
    "images": {
        "hero": {
            "images": [{"file_path": "/path/to/image.png"}]
        }
    }
}

result = await publish_to_github_pages(article)
# {
#     "status": "success",
#     "post_path": "docs/_posts/2024-12-29-title.md",
#     "public_url": "https://takubon0202.github.io/if-blog-auto/2024/12/29/title/"
# }
```

### コマンドライン
```bash
cd src/scripts
python publish.py
```

## ファイル構造

### 記事ファイル
```
docs/_posts/YYYY-MM-DD-{slug}.md
```

### 画像ファイル
```
docs/assets/images/{slug}_{filename}.png
```

## Front Matter自動生成
```yaml
---
layout: post
title: "記事タイトル"
description: "メタディスクリプション"
date: 2024-12-29 10:00:00 +0900
categories: [カテゴリ]
tags: [タグ1, タグ2]
author: "AI Blog Generator"
featured_image: "/if-blog-auto/assets/images/slug_hero.png"
---
```

## Git操作

### 自動コミット
```bash
git add docs/
git commit -m "Add blog post: {title}"
git push origin main
```

### コミットメッセージ規則
- 新規投稿: `Add blog post: {title}`
- 更新: `Update blog post: {title}`
- 画像追加: `Add images for: {title}`

## GitHub Pages設定

### リポジトリ設定
1. Settings > Pages
2. Source: Deploy from a branch
3. Branch: main
4. Folder: /docs

### 公開URL
```
https://takubon0202.github.io/if-blog-auto/
```

## エラーハンドリング

| エラー | 対処 |
|--------|------|
| Git push失敗 | 認証確認、リトライ |
| ファイル名重複 | タイムスタンプ追加 |
| 画像なし | featured_image省略 |
| 長いタイトル | 60文字で切り詰め |
| 長い説明 | 120文字で切り詰め |

## デプロイ確認

### GitHub Actions
```bash
# 最新のビルド状態確認
gh run list --workflow=pages-build-deployment --limit=1
```

### 手動確認
1. GitHubリポジトリのActionsタブを確認
2. pages-build-deploymentワークフローの状態確認
3. 公開URLにアクセスして記事を確認

## 制限事項
- リポジトリ容量: 1GB以下推奨
- 単一ファイル: 100MB以下
- ビルド時間: 10分以内
- デプロイ頻度: 10回/時間

## 関連スキル
- `github-pages.md`: GitHub Pages詳細操作
- `jekyll-content.md`: Jekyllコンテンツ生成

## 関連エージェント
- `site-builder-agent.md`: サイト構造管理
- `blog-publisher-agent.md`: 記事投稿処理
