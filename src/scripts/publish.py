#!/usr/bin/env python3
"""
GitHub Pages (Jekyll) 公開スクリプト

ブログ記事をGitHub Pagesに投稿します。
"""
import os
import re
import asyncio
import subprocess
import shutil
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, List
import unicodedata

# タイムゾーンユーティリティをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.timezone import now_jst, format_datetime_jst, format_date, get_timestamp_jst

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitHubPagesPublisher:
    """GitHub Pages投稿クラス"""

    def __init__(self):
        self.repo_root = Path(__file__).parent.parent.parent
        self.docs_dir = self.repo_root / "docs"
        self.posts_dir = self.docs_dir / "_posts"
        self.images_dir = self.docs_dir / "assets" / "images"
        self.videos_dir = self.docs_dir / "assets" / "videos"
        self.base_url = "https://takubon0202.github.io/if-blog-auto"

        # ディレクトリ作成
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)

    def slugify(self, text: str) -> str:
        """URLスラッグを生成"""
        # 正規化
        text = unicodedata.normalize('NFKC', text)
        # 英数字とハイフン以外を削除
        text = re.sub(r'[^\w\s-]', '', text.lower())
        # スペースをハイフンに
        text = re.sub(r'[-\s]+', '-', text).strip('-')
        # 50文字に制限
        return text[:50] or 'untitled'

    def generate_front_matter(
        self,
        title: str,
        description: str,
        categories: List[str],
        tags: Optional[List[str]] = None,
        featured_image: Optional[str] = None,
        author: str = "AI Blog Generator"
    ) -> str:
        """Jekyll用Front Matterを生成（日本時間）"""
        date_str = format_datetime_jst()  # JST timezone-aware

        lines = [
            "---",
            "layout: post",
            f'title: "{title}"',
            f'description: "{description}"',
            f"date: {date_str}",
            f"categories: [{', '.join(categories)}]",
        ]

        if tags:
            lines.append(f"tags: [{', '.join(tags)}]")

        lines.append(f'author: "{author}"')

        if featured_image:
            lines.append(f'featured_image: "{featured_image}"')

        lines.append("---")
        lines.append("")

        return "\n".join(lines)

    def copy_images(self, article: Dict, slug: str) -> Optional[str]:
        """画像をdocs/assets/imagesにコピー（検証付き）"""
        images = article.get("images", {})
        hero = images.get("hero", {})
        hero_images = hero.get("images", [])

        if not hero_images:
            logger.info("No hero images available")
            return None

        # 最初の画像をコピー
        first_image = hero_images[0]
        src_path = Path(first_image.get("file_path", ""))

        if not src_path.exists():
            logger.warning(f"Image not found: {src_path}")
            return None

        # 画像サイズを検証（最低10KB以上で正常な画像と判断）
        MIN_IMAGE_SIZE = 10 * 1024  # 10KB
        file_size = src_path.stat().st_size
        if file_size < MIN_IMAGE_SIZE:
            logger.warning(f"Image too small ({file_size} bytes), likely corrupted: {src_path}")
            return None

        # PNGヘッダーの検証
        with open(src_path, 'rb') as f:
            header = f.read(8)
            png_signature = b'\x89PNG\r\n\x1a\n'
            if header != png_signature:
                logger.warning(f"Invalid PNG file (wrong header): {src_path}")
                return None

        # コピー先
        filename = f"{slug}_{src_path.name}"
        dest_path = self.images_dir / filename

        shutil.copy(src_path, dest_path)
        logger.info(f"Copied valid image ({file_size} bytes): {dest_path}")

        # Jekyll用の相対パス（relative_urlフィルタで変換されるためbaseurl不要）
        return f"/assets/images/{filename}"

    def find_existing_videos(self, topic: str = None) -> Optional[Dict]:
        """
        output/videos/から既存の動画を探す（フォールバック用）

        Args:
            topic: トピックID（指定された場合はそのトピックの動画を優先）

        Returns:
            見つかった動画の情報
        """
        output_videos_dir = self.repo_root / "output" / "videos"
        if not output_videos_dir.exists():
            return None

        # 最新の動画ファイルを探す
        video_files = list(output_videos_dir.glob("blog_video_*.mp4"))
        if not video_files:
            video_files = list(output_videos_dir.glob("slide_video_*.mp4"))
        if not video_files:
            return None

        # トピック指定がある場合はフィルタリング
        if topic:
            topic_videos = [v for v in video_files if topic in v.name]
            if topic_videos:
                video_files = topic_videos

        # 最新のものを選択（更新日時でソート）
        video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        found_videos = {}
        for video_file in video_files:
            if "short" in video_file.name and "short" not in found_videos:
                found_videos["short"] = {
                    "path": str(video_file),
                    "duration": 15,
                    "resolution": "1080x1920"
                }
            elif "short" not in video_file.name and "standard" not in found_videos:
                found_videos["standard"] = {
                    "path": str(video_file),
                    "duration": 30,
                    "resolution": "1920x1080"
                }

            if "standard" in found_videos:
                break  # 標準動画が見つかれば十分

        if found_videos:
            logger.info(f"Found existing videos: {list(found_videos.keys())}")

        return found_videos if found_videos else None

    def copy_videos(self, article: Dict, slug: str) -> Optional[Dict]:
        """動画をdocs/assets/videosにコピー（フォールバック付き）"""
        videos = article.get("videos", {})

        # 動画が渡されなかった場合、既存の動画を探す
        if not videos:
            logger.info("No videos in article data, searching for existing videos...")
            topic = article.get("topic") or article.get("topic_id")
            videos = self.find_existing_videos(topic)
            if videos:
                logger.info(f"Using existing videos for topic '{topic}': {list(videos.keys())}")

        if not videos:
            logger.info("No videos available (even after fallback)")
            return None

        copied_videos = {}

        for video_type, video_info in videos.items():
            src_path = Path(video_info.get("path", ""))

            if not src_path.exists():
                logger.warning(f"Video not found: {src_path}")
                continue

            # ファイルサイズ検証（最低100KB以上）
            MIN_VIDEO_SIZE = 100 * 1024  # 100KB
            file_size = src_path.stat().st_size
            if file_size < MIN_VIDEO_SIZE:
                logger.warning(f"Video too small ({file_size} bytes): {src_path}")
                continue

            # コピー先
            filename = f"{slug}_{video_type}_{src_path.name}"
            dest_path = self.videos_dir / filename

            shutil.copy(src_path, dest_path)
            logger.info(f"Copied video ({file_size} bytes): {dest_path}")

            copied_videos[video_type] = {
                "path": f"/assets/videos/{filename}",
                "duration": video_info.get("duration", 30),
                "resolution": video_info.get("resolution", "1920x1080")
            }

        return copied_videos if copied_videos else None

    def embed_video_section(self, videos: Dict) -> str:
        """動画セクションのHTMLを生成"""
        if not videos:
            return ""

        sections = []
        sections.append("\n\n---\n\n## 動画で見る\n")

        # 標準動画
        if "standard" in videos:
            video = videos["standard"]
            video_path = video["path"]
            sections.append(f"""
<div class="video-container">
<video controls width="100%" preload="metadata">
  <source src="{{{{ '{video_path}' | relative_url }}}}" type="video/mp4">
  お使いのブラウザは動画再生に対応していません。
</video>
<p class="video-caption">記事の要約動画（{video["duration"]}秒）</p>
</div>
""")

        # ショート動画
        if "short" in videos:
            video = videos["short"]
            video_path = video["path"]
            sections.append(f"""
<div class="video-container video-short">
<video controls width="320" preload="metadata">
  <source src="{{{{ '{video_path}' | relative_url }}}}" type="video/mp4">
  お使いのブラウザは動画再生に対応していません。
</video>
<p class="video-caption">ショート動画（{video["duration"]}秒・縦型）</p>
</div>
""")

        return "\n".join(sections)

    def create_post_file(
        self,
        title: str,
        content: str,
        description: str,
        categories: List[str],
        tags: Optional[List[str]] = None,
        featured_image: Optional[str] = None,
        video_section: Optional[str] = None
    ) -> Path:
        """記事ファイルを作成（日本時間）"""
        slug = self.slugify(title)
        filename = f"{format_date()}-{slug}.md"  # JST date
        filepath = self.posts_dir / filename

        # Front Matter生成
        front_matter = self.generate_front_matter(
            title=title,
            description=description,
            categories=categories,
            tags=tags,
            featured_image=featured_image
        )

        # ファイル書き込み（動画セクションを末尾に追加）
        full_content = front_matter + content
        if video_section:
            full_content += video_section
        filepath.write_text(full_content, encoding='utf-8')
        logger.info(f"Created post: {filepath}")

        return filepath

    def is_ci_environment(self) -> bool:
        """CI環境かどうかを判定"""
        # GitHub Actions, GitLab CI, CircleCI など
        ci_vars = ['GITHUB_ACTIONS', 'CI', 'GITLAB_CI', 'CIRCLECI', 'JENKINS_URL']
        return any(os.environ.get(var) for var in ci_vars)

    def git_commit_and_push(self, message: str) -> bool:
        """Git操作（add, commit, push）"""
        # CI環境ではワークフローがgit操作を行うためスキップ
        if self.is_ci_environment():
            logger.info("CI environment detected - skipping git operations (handled by workflow)")
            return True

        try:
            # Git add
            subprocess.run(
                ["git", "add", "docs/"],
                cwd=self.repo_root,
                check=True,
                capture_output=True
            )

            # Git commit
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_root,
                check=True,
                capture_output=True
            )

            # Git push
            subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=self.repo_root,
                check=True,
                capture_output=True
            )

            logger.info("Successfully pushed to GitHub")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {e}")
            logger.error(f"Stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
            return False

    def get_public_url(self, title: str) -> str:
        """公開URLを生成（日本時間）"""
        slug = self.slugify(title)
        date_path = format_date(fmt="%Y/%m/%d")  # JST date
        return f"{self.base_url}/{date_path}/{slug}/"


async def publish_to_github_pages(article: Dict) -> Dict:
    """
    記事をGitHub Pagesに投稿

    Args:
        article: 記事データ
            - title: タイトル
            - content: 本文（Markdown）
            - description: 概要
            - categories: カテゴリリスト
            - tags: タグリスト（オプション）
            - images: 画像データ（オプション）
            - videos: 動画データ（オプション）

    Returns:
        投稿結果
    """
    publisher = GitHubPagesPublisher()

    title = article.get("title", "Untitled")
    content = article.get("content", "")
    description = article.get("description", "")[:120]  # 120文字制限
    categories = article.get("categories", ["未分類"])
    tags = article.get("tags", [])

    # タイトルが長すぎる場合は切り詰め
    if len(title) > 60:
        title = title[:57] + "..."

    try:
        # 画像コピー
        slug = publisher.slugify(title)
        featured_image = publisher.copy_images(article, slug)

        # 動画コピー
        copied_videos = publisher.copy_videos(article, slug)
        video_section = publisher.embed_video_section(copied_videos)
        if copied_videos:
            logger.info(f"Videos embedded: {list(copied_videos.keys())}")

        # 記事ファイル作成
        post_path = publisher.create_post_file(
            title=title,
            content=content,
            description=description,
            categories=categories,
            tags=tags,
            featured_image=featured_image,
            video_section=video_section
        )

        # Git操作
        commit_message = f"Add blog post: {title}"
        git_success = publisher.git_commit_and_push(commit_message)

        if not git_success:
            return {
                "status": "error",
                "message": "Git push failed",
                "post_path": str(post_path)
            }

        # 公開URL
        public_url = publisher.get_public_url(title)

        return {
            "status": "success",
            "post_path": str(post_path),
            "public_url": public_url,
            "message": f"Successfully published: {title}"
        }

    except Exception as e:
        logger.error(f"Publish failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# 後方互換性のためWordPress関数を残す（無効化）
async def publish_to_wordpress(article: dict) -> dict:
    """WordPress投稿（非推奨）"""
    logger.warning("WordPress publishing is disabled. Use GitHub Pages instead.")
    return await publish_to_github_pages(article)


if __name__ == "__main__":
    import json

    # テスト用記事
    test_article = {
        "title": "テスト投稿",
        "content": "# テスト\n\nこれはテスト投稿です。\n\n## セクション1\n\n本文...",
        "description": "テスト投稿の説明文です。",
        "categories": ["テスト"],
        "tags": ["テスト", "GitHub Pages"]
    }

    result = asyncio.run(publish_to_github_pages(test_article))
    print(json.dumps(result, ensure_ascii=False, indent=2))
