from django.urls import path
from . import views

app_name = 'core'

# path('ブラウザでアクセスするURL(<型：変数の値>)', 関連するビュー, 'HTMLやコードで使う名前')

urlpatterns = [
    path('', views.home, name='home'),
    path('summary/', views.summary, name='summary'),
    path('budget/edit/', views.edit_budget, name='edit_budget'),
    path("payment-settings/", views.payment_settings, name="payment_settings"),

    path("payment-settings/cards/new/", views.creditcard_create, name="creditcard_create"),
    path("payment-settings/cards/<int:pk>/edit/", views.creditcard_edit, name="creditcard_edit"),
    path("payment-settings/cards/<int:pk>/delete/", views.creditcard_delete, name="creditcard_delete"),

    path("payment-settings/items/new/", views.paymentitem_create, name="paymentitem_create"),
    path("payment-settings/items/<int:pk>/edit/", views.paymentitem_edit, name="paymentitem_edit"),
    path("payment-settings/items/<int:pk>/delete/", views.paymentitem_delete, name="paymentitem_delete"),
]