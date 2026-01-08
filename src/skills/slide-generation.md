# Slide Generation Skill

## 概要
ブログ記事からMarp互換スライドを自動生成するスキル。

## 必要パッケージ

```bash
# Marp CLI
npm install -g @marp-team/marp-cli

# PDF to Image (Python)
pip install pdf2image pillow

# システム依存 (Ubuntu/Debian)
sudo apt-get install poppler-utils
```

## API設定

### スライドコンテンツ生成
```python
from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)

# スライド構成生成
response = client.models.generate_content(
    model="gemini-3-pro-preview",
    contents=slide_prompt,
    config=types.GenerateContentConfig(
        temperature=0.7,
        top_p=0.9
    )
)
```

### スライド用画像生成
```python
# 各スライドの画像生成（16:9必須）
response = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents=image_prompt,
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        temperature=1.0
    )
)
```

## Marpスライド構造

```python
MARP_TEMPLATE = """---
marp: true
theme: default
paginate: true
backgroundColor: {bg_color}
color: {text_color}
style: |
  section {{
    font-family: 'Noto Sans JP', 'Hiragino Sans', sans-serif;
    background: linear-gradient(135deg, {bg_color} 0%, {bg_secondary} 100%);
  }}
  h1 {{
    color: {primary_color};
    font-size: 56px;
    font-weight: 800;
  }}
  h2 {{
    color: {secondary_color};
    font-size: 40px;
  }}
  ul {{
    font-size: 28px;
    line-height: 1.8;
  }}
  p {{
    font-size: 24px;
    line-height: 1.6;
  }}
---

{slides_content}
"""
```

## スライドタイプ別テンプレート

### タイトルスライド
```markdown
<!-- _class: lead -->

# {title}

## {subtitle}

![bg right:45% contain]({image_path})

**{author_name}** | {date}
```

### コンテンツスライド
```markdown
# {heading}

![bg left:40%]({image_path})

- {point_1}
- {point_2}
- {point_3}
```

### まとめスライド
```markdown
<!-- _class: lead -->

# まとめ

{key_takeaways}

![bg opacity:0.3]({image_path})
```

## PDF変換

```python
import subprocess

def export_to_pdf(markdown_path: str, output_path: str) -> bool:
    """Marp CLIでPDFエクスポート"""
    cmd = [
        "npx", "@marp-team/marp-cli",
        markdown_path,
        "--pdf",
        "--allow-local-files",
        "-o", output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0
```

## PDF→画像変換

```python
from pdf2image import convert_from_path

def pdf_to_images(pdf_path: str, output_dir: str) -> list[str]:
    """PDFを個別PNG画像に変換"""
    images = convert_from_path(
        pdf_path,
        dpi=150,  # 1920x1080相当
        fmt="png"
    )

    image_paths = []
    for i, image in enumerate(images):
        path = f"{output_dir}/slide_{i+1:02d}.png"
        image.save(path, "PNG")
        image_paths.append(path)

    return image_paths
```

## 品質チェック

```python
def validate_slides(slides: list) -> dict:
    """スライド品質を検証（3倍厳格）"""
    score = 100
    issues = []

    # スライド枚数チェック
    if not (10 <= len(slides) <= 15):
        score -= 20
        issues.append(f"スライド枚数が範囲外: {len(slides)}")

    # 各スライドのテキスト量チェック
    for i, slide in enumerate(slides):
        text_length = len(slide.get("text", ""))
        if text_length > 150:
            score -= 5
            issues.append(f"スライド{i+1}: テキスト過多 ({text_length}文字)")

    # 画像存在チェック
    for i, slide in enumerate(slides):
        if not slide.get("image_path"):
            score -= 10
            issues.append(f"スライド{i+1}: 画像なし")

    return {
        "score": max(0, score),
        "passed": score >= 95,
        "issues": issues
    }
```

## 出力形式

```python
{
    "status": "success",
    "markdown_path": "output/slides/20250106_ai_tools.md",
    "pdf_path": "output/slides/20250106_ai_tools.pdf",
    "slide_images": [
        "output/slides/images/slide_01.png",
        "output/slides/images/slide_02.png",
        # ...
    ],
    "slide_count": 12,
    "quality_score": 98,
    "generated_at": "2025-01-06T15:30:00+09:00"
}
```
