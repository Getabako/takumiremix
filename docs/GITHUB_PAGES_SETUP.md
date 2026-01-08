# GitHub Pages 設定ガイド

このガイドでは、if-blog-autoプロジェクトでGitHub Pagesを正しく設定する方法を説明します。

## 手順1: GitHub Pagesソースの設定

1. GitHubリポジトリページ（https://github.com/takubon0202/if-blog-auto）にアクセス
2. **Settings**タブをクリック
3. 左サイドバーで**Pages**をクリック
4. **Build and deployment**セクションで以下を設定:

   ### Source（ソース）
   **GitHub Actions** を選択

   これにより、プッシュごとにワークフローが自動的にサイトをビルド・デプロイします。

## 手順2: ワークフロー権限の確認

1. **Settings** → **Actions** → **General**に移動
2. **Workflow permissions**セクションで以下を確認:
   - **Read and write permissions**が選択されていること
   - **Allow GitHub Actions to create and approve pull requests**にチェックが入っていること

## 手順3: デプロイの実行

### 方法A: 自動デプロイ（推奨）
`docs/`フォルダに変更をプッシュすると、自動的にデプロイが実行されます。

### 方法B: 手動デプロイ
1. **Actions**タブに移動
2. **Deploy to GitHub Pages**ワークフローを選択
3. **Run workflow**ボタンをクリック

## 手順4: デプロイ状況の確認

1. **Actions**タブでワークフローの実行状況を確認
2. 緑のチェックマークが表示されれば成功
3. https://takubon0202.github.io/if-blog-auto/ にアクセスしてサイトを確認

## トラブルシューティング

### 真っ白なページが表示される場合

1. **Actions**タブで最新のワークフロー実行を確認
2. エラーがある場合はログを確認
3. **Deploy to GitHub Pages**ワークフローを手動で実行

### 404エラーが表示される場合

1. GitHub Pagesが有効になっているか確認
2. ソースが**GitHub Actions**に設定されているか確認
3. ワークフローが正常に完了しているか確認

### CSSが適用されない場合

1. ブラウザのキャッシュをクリア
2. `_config.yml`の`baseurl`が`/if-blog-auto`になっているか確認

## 設定完了後のURL

ブログは以下のURLで公開されます:
- メインページ: https://takubon0202.github.io/if-blog-auto/
- カテゴリ: https://takubon0202.github.io/if-blog-auto/categories
- アーカイブ: https://takubon0202.github.io/if-blog-auto/archive
