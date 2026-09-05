"""Bridge transport helpers for outbound WhatsApp messages and media."""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Optional, Tuple

import requests

import audio


def send_message(
    recipient: str,
    message: str,
    *,
    base_url: str,
    bridge_failure: Callable[[Exception], str],
    http_client: Any = requests,
) -> Tuple[bool, str]:
    try:
        if not recipient:
            return False, "Recipient must be provided"

        response = http_client.post(
            f"{base_url}/send",
            json={"recipient": recipient, "message": message},
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        return False, f"Error: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return False, bridge_failure(e)
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def send_file(
    recipient: str,
    media_path: str,
    *,
    base_url: str,
    bridge_failure: Callable[[Exception], str],
    http_client: Any = requests,
) -> Tuple[bool, str]:
    try:
        if not recipient:
            return False, "Recipient must be provided"
        if not media_path:
            return False, "Media path must be provided"
        if not os.path.isfile(media_path):
            return False, f"Media file not found: {media_path}"

        response = http_client.post(
            f"{base_url}/send",
            json={"recipient": recipient, "media_path": media_path},
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        return False, f"Error: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return False, bridge_failure(e)
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def send_audio_message(
    recipient: str,
    media_path: str,
    *,
    base_url: str,
    bridge_failure: Callable[[Exception], str],
    http_client: Any = requests,
    audio_module: Any = audio,
) -> Tuple[bool, str]:
    try:
        if not recipient:
            return False, "Recipient must be provided"
        if not media_path:
            return False, "Media path must be provided"
        if not os.path.isfile(media_path):
            return False, f"Media file not found: {media_path}"
        if not media_path.endswith(".ogg"):
            try:
                media_path = audio_module.convert_to_opus_ogg_temp(media_path)
            except Exception as e:
                return False, f"Error converting file to opus ogg. You likely need to install ffmpeg: {str(e)}"

        response = http_client.post(
            f"{base_url}/send",
            json={"recipient": recipient, "media_path": media_path},
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        return False, f"Error: HTTP {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return False, bridge_failure(e)
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def download_media(
    message_id: str,
    chat_jid: str,
    *,
    base_url: str,
    bridge_failure: Callable[[Exception], str],
    error_type: type[Exception],
    http_client: Any = requests,
) -> Optional[str]:
    try:
        response = http_client.post(
            f"{base_url}/download",
            json={"message_id": message_id, "chat_jid": chat_jid},
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                return result.get("path")
            raise error_type(
                f"The bridge could not download media for message {message_id}: "
                f"{result.get('message', 'Unknown error')}"
            )

        raise error_type(
            f"The bridge returned HTTP {response.status_code} downloading media for "
            f"message {message_id}: {response.text}"
        )
    except requests.RequestException as e:
        raise error_type(bridge_failure(e)) from e
    except json.JSONDecodeError as e:
        raise error_type(
            f"The bridge returned an unreadable download response: {response.text}"
        ) from e
