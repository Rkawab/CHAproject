from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, PermissionsMixin
)
from uuid import uuid4
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import UserManager
from .utils import send_activation_email  # メール送信機能の追加


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)  # これを元にログイン
    is_active = models.BooleanField(default=False)  # 認証用のURLを発行して有効化したらTrue
    is_staff = models.BooleanField(default=False)   # Trueだと認証画面に入れる

    objects = UserManager()

    USERNAME_FIELD = 'email'    # 認証に行う中心となるフィールドをメールに設定
    REQUIRED_FIELDS = ['username']  # superuserを作るときに絶対に必要になるフィールド
    
    class Meta:
        db_table = 'user'

class UserActivateTokenManager(models.Manager):
    # トークンを使ってユーザーを有効化する処理
    def activate_user_by_token(self, token):    # やっていることはUserのデータベースの1つを書き換えているだけ(is_activate：0 → 1)
        user_activate_token = self.filter(
            token=token,
            expired_at__gte=timezone.now()  # expired_atのテーブルが今より後のもの
        ).first()   # レコード1件だけ取得
        if not user_activate_token:
            raise ValueError('トークンが存在しません')

        user = user_activate_token.user
        user.is_active = True
        user.save()
        return user

    # トークンを新規発行 or 更新する処理
    def create_or_update_token(self, user):
        token = str(uuid4())    # トークン発行
        expired_at = timezone.now() + timedelta(days=1)    # トークンの期限(1日後)
        user_token, created = self.update_or_create(    # self.update_or_createはこのクラスにないので、親クラスのManagerのインスタンスを使う
            user=user,
            defaults={'token': token, 'expired_at': expired_at,}
        )
        return user_token

# ユーザー認証を与えるトークンを発行するためのモデル
class UserActivateToken(models.Model):
    token = models.UUIDField(db_index=True, unique=True, default=uuid4)  
    # ユニークな識別子（UUID）を生成
    # db_index=True: 検索を高速化するためのインデックス
    # unique=True: 重複しない値を保証

    expired_at = models.DateTimeField()  
    # トークンの有効期限（日時を管理）

    objects: UserActivateTokenManager = UserActivateTokenManager()  # objects は UserActivateTokenManager 型ですよ、という型ヒント

    user = models.OneToOneField(  
        'User',  # Userモデルと1対1の関係を持つ
        on_delete=models.CASCADE,  # ユーザーが削除されるとトークンも削除される
        related_name='user_activate_token',  # 逆参照時の名前を指定
    )

    class Meta:
        db_table = 'user_activate_token'  # データベーステーブル名を指定

@receiver(post_save, sender=User)   # デコレーター (Userモデルが 保存（post_save）されたあとに自動的に呼ばれる処理)
def publish_token(sender, instance, created, **kwargs): # これらの引数はDjangoが自動で引数を関数に渡す
    if created:  # ← ユーザーが新規作成されたときだけ
        user_activate_token = UserActivateToken.objects.create_or_update_token(instance)
        send_activation_email(instance, user_activate_token.token)  # ← メール送信に置き換え
