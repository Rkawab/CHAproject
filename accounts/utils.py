# accounts/utils.py

import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def send_activation_email(user, token):
    """
    ユーザー登録時に本登録用リンクをメール送信する関数。
    メール送信に失敗した場合は例外を送出する。
    """
    site_url = getattr(settings, "SITE_URL", "http://localhost:8000")
    activation_url = f"{site_url}/accounts/activate_user/{token}"
    subject = "【家計簿アプリ】ユーザー本登録を完了してください"
    message = f"""
{user.username}さん

ユーザー登録ありがとうございます。
以下のURLをクリックして、本登録を完了してください：

{activation_url}

※このリンクの有効期限は24時間です。
"""

    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]

    try:
        send_mail(subject, message, from_email, recipient_list)
    except Exception as e:
        logger.error(
            "アクティベーションメール送信失敗 user_id=%s email=%s: %s",
            user.pk,
            user.email,
            e,
        )
        raise
