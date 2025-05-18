from django.urls import path
from . import views

app_name = 'fixedcosts'

urlpatterns = [
    # 固定費一覧（デフォルトは現在の年月）
    path('', views.fixedcosts_list, name='list'),
    # 指定年月の固定費一覧
    path('<int:year>/<int:month>/', views.fixedcosts_list, name='list_by_month'),
    # 固定費の編集（新規作成も含む）
    path('edit/', views.fixedcosts_edit, name='edit'),
    path('edit/<int:year>/<int:month>/', views.fixedcosts_edit, name='edit_by_month'),
    # 固定費の削除
    path('delete/<int:year>/<int:month>/', views.fixedcosts_delete, name='delete'),
]