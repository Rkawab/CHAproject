from django.shortcuts import render, redirect
from . import forms
from .models import UserActivateToken
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required

# ユーザー登録画面のビュー
def regist(request):
    # フォームのインスタンスを作成
    regist_form = forms.RegistForm(request.POST or None)    # request.POST or None：フォームのデータが送信されている場合 → request.POST をフォームに渡す
    if regist_form.is_valid():  # formsのcleanメソッドに記載したエラーが発生していない場合True
        regist_form.save(commit=True)   # commit=True：データベースに保存する
        return redirect('core:home')    # 登録完了したら/homeの画面に移る
    return render(request, 'accounts/regist.html', context={    # バリデーションに失敗した場合の処理(ifがFalse)
        'regist_form': regist_form
        })
        # フォームオブジェクトをテンプレートに渡し、表示できるようにする

# ユーザーを有効化するビュー
def activate_user(request, token):
    activate_form = forms.UserActivateForm(request.POST or None)    # request.POST or None：フォームのデータが送信されている場合 → request.POST をフォームに渡す
    if activate_form.is_valid():
        UserActivateToken.objects.activate_user_by_token(token)     # Userテーブルのtokenが一致した場所のis_activateをTrueにした
        messages.success(request, 'ユーザーを有効化しました')
    activate_form.initial['token'] = token
    return render(
        request, 'accounts/activate_user.html', context={
            'activate_form': activate_form,
        }
    )

def user_login(request):
    login_form = forms.LoginForm(request.POST or None)
    if login_form.is_valid():
        email = login_form.cleaned_data['email']
        password = login_form.cleaned_data['password']
        user = authenticate(email=email, password=password) # 認証。 DjangoのAUTH_USER_MODEL に登録されていて、かつパスワードが一致する場合、該当のユーザーオブジェクトを返す
        if user:
            login(request, user)    # ログイン状態に。request.userの値を該当のユーザーに更新する
            return redirect('core:home')
        else:
            messages.warning(request, 'ログインに失敗しました')
    return render(
        request, 'accounts/user_login.html', context={
            'login_form': login_form,
        }
    )

@login_required # ログインが成功した後でしか実行されないビュー
def user_logout(request):   # ログアウトの処理を実行してHome画面に移動
    logout(request)
    return redirect('core:home')

@login_required
def user_info(request):
    return render(request, 'accounts/user_info.html', context={
        'user': request.user  # テンプレートで `user.username` などが直接使える
    })

@login_required
def user_edit(request):
    user_edit_form = forms.UserEditForm(request.POST or None, request.FILES or None, instance=request.user)
    if user_edit_form.is_valid():
        user_edit_form.save(commit=True)
        messages.success(request, '更新完了しました')
    return render(request, 'accounts/user_edit.html', context={
        'user_edit_form': user_edit_form,
    })

@login_required
def change_password(request):
    password_change_form = forms.PasswordChangeForm(request.POST or None, instance=request.user)
    if password_change_form.is_valid():
        password_change_form.save(commit=True)
        messages.success(request, 'パスワード更新しました')
        update_session_auth_hash(request, request.user) # パスワード更新してもログアウトされなくなる
    return render(
        request, 'accounts/change_password.html', context={
            'password_change_form': password_change_form,
        }
    )