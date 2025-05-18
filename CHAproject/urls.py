from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('ブラウザでアクセスするURL', さらに細かいURL設定が書かれたファイルを読み込む)
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),  # "accounts/" 以下のURLを accounts.urls に委任
    path('variablecosts/', include('variablecosts.urls')),
    path('fixedcosts/', include('fixedcosts.urls')),
]
