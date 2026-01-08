#!/usr/bin/env python3
"""
品質評価システム - 3倍厳格評価

ブログ記事、スライド、動画の品質を厳格に評価し、
95%以上の合格ラインを確保するためのシステム。

使用方法:
    from quality_evaluator import QualityEvaluator
    evaluator = QualityEvaluator()
    result = evaluator.evaluate_all(article, slides, video)
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.gemini_client import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QualityResult:
    """品質評価結果"""
    category: str
    score: float
    max_score: float
    passed: bool
    issues: List[str]
    recommendations: List[str]


class QualityEvaluator:
    """品質評価クラス（高品質保証）"""

    # 合格ライン（97%以上 - 最高品質を保証）
    PASS_THRESHOLD = 0.97

    # 各評価項目の重み（合計100）
    WEIGHTS = {
        # ブログ記事評価（50点）- 2倍品質対応
        "article_length": 10,       # 20,000文字以上
        "article_structure": 10,    # 導入→本論→結論の構成（15セクション以上）
        "article_sources": 8,       # 情報ソースの品質（10個以上）
        "article_seo": 6,           # SEO最適化
        "article_readability": 8,   # 読みやすさと没入感
        "article_no_emoji": 4,      # 絵文字禁止遵守
        "article_engagement": 4,    # 読者エンゲージメント要素

        # スライド評価（30点）
        "slide_count": 5,           # 10-15枚
        "slide_text_length": 5,     # 1枚100文字以内
        "slide_images": 5,          # 全スライドに画像
        "slide_structure": 5,       # 論理的構成
        "slide_design": 5,          # デザイン統一性
        "slide_marp_compat": 5,     # Marp互換性

        # 動画評価（30点）
        "video_resolution": 5,      # 1920x1080
        "video_audio": 5,           # 音声品質
        "video_timing": 5,          # タイミング同期
        "video_transitions": 5,     # トランジション品質
        "video_file_size": 5,       # ファイルサイズ適正
        "video_no_errors": 5,       # エラーなし
    }

    def __init__(self):
        self.gemini_client = None

    def _get_gemini_client(self) -> GeminiClient:
        """GeminiClientを取得"""
        if self.gemini_client is None:
            self.gemini_client = GeminiClient()
        return self.gemini_client

    def evaluate_article(self, article: Dict) -> QualityResult:
        """
        ブログ記事の品質を評価（5倍厳格・エンゲージメント重視）

        Args:
            article: 記事データ
                - title: タイトル
                - content: 本文
                - word_count: 文字数
                - seo_score: SEOスコア

        Returns:
            QualityResult: 評価結果
        """
        score = 0
        max_score = 50  # 50点満点に変更
        issues = []
        recommendations = []

        content = article.get("content", "")
        word_count = article.get("word_count", len(content))

        # 文字数の最小要件（15,000文字未満は強制不合格フラグ）
        critical_length_failure = word_count < 15000

        # 1. 文字数チェック（20,000文字以上）
        if word_count >= 20000:
            score += self.WEIGHTS["article_length"]
        elif word_count >= 15000:
            score += self.WEIGHTS["article_length"] * 0.7
            issues.append(f"文字数が目標未達: {word_count}文字（目標20,000+）")
        elif word_count >= 10000:
            score += self.WEIGHTS["article_length"] * 0.4
            issues.append(f"[重要] 文字数が不足: {word_count}文字（最低15,000+必須）")
            recommendations.append("記事の内容を大幅に拡充してください（最低15,000文字以上）")
        elif word_count >= 5000:
            score += self.WEIGHTS["article_length"] * 0.2
            issues.append(f"[致命的] 文字数が大幅に不足: {word_count}文字")
            recommendations.append("記事の内容を大幅に拡充してください（目標20,000文字以上）")
        else:
            issues.append(f"[致命的] 文字数が著しく不足: {word_count}文字")
            recommendations.append("記事の内容を大幅に拡充してください（目標20,000文字以上）")

        # 2. 構成チェック（導入→本論→結論、12セクション以上）
        has_intro = "はじめに" in content or "導入" in content or content.startswith("#")
        section_count = content.count("## ")
        has_conclusion = "まとめ" in content or "結論" in content or "おわりに" in content
        has_qa = "Q&A" in content or "よくある質問" in content or "FAQ" in content

        if has_intro and section_count >= 12 and has_conclusion:
            score += self.WEIGHTS["article_structure"]
        elif has_intro and section_count >= 8 and has_conclusion:
            score += self.WEIGHTS["article_structure"] * 0.7
            issues.append(f"セクション数が目標未達: {section_count}個（目標12+）")
        elif section_count >= 5:
            score += self.WEIGHTS["article_structure"] * 0.5
            issues.append(f"記事の構成が不完全: {section_count}セクション")
        else:
            issues.append(f"記事の構成が不十分: {section_count}セクション")
            recommendations.append("15セクション以上の充実した構成にしてください")

        # 3. 情報ソースチェック（10個以上推奨）
        sources = article.get("sources", [])
        source_count = len(sources)
        if source_count >= 10:
            score += self.WEIGHTS["article_sources"]
        elif source_count >= 7:
            score += self.WEIGHTS["article_sources"] * 0.7
            issues.append(f"情報ソースがやや少ない: {source_count}件（推奨10+）")
        elif source_count >= 5:
            score += self.WEIGHTS["article_sources"] * 0.5
            issues.append(f"情報ソースが少ない: {source_count}件（推奨10+）")
        else:
            issues.append(f"情報ソースが不足: {source_count}件")
            recommendations.append("信頼できる情報ソースを10個以上追加してください")

        # 4. SEOスコアチェック
        seo_score = article.get("seo_score", 70)
        if seo_score >= 85:
            score += self.WEIGHTS["article_seo"]
        elif seo_score >= 70:
            score += self.WEIGHTS["article_seo"] * 0.7
            issues.append(f"SEOスコアが目標未達: {seo_score}（目標85+）")
        else:
            score += self.WEIGHTS["article_seo"] * 0.3
            issues.append(f"SEOスコアが低い: {seo_score}")
            recommendations.append("キーワード最適化とメタ情報を改善してください")

        # 5. 読みやすさチェック
        avg_paragraph_length = len(content) / max(content.count("\n\n"), 1)
        has_lists = "- " in content or "* " in content or "1. " in content
        has_headings = "## " in content

        readability_score = 0
        if avg_paragraph_length < 500:
            readability_score += 0.4
        if has_lists:
            readability_score += 0.3
        if has_headings:
            readability_score += 0.3

        score += self.WEIGHTS["article_readability"] * readability_score
        if readability_score < 0.7:
            issues.append("読みやすさに改善の余地あり")
            recommendations.append("適切な見出しと箇条書きを使用してください")

        # 6. 絵文字禁止チェック
        import re
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "]+",
            flags=re.UNICODE
        )
        if not emoji_pattern.search(content):
            score += self.WEIGHTS["article_no_emoji"]
        else:
            issues.append("絵文字が使用されています（禁止）")
            recommendations.append("全ての絵文字を削除してください")

        # 7. エンゲージメント要素チェック（読者をワクワクさせる要素）
        engagement_score = 0
        engagement_checks = {
            "question": "?" in content or "でしょうか" in content,  # 読者への問いかけ
            "story": "事例" in content or "ケース" in content or "ストーリー" in content,  # ストーリー要素
            "surprise": "意外" in content or "知っていましたか" in content or "実は" in content,  # 驚きの要素
            "action": "アクション" in content or "実践" in content or "今日から" in content,  # 行動促進
        }
        for check_name, check_result in engagement_checks.items():
            if check_result:
                engagement_score += 0.25

        score += self.WEIGHTS["article_engagement"] * engagement_score
        if engagement_score < 0.75:
            issues.append("読者エンゲージメント要素が不足しています")
            recommendations.append("読者への問いかけ、驚きの事実、ストーリー要素を追加してください")

        # 15,000文字未満は強制不合格（スコアに関係なく）
        score_passed = (score / max_score) >= self.PASS_THRESHOLD
        passed = score_passed and not critical_length_failure

        if critical_length_failure and score_passed:
            issues.insert(0, f"[強制不合格] 文字数が最低基準（15,000文字）未満: {word_count}文字")
            recommendations.insert(0, "記事を15,000文字以上に拡充することが必須です")

        return QualityResult(
            category="article",
            score=score,
            max_score=max_score,
            passed=passed,
            issues=issues,
            recommendations=recommendations
        )

    def evaluate_slides(self, slides_data: Dict) -> QualityResult:
        """
        スライドの品質を評価（3倍厳格）

        Args:
            slides_data: スライドデータ
                - slides: スライドリスト
                - slide_images: 画像パスリスト
                - markdown_path: マークダウンパス
                - pdf_path: PDFパス

        Returns:
            QualityResult: 評価結果
        """
        score = 0
        max_score = 30
        issues = []
        recommendations = []

        slides = slides_data.get("slides", [])
        slide_images = slides_data.get("slide_images", [])
        markdown_path = slides_data.get("markdown_path")
        pdf_path = slides_data.get("pdf_path")

        # 1. スライド枚数チェック（10-15枚）
        slide_count = len(slides)
        if 10 <= slide_count <= 15:
            score += self.WEIGHTS["slide_count"]
        elif 8 <= slide_count <= 17:
            score += self.WEIGHTS["slide_count"] * 0.6
            issues.append(f"スライド枚数が推奨範囲外: {slide_count}枚（推奨10-15枚）")
        else:
            issues.append(f"スライド枚数が不適切: {slide_count}枚")
            recommendations.append("スライド枚数を10-15枚に調整してください")

        # 2. テキスト量チェック（1枚100文字以内）
        text_ok_count = 0
        for i, slide in enumerate(slides):
            heading = slide.get("heading", "")
            points = slide.get("points", [])
            total_text = heading + " ".join(points)
            if len(total_text) <= 100:
                text_ok_count += 1
            else:
                issues.append(f"スライド{i+1}: テキスト過多（{len(total_text)}文字）")

        text_ratio = text_ok_count / max(slide_count, 1)
        score += self.WEIGHTS["slide_text_length"] * text_ratio
        if text_ratio < 0.8:
            recommendations.append("各スライドのテキスト量を100文字以内に抑えてください")

        # 3. 画像チェック（全スライドに画像）
        image_count = len(slide_images)
        if image_count >= slide_count:
            score += self.WEIGHTS["slide_images"]
        elif image_count >= slide_count * 0.8:
            score += self.WEIGHTS["slide_images"] * 0.7
            issues.append(f"一部のスライドに画像がありません: {image_count}/{slide_count}")
        else:
            issues.append(f"画像が大幅に不足: {image_count}/{slide_count}")
            recommendations.append("全てのスライドに画像を追加してください")

        # 4. 構成チェック（論理的構成）
        has_title = any(s.get("type") == "title" for s in slides)
        has_ending = any(s.get("type") == "ending" for s in slides)
        content_slides = [s for s in slides if s.get("type") == "content"]

        if has_title and has_ending and len(content_slides) >= 5:
            score += self.WEIGHTS["slide_structure"]
        elif has_title or has_ending:
            score += self.WEIGHTS["slide_structure"] * 0.5
            issues.append("スライド構成が不完全")
        else:
            issues.append("スライド構成が不適切")
            recommendations.append("タイトル→コンテンツ→エンディングの構成を確保してください")

        # 5. デザイン統一性チェック
        # 画像サイズの一貫性をチェック
        design_score = 1.0
        for path in slide_images:
            try:
                size = Path(path).stat().st_size
                if size < 10 * 1024:  # 10KB未満
                    design_score -= 0.1
                    issues.append(f"画像サイズが小さすぎます: {Path(path).name}")
            except Exception:
                design_score -= 0.1

        score += self.WEIGHTS["slide_design"] * max(0, design_score)

        # 6. Marp互換性チェック
        marp_compat = True
        if markdown_path and Path(markdown_path).exists():
            content = Path(markdown_path).read_text(encoding="utf-8")
            if "marp: true" in content:
                score += self.WEIGHTS["slide_marp_compat"]
            else:
                marp_compat = False
                issues.append("Marpフロントマターがありません")
        elif pdf_path and Path(pdf_path).exists():
            score += self.WEIGHTS["slide_marp_compat"]  # PDFが生成されていれば互換性あり
        else:
            marp_compat = False
            issues.append("マークダウンまたはPDFが見つかりません")
            recommendations.append("Marp互換のマークダウンを生成してください")

        passed = (score / max_score) >= self.PASS_THRESHOLD
        return QualityResult(
            category="slides",
            score=score,
            max_score=max_score,
            passed=passed,
            issues=issues,
            recommendations=recommendations
        )

    def evaluate_video(self, video_data: Dict) -> QualityResult:
        """
        動画の品質を評価（3倍厳格）

        Args:
            video_data: 動画データ
                - videos.standard.path: 動画パス
                - videos.standard.resolution: 解像度
                - videos.standard.has_audio: 音声有無
                - narration.script: ナレーションスクリプト

        Returns:
            QualityResult: 評価結果
        """
        score = 0
        max_score = 30
        issues = []
        recommendations = []

        standard = video_data.get("videos", {}).get("standard", {})
        narration = video_data.get("narration", {})

        video_path = standard.get("path")
        resolution = standard.get("resolution", "")
        has_audio = standard.get("has_audio", False)
        size_bytes = standard.get("size_bytes", 0)

        # 1. 解像度チェック（1920x1080）
        if resolution == "1920x1080":
            score += self.WEIGHTS["video_resolution"]
        elif "1920" in resolution or "1080" in resolution:
            score += self.WEIGHTS["video_resolution"] * 0.7
            issues.append(f"解像度が標準と異なります: {resolution}")
        else:
            issues.append(f"解像度が不適切: {resolution}")
            recommendations.append("1920x1080の解像度で出力してください")

        # 2. 音声品質チェック
        if has_audio:
            audio_size = narration.get("audio_size_bytes", 0)
            script = narration.get("script", "")
            if audio_size > 50000 and len(script) > 100:
                score += self.WEIGHTS["video_audio"]
            elif audio_size > 0:
                score += self.WEIGHTS["video_audio"] * 0.6
                issues.append("音声品質に改善の余地があります")
            else:
                issues.append("音声データが不正です")
        else:
            issues.append("音声が含まれていません（必須）")
            recommendations.append("TTS音声を生成して動画に統合してください")

        # 3. タイミング同期チェック
        # 動画長と音声長の整合性
        duration = standard.get("duration", 30)
        if 25 <= duration <= 120:
            score += self.WEIGHTS["video_timing"]
        else:
            score += self.WEIGHTS["video_timing"] * 0.5
            issues.append(f"動画の長さが不適切: {duration}秒")

        # 4. トランジション品質（ファイルサイズから推測）
        if size_bytes > 5 * 1024 * 1024:  # 5MB以上
            score += self.WEIGHTS["video_transitions"]
        elif size_bytes > 2 * 1024 * 1024:  # 2MB以上
            score += self.WEIGHTS["video_transitions"] * 0.7
            issues.append("動画の品質が低い可能性があります")
        else:
            issues.append("動画ファイルサイズが小さすぎます")
            recommendations.append("高品質設定で動画を再レンダリングしてください")

        # 5. ファイルサイズ適正チェック
        if 2 * 1024 * 1024 <= size_bytes <= 100 * 1024 * 1024:  # 2MB-100MB
            score += self.WEIGHTS["video_file_size"]
        elif size_bytes > 0:
            score += self.WEIGHTS["video_file_size"] * 0.5
            if size_bytes < 2 * 1024 * 1024:
                issues.append("ファイルサイズが小さすぎます")
            else:
                issues.append("ファイルサイズが大きすぎます")
        else:
            issues.append("動画ファイルが存在しません")

        # 6. エラーチェック
        if video_data.get("status") == "success" and video_path and Path(video_path).exists():
            score += self.WEIGHTS["video_no_errors"]
        elif video_data.get("status") == "success":
            score += self.WEIGHTS["video_no_errors"] * 0.5
            issues.append("動画ファイルが見つかりません")
        else:
            issues.append(f"動画生成エラー: {video_data.get('error', '不明')}")
            recommendations.append("エラーを解決して動画を再生成してください")

        passed = (score / max_score) >= self.PASS_THRESHOLD
        return QualityResult(
            category="video",
            score=score,
            max_score=max_score,
            passed=passed,
            issues=issues,
            recommendations=recommendations
        )

    def evaluate_all(
        self,
        article: Dict,
        slides_data: Optional[Dict] = None,
        video_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        全コンポーネントの品質を総合評価

        Args:
            article: 記事データ
            slides_data: スライドデータ（オプション）
            video_data: 動画データ（オプション）

        Returns:
            総合評価結果
        """
        results = {}
        total_score = 0
        total_max = 0

        # 記事評価
        article_result = self.evaluate_article(article)
        results["article"] = {
            "score": article_result.score,
            "max_score": article_result.max_score,
            "percentage": round(article_result.score / article_result.max_score * 100, 1),
            "passed": article_result.passed,
            "issues": article_result.issues,
            "recommendations": article_result.recommendations
        }
        total_score += article_result.score
        total_max += article_result.max_score

        # スライド評価
        if slides_data:
            slides_result = self.evaluate_slides(slides_data)
            results["slides"] = {
                "score": slides_result.score,
                "max_score": slides_result.max_score,
                "percentage": round(slides_result.score / slides_result.max_score * 100, 1),
                "passed": slides_result.passed,
                "issues": slides_result.issues,
                "recommendations": slides_result.recommendations
            }
            total_score += slides_result.score
            total_max += slides_result.max_score

        # 動画評価
        if video_data:
            video_result = self.evaluate_video(video_data)
            results["video"] = {
                "score": video_result.score,
                "max_score": video_result.max_score,
                "percentage": round(video_result.score / video_result.max_score * 100, 1),
                "passed": video_result.passed,
                "issues": video_result.issues,
                "recommendations": video_result.recommendations
            }
            total_score += video_result.score
            total_max += video_result.max_score

        # 総合スコア
        overall_percentage = round(total_score / total_max * 100, 1) if total_max > 0 else 0
        overall_passed = overall_percentage >= (self.PASS_THRESHOLD * 100)

        # 全ての問題点と推奨事項を集約
        all_issues = []
        all_recommendations = []
        for category, data in results.items():
            for issue in data.get("issues", []):
                all_issues.append(f"[{category}] {issue}")
            for rec in data.get("recommendations", []):
                all_recommendations.append(f"[{category}] {rec}")

        return {
            "overall": {
                "score": total_score,
                "max_score": total_max,
                "percentage": overall_percentage,
                "passed": overall_passed,
                "threshold": self.PASS_THRESHOLD * 100
            },
            "categories": results,
            "all_issues": all_issues,
            "all_recommendations": all_recommendations,
            "summary": self._generate_summary(overall_percentage, overall_passed)
        }

    def _generate_summary(self, percentage: float, passed: bool) -> str:
        """評価サマリーを生成"""
        if passed:
            return f"品質評価合格: {percentage}%（基準: {self.PASS_THRESHOLD * 100}%）"
        else:
            gap = (self.PASS_THRESHOLD * 100) - percentage
            return f"品質評価不合格: {percentage}%（基準まであと{gap:.1f}ポイント必要）"


async def evaluate_workflow(
    article: Dict,
    slides_data: Optional[Dict] = None,
    video_data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    ワークフロー品質評価のエントリーポイント

    Args:
        article: 記事データ
        slides_data: スライドデータ（オプション）
        video_data: 動画データ（オプション）

    Returns:
        評価結果
    """
    evaluator = QualityEvaluator()
    return evaluator.evaluate_all(article, slides_data, video_data)


if __name__ == "__main__":
    # テスト用
    import json

    test_article = {
        "title": "テスト記事",
        "content": "# はじめに\n\n" + "テスト内容。" * 500 + "\n\n## まとめ\n\n結論です。",
        "word_count": 5000,
        "seo_score": 80,
        "sources": [{"title": "Source 1", "url": "https://example.com"}]
    }

    evaluator = QualityEvaluator()
    result = evaluator.evaluate_all(test_article)
    print(json.dumps(result, ensure_ascii=False, indent=2))
