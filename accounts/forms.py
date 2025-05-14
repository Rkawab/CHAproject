from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


# models.pyのUserクラスに継承したUserをそのまま持ってくる
User = get_user_model()

class RegistForm(forms.ModelForm):

    # フィールドは変数confirm_passwordとして定義しても、文字列としてcleaned_data['confirm_password']でアクセスする。
    # パスワードを確認するためのフィールドの作成
    confirm_password = forms.CharField(
        label='パスワード再入力', widget=forms.PasswordInput()
    )
    # label:表示名を変更。
    # widget:入力形式を変更。今回はパスワードなので見えないようになる

    class Meta():
        model = User
        fields = ('username', 'email', 'password')
        labels = {
            'username': '名前',
            'email': 'メールアドレス',
            'password': 'パスワード',
        }
        widgets = {
            'password': forms.PasswordInput()
        }
    
    # パスワードと確認パスワードが一致するか確認する処理(バリデーション)
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data['password']
        confirm_password = cleaned_data['confirm_password']
        # 一致しない場合の処理
        if password != confirm_password:
            self.add_error('password', 'パスワードが一致しません')  # add_error(指定したフィールド, エラーメッセージ) (djangoにあるインスタンス)
            # → パスワードが書かれているフィールドに、一致しないメッセージを載せる指示
        try:
            validate_password(password, self.instance)  # validate_password(パスワード, ユーザー) (djangoにあるインスタンス)
            # → self.instance は現在のフォームのインスタンス（= 新規ユーザー）を指す
        except ValidationError as e:
            self.add_error('password', e)   # validate_password(パスワード, ユーザー) (djangoにあるインスタンス)
        return cleaned_data
    
    def save(self, commit=False):
        user = super().save(commit=False)   # このメソッドが完了するまではまだデータベースへの保存はしない
        user.set_password(self.cleaned_data['password'])
        user.is_active = False  # ← ここを追加
        if commit:
            user.save() # .save(commit=True)で呼び出されたら、通常通り保存
        return user

# ユーザー本登録のためのフォーム
class UserActivateForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput()) # HiddenInputはフォームに表示されない隠しフィールドになっている

class LoginForm(forms.Form):
    email = forms.EmailField(label="メールアドレス")
    password = forms.CharField(label="パスワード", widget=forms.PasswordInput())

class UserEditForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ('username', 'email')
        label = {
            'username': '名前',
            'email': 'メールアドレス',
        }

class PasswordChangeForm(forms.ModelForm):

    confirm_password = forms.CharField(
        label='パスワード再設定', widget=forms.PasswordInput()
    )

    class Meta:
        model = User
        fields = ('password',)
        labels = {
            'password': 'パスワード',
        }
        widgets = {
            'password': forms.PasswordInput()
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data['password']
        confirm_password = cleaned_data['confirm_password']
        if password != confirm_password:
            self.add_error('password', 'パスワードが一致しません')
        try:
            validate_password(password, self.instance)
        except ValidationError as e:
            self.add_error('password', e)
        return cleaned_data

    def save(self, commit=False):   # commitをTrueにして実行しないと保存できないようになる
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])    # パスワードの暗号化
        if commit:
            user.save()
        return user