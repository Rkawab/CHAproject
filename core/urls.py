from django.urls import path
from . import views

app_name = 'core'

# path('ブラウザでアクセスするURL(<型：変数の値>)', 関連するビュー, 'HTMLやコードで使う名前')

urlpatterns = [
    path('', views.home, name='home'),
]