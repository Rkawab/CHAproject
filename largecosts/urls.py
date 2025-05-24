from django.urls import path
from . import views

app_name = 'largecosts'

urlpatterns = [
    path('', views.largecosts_list, name='list'),
    path('<int:year>/<int:month>/', views.largecosts_list, name='list_by_month'),
    path('new/', views.largecosts_regist, name='regist'),
    path('edit/<int:pk>/', views.largecosts_edit, name='edit'),
    path('delete/<int:pk>/', views.largecosts_delete, name='delete'),
    path('clear_settlement/', views.clear_settlement, name='clear_settlement'),
]
