from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from gemini_client import GeminiClient

# FastAPI Application Setup
app = FastAPI(
    title="IF Blog Auto API",
    description="API for automated blog content generation",
    version="1.0.0"
)

# CORS Settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini Client
gemini_client = GeminiClient()

# Data Models
class GenerateRequest(BaseModel):
    topic: str
    target_keywords: Optional[str] = None
    content_type: Optional[str] = "article"

class ResearchRequest(BaseModel):
    topic: str

class WriteRequest(BaseModel):
    research_data: Dict[str, Any]

class ImageRequest(BaseModel):
    article_data: Dict[str, Any]

class SEORequest(BaseModel):
    article_data: Dict[str, Any]

class ReviewRequest(BaseModel):
    article_data: Dict[str, Any]

class PublishRequest(BaseModel):
    post_id: str

# Database path (JSON file for simplicity)
DB_PATH = Path(__file__).parent.parent.parent / "data" / "posts.json"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Helper Functions
def load_posts() -> List[Dict[str, Any]]:
    """Load posts from JSON database"""
    if not DB_PATH.exists():
        return []
    try:
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading posts: {e}")
        return []

def save_posts(posts: List[Dict[str, Any]]) -> bool:
    """Save posts to JSON database"""
    try:
        with open(DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving posts: {e}")
        return False

def create_post(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new post entry"""
    posts = load_posts()

    post = {
        "id": f"post_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "title": data.get("title", "Untitled"),
        "content": data.get("content", ""),
        "status": "draft",
        "created_at": datetime.now().isoformat(),
        "published_at": None,
        "views": 0,
        "metadata": data.get("metadata", {}),
        "seo_data": data.get("seo_data", {}),
        "images": data.get("images", []),
        "review_data": data.get("review_data", {})
    }

    posts.append(post)
    save_posts(posts)

    return post

def get_post_by_id(post_id: str) -> Optional[Dict[str, Any]]:
    """Get a post by ID"""
    posts = load_posts()
    for post in posts:
        if post.get("id") == post_id:
            return post
    return None

def update_post(post_id: str, updates: Dict[str, Any]) -> bool:
    """Update a post"""
    posts = load_posts()
    for i, post in enumerate(posts):
        if post.get("id") == post_id:
            posts[i].update(updates)
            return save_posts(posts)
    return False

def calculate_stats() -> Dict[str, Any]:
    """Calculate statistics from posts"""
    posts = load_posts()

    total_posts = len(posts)
    published_posts = len([p for p in posts if p.get("status") == "published"])
    draft_posts = len([p for p in posts if p.get("status") == "draft"])
    total_views = sum(p.get("views", 0) for p in posts)

    return {
        "total_posts": total_posts,
        "published_posts": published_posts,
        "draft_posts": draft_posts,
        "total_views": total_views
    }

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "IF Blog Auto API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/api/stats")
async def get_stats():
    """Get statistics"""
    try:
        stats = calculate_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/posts")
async def get_posts():
    """Get all posts"""
    try:
        posts = load_posts()
        # Sort by created_at descending
        posts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return JSONResponse(content=posts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/posts/{post_id}")
async def get_post(post_id: str):
    """Get a specific post"""
    post = get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return JSONResponse(content=post)

@app.post("/api/generate/research")
async def generate_research(request: ResearchRequest):
    """Generate research for a topic"""
    try:
        # Use GeminiClient to generate research
        research_prompt = f"""
        トピック「{request.topic}」について、以下の項目を徹底的にリサーチしてください：

        1. トピックの概要と重要性
        2. 主要なトレンドと最新情報
        3. ターゲット読者が知りたいこと
        4. よくある質問と回答
        5. 関連キーワードと検索意図
        6. 競合記事の分析
        7. 独自の切り口やアングル

        JSON形式で結果を返してください。
        """

        research_data = gemini_client.generate_text(research_prompt)

        return JSONResponse(content={
            "success": True,
            "topic": request.topic,
            "research_data": research_data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research generation failed: {str(e)}")

@app.post("/api/generate/write")
async def generate_write(request: WriteRequest):
    """Generate article content"""
    try:
        research_data = request.research_data

        write_prompt = f"""
        以下のリサーチデータに基づいて、SEOに最適化された高品質なブログ記事を執筆してください：

        {json.dumps(research_data, ensure_ascii=False, indent=2)}

        記事の要件：
        - タイトル（魅力的で検索に強い）
        - 導入文（読者を引き込む）
        - 見出し構成（H2, H3を適切に使用）
        - 本文（詳細で価値のある情報）
        - まとめ（行動を促す）
        - 文字数：3000文字以上

        Markdown形式で記事を返してください。
        """

        article_content = gemini_client.generate_text(write_prompt)

        # Create post entry
        post_data = {
            "title": "Generated Article",  # Extract from content
            "content": article_content,
            "metadata": {
                "research_data": research_data
            }
        }

        post = create_post(post_data)

        return JSONResponse(content={
            "success": True,
            "post_id": post["id"],
            "content": article_content,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Writing generation failed: {str(e)}")

@app.post("/api/generate/images")
async def generate_images(request: ImageRequest):
    """Generate images for article"""
    try:
        article_data = request.article_data

        # TODO: Implement actual image generation
        # For now, return placeholder data

        images = [
            {
                "type": "featured",
                "url": "/images/placeholder-featured.jpg",
                "alt": "Featured image",
                "width": 1200,
                "height": 630
            },
            {
                "type": "content",
                "url": "/images/placeholder-content-1.jpg",
                "alt": "Content image 1",
                "width": 800,
                "height": 600
            }
        ]

        return JSONResponse(content={
            "success": True,
            "images": images,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

@app.post("/api/generate/seo")
async def generate_seo(request: SEORequest):
    """Generate SEO optimization"""
    try:
        article_data = request.article_data

        seo_prompt = f"""
        以下の記事データに基づいて、SEO最適化を行ってください：

        {json.dumps(article_data, ensure_ascii=False, indent=2)}

        以下を生成してください：
        1. メタタイトル（60文字以内）
        2. メタディスクリプション（160文字以内）
        3. メタキーワード（10個程度）
        4. OGP設定
        5. 構造化データ（JSON-LD）
        6. 内部リンク提案
        7. 外部リンク提案

        JSON形式で返してください。
        """

        seo_data = gemini_client.generate_text(seo_prompt)

        return JSONResponse(content={
            "success": True,
            "seo_data": seo_data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SEO generation failed: {str(e)}")

@app.post("/api/generate/review")
async def generate_review(request: ReviewRequest):
    """Generate quality review"""
    try:
        article_data = request.article_data

        review_prompt = f"""
        以下の記事を品質レビューしてください：

        {json.dumps(article_data, ensure_ascii=False, indent=2)}

        以下の観点で評価してください（各項目10点満点）：
        1. コンテンツの質と独自性
        2. SEO最適化度
        3. 読みやすさ
        4. 構成の論理性
        5. 情報の正確性
        6. ビジュアルの適切性
        7. CTAの効果性

        改善提案も含めてJSON形式で返してください。
        """

        review_data = gemini_client.generate_text(review_prompt)

        return JSONResponse(content={
            "success": True,
            "review_data": review_data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review generation failed: {str(e)}")

@app.post("/api/posts/publish")
async def publish_post(request: PublishRequest):
    """Publish a post"""
    try:
        post = get_post_by_id(request.post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # Update post status
        updates = {
            "status": "published",
            "published_at": datetime.now().isoformat()
        }

        success = update_post(request.post_id, updates)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update post")

        return JSONResponse(content={
            "success": True,
            "post_id": request.post_id,
            "message": "Post published successfully",
            "timestamp": datetime.now().isoformat()
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publishing failed: {str(e)}")

@app.get("/api/posts/{post_id}/download")
async def download_post(post_id: str):
    """Download post as file"""
    post = get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Create temporary file
    temp_file = Path(f"/tmp/{post_id}.md")
    temp_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(f"# {post['title']}\n\n")
            f.write(f"{post['content']}\n")

        return FileResponse(
            temp_file,
            media_type='text/markdown',
            filename=f"{post['title']}.md"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: str):
    """Delete a post"""
    try:
        posts = load_posts()
        original_length = len(posts)
        posts = [p for p in posts if p.get("id") != post_id]

        if len(posts) == original_length:
            raise HTTPException(status_code=404, detail="Post not found")

        save_posts(posts)

        return JSONResponse(content={
            "success": True,
            "message": "Post deleted successfully",
            "timestamp": datetime.now().isoformat()
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "gemini_client": "initialized" if gemini_client else "not initialized"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
