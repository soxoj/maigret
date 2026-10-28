# Maigret

<div align="center">
  <div>
    <a href="https://pypi.org/project/maigret/">
        <img alt="PyPI version badge for Maigret" src="https://img.shields.io/pypi/v/maigret?style=flat-square" />
    </a>
    <a href="https://pepy.tech/project/maigret">
      <img alt="Total downloads" src="https://static.pepy.tech/badge/maigret" />
      <img alt="Downloads/month" src="https://static.pepy.tech/badge/maigret/month" />
    </a>
  </div>
  <div>
    <a href="https://github.com/soxoj/maigret">
        <img alt="View count for Maigret project" src="https://komarev.com/ghpvc/?username=maigret&color=brightgreen&label=views&style=flat-square" />
    </a>
    <a href="https://github.com/soxoj/maigret">
        <img alt="Minimum Python version required: 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-brightgreen?style=flat-square" />
    </a>
    <a href="https://github.com/soxoj/maigret/blob/main/LICENSE">
        <img alt="License badge for Maigret" src="https://img.shields.io/github/license/soxoj/maigret?style=flat-square" />
    </a>
    <a href="https://maigret.readthedocs.io/">
        <img alt="Maigret documentation" src="https://img.shields.io/readthedocs/maigret?style=flat-square&label=docs" />
    </a>
  </div>
  <br>
  <div>
    <img src="https://raw.githubusercontent.com/soxoj/maigret/main/static/maigret.png" height="300" alt="Maigret logo"/>
  </div>
  <br>
  <div>
    <a href="https://codewiki.google/github.com/soxoj/maigret">
        <img alt="Ask Code Wiki about Maigret" src="https://img.shields.io/badge/Code_Wiki-ask_about_repo-yellow?logo=googlegemini" />
    </a>
    <a href="https://deepwiki.com/soxoj/maigret">
        <img alt="Ask DeepWiki about Maigret" src="https://img.shields.io/badge/DeepWiki-ask_about_repo-yellow" />
    </a>
  </div>
  <br>
  <div>
    <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a> · <a href="README.fr.md">Français</a> · <b>日本語</b>
  </div>
  <br>
  <div>
    📖 <a href="https://maigret.readthedocs.io/"><b>ドキュメント</b></a>
  </div>
  <br>
</div>

