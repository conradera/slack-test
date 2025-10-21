import os
import json
import logging
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_bolt.request import BoltRequest
from slack_bolt.response import BoltResponse
from http import HTTPStatus

# ロギング設定
logging.basicConfig(level=logging.INFO)

# Slack Appの初期化（環境変数からトークンとシークレットを取得）
bolt_app = App(
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    token=os.environ.get("SLACK_BOT_TOKEN"),
    process_before_response=True  # Vercelでの高速応答のため
)

# -----------------------------------------------
# Slack Request URL 検証のためのカスタムハンドラ
# -----------------------------------------------

# Vercelで実行されるエントリーポイント
def handler(req: HttpRequest):
    try:
        # 1. リクエストボディの解析
        body = json.loads(req.body)
    except json.JSONDecodeError:
        # JSONデコードエラーの場合、通常のBoltハンドラに委譲
        return SlackRequestHandler(app=bolt_app).handle(req)

    # 2. url_verification イベントのチェック
    if body.get('type') == 'url_verification':
        challenge = body.get('challenge')
        if challenge:
            # challenge パラメータをプレーンテキストで返却
            return BoltResponse(
                status=HTTPStatus.OK.value,
                body=challenge,
                headers={"Content-Type": ["text/plain"]}
            )

    # 3. それ以外のすべてのリクエストは、Boltフレームワークの標準処理に委譲
    return SlackRequestHandler(app=bolt_app).handle(req)


# -----------------------------------------------
# アプリのロジック (チャンネル参加イベント)
# -----------------------------------------------

@bolt_app.event("member_joined_channel")
def handle_member_joined_channel(event, client, logger):
    """
    新しいメンバーがチャンネルに参加したときに歓迎メッセージを投稿する
    """
    user_id = event["user"]
    channel_id = event["channel"]

    # メンバーがBot自身ではないかチェック
    if client.auth_test().get("user_id") == user_id:
        return

    # 歓迎メッセージの作成
    welcome_message = (
        f"ようこそ！ :tada: <@{user_id}> さん、このチャンネルにご参加ありがとうございます！\n\n"
        f"私たちはこのチャンネルで主に*最新のプロジェクトアップデートや技術的な議論*を共有しています。\n"
        f"ぜひ、まずは <#C012345> (もしあれば) で自己紹介をお願いします！\n"
        f"ご不明な点があれば、いつでも質問してくださいね！ :bulb:"
    )

    try:
        # チャンネルにメッセージを投稿
        client.chat_postMessage(
            channel=channel_id,
            text=welcome_message
        )
        logger.info(f"Welcome message sent to {user_id} in {channel_id}")
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")
        # VercelのLogsに出力されるようにエラーをロギング
        print(f"ERROR: Failed to send message: {e}")

# -----------------------------------------------
# Vercelのインポート処理のためのダミー定義
# -----------------------------------------------

# Vercelは直接 'handler' 関数を呼び出せないため、
# Vercelの環境に合わせて HttpRequest クラスをここで定義します。
class HttpRequest:
    def __init__(self, body):
        self.body = body

# Vercelの関数ランタイムからのリクエスト処理
# (このコードは、Vercelの環境で自動的に調整されますが、
# 互換性のため残しておきます)
def http_handler(event, context):
    try:
        # Vercelからのリクエストイベントからbodyを抽出
        if 'body' in event and event['body'] is not None:
            body = event['body']
        else:
            body = "{}"

        req = HttpRequest(body=body)
        response = handler(req)

        return {
            "statusCode": response.status,
            "headers": {k: v[0] for k, v in response.headers.items()},
            "body": response.body,
        }
    except Exception as e:
        logging.error(f"Execution failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }