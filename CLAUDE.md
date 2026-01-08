# Blog Automation Project Rules - Gemini API Edition

## プロジェクト概要
Multi-Search（3回検索、メイン）とDeep Research API（日曜のみ・週間総括）を活用し、最新トレンド情報を自動収集して画像・動画付きブログ記事を生成・投稿するシステム。

## 技術スタック
- **AI**: Gemini 3 Pro Preview, Deep Research Pro Preview（日曜のみ）
- **言語**: Python 3.11+, JavaScript (Node.js 20+), TypeScript
- **検索（メイン）**: Multi-Search 3回検索 (Gemini Built-in) - 月〜土曜日
- **検索（深層）**: Deep Research API - 日曜日のみ（週間総括）
- **画像生成**: Gemini 2.5 Flash image (`gemini-2.5-flash-image`)
- **動画生成**: Remotion 4.0 (React-based video framework)
- **CI/CD**: GitHub Actions
- **CMS**: GitHub Pages (Jekyll)
- **公開URL**: https://takubon0202.github.io/if-blog-auto/
- **必須ライブラリ**: `google-genai>=1.56.0` (Interactions API/Deep Research対応)

## リサーチ方法の選択ルール（重要）

| 曜日 | リサーチ方法 | 検索回数 | 処理時間 | 内容 |
|-----|-------------|----------|---------|------|
| **月〜土** | Multi-Search | 3回 | 約10秒 | 単一トピック調査 |
| **日曜日** | Deep Research API | 1回 | 約5分 | **週間総括**（6分野横断） |
| **フォールバック** | Multi-Search | 3回 | 約10秒 | Deep Research失敗時 |

**設計理由**:
- Deep ResearchはRPM 1/分の厳しいレート制限があるため、週1回（日曜日）のみ使用
- 日曜日は6トピックを横断した「週間トレンド総括」記事を生成
- 通常はMulti-Search（3回検索）でDeep Research簡易版として高品質な情報収集

## 対象トピック（6種類 + 週間総括）

| ID | トピック | 曜日 | リサーチ方法 |
|----|----------|------|-------------|
| `psychology` | 心理学・メンタルヘルス | 月曜 | Multi-Search |
| `education` | 教育・学習科学 | 火曜 | Multi-Search |
| `startup` | 起業家育成・スタートアップ | 水曜 | Multi-Search |
| `investment` | 投資教育・金融リテラシー | 木曜 | Multi-Search |
| `ai_tools` | AIツール・技術動向 | 金曜 | Multi-Search |
| `inclusive_education` | インクルーシブ教育・多様な学び | 土曜 | Multi-Search |
| `weekly_summary` | **週間トレンド総括** | **日曜** | **Deep Research** |

※ 不登校支援と発達障害・ニューロダイバーシティは `inclusive_education` として統合

## システムフロー
```
1. 情報収集
   ├── 【月〜土】Multi-Search 3回検索 + gemini-3-pro-preview
   └── 【日曜日】deep-research-pro-preview-12-2025（週間総括）
   └── 【失敗時】Multi-Searchへ自動フォールバック

2. Gemini 3 Pro (ブログ生成)
   └── gemini-3-pro-preview で記事を執筆（10,000文字以上）

3. 画像生成
   └── gemini-2.5-flash-image でアニメ風アイキャッチ画像生成
       ├── 16:9 横長フォーマット必須
       └── キャラクター多様性（男女・年齢ランダム）

4. 動画生成（2モード選択可能）
   ├── 【推奨】スライドベース動画
   │   ├── スライド生成: Gemini 3 Pro（10-15枚）
   │   ├── スライド画像: Gemini 2.5 Flash image
   │   ├── PDF変換: Marp CLI
   │   ├── 画像変換: PDF→PNG（各スライド）
   │   ├── 動画生成: Remotion SlideVideo
   │   └── 音声: Gemini 2.5 Flash TTS
   │
   └── 【従来】30秒概要動画
       ├── Remotion BlogVideo（30秒、1920x1080）
       └── TTS音声: Gemini 2.5 Flash TTS

5. SEO最適化 & レビュー
   └── gemini-3-flash-preview（思考オフ）で高速処理

6. 品質評価（3倍厳格）
   └── 95%以上で合格、不合格時は自動再試行（最大3回）

7. GitHub Pages投稿
   └── Git push → Jekyll自動ビルド → 公開
```

## 動画生成モード

### スライドベース動画（推奨）
高品質な解説動画を自動生成する新ワークフロー:

```
ブログ記事 → スライド生成（10-15枚）→ Marp PDF → 画像変換 → Remotion動画 + TTS音声
```

| 項目 | 値 |
|------|------|
| スライド枚数 | 10-15枚 |
| 各スライド表示時間 | 5秒（調整可能） |
| 動画長 | 50-75秒（スライド数×5秒） |
| 解像度 | 1920x1080 |
| 音声 | Gemini 2.5 Flash TTS |

### 従来モード
30秒の概要動画を生成:

| 項目 | 値 |
|------|------|
| 動画長 | 30秒 |
| 解像度 | 1920x1080 |
| 構成 | タイトル→画像→ポイント×3→エンディング |

## Gemini API使用ルール

### モデル選択
| 用途 | モデル/ツール | 曜日/タイミング |
|------|-------------|----------------|
| 情報収集（メイン） | `gemini-3-pro-preview` + Multi-Search 3回 | 月〜土（デフォルト） |
| 情報収集（週間総括） | `deep-research-pro-preview-12-2025` | 日曜のみ |
| 情報収集（フォールバック） | `gemini-3-pro-preview` + Multi-Search 3回 | Deep Research失敗時 |
| コンテンツ生成 | `gemini-3-pro-preview` | 全曜日 |
| SEO最適化 | `gemini-3-flash-preview`（思考オフ） | 全曜日 |
| 品質レビュー | `gemini-3-flash-preview`（思考オフ） | 全曜日 |
| 画像生成 | `gemini-2.5-flash-image` | 全曜日 |
| 動画生成 | Remotion 4.0 (React) | 全曜日 |
| 軽量タスク | `gemini-3-flash-preview`（思考オフ） | 全曜日 |

