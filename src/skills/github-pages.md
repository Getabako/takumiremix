# GitHub Pages Skill

## 概要
GitHub Pagesへの記事投稿とサイト管理スキル

## 使用技術
- Git / GitHub CLI
- Jekyll (GitHub Pages native)
- GitHub Actions

## サイト情報
```yaml
repository: takubon0202/if-blog-auto
branch: main
source_dir: docs/
public_url: https://takubon0202.github.io/if-blog-auto/
```

## 主要操作

### 1. 記事投稿
```python
import subprocess
from pathlib import Path
from datetime import datetime

def publish_post(title: str, content: str, metadata: dict) -> str:
    """記事をGitHub Pagesに投稿"""
    docs_dir = Path("docs")
    posts_dir = docs_dir / "_posts"

    # ファイル名生成
    date = datetime.now()
    slug = slugify(title)
    filename = f"{date.strftime('%Y-%m-%d')}-{slug}.md"
    filepath = posts_dir / filename

    # Front Matter + コンテンツ
    post_content = generate_front_matter(title, metadata) + content

    # ファイル書き込み
    filepath.write_text(post_content, encoding='utf-8')

    # Git操作
    subprocess.run(["git", "add", str(filepath)])
    subprocess.run(["git", "commit", "-m", f"Add post: {title}"])
    subprocess.run(["git", "push", "origin", "main"])

    return f"https://takubon0202.github.io/if-blog-auto/{date.strftime('%Y/%m/%d')}/{slug}/"
```

### 2. 画像アップロード
```python
def upload_image(image_path: str, post_slug: str) -> str:
    """画像をGitHub Pagesにアップロード"""
    images_dir = Path("docs/assets/images")
    images_dir.mkdir(parents=True, exist_ok=True)

    # ファイルコピー
    filename = f"{post_slug}_{Path(image_path).name}"
    dest_path = images_dir / filename
    shutil.copy(image_path, dest_path)

    # 相対URL
    return f"/if-blog-auto/assets/images/{filename}"
```

### 3. サイト設定更新
```python
def update_config(key: str, value: any) -> None:
    """_config.ymlを更新"""
    config_path = Path("docs/_config.yml")
    config = yaml.safe_load(config_path.read_text())
    config[key] = value
    config_path.write_text(yaml.dump(config, allow_unicode=True))
```

## Front Matter生成
```python
def generate_front_matter(title: str, metadata: dict) -> str:
    """Jekyll用Front Matterを生成"""
    fm = {
        "layout": "post",
        "title": title,
        "description": metadata.get("description", ""),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S +0900"),
        "categories": metadata.get("categories", []),
        "tags": metadata.get("tags", []),
        "author": metadata.get("author", "AI Blog Generator"),
    }

    if metadata.get("featured_image"):
        fm["featured_image"] = metadata["featured_image"]

    return f"---\n{yaml.dump(fm, allow_unicode=True, default_flow_style=False)}---\n\n"
```

## スラッグ生成
```python
import re
import unicodedata

def slugify(text: str) -> str:
    """URLスラッグを生成"""
    # 日本語をローマ字に変換（簡易版）
    # 実際にはpykakasiなどを使用
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text).strip('-')
    return text[:50] or 'untitled'
```

## GitHub CLI操作
```bash
# リポジトリ情報確認
gh repo view takubon0202/if-blog-auto

# Pages状態確認
gh api repos/takubon0202/if-blog-auto/pages

# 最新のデプロイ確認
gh run list --workflow=pages-build-deployment --limit=1
```

## GitHub Actions連携
```yaml
# .github/workflows/deploy-pages.yml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]
    paths:
      - 'docs/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Pages
        uses: actions/configure-pages@v4
      - name: Build with Jekyll
        uses: actions/jekyll-build-pages@v1
        with:
          source: ./docs
          destination: ./_site
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
      - name: Deploy to GitHub Pages
        uses: actions/deploy-pages@v4
```

## エラーハンドリング
| エラー | 対処 |
|--------|------|
| Push権限エラー | トークン確認・再認証 |
| ビルドエラー | Front Matter構文チェック |
| 画像サイズ超過 | 圧縮処理を適用 |
| 同名ファイル | タイムスタンプ追加 |

## 制限事項
- リポジトリ容量: 1GB以下推奨
- 単一ファイル: 100MB以下
- ビルド時間: 10分以内
- デプロイ頻度: 10回/時間
