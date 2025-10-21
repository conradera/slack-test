import os
import json
import logging
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, jsonify
from http import HTTPStatus

# ロギング設定
logging.basicConfig(level=logging.INFO)

# Flask appの初期化
flask_app = Flask(__name__)

# Slack Appの初期化（環境変数からトークンとシークレットを取得）
bolt_app = App(
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    token=os.environ.get("SLACK_BOT_TOKEN"),
    process_before_response=True
)

# SlackRequestHandlerの初期化
handler = SlackRequestHandler(bolt_app)

# -----------------------------------------------
# Flask Routes
# -----------------------------------------------

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Slack Events API endpoint"""
    return handler.handle(request)

@flask_app.route("/slack/interactive", methods=["POST"])
def slack_interactive():
    """Slack Interactive Components endpoint"""
    return handler.handle(request)

@flask_app.route("/slack/oauth", methods=["GET"])
def slack_oauth():
    """Slack OAuth callback endpoint"""
    return handler.handle(request)

@flask_app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Slack bot is running"})


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
# Flask App Runner
# -----------------------------------------------

if __name__ == "__main__":
    # 環境変数のチェック
    if not os.environ.get("SLACK_BOT_TOKEN"):
        print("Warning: SLACK_BOT_TOKEN environment variable is not set")
        print("Please set your Slack bot token to test the app")
    
    if not os.environ.get("SLACK_SIGNING_SECRET"):
        print("Warning: SLACK_SIGNING_SECRET environment variable is not set")
        print("Please set your Slack signing secret to test the app")
    
    # Flask appを起動
    print("Starting Slack bot server...")
    print("Available endpoints:")
    print("  GET  / - Health check")
    print("  POST /slack/events - Slack Events API")
    print("  POST /slack/interactive - Slack Interactive Components")
    print("  GET  /slack/oauth - Slack OAuth callback")
    print("\nTo test locally, use ngrok or similar tool to expose this server to Slack")
    
    flask_app.run(host="0.0.0.0", port=3000, debug=True)