#!/usr/bin/env python3
"""
タイムゾーンユーティリティ - 日本標準時(JST)対応

すべての日時処理で日本時間を使用するためのユーティリティモジュール。
GitHub Actions (UTC環境) でも正しく JST を出力します。
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

# 日本標準時 (JST = UTC+9)
JST = timezone(timedelta(hours=9), name='JST')


def now_jst() -> datetime:
    """
    現在の日本時間を取得

    Returns:
        datetime: 日本時間のdatetimeオブジェクト（タイムゾーン情報付き）
    """
    return datetime.now(JST)


def format_date(dt: Optional[datetime] = None, fmt: str = "%Y-%m-%d") -> str:
    """
    日付をフォーマット

    Args:
        dt: datetimeオブジェクト（Noneの場合は現在のJST）
        fmt: strftimeフォーマット文字列

    Returns:
        str: フォーマットされた日付文字列
    """
    if dt is None:
        dt = now_jst()
    return dt.strftime(fmt)


def format_datetime_jst(dt: Optional[datetime] = None) -> str:
    """
    Jekyll用の日時文字列を生成（JST +0900付き）

    Args:
        dt: datetimeオブジェクト（Noneの場合は現在のJST）

    Returns:
        str: "YYYY-MM-DD HH:MM:SS +0900" 形式の文字列
    """
    if dt is None:
        dt = now_jst()
    return dt.strftime("%Y-%m-%d %H:%M:%S +0900")


def format_iso_jst(dt: Optional[datetime] = None) -> str:
    """
    ISO 8601形式の日時文字列を生成（タイムゾーン付き）

    Args:
        dt: datetimeオブジェクト（Noneの場合は現在のJST）

    Returns:
        str: ISO 8601形式の文字列（例: 2025-12-29T16:50:44+09:00）
    """
    if dt is None:
        dt = now_jst()
    return dt.isoformat()


def get_timestamp_jst(fmt: str = "%Y%m%d_%H%M%S") -> str:
    """
    ファイル名用のタイムスタンプを生成

    Args:
        fmt: strftimeフォーマット文字列

    Returns:
        str: タイムスタンプ文字列
    """
    return now_jst().strftime(fmt)


def get_weekday_jst() -> int:
    """
    現在の曜日を取得（JST基準）

    Returns:
        int: 曜日（0=月曜日, 6=日曜日）
    """
    return now_jst().weekday()


def get_weekday_name_jst() -> str:
    """
    現在の曜日名を取得（英語小文字）

    Returns:
        str: 曜日名（monday, tuesday, ...）
    """
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    return days[get_weekday_jst()]


if __name__ == "__main__":
    # テスト出力
    print(f"現在のJST時刻: {now_jst()}")
    print(f"日付: {format_date()}")
    print(f"Jekyll用: {format_datetime_jst()}")
    print(f"ISO形式: {format_iso_jst()}")
    print(f"タイムスタンプ: {get_timestamp_jst()}")
    print(f"曜日: {get_weekday_name_jst()}")
