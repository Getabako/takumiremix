# Jekyll Content Skill

## 概要
Jekyll形式のブログコンテンツを生成・管理するスキル

## 使用技術
- Jekyll / Liquid テンプレート
- YAML Front Matter
- Markdown
- Kramdown (GitHub Pages default)

## コンテンツ構造

### 記事ファイル形式
```markdown
---
layout: post
title: "記事タイトル"
description: "メタディスクリプション"
date: 2024-12-29 10:00:00 +0900
categories: [カテゴリ1, カテゴリ2]
tags: [タグ1, タグ2, タグ3]
author: "AI Blog Generator"
featured_image: "/assets/images/hero.png"
---

# 記事タイトル

導入文...

## セクション1

本文...

## まとめ

結論...
```

### Front Matter必須項目
| 項目 | 型 | 説明 |
|------|-----|------|
| layout | string | レイアウト名（post） |
| title | string | 記事タイトル（60文字以内推奨） |
| description | string | メタディスクリプション（120文字以内） |
| date | datetime | 公開日時（ISO 8601形式） |
| categories | array | カテゴリ（1-3個推奨） |

### Front Matter任意項目
| 項目 | 型 | 説明 |
|------|-----|------|
| tags | array | タグ（3-5個推奨） |
| author | string | 著者名 |
| featured_image | string | アイキャッチ画像パス |
| published | boolean | 公開状態（デフォルト: true） |

## 記事テンプレート生成
```python
from datetime import datetime
from typing import List, Optional
import yaml

def generate_jekyll_post(
    title: str,
    content: str,
    description: str,
    categories: List[str],
    tags: Optional[List[str]] = None,
    featured_image: Optional[str] = None
) -> str:
    """Jekyll形式の記事を生成"""

    front_matter = {
        "layout": "post",
        "title": title,
        "description": description,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S +0900"),
        "categories": categories,
        "author": "AI Blog Generator"
    }

    if tags:
        front_matter["tags"] = tags

    if featured_image:
        front_matter["featured_image"] = featured_image

    # YAML形式に変換
    fm_yaml = yaml.dump(
        front_matter,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False
    )

    return f"---\n{fm_yaml}---\n\n{content}"
```

## Markdown拡張（Kramdown）

### テーブル
```markdown
| ヘッダー1 | ヘッダー2 |
|-----------|-----------|
| セル1     | セル2     |
```

### コードブロック
````markdown
```python
def hello():
    print("Hello, World!")
```
````

### 注釈
```markdown
> **注意**: 重要な情報
{: .note}
```

### 目次自動生成
```markdown
* TOC
{:toc}
```

## カテゴリマッピング
```python
CATEGORY_MAP = {
    "psychology": "心理学・メンタルヘルス",
    "education": "教育・学習科学",
    "startup": "起業家育成・スタートアップ",
    "investment": "投資教育・金融リテラシー",
    "ai_tools": "AIツール・技術動向",
    "school_refusal": "不登校支援",
    "neurodiversity": "発達障害・ニューロダイバーシティ"
}
```

## SEO最適化

### タイトル生成
```python
def optimize_title(title: str) -> str:
    """SEO最適化されたタイトルを生成"""
    # 60文字以内に収める
    if len(title) > 60:
        title = title[:57] + "..."
    return title
```

### メタディスクリプション
```python
def generate_description(content: str) -> str:
    """コンテンツからメタディスクリプションを生成"""
    # 最初の段落から抽出
    # 120文字以内に収める
    desc = extract_first_paragraph(content)
    if len(desc) > 120:
        desc = desc[:117] + "..."
    return desc
```

## 画像パス変換
```python
def convert_image_path(local_path: str, post_slug: str) -> str:
    """ローカルパスをJekyll用パスに変換"""
    filename = Path(local_path).name
    return f"/if-blog-auto/assets/images/{post_slug}_{filename}"
```

## バリデーション
```python
def validate_post(post_content: str) -> List[str]:
    """記事の妥当性をチェック"""
    errors = []

    # Front Matterの存在確認
    if not post_content.startswith("---"):
        errors.append("Front Matterが見つかりません")

    # 必須項目の確認
    fm = extract_front_matter(post_content)
    required = ["layout", "title", "date"]
    for key in required:
        if key not in fm:
            errors.append(f"必須項目がありません: {key}")

    # タイトル長チェック
    if len(fm.get("title", "")) > 60:
        errors.append("タイトルが60文字を超えています")

    return errors
```

## 記事一覧取得
```python
def list_posts(posts_dir: Path) -> List[dict]:
    """投稿済み記事の一覧を取得"""
    posts = []
    for file in posts_dir.glob("*.md"):
        content = file.read_text(encoding='utf-8')
        fm = extract_front_matter(content)
        posts.append({
            "filename": file.name,
            "title": fm.get("title"),
            "date": fm.get("date"),
            "categories": fm.get("categories", [])
        })
    return sorted(posts, key=lambda x: x["date"], reverse=True)
```
