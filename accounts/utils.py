# accounts/utils.py

from django.core.mail import send_mail
from django.conf import settings

def send_activation_email(user, token):
    """
    ユーザー登録時に本登録用リンクをメール送信する関数
    """
    activation_url = f'https://127.0.0.1:8000/accounts/activate_user/{token}'  # ← 本番ドメインに置き換える
    subject = '【家計簿アプリ】ユーザー本登録を完了してください'
    message = f'''
{user.username}さん

ユーザー登録ありがとうございます。
以下のURLをクリックして、本登録を完了してください：

{activation_url}

※このリンクの有効期限は24時間です。
'''

    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]

    send_mail(subject, message, from_email, recipient_list)
