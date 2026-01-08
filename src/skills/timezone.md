# Timezone Skill - 日本標準時 (JST) 対応

## 概要
すべての日時処理で日本時間 (JST = UTC+9) を一貫して使用するためのスキル。
GitHub Actions の UTC 環境でも正しく JST を出力します。

## 使用モジュール
- `src/lib/timezone.py`

## 利用可能な関数

### 1. now_jst()
現在の日本時間を取得（タイムゾーン情報付き）

```python
from lib.timezone import now_jst

current_time = now_jst()
# 出力例: datetime.datetime(2025, 12, 29, 16, 50, 44, tzinfo=...)
```

### 2. format_date(dt=None, fmt="%Y-%m-%d")
日付をフォーマット

```python
from lib.timezone import format_date

date_str = format_date()  # "2025-12-29"
date_str = format_date(fmt="%Y/%m/%d")  # "2025/12/29"
```

### 3. format_datetime_jst(dt=None)
Jekyll用の日時文字列を生成

```python
from lib.timezone import format_datetime_jst

jekyll_date = format_datetime_jst()
# 出力: "2025-12-29 16:50:44 +0900"
```

### 4. format_iso_jst(dt=None)
ISO 8601形式の日時文字列

```python
from lib.timezone import format_iso_jst

iso_date = format_iso_jst()
# 出力: "2025-12-29T16:50:44+09:00"
```

### 5. get_timestamp_jst(fmt="%Y%m%d_%H%M%S")
ファイル名用タイムスタンプ

```python
from lib.timezone import get_timestamp_jst

timestamp = get_timestamp_jst()
# 出力: "20251229_165044"
```

### 6. get_weekday_jst() / get_weekday_name_jst()
曜日を取得（JST基準）

```python
from lib.timezone import get_weekday_jst, get_weekday_name_jst

weekday_num = get_weekday_jst()  # 0=月曜日, 6=日曜日
weekday_name = get_weekday_name_jst()  # "monday", "tuesday", ...
```

## 使用箇所

| ファイル | 用途 |
|---------|------|
| `publish.py` | 記事のfront matter日時、ファイル名 |
| `generate_content.py` | 記事内の日付 |
| `generate_image.py` | 画像ファイルのタイムスタンプ |
| `main.py` | ローカル保存のファイル名 |
| `daily-blog-generation.yml` | 曜日判定、コミット日付 |

## Jekyll設定
`docs/_config.yml` に以下を設定済み:

```yaml
timezone: Asia/Tokyo
```

## GitHub Actions設定
`.github/workflows/daily-blog-generation.yml` に以下を設定済み:

```yaml
env:
  TZ: 'Asia/Tokyo'
```

## 注意事項
- すべての日時処理で `datetime.now()` の代わりに `now_jst()` を使用
- ファイル名には `format_date()` または `get_timestamp_jst()` を使用
- Jekyll front matter には `format_datetime_jst()` を使用
- API レスポンスには `format_iso_jst()` を使用
