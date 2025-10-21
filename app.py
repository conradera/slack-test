import os
import json
import logging
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from http import HTTPStatus
# Remove unnecessary imports to align with the Vercel/Lambda entry point function

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Slack App (tokens and secrets from environment variables)
bolt_app = App(
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    token=os.environ.get("SLACK_BOT_TOKEN"),
    process_before_response=True  # Essential for meeting Slack's 3-second response rule
)

# Initialize the SlackRequestHandler globally
# This minimizes cold start initialization cost in Lambda/Vercel
slack_handler = SlackRequestHandler(app=bolt_app)

# -----------------------------------------------
# Application Logic (Channel Join Event)
# -----------------------------------------------

@bolt_app.event("member_joined_channel")
def handle_member_joined_channel(event, client, logger):
    """
    Posts a welcome message when a new member joins a channel.
    """
    user_id = event["user"]
    channel_id = event["channel"]

    # Check if the member joining is the bot itself
    # Note: auth_test is a synchronous API call and might introduce latency
    if client.auth_test().get("user_id") == user_id:
        return

    # Create the welcome message
    # (The channel ID #general is a placeholder and should be updated if necessary)
    welcome_message = (
        f"Welcome! :tada: <@{user_id}>, thanks for joining this channel!\n\n"
        f"In this channel, we primarily share *the latest project updates and technical discussions*.\n"
        f"Feel free to introduce yourself in the #general channel!\n"
        f"If you have any questions, don't hesitate to ask! :bulb:"
    )

    try:
        # Post the message to the channel
        client.chat_postMessage(
            channel=channel_id,
            text=welcome_message
        )
        logger.info(f"Welcome message sent to {user_id} in {channel_id}")
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")


# -----------------------------------------------
# Vercel/Lambda Entry Point (Handler Integration)
# -----------------------------------------------

def handler(event, context):
    """
    The standard entry point for Vercel (AWS Lambda).
    It prioritizes custom URL verification logic and delegates all others
    to the standard Bolt handler.
    """
    body_str = event.get('body')

    # If there is no body (e.g., a GET request), delegate immediately to the Bolt handler
    if not body_str:
        return slack_handler.handle(event, context)

    try:
        # Attempt to parse the body as JSON
        body = json.loads(body_str)

        # 1. Custom handling for url_verification event
        if body.get('type') == 'url_verification':
            challenge = body.get('challenge')
            logger.info("Handling custom URL Verification request.")
            if challenge:
                # Return the challenge parameter as plain text immediately
                return {
                    "statusCode": HTTPStatus.OK.value,
                    "headers": {"Content-Type": "text/plain"},
                    "body": challenge
                }

    except json.JSONDecodeError:
        # If JSON decoding fails (e.g., if it's a signed payload but not JSON),
        # delegate to SlackRequestHandler for signature verification failure handling.
        logger.warning("JSON decode failed. Delegating to SlackRequestHandler for verification.")
        pass
    except Exception as e:
        # Catch any other unexpected errors during pre-processing
        logger.error(f"Custom handler pre-processing error: {e}")
        pass

    # 2. All requests other than url_verification are delegated to
    # the Slack Bolt framework's standard processing (including signature verification)
    return slack_handler.handle(event, context)
