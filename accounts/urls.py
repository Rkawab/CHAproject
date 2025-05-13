from django.urls import path
from . import views

app_name = 'accounts'

# path('ブラウザでアクセスするURL(<型：変数の値>)', 関連するビュー, 'HTMLやコードで使う名前')
urlpatterns = [
    path('regist', views.regist, name='regist'),
    path('activate_user/<uuid:token>', views.activate_user, name='activate_user'),
    path('login', views.user_login, name='login'),
    path('logout', views.user_logout, name='logout'),
    path('edit', views.user_edit, name='edit'),
    path('info', views.user_info, name='info'),
    path('change_password', views.change_password, name='change_password'),
]