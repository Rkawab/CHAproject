# variablecosts/receipt_reader.py

import base64
import json
from mimetypes import guess_type
from typing import BinaryIO

from django.conf import settings
from openai import OpenAI


class ReceiptReadError(Exception):
    """レシート読み取りに失敗したときに投げる例外."""
    pass


# settings からキーを使ってクライアント生成
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _file_to_data_url(image_file: BinaryIO) -> str:
    """
    Django の UploadedFile などを data URL (data:image/...;base64,xxx) に変換。
    """
    data = image_file.read()

    mime_type = getattr(image_file, "content_type", None)
    if not mime_type:
        mime_type, _ = guess_type(getattr(image_file, "name", ""))
    if not mime_type:
        mime_type = "image/jpeg"

    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def extract_receipt_info(image_file: BinaryIO) -> dict:
    """
    レシート画像から以下の情報を取得して返すメイン関数（これ1本に統一）:

    戻り値の dict 例:
    {
        "amount": 1234,                 # 合計金額（税込）
        "purchase_date": "2025-01-23",  # 購入日 (YYYY-MM-DD)
        "raw_category": "食材費",       # 食材費 / 外食費用 / 生活雑貨 / 贅沢費用 / 医療費 / その他
        "description": "さんま",        # 1品なら品名 / 2品以上なら店名
    }

    失敗したら ReceiptReadError を投げる。
    """
    data_url = _file_to_data_url(image_file)

    user_prompt = """
これは日本語のレシートの画像です。次の情報を特定して JSON で返してください。

- amount: 支払い合計金額（税込）の数値（整数）
- purchase_date: 購入日。フォーマットは必ず "YYYY-MM-DD" とする。
- raw_category: この支出の費目。必ず次のどれか一つだけを選んで返すこと:
  「食材費」「外食費用」「生活雑貨」「贅沢費用」「医療費」「その他」
  判断ルール:
    * スーパーの買い物、または品目に食材が含まれていれば → 「食材費」
    * レストラン・カフェなどの飲食店のレシート → 「外食費用」
    * ドラッグストア、100円均一などで主に日用品・雑貨の場合 → 「生活雑貨」
    * レジャー施設、テーマパーク、娯楽サービスなど → 「贅沢費用」
    * クリニック、病院、薬局での医療行為・処方薬が中心 → 「医療費」
    * どれにもはっきり当てはまらなければ → 「その他」
- description: 名称フィールドに入れる短い日本語の文字列。
    * レシートに商品が1品だけなら、その商品の名前だけを返す（例: "さんま"）。
    * 2品以上ある場合は、レシートに書かれている店舗名だけを返す（例: "ヨークマート"）。

必ず日本語の説明文を一切含めず、次のような形式の JSON だけを返してください:

{
  "amount": 1234,
  "purchase_date": "2025-01-23",
  "raw_category": "食材費",
  "description": "さんま"
}
    """.strip()

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",  # Vision対応モデル
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that extracts structured data "
                        "from Japanese receipts and responds ONLY in JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url,
                                "detail": "low",
                            },
                        },
                    ],
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=300,
        )
    except Exception as e:
        raise ReceiptReadError(f"AI呼び出しでエラーが発生しました: {e}")

    content = response.choices[0].message.content

    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        raise ReceiptReadError("AIの応答をJSONとして解釈できませんでした。")

    # 必須キーのチェック
    for key in ("amount", "purchase_date", "raw_category", "description"):
        if key not in obj:
            raise ReceiptReadError(f"AIの応答に '{key}' が含まれていません。")

    try:
        amount = int(obj["amount"])
    except (TypeError, ValueError):
        raise ReceiptReadError(f"金額 'amount' を整数に変換できません: {obj['amount']}")

    purchase_date = str(obj["purchase_date"])
    raw_category = str(obj["raw_category"])
    description = str(obj["description"])

    return {
        "amount": amount,
        "purchase_date": purchase_date,
        "raw_category": raw_category,
        "description": description,
    }
