# Gemini Content Skill - 7日以内最新情報 & 引用元必須版

## 概要
Gemini 3 Pro Previewを使用したコンテンツ生成スキル。
**7日以内の最新情報のみを使用**し、**引用元を必ず記載**します。

## 重要な制約条件

### 7日以内限定ルール（必須遵守）
- 過去7日以内の情報のみを記事に含める
- すべての情報に具体的な日付（YYYY年MM月DD日）を明記
- 日時処理はすべて日本標準時（JST = UTC+9）を使用

### 引用元必須ルール
- 記事末尾に必ず「参考文献・引用元」セクションを含める
- 最低5つ以上のソースURLを記載
- URLは完全形式（https://で始まる）で記載
- `<div class="sources-section">`タグで囲む

## モデル設定

### 高品質コンテンツ生成
```python
response = client.models.generate_content(
    model="gemini-3-pro-preview",
    contents=prompt,
    config={
        "temperature": 0.7,
        "max_output_tokens": 8192,
        "top_p": 0.9,
        "top_k": 40
    }
)
```

### 高速ドラフト生成
```python
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt,
    config={
        "temperature": 0.5,
        "max_output_tokens": 4096
    }
)
```

## プロンプトテンプレート

### ブログ記事生成（7日以内限定）
```
あなたはプロのブログライターです。以下の情報を基に、読者にとって価値のあるブログ記事を執筆してください。

【重要】本日は{today}です。記事内の情報は過去7日以内（{start_date}〜{end_date}）の最新情報のみを使用してください。

【トピック】{topic}
【調査結果】{research_summary}
【調査期間】{start_date}〜{end_date}（7日以内の最新情報）
【ターゲット読者】{target_audience}
【文字数】{word_count}文字程度
【トーン】{tone}
【参考文献・引用元（{sources_count}件）】
{sources}

執筆ガイドライン:
- 導入で読者の興味を引く
- 具体的なデータ・事例を含める（日付を明記）
- 専門用語は初出時に解説
- 段落は3-4文で区切る
- 結論で読者に行動を促す
- 7日より古い情報は使用しない

引用元記載ルール（必須）:
- 記事末尾に必ず「参考文献・引用元」セクションを設ける
- 調査で使用したソースをリンク形式で列挙
- URLは完全形式（https://で始まる）で記載
- <div class="sources-section">タグで囲む
- 最後に「この記事はAIによって生成されました。情報は{today}時点のものです。」を追加

出力形式: Markdown（参考文献セクション含む）
```

## 引用元セクションテンプレート
```markdown
---

## 参考文献・引用元

<div class="sources-section">

この記事は以下の情報源を参考に作成されました（{start_date}〜{end_date}の調査に基づく）：

- [ソースタイトル1](https://example.com/article1)
- [ソースタイトル2](https://example.com/article2)
- [ソースタイトル3](https://example.com/article3)
- [ソースタイトル4](https://example.com/article4)
- [ソースタイトル5](https://example.com/article5)

</div>

---

*この記事はAIによって生成されました。情報は{today}時点のものです。*
```

## 品質向上テクニック

### Chain of Thought
```
以下のステップで記事を作成してください:

Step 1: 記事の目的と読者価値を定義
Step 2: 主要なポイントを3-5つリストアップ（7日以内の情報のみ）
Step 3: 各ポイントの論拠・データを整理（日付を確認）
Step 4: 記事構成（見出し）を決定
Step 5: 各セクションを執筆
Step 6: 導入と結論を最適化
Step 7: 参考文献・引用元セクションを追加

各ステップの思考過程を示してから、最終的な記事を出力してください。
```

## 品質チェックリスト
- [ ] 7日以内の情報のみを使用しているか
- [ ] すべての情報に日付が明記されているか
- [ ] 参考文献・引用元セクションがあるか
- [ ] 最低5つ以上のソースURLが記載されているか
- [ ] URLが完全形式（https://）か
- [ ] sources-sectionタグで囲まれているか

## 関連スキル
- `gemini-research.md`: 7日以内最新情報の収集
- `timezone.md`: JST日時処理