### API呼び出しパターン
```python
# 同期的なコンテンツ生成
response = ai.models.generate_content(
    model="gemini-3-pro-preview",
    contents=prompt
)

# 非同期Deep Research
interaction = client.interactions.create(
    input=research_query,
    agent="deep-research-pro-preview-12-2025",
    background=True
)

# 画像生成（Gemini 2.5 Flash image）
# 重要: response_modalities=["IMAGE"] が必須
response = ai.models.generate_content(
    model="gemini-2.5-flash-image",
    contents=image_prompt,
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"]  # 必須設定
    )
)
# レスポンスのinline_dataから画像を取得
```

### Google Search Tool使用
```python
# 検索ツール有効化
response = ai.models.generate_content(
    model="gemini-3-pro-preview",
    contents=prompt,
    config={
        "tools": [{"google_search": {}}]
    }
)
```

## サブエージェント呼び出し規則
```
Task: [具体的なタスク内容]
Agent: src/agents/[agent-name].md
Gemini Model: [使用モデル]
Input: [入力データ]
Expected Output: [期待する出力形式]
```

### 利用可能なサブエージェント
- `google-search-agent.md`: Multi-Search 3回検索による情報収集（メイン・月〜土）
- `deep-research-agent.md`: Deep Researchによる週間総括（日曜のみ）
- `writing-agent.md`: Gemini 3 Proによる記事執筆
- `image-agent.md`: Gemini 2.5 Flash imageによる画像生成
- `video-agent.md`: Remotionによる動画生成（標準30秒/ショート15秒）
- `seo-agent.md`: SEO最適化
- `review-agent.md`: 品質レビュー

## スキル使用規則
```
Skill: src/skills/[skill-name].md
Purpose: [使用目的]
API: [使用するGemini API]
```

### 利用可能なスキル
- `gemini-research.md`: Deep Research実行
- `gemini-content.md`: コンテンツ生成
- `image-generation.md`: 画像生成（Gemini 2.5 Flash image）
- `remotion-video.md`: 動画生成（Remotion 4.0）
- `cms-integration.md`: CMS連携

## 品質基準
- ブログ記事: 最低1500文字
- SEOスコア: 80点以上目標
- 画像: 1記事につき最低1枚
- 情報ソース: Deep Researchで最低5つの信頼できるソース

## デザインガイドライン（必須遵守）

### 絶対禁止事項
1. **絵文字の使用禁止** - タイトル、見出し、本文すべてで絵文字を使わない
2. **紫色系の禁止** - 紫、バイオレット、ラベンダー系の色は使用しない
3. **AIっぽい表現の禁止**:
   - 「革新的」「画期的」「驚くべき」などの陳腐な表現
   - 過度な感嘆符の使用
   - 「さあ、始めましょう」などの押し付けがましい表現

### 推奨スタイル
- クリーンでミニマルなデザイン
- Deep Navy (#1a1a2e) を基調とした配色
- 専門的だが親しみやすいトーン
- 科学的・論理的なアプローチ

### 詳細ガイドライン
詳細は `src/config/design-guidelines.md` を参照

## 禁止事項
- 著作権侵害コンテンツの生成
- 未検証情報の断定的記述
- APIキーのハードコーディング
- レート制限を無視した連続呼び出し
- 絵文字の使用
- 紫色系のデザイン

## ドキュメント更新ルール（必須遵守）

### README.md の更新義務
**すべてのサブエージェントは、機能追加・修正・エラー対応を行った際に必ずREADME.mdを最新仕様に更新すること。**

更新すべき内容:
1. **最新アップデート**: 新機能・修正内容を記載
2. **トラブルシューティング**: 新しいエラーと解決策を追加
3. **技術スタック**: ライブラリバージョンの更新
4. **内部動作フロー**: システムの動作説明を最新化

### エラー時の手順ドキュメント化
エラーハンドリングを追加・修正した場合、以下を必ずドキュメント化:
1. **エラーメッセージ**: 発生するエラーの具体例
2. **原因**: エラーの根本原因
3. **解決策**: 修正方法・回避策
4. **フォールバック**: 代替処理の説明

### 内部動作フローの記載
システム変更時は以下のフローを更新:
```
例: Deep Research フォールバックフロー（週間総括）
┌─────────────────────────────────────────────┐
│ Deep Research API 呼び出し（週間総括）        │
│ topic=weekly_summary → 6分野横断クエリ生成   │
└─────────────────┬───────────────────────────┘
                  │
        ┌─────────▼─────────┐
        │   成功？          │
        └─────────┬─────────┘
                  │
       ┌──────────┴──────────┐
       │                     │
   ┌───▼───┐            ┌────▼────┐
   │ 成功  │            │  失敗   │
   └───┬───┘            └────┬────┘
       │                     │
       │              ┌──────▼──────┐
       │              │ エラー通知  │
       │              │ ログ出力    │
       │              └──────┬──────┘
       │                     │
       │              ┌──────▼──────────────┐
       │              │ Multi-Search 3回検索│
       │              │ フォールバック実行   │
       │              └──────┬──────────────┘
       │                     │
   ┌───▼─────────────────────▼───┐
   │      結果を返却              │
   │  (method: deep_research     │
   │   or multi_search)          │
   └─────────────────────────────┘
```