**Maigret** は **ユーザー名だけ** を手がかりに人物の調査ファイル（ドシエ）を作成するツールです。膨大な数のサイトでアカウントの有無を確認し、Web ページから入手可能な情報をすべて収集します。API キーは不要です。**[AI プロファイリング（デモ）](#ai-analysis)**。

## スポンサー

<p align="center">
  <a href="https://noimosiny.com/?utm_campaign=maigret&utm_source=github">
    <img width="600" alt="Noimosiny" src="https://github.com/user-attachments/assets/cef16613-4337-47a3-9105-2621197b17d1" />
  </a>
</p>

<p>
  <a href="https://noimosiny.com/?utm_campaign=maigret&utm_source=github"><b>Noimosiny</b></a> は、プロの調査員やアナリスト向けの総合 OSINT プラットフォームです。250 以上のモジュールで、メールアドレス・電話番号・ユーザー名の逆引き検索が可能です。強力なツールで情報収集を自動化しましょう。
</p>

<br>

<p align="center">
  <a href="https://www.rapidproxy.io/?ref=soxoj">
    <img src="https://github.com/user-attachments/assets/4ed589d1-37cb-4a40-9273-bff4d6f1a514" width="500" alt="RapidProxy">
  </a>
</p>

<p>
  <a href="https://www.rapidproxy.io/?ref=soxoj"><b>RapidProxy</b></a> は、Twitter のスクレイピング、Selenium による自動化、Web データ抽出向けの高性能な住宅用プロキシを提供しています。9,000 万以上の IP • スマートローテーション • ブロック回避 • 無期限のトラフィック。<br>
<b>特別オファー</b>：無料でお試しいただけます。プランは $0.65/GB から。コード <b>RAPID10</b> で 10% オフ。
</p>

<p align="center">
  <a href="https://www.thordata.com/?ls=dmt&lk=dmt">
    <img src="https://github.com/user-attachments/assets/6d92bda0-c953-49b5-ab7e-73b0e67f17e2" width="350" alt="Thordata">
  </a>
</p>

<p>
  <a href="https://www.thordata.com/?ls=dmt&lk=dmt"><b>ThorData</b></a> は、OSINT リサーチ、ユーザー名検索、検索による偵察のための住宅用プロキシと Web データ API を提供しています。
<b>190 か国以上</b>にわたる <b>1 億以上の住宅用 IP</b> を利用して、リクエストの失敗、403 エラー、地域による制限を減らせます。構造化された検索結果には SERP API を、公開 Web データの収集には Web Scraper API をご利用ください。
<br>
<b>特別オファー：</b>3 日間の無料トライアルに加え、コード <b>SOXOJ10</b> で <b>10% オフ</b>。
</p>

## 目次

- [1 分で始める](#one-minute)
- [主な機能](#main-features)
- [デモ](#demo)
- [インストール](#installation)
- [使い方](#usage)
- [コントリビュート](#contributing)
- [商用利用](#commercial-use)
- [概要](#about)

<a id="one-minute"></a>
## 1 分で始める

Python 3.10 以上がインストールされていることを確認してください。

```bash
pip install maigret
maigret YOUR_USERNAME
```

インストールしたくない場合は、[コミュニティの Telegram ボット](https://maigret.app/readme-en)または[クラウドシェル](#cloud-shells)をお試しください。

Web UI を使いたい場合は、[起動方法](#web-interface)を参照してください。

あわせて参照：[クイックスタート](https://maigret.readthedocs.io/en/latest/quick-start.html)。

<a id="main-features"></a>
## 主な機能

- 5,900 のサイトに対応（[全リストはこちら](https://github.com/soxoj/maigret/blob/main/sites.md)）。デフォルトではトラフィックの多い上位 500 サイトをチェックします。`-a` を指定するとすべてのサイトを、`--tags` を指定するとカテゴリや国で絞り込んでスキャンします。
- Python プロジェクトに組み込み可能 — `maigret` をインポートしてプログラムから検索を実行できます（[ライブラリとしての使い方](https://maigret.readthedocs.io/en/latest/library-usage.html)を参照）。
- プロフィールページやサイトの API から、他のアカウントへのリンクを含め、アカウント所有者に関する入手可能な情報をすべて[抽出](https://github.com/soxoj/socid_extractor)します。
- 発見したユーザー名やその他の ID を使って再帰的に検索します。
- タグ（サイトのカテゴリ、国）による絞り込みが可能です。
- ブロック、検閲、CAPTCHA を検出し、部分的に回避します。
- 実行のたびに（24 時間に 1 回）GitHub から[自動更新されるサイトデータベース](https://maigret.readthedocs.io/en/latest/settings.html#database-auto-update)を取得し、オフライン時は内蔵のデータベースにフォールバックします。
- Tor や I2P のサイトにも対応し、ドメインのチェックも可能です。
- 結果をグラフで閲覧し、あらゆる形式のレポートを 1 つのページからダウンロードできる [Web インターフェース](#web-interface)を同梱しています。
- オプションの [AI 分析モード](#ai-analysis)（`--ai`）では、OpenAI 互換 API を使って生の検索結果を短い調査サマリーにまとめます。

全機能の一覧は[機能ドキュメント](https://maigret.readthedocs.io/en/latest/features.html)を参照してください。

### 導入事例

Maigret をベースに構築された、プロ向けの OSINT・ソーシャルメディア分析ツール：

<a href="https://github.com/SocialLinks-IO/sociallinks-api"><img height="60" alt="Social Links API" src="https://github.com/user-attachments/assets/789747b2-d7a0-4d4e-8868-ffc4427df660"></a>
<a href="https://sociallinks.io/products/sl-crimewall"><img height="60" alt="Social Links Crimewall" src="https://github.com/user-attachments/assets/0b18f06c-2f38-477b-b946-1be1a632a9d1"></a>
<a href="https://usersearch.ai/"><img height="60" alt="UserSearch" src="https://github.com/user-attachments/assets/66daa213-cf7d-40cf-9267-42f97cf77580"></a>

<a id="demo"></a>
## デモ

### 動画

<a href="https://asciinema.org/a/Ao0y7N0TTxpS0pisoprQJdylZ">
  <img src="https://asciinema.org/a/Ao0y7N0TTxpS0pisoprQJdylZ.svg" alt="asciicast" width="600">
</a>

### レポート

[PDF レポート](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotographycars.pdf)、[HTML レポート](https://htmlpreview.github.io/?https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotographycars.html)

![HTML レポートのスクリーンショット](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotography_html_screenshot.png)

![XMind 8 レポートのスクリーンショット](https://raw.githubusercontent.com/soxoj/maigret/main/static/report_alexaimephotography_xmind_screenshot.png)

[コンソール出力の全文](https://raw.githubusercontent.com/soxoj/maigret/main/static/recursive_search.md)

<a id="installation"></a>
## インストール

[1 分で始める](#one-minute)の手順をすでに実行済みなら、準備は完了です。以下はその他のインストール方法です。

何もインストールしたくない場合は、[コミュニティの Telegram ボット](https://maigret.app/readme-en)をご利用ください。

### Windows

[Releases](https://github.com/soxoj/maigret/releases) から `maigret_standalone.exe` をダウンロードしてください。起動方法は 2 通りあります：

- **ダブルクリックする** — Maigret がユーザー名を尋ね、デフォルトの検索を実行し、レポートへのリンクが見えるよう最後に待機します。
- **ターミナルから実行する** — コマンドプロンプト（`Win+R` を押して `cmd` と入力し Enter）または PowerShell を開くと、追加のオプションを指定できます：

```cmd
cd %USERPROFILE%\Downloads
maigret_standalone.exe USERNAME
maigret_standalone.exe USERNAME --html       :: HTML レポートも保存する
maigret_standalone.exe --help                :: すべてのオプションを表示する
```

動画ガイド：https://youtu.be/qIgwTZOmMmM

<a id="cloud-shells"></a>
### クラウドシェル

クラウドシェルや Jupyter ノートブックを使って、ブラウザ上で Maigret を実行できます：

<a href="https://console.cloud.google.com/cloudshell/open?git_repo=https://github.com/soxoj/maigret&tutorial=cloudshell-tutorial.md"><img src="https://user-images.githubusercontent.com/27065646/92304704-8d146d80-ef80-11ea-8c29-0deaabb1c702.png" alt="Open in Cloud Shell" height="50"></a>
<a href="https://repl.it/github/soxoj/maigret"><img src="https://replit.com/badge/github/soxoj/maigret" alt="Run on Replit" height="50"></a>

<a href="https://colab.research.google.com/gist/soxoj/879b51bc3b2f8b695abb054090645000/maigret-collab.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab" height="45"></a>
<a href="https://mybinder.org/v2/gist/soxoj/9d65c2f4d3bec5dd25949197ea73cf3a/HEAD"><img src="https://mybinder.org/badge_logo.svg" alt="Open In Binder" height="45"></a>

### Snap (Linux)

<a href="https://snapcraft.io/maigret"><img src="https://snapcraft.io/static/images/badges/en/snap-store-black.svg" alt="Get it from the Snap Store" height="50"></a>

```bash
sudo snap install maigret

# 使い方
maigret username
```

amd64 と arm64 に対応しており、Python は不要です。snap は strict confinement で動作し、ホームディレクトリ内にのみ書き込めるため、ホームディレクトリから実行してください。USB ドライブを使う場合は、一度だけ `sudo snap connect maigret:removable-media` でインターフェースを接続してください。

### ローカルインストール (pip)

```bash
# PyPI からインストール
pip3 install maigret

# 使い方
maigret username
```

### ソースから

```bash
# またはクローンして手動でインストール
git clone https://github.com/soxoj/maigret && cd maigret

# ビルドしてインストール
pip3 install .

# 使い方
maigret username
```

### Docker

2 種類のイメージが公開されています：

- `soxoj/maigret:latest` — CLI モード（デフォルト）
- `soxoj/maigret:web` — [Web インターフェース](#web-interface)を自動的に起動

```bash
# 公式イメージ (CLI)
docker pull soxoj/maigret

# CLI での使い方
docker run -v /mydir:/app/reports soxoj/maigret:latest username --html

# Web UI (http://localhost:5000 を開く)
docker run -p 5000:5000 soxoj/maigret:web

# 任意のポートで Web UI を起動
docker run -e PORT=8080 -p 8080:8080 soxoj/maigret:web

# 手動でビルド
docker build -t maigret .                  # CLI イメージ (デフォルトのターゲット)
docker build --target web -t maigret-web . # Web UI イメージ
```

### トラブルシューティング

ビルドエラーが発生した場合は、[トラブルシューティングガイド](https://maigret.readthedocs.io/en/latest/installation.html#troubleshooting)を参照してください。

PDF レポート（`--pdf`）はオプションの追加機能で、`pip install 'maigret[pdf]'` でインストールします。Linux/macOS ではシステムレベルのグラフィックライブラリが必要です。OS ごとのインストール手順は [PDF レポートのセクション](https://maigret.readthedocs.io/en/latest/installation.html#optional-pdf-reports-maigret-pdf)を参照してください。

<a id="usage"></a>
## 使い方

### 例

```bash
# HTML、PDF、XMind のレポートを作成
maigret user --html
maigret user --pdf
maigret user --xmind # XMind 2022 以降のリーダー向けのマニフェスト付きレガシー XML

# 機械可読な形式でのエクスポート
maigret user --json ndjson   # 改行区切りの JSON (--json simple も可)
maigret user --csv
maigret user --txt
maigret user --graph         # インタラクティブな D3 グラフ (HTML)
maigret user --neo4j         # Neo4j 用 Cypher スクリプト (グラフデータベース)

# photo と dating のタグが付いたサイトで検索
maigret user --tags photo,dating

# us タグが付いたサイトで検索
maigret user --tags us

# ページ内で特定のキーワードにも言及しているサイトをハイライト
maigret user --keywords python rust
# キーワードに一致したサイトは明るい緑色の "[++]" で表示される

# 利用可能なすべてのサイトで 3 つのユーザー名を検索
maigret user1 user2 user3 -a

# AI による調査サマリー (OPENAI_API_KEY が必要)
maigret user --ai
```

`--neo4j` は結果のグラフを `*_neo4j.cypher` スクリプトとして書き出します。`cypher-shell -u neo4j -p <password> < report_user_neo4j.cypher` でインポートするか、Neo4j Browser に貼り付けてください。再インポートしても結果は変わりません（冪等）。[Neo4j エクスポートのドキュメント](https://maigret.readthedocs.io/en/latest/command-line-options.html#neo4j-export)を参照してください。

すべてのオプションは `maigret --help` で確認できます。ドキュメント：[CLI オプション](https://maigret.readthedocs.io/en/latest/command-line-options.html)、[その他の例](https://maigret.readthedocs.io/en/latest/usage-examples.html)。403 エラーやタイムアウトが発生する場合は [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照してください。

<a id="web-interface"></a>
### Web インターフェース

Maigret には、結果のグラフ表示やレポートのダウンロードができる Web UI が組み込まれています。

自分で動かしたくない場合は、公開済みの `soxoj/maigret:web` Docker イメージをワンクリックでホスティングアプリとしてデプロイできます：

<a href="https://render.com/deploy?repo=https://github.com/soxoj/maigret&path=utils/render.yaml"><img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render" height="40"></a>

Render の無料プランで動作します（15 分間アイドル状態が続くと停止し、次のリクエストで再起動します）。インスタンスにはログイン機能が設定されていないため、URL を知っている人は誰でも利用できます。

<details>
<summary>Web インターフェースのスクリーンショット</summary>

![Web インターフェース：開始方法](https://raw.githubusercontent.com/soxoj/maigret/main/static/web_interface_screenshot_start.png)

![Web インターフェース：結果](https://raw.githubusercontent.com/soxoj/maigret/main/static/web_interface_screenshot.png)

</details>

```console
maigret --web 5000
```

http://127.0.0.1:5000 を開き、ユーザー名を入力して結果を確認します。

### Python ライブラリ

**Maigret は独自の Python プロジェクトに組み込むことができます。** CLI は、直接呼び出せる非同期関数の薄いラッパーにすぎません。カスタムパイプラインを構築したり、結果を独自のツールに渡したり、より大規模な OSINT ワークフローの中で実行したりできます。

動作するサンプル、非同期処理のパターン、タグによるサイトの絞り込み方法については、[ライブラリ利用ガイド](https://maigret.readthedocs.io/en/latest/library-usage.html)を参照してください。

### 便利な CLI フラグ

- `--parse URL` — プロフィールページを解析して ID やユーザー名を抽出し、それらを使って再帰的な検索を開始します。
- `--permute` — 2 つ以上の入力からありそうなユーザー名のバリエーションを生成し（例：`john doe` → `johndoe`、`j.doe`、…）、そのすべてを検索します。
- `--self-check [--auto-disable]` — データベースを監査するメンテナー向けに、`usernameClaimed` / `usernameUnclaimed` のペアを実際のサイトに対して検証します。
- `--ai` / `--ai-model` — 検索結果に対して [AI 分析](#ai-analysis)を実行し、短い調査サマリーをターミナルにストリーミング出力します。

<a id="ai-analysis"></a>
### AI 分析

[![asciicast](https://asciinema.org/a/979404.svg)](https://asciinema.org/a/979404)

`--ai` は検索結果を収集して内部的に Markdown レポートを作成し、それを OpenAI 互換の Chat Completion エンドポイントに送信して、短く中立的な調査サマリー（推定される本名、所在地、職業、興味・関心、使用言語、確信度、追加調査の手がかり）を生成します。サイトごとの進捗表示は抑制され、モデルの出力が標準出力にストリーミングされます。

```bash
export OPENAI_API_KEY=sk-...
maigret user --ai

# 別のモデルを指定
maigret user --ai --ai-model gpt-4o-mini
```

キーは `settings.json` の `openai_api_key` でも設定できます。エンドポイントのデフォルトは `https://api.openai.com/v1` ですが、`settings.json` の `openai_api_base_url` で任意の OpenAI 互換 API（Azure OpenAI、OpenRouter、ローカルサーバーなど）を指定できます。全オプションの一覧は[設定のドキュメント](https://maigret.readthedocs.io/en/latest/settings.html)を参照してください。

### Tor / I2P / プロキシ

Maigret はプロキシ、Tor、I2P を経由してチェックを行うことができます。`.onion` / `.i2p` サイトや、データセンターの IP をブロックする WAF の回避に便利です。

```bash
# 任意の HTTP/SOCKS プロキシ
maigret user --proxy socks5://127.0.0.1:1080

# Tor (デフォルトのゲートウェイは socks5://127.0.0.1:9050)
maigret user --tor-proxy socks5://127.0.0.1:9050

# I2P (デフォルトのゲートウェイは http://127.0.0.1:4444)
maigret user --i2p-proxy http://127.0.0.1:4444
```

コマンドを実行する前に Tor / I2P デーモンを起動しておいてください。Maigret はこれらのゲートウェイを管理しません。

### Cloudflare の回避

> **実験的機能です。** Cloudflare webgate は活発に開発中であり、設定スキーマ、CLI の挙動、対象となるサイトの範囲は、後方互換性の保証なく変更される可能性があります。

データベース内の一部のサイトでは、JavaScript のチャレンジを解くために実際のブラウザが必要です。Maigret はこれらのチェックをローカルの [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) インスタンスに任せることができます：

```bash
docker run -d -p 8191:8191 --name flaresolverr ghcr.io/flaresolverr/flaresolverr:latest
maigret --cloudflare-bypass <username>
```

この回避機能はオプトイン方式（`--cloudflare-bypass` または `settings.json` の `cloudflare_bypass.enabled`）で、`protection` フィールドが一致するサイトに対してのみ動作します。バックエンドのオプションや設定については[機能ドキュメント](https://maigret.readthedocs.io/en/latest/features.html#cloudflare-bypass)を参照してください。

<a id="contributing"></a>
## コントリビュート

`data.json` 内のサイトは、必要な箇所だけをピンポイントで追加・修正してください（`json.load`/`json.dump` は使わないでください）。その後 `./utils/update_site_data.py` を実行して `sites.md` とデータベースのメタデータを再生成し、プルリクエストを作成してください。詳しくは [CONTRIBUTING ガイド](https://github.com/soxoj/maigret/blob/main/CONTRIBUTING.md)と[開発ドキュメント](https://maigret.readthedocs.io/en/latest/development.html)を参照してください。リリース履歴：[CHANGELOG.md](CHANGELOG.md)。

<a id="commercial-use"></a>
## 商用利用

オープンソース版の Maigret は MIT ライセンスで提供されており、制限なく無料で商用利用できます。ただし、サイトのチェックは時間の経過とともに動作しなくなるため、継続的なメンテナンスが必要です。

**毎日更新されるサイトデータベース**や**ユーザー名チェック API** を必要とする本格的な商用利用については、こちらまでご連絡ください：📧 [maigret@soxoj.com](mailto:maigret@soxoj.com)

- プライベートサイトデータベース — 5,000 以上のサイトを毎日更新（公開されているオープンソースのデータベースとは別物です）
- ユーザー名チェック API — Maigret をあなたの製品に統合

<a id="about"></a>
## 概要

### 免責事項

**教育目的および合法的な目的でのみ使用してください。** お住まいの地域で適用されるすべての法令（GDPR、CCPA など）を遵守する責任は利用者にあります。作者は不正利用について一切の責任を負いません。

### フィードバック

[Issue を作成](https://github.com/soxoj/maigret/issues) · [GitHub Discussions](https://github.com/soxoj/maigret/discussions) · [Telegram](https://t.me/soxoj)

### SOWEL 分類

使用している OSINT 手法：
- [SOTL-2.2. Search For Accounts On Other Platforms](https://sowel.soxoj.com/other-platform-accounts)
- [SOTL-6.1. Check Logins Reuse To Find Another Account](https://sowel.soxoj.com/logins-reuse)
- [SOTL-6.2. Check Nicknames Reuse To Find Another Account](https://sowel.soxoj.com/nicknames-reuse)

### ライセンス

MIT © [Maigret](https://github.com/soxoj/maigret)
