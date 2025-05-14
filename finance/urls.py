from django.urls import path
from . import views

app_name = 'household'

# path('ブラウザでアクセスするURL(<型：変数の値>)', 関連するビュー, 'HTMLやコードで使う名前')

urlpatterns = [
    path('', views.household_list, name='list'),
    path('<int:year>/<int:month>/', views.household_list, name='list_by_month'),  # 任意の年月
    path('new/', views.household_regist, name='regist'),
    path('edit/<int:pk>/', views.household_edit, name='edit'),
    path('delete/<int:pk>/', views.household_delete, name='delete'),
    path('clear_payer/<str:payer_name>/', views.clear_payer, name='clear_payer'),
]