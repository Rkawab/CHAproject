# 家計簿アプリ（Django）

このプロジェクトは、Djangoで構築された個人・家庭用のシンプルな家計簿アプリケーションです。ユーザー登録、ログイン認証、変動費の管理、月次サマリー表示など、基本的な家計簿機能を備えています。

## 📦 主な機能

- ユーザー登録・認証（メール有効化付き）
- ユーザー情報の編集・パスワード変更
- 変動費（買い物など）の登録・編集・削除
- 月ごとの支出一覧と合計表示
- 費目ごとの集計、立替者ごとの支出集計
- Bootstrap 5 + カスタムCSSによるUI
- セキュアなカスタムユーザーモデル（`accounts.User`）

## 🗂️ ディレクトリ構成

```csharp
CHAproject/
├── CHAproject/ # プロジェクト設定ディレクトリ
│ ├── settings.py # 各種Django設定（DB・セキュリティ等）
│ ├── urls.py # URLルーティング定義
│ └── ...
├── accounts/ # ユーザー管理アプリ
│ ├── models.py # カスタムユーザーモデル
│ ├── forms.py # 各種フォーム
│ ├── views.py # ユーザー登録・認証処理
│ └── ...
├── core/ # ホーム画面など共通機能
│ └── views.py # ホームビュー（統計表示）
├── variablecosts/ # 変動費管理アプリ
│ ├── models.py # 費目・出費モデル
│ ├── views.py # 登録・編集・削除・月別表示
│ └── ...
├── fixedcosts/ # 固定費管理アプリ
│ ├── models.py # 固定費モデル
│ ├── views.py # 登録・編集・削除・月別表示
│ └── ...
├── largecosts/ # 大型出費管理アプリ
│ ├── models.py # 大型出費モデル
│ ├── views.py # 登録・編集・削除・月別表示
│ └── ...
├── templates/ # HTMLテンプレート
│ ├── base.html # レイアウト共通ファイル
│ ├── accounts/ # 認証関連テンプレート
│ ├── variablecosts/ # 変動費画面
│ ├── fixedcosts/ # 固定費画面
│ ├── largecosts/ # 大型出費画面
│ └── ...
├── static/ # 静的ファイル(CSS等)
│ └── css/custom.css
├── requirements.txt # 依存ライブラリ
├── manage.py
└── .gitignore
```

## 🖥️ 使用技術

- Python 3.11+
- Django 5.2
- PostgreSQL（Supabase対応）
- Bootstrap 5
- Whitenoise（静的ファイル管理）
- Gunicorn（WSGIサーバ）
- .envによる環境変数管理

## 🔧 セットアップ方法

### 1. リポジトリをクローン

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

### 2. 仮想環境を作成・アクティベート

```bash
python -m venv venv
source venv/bin/activate  # Windowsは venv\Scripts\activate
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. .env ファイルを作成

プロジェクトルートに `.env` を作成し、以下を記載：

```ini
SECRET_KEY=your-secret-key
dbname=your-db-name
user=your-db-user
password=your-db-password
host=your-db-host
port=5432
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password
RENDER_EXTERNAL_HOSTNAME=your-render-hostname.onrender.com
```

### 5. マイグレーションと管理ユーザー作成

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. ローカルサーバーで起動

```bash
python manage.py runserver
```

ブラウザで http://localhost:8000 にアクセス。


## 🚀 デプロイ

Render.com などで運用可能。以下を参考に：

- `DEBUG = False` に設定
- `.env` に Render のホスト名を設定
- `whitenoise` により静的ファイルを提供
- `gunicorn` をWSGIサーバとして使用


## 📧 メール設定（Gmailの場合）

`.env` に以下を設定：

```bash
EMAIL_HOST_USER=your-gmail@gmail.com
EMAIL_HOST_PASSWORD=your-app-password  # 2段階認証後に生成したアプリ用パスワード
```


## 🛡️ セキュリティ

- カスタムユーザーモデルによる拡張性の高い設計
- bcrypt による安全なパスワードハッシュ
- CSRF/認証制限（`@login_required`）を徹底


## 📌 注意事項

- デフォルトでは誰でもユーザー登録できます。運用に合わせて制限してください。
- メール機能を使うには SMTP 設定が必要です。
- 管理画面は `/admin/` からアクセス可能です。


## 📝 ライセンス

MIT License


## 🙌 作者

- 名前：Rkawab
- GitHub: @Beecom