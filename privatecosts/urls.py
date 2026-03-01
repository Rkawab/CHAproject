from django.urls import path
from . import views

app_name = "privatecosts"

urlpatterns = [
    # インデックス（Payerボタン一覧）
    path("", views.privatecosts_index, name="index"),
    # 特定Payerの個人家計簿
    path("<str:payer_name>/", views.privatecosts_detail, name="detail"),
    path(
        "<str:payer_name>/<int:year>/<int:month>/",
        views.privatecosts_detail,
        name="detail_by_month",
    ),
    # 変動費 CRUD
    path(
        "<str:payer_name>/variable/new/",
        views.private_variable_new,
        name="variable_new",
    ),
    path(
        "<str:payer_name>/variable/edit/<int:pk>/",
        views.private_variable_edit,
        name="variable_edit",
    ),
    path(
        "<str:payer_name>/variable/delete/<int:pk>/",
        views.private_variable_delete,
        name="variable_delete",
    ),
    # レシート読み取りAPI
    path(
        "<str:payer_name>/variable/scan-receipt/",
        views.scan_receipt,
        name="scan_receipt",
    ),
    # 固定費 CRUD
    path(
        "<str:payer_name>/fixed/edit/",
        views.private_fixed_edit,
        name="fixed_edit",
    ),
    path(
        "<str:payer_name>/fixed/edit/<int:year>/<int:month>/",
        views.private_fixed_edit,
        name="fixed_edit_by_month",
    ),
    path(
        "<str:payer_name>/fixed/delete/<int:year>/<int:month>/",
        views.private_fixed_delete,
        name="fixed_delete",
    ),
]
