# variablecosts/receipt_reader.py

import base64
import json
from mimetypes import guess_type
from typing import BinaryIO

from django.conf import settings          # ★ 追加
from openai import OpenAI                 # pip install --upgrade openai


class ReceiptReadError(Exception):
    """レシート読み取りに失敗したときに投げる例外."""
    pass


# ★ settings からキーを使ってクライアント生成
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _file_to_data_url(image_file: BinaryIO) -> str:
    """
    DjangoのUploadedFile (InMemoryUploadedFile / TemporaryUploadedFile) などを
    data:image/...;base64,xxxxx 形式の data URL に変換する。
    """
    data = image_file.read()

    mime_type = getattr(image_file, "content_type", None)
    if not mime_type:
        mime_type, _ = guess_type(getattr(image_file, "name", ""))
    if not mime_type:
        mime_type = "image/jpeg"

    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def extract_total_amount(image_file: BinaryIO) -> int:
    """
    ChatGPT(Vision対応モデル)を使ってレシート画像から合計金額（税込）を抽出する。

    戻り値: 合計金額を int で返す。
    失敗したら ReceiptReadError を投げる。
    """
    data_url = _file_to_data_url(image_file)

    user_prompt = (
        "これは日本語のレシートの画像です。"
        "支払い合計金額（税込）を1つだけ特定し、数値のみを返してください。"
        "返答は必ず次のJSON形式で、日本語のテキストを含めずに返してください:\n"
        '{"total": 1234}'
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",  # Vision対応の軽量モデル
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that extracts numeric totals "
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
            response_format={"type": "json_object"},  # JSONモード
            max_tokens=50,
        )
    except Exception as e:
        raise ReceiptReadError(f"AI呼び出しでエラーが発生しました: {e}")

    content = response.choices[0].message.content

    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        raise ReceiptReadError("AIの応答をJSONとして解釈できませんでした。")

    total = obj.get("total")
    if total is None:
        raise ReceiptReadError("AIの応答に 'total' が含まれていません。")

    try:
        return int(total)
    except (TypeError, ValueError):
        raise ReceiptReadError(f"金額 'total' を整数に変換できません: {total}")
