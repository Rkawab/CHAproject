from django.urls import path
from . import views

app_name = "fixedcosts"

urlpatterns = [
    # 固定費一覧（デフォルトは現在の年月）
    path("", views.fixedcosts_list, name="list"),
    # 指定年月の固定費一覧
    path("<int:year>/<int:month>/", views.fixedcosts_list, name="list_by_month"),
    # 固定費の編集（新規作成も含む）
    path("edit/", views.fixedcosts_edit, name="edit"),
    path("edit/<int:year>/<int:month>/", views.fixedcosts_edit, name="edit_by_month"),
    # 固定費の削除
    path("delete/<int:year>/<int:month>/", views.fixedcosts_delete, name="delete"),
    # サブスク管理
    path("subscriptions/", views.subscription_list, name="subscription_list"),
    path("subscriptions/new/", views.subscription_create, name="subscription_create"),
    path("subscriptions/<int:pk>/edit/", views.subscription_edit, name="subscription_edit"),
    path("subscriptions/<int:pk>/delete/", views.subscription_delete, name="subscription_delete"),
]
