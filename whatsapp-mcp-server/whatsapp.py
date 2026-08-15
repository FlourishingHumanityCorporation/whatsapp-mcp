import sqlite3
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Tuple
import os.path
import requests
import json
import audio

MESSAGES_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "whatsapp-bridge",
    "store",
    "messages.db",
)
WHATSAPP_API_BASE_URL = "http://localhost:8080/api"

# How long to wait on the bridge's own liveness endpoint. It is a local process, so
# a slow answer means something is wrong rather than something is busy.
BRIDGE_HEALTH_TIMEOUT_SECONDS = 5.0


class WhatsAppError(Exception):
    """A request could not be answered.

    This exists so that a failure can never be returned as an empty list. On
    2026-08-15 a single bad column reference was swallowed by ``except
    sqlite3.Error: return []`` and read as "you have no WhatsApp contacts", while
    the store held 882 chats. An error and an empty inbox must not look alike.
    """


@dataclass
class BridgeStatus:
    """What the bridge reports about itself, or why it could not be asked."""

    running: bool
    connected: bool
    logged_in: bool
    last_message_time: Optional[datetime]
    detail: str

    @property
    def usable(self) -> bool:
        """True when the bridge could currently deliver fresh WhatsApp data."""
        return self.running and self.connected and self.logged_in


def check_bridge(timeout: float = BRIDGE_HEALTH_TIMEOUT_SECONDS) -> BridgeStatus:
    """Ask the bridge whether it is connected and logged in.

    The status is read from the bridge rather than inferred from the outside: an
    open port proves a process is listening, not that WhatsApp accepted it.
    """
    unreachable = BridgeStatus(
        running=False,
        connected=False,
        logged_in=False,
        last_message_time=None,
        detail=(
            "The WhatsApp bridge is not running (nothing is answering at "
            f"{WHATSAPP_API_BASE_URL}). Start it with: cd whatsapp-bridge && go run main.go"
        ),
    )

    try:
        response = requests.get(f"{WHATSAPP_API_BASE_URL}/health", timeout=timeout)
    except requests.RequestException as e:
        unreachable.detail = f"{unreachable.detail} (probe failed: {e})"
        return unreachable

    if response.status_code == 404:
        return BridgeStatus(
            running=True,
            connected=False,
            logged_in=False,
            last_message_time=None,
            detail=(
                "A bridge is running but predates the /api/health endpoint, so its "
                "connection state cannot be read. Rebuild it from the current source."
            ),
        )

    if response.status_code != 200:
        unreachable.running = True
        unreachable.detail = (
            f"The bridge answered HTTP {response.status_code} on its health endpoint."
        )
        return unreachable

    try:
        payload = response.json()
    except json.JSONDecodeError as e:
        unreachable.running = True
        unreachable.detail = f"The bridge returned an unreadable health response: {e}"
        return unreachable

    last_message_time = None
    raw_timestamp = payload.get("last_message_time")
    if raw_timestamp:
        try:
            last_message_time = datetime.fromisoformat(raw_timestamp)
        except ValueError as e:
            print(
                f"Bridge reported an unparseable last_message_time {raw_timestamp!r}: {e}"
            )

    connected = bool(payload.get("connected", False))
    logged_in = bool(payload.get("logged_in", False))

    if connected and logged_in:
        detail = "The bridge is running, connected and logged in."
    elif logged_in:
        detail = "The bridge is running and paired, but is not currently connected to WhatsApp."
    else:
        detail = (
            "The bridge is running but is not logged in to WhatsApp. It needs a QR "
            "scan from the phone before it can sync."
        )

    return BridgeStatus(
        running=True,
        connected=connected,
        logged_in=logged_in,
        last_message_time=last_message_time,
        detail=detail,
    )


def _open_message_store() -> sqlite3.Connection:
    """Open the local message store.

    Checked explicitly because ``sqlite3.connect`` CREATES an empty database for a
    missing path. That turns a wrong path into a store with no tables, whose reads
    then fail in a way that used to be swallowed into an empty result.
    """
    if not os.path.isfile(MESSAGES_DB_PATH):
        raise WhatsAppError(
            f"No WhatsApp message store at {MESSAGES_DB_PATH}. The bridge has never "
            "completed a sync from this checkout, so there is no history to read."
        )
    return sqlite3.connect(MESSAGES_DB_PATH)


def _describe_history_age(status: BridgeStatus) -> str:
    """Describe how stale the stored history is, when that is known."""
    if status.last_message_time is None:
        return ""
    age_days = (
        datetime.now(status.last_message_time.tzinfo) - status.last_message_time
    ).days
    return f" Local history was last updated {status.last_message_time:%Y-%m-%d} ({age_days} days ago)."


def _describe_bridge_call_failure(error: Exception) -> str:
    """Explain a failed bridge call in terms of the bridge, not the HTTP client.

    "Request error: Connection refused" names the symptom; the operator needs to
    know the bridge is not running and how to start it.
    """
    status = check_bridge()
    if status.running:
        return f"The WhatsApp bridge could not complete the request: {error}"
    return f"{status.detail} (underlying error: {error})"


def _refuse_unexplained_empty(what: str) -> None:
    """Raise if an empty result cannot be trusted to mean "there is nothing".

    Called only when a read found no rows, which is the one outcome a caller cannot
    interpret alone. If the bridge is usable, empty genuinely means empty and this
    returns. If it is not, the empty result is reported as the symptom it is.
    """
    status = check_bridge()
    if status.usable:
        return
    raise WhatsAppError(
        f"Found no {what}, but this empty result cannot be trusted: the WhatsApp "
        f"bridge is not usable, so local data may be missing or stale rather than "
        f"absent. {status.detail}{_describe_history_age(status)}"
    )


@dataclass
class Message:
    timestamp: datetime
    sender: str
    content: str
    is_from_me: bool
    chat_jid: str
    id: str
    chat_name: Optional[str] = None
    media_type: Optional[str] = None


@dataclass
class Chat:
    jid: str
    name: Optional[str]
    last_message_time: Optional[datetime]
    last_message: Optional[str] = None
    last_sender: Optional[str] = None
    last_is_from_me: Optional[bool] = None

    @property
    def is_group(self) -> bool:
        """Determine if chat is a group based on JID pattern."""
        return self.jid.endswith("@g.us")


@dataclass
class Contact:
    phone_number: str
    name: Optional[str]
    jid: str


@dataclass
class MessageContext:
    message: Message
    before: List[Message]
    after: List[Message]


def get_sender_name(sender_jid: str) -> str:
    try:
        conn = _open_message_store()
        cursor = conn.cursor()

        # First try matching by exact JID
        cursor.execute(
            """
            SELECT name
            FROM chats
            WHERE jid = ?
            LIMIT 1
        """,
            (sender_jid,),
        )

        result = cursor.fetchone()

        # If no result, try looking for the number within JIDs
        if not result:
            # Extract the phone number part if it's a JID
            if "@" in sender_jid:
                phone_part = sender_jid.split("@")[0]
            else:
                phone_part = sender_jid

            cursor.execute(
                """
                SELECT name
                FROM chats
                WHERE jid LIKE ?
                LIMIT 1
            """,
                (f"%{phone_part}%",),
            )

            result = cursor.fetchone()

        if result and result[0]:
            return result[0]
        else:
            return sender_jid

    except sqlite3.Error as e:
        # Falling back to the raw JID here would be indistinguishable from a sender
        # who genuinely has no stored name, hiding a broken store behind plausible
        # output for every message rendered.
        raise WhatsAppError(
            f"Could not look up the display name for {sender_jid}: {e}"
        ) from e
    finally:
        if "conn" in locals():
            conn.close()


def format_message(message: Message, show_chat_info: bool = True) -> None:
    """Print a single message with consistent formatting."""
    output = ""

    if show_chat_info and message.chat_name:
        output += f"[{message.timestamp:%Y-%m-%d %H:%M:%S}] Chat: {message.chat_name} "
    else:
        output += f"[{message.timestamp:%Y-%m-%d %H:%M:%S}] "

    content_prefix = ""
    if hasattr(message, "media_type") and message.media_type:
        content_prefix = f"[{message.media_type} - Message ID: {message.id} - Chat JID: {message.chat_jid}] "

    try:
        sender_name = (
            get_sender_name(message.sender) if not message.is_from_me else "Me"
        )
        output += f"From: {sender_name}: {content_prefix}{message.content}\n"
    except Exception as e:
        print(f"Error formatting message: {e}")
    return output


def format_messages_list(messages: List[Message], show_chat_info: bool = True) -> None:
    output = ""
    if not messages:
        output += "No messages to display."
        return output

    for message in messages:
        output += format_message(message, show_chat_info)
    return output


def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1,
) -> List[Message]:
    """Get messages matching the specified criteria with optional context."""
    try:
        conn = _open_message_store()
        cursor = conn.cursor()

        # Build base query
        query_parts = [
            "SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.media_type FROM messages"
        ]
        query_parts.append("JOIN chats ON messages.chat_jid = chats.jid")
        where_clauses = []
        params = []

        # Add filters
        if after:
            try:
                after = datetime.fromisoformat(after)
            except ValueError:
                raise ValueError(
                    f"Invalid date format for 'after': {after}. Please use ISO-8601 format."
                )

            where_clauses.append("messages.timestamp > ?")
            params.append(after)

        if before:
            try:
                before = datetime.fromisoformat(before)
            except ValueError:
                raise ValueError(
                    f"Invalid date format for 'before': {before}. Please use ISO-8601 format."
                )

            where_clauses.append("messages.timestamp < ?")
            params.append(before)

        if sender_phone_number:
            where_clauses.append("messages.sender = ?")
            params.append(sender_phone_number)

        if chat_jid:
            where_clauses.append("messages.chat_jid = ?")
            params.append(chat_jid)

        if query:
            where_clauses.append("LOWER(messages.content) LIKE LOWER(?)")
            params.append(f"%{query}%")

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        # Add pagination
        offset = page * limit
        query_parts.append("ORDER BY messages.timestamp DESC")
        query_parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset])

        cursor.execute(" ".join(query_parts), tuple(params))
        messages = cursor.fetchall()

        result = []
        for msg in messages:
            message = Message(
                timestamp=datetime.fromisoformat(msg[0]),
                sender=msg[1],
                chat_name=msg[2],
                content=msg[3],
                is_from_me=msg[4],
                chat_jid=msg[5],
                id=msg[6],
                media_type=msg[7],
            )
            result.append(message)

        if include_context and result:
            # Add context for each message
            messages_with_context = []
            for msg in result:
                context = get_message_context(msg.id, context_before, context_after)
                messages_with_context.extend(context.before)
                messages_with_context.append(context.message)
                messages_with_context.extend(context.after)

            return format_messages_list(messages_with_context, show_chat_info=True)

        if not result:
            _refuse_unexplained_empty("messages")

        # Format and display messages without context
        return format_messages_list(result, show_chat_info=True)

    except sqlite3.Error as e:
        raise WhatsAppError(
            f"Could not read messages from the message store: {e}"
        ) from e
    finally:
        if "conn" in locals():
            conn.close()


def get_message_context(
    message_id: str, before: int = 5, after: int = 5
) -> MessageContext:
    """Get context around a specific message."""
    try:
        conn = _open_message_store()
        cursor = conn.cursor()

        # Get the target message first
        cursor.execute(
            """
            SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.chat_jid, messages.media_type
            FROM messages
            JOIN chats ON messages.chat_jid = chats.jid
            WHERE messages.id = ?
        """,
            (message_id,),
        )
        msg_data = cursor.fetchone()

        if not msg_data:
            raise ValueError(f"Message with ID {message_id} not found")

        target_message = Message(
            timestamp=datetime.fromisoformat(msg_data[0]),
            sender=msg_data[1],
            chat_name=msg_data[2],
            content=msg_data[3],
            is_from_me=msg_data[4],
            chat_jid=msg_data[5],
            id=msg_data[6],
            media_type=msg_data[8],
        )

        # Get messages before
        cursor.execute(
            """
            SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.media_type
            FROM messages
            JOIN chats ON messages.chat_jid = chats.jid
            WHERE messages.chat_jid = ? AND messages.timestamp < ?
            ORDER BY messages.timestamp DESC
            LIMIT ?
        """,
            (msg_data[7], msg_data[0], before),
        )

        before_messages = []
        for msg in cursor.fetchall():
            before_messages.append(
                Message(
                    timestamp=datetime.fromisoformat(msg[0]),
                    sender=msg[1],
                    chat_name=msg[2],
                    content=msg[3],
                    is_from_me=msg[4],
                    chat_jid=msg[5],
                    id=msg[6],
                    media_type=msg[7],
                )
            )

        # Get messages after
        cursor.execute(
            """
            SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.media_type
            FROM messages
            JOIN chats ON messages.chat_jid = chats.jid
            WHERE messages.chat_jid = ? AND messages.timestamp > ?
            ORDER BY messages.timestamp ASC
            LIMIT ?
        """,
            (msg_data[7], msg_data[0], after),
        )

        after_messages = []
        for msg in cursor.fetchall():
            after_messages.append(
                Message(
                    timestamp=datetime.fromisoformat(msg[0]),
                    sender=msg[1],
                    chat_name=msg[2],
                    content=msg[3],
                    is_from_me=msg[4],
                    chat_jid=msg[5],
                    id=msg[6],
                    media_type=msg[7],
                )
            )

        return MessageContext(
            message=target_message, before=before_messages, after=after_messages
        )

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        raise
    finally:
        if "conn" in locals():
            conn.close()


def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active",
) -> List[Chat]:
    """Get chats matching the specified criteria."""
    try:
        conn = _open_message_store()
        cursor = conn.cursor()

        # The message columns are selected only alongside the join that supplies
        # them. Selecting them unconditionally made include_last_message=False fail
        # with "no such column: messages.content" for every caller.
        message_columns = (
            """,
                messages.content as last_message,
                messages.sender as last_sender,
                messages.is_from_me as last_is_from_me"""
            if include_last_message
            else ""
        )

        # Build base query
        query_parts = [
            f"""
            SELECT
                chats.jid,
                chats.name,
                chats.last_message_time{message_columns}
            FROM chats
        """
        ]

        if include_last_message:
            query_parts.append("""
                LEFT JOIN messages ON chats.jid = messages.chat_jid
                AND chats.last_message_time = messages.timestamp
            """)

        where_clauses = []
        params = []

        if query:
            where_clauses.append(
                "(LOWER(chats.name) LIKE LOWER(?) OR chats.jid LIKE ?)"
            )
            params.extend([f"%{query}%", f"%{query}%"])

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        # Add sorting
        order_by = (
            "chats.last_message_time DESC" if sort_by == "last_active" else "chats.name"
        )
        query_parts.append(f"ORDER BY {order_by}")

        # Add pagination
        offset = (page) * limit
        query_parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset])

        cursor.execute(" ".join(query_parts), tuple(params))
        chats = cursor.fetchall()

        result = []
        for chat_data in chats:
            chat = Chat(
                jid=chat_data[0],
                name=chat_data[1],
                last_message_time=datetime.fromisoformat(chat_data[2])
                if chat_data[2]
                else None,
                last_message=chat_data[3] if include_last_message else None,
                last_sender=chat_data[4] if include_last_message else None,
                last_is_from_me=chat_data[5] if include_last_message else None,
            )
            result.append(chat)

        if not result:
            _refuse_unexplained_empty("chats")

        return result

    except sqlite3.Error as e:
        raise WhatsAppError(f"Could not read chats from the message store: {e}") from e
    finally:
        if "conn" in locals():
            conn.close()


def search_contacts(query: str) -> List[Contact]:
    """Search contacts by name or phone number."""
    try:
        conn = _open_message_store()
        cursor = conn.cursor()

        # Split query into characters to support partial matching
        search_pattern = "%" + query + "%"

        cursor.execute(
            """
            SELECT DISTINCT
                jid,
                name
            FROM chats
            WHERE
                (LOWER(name) LIKE LOWER(?) OR LOWER(jid) LIKE LOWER(?))
                AND jid NOT LIKE '%@g.us'
            ORDER BY name, jid
            LIMIT 50
        """,
            (search_pattern, search_pattern),
        )

        contacts = cursor.fetchall()

        result = []
        for contact_data in contacts:
            contact = Contact(
                phone_number=contact_data[0].split("@")[0],
                name=contact_data[1],
                jid=contact_data[0],
            )
            result.append(contact)

        if not result:
            _refuse_unexplained_empty(f"contacts matching {query!r}")

        return result

    except sqlite3.Error as e:
        raise WhatsAppError(
            f"Could not search contacts in the message store: {e}"
        ) from e
    finally:
        if "conn" in locals():
            conn.close()


def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Chat]:
    """Get all chats involving the contact.

    Args:
        jid: The contact's JID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    try:
        conn = _open_message_store()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT
                c.jid,
                c.name,
                c.last_message_time,
                m.content as last_message,
                m.sender as last_sender,
                m.is_from_me as last_is_from_me
            FROM chats c
            JOIN messages m ON c.jid = m.chat_jid
            WHERE m.sender = ? OR c.jid = ?
            ORDER BY c.last_message_time DESC
            LIMIT ? OFFSET ?
        """,
            (jid, jid, limit, page * limit),
        )

        chats = cursor.fetchall()

        result = []
        for chat_data in chats:
            chat = Chat(
                jid=chat_data[0],
                name=chat_data[1],
                last_message_time=datetime.fromisoformat(chat_data[2])
                if chat_data[2]
                else None,
                last_message=chat_data[3],
                last_sender=chat_data[4],
                last_is_from_me=chat_data[5],
            )
            result.append(chat)

        if not result:
            _refuse_unexplained_empty(f"chats involving {jid}")

        return result

    except sqlite3.Error as e:
        raise WhatsAppError(
            f"Could not read chats for {jid} from the message store: {e}"
        ) from e
    finally:
        if "conn" in locals():
            conn.close()


def get_last_interaction(jid: str) -> str:
    """Get most recent message involving the contact."""
    try:
        conn = _open_message_store()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                m.timestamp,
                m.sender,
                c.name,
                m.content,
                m.is_from_me,
                c.jid,
                m.id,
                m.media_type
            FROM messages m
            JOIN chats c ON m.chat_jid = c.jid
            WHERE m.sender = ? OR c.jid = ?
            ORDER BY m.timestamp DESC
            LIMIT 1
        """,
            (jid, jid),
        )

        msg_data = cursor.fetchone()

        if not msg_data:
            _refuse_unexplained_empty(f"interaction with {jid}")
            return None

        message = Message(
            timestamp=datetime.fromisoformat(msg_data[0]),
            sender=msg_data[1],
            chat_name=msg_data[2],
            content=msg_data[3],
            is_from_me=msg_data[4],
            chat_jid=msg_data[5],
            id=msg_data[6],
            media_type=msg_data[7],
        )

        return format_message(message)

    except sqlite3.Error as e:
        raise WhatsAppError(
            f"Could not read the last interaction with {jid}: {e}"
        ) from e
    finally:
        if "conn" in locals():
            conn.close()


def get_chat(chat_jid: str, include_last_message: bool = True) -> Optional[Chat]:
    """Get chat metadata by JID."""
    try:
        conn = _open_message_store()
        cursor = conn.cursor()

        query = """
            SELECT
                c.jid,
                c.name,
                c.last_message_time,
                m.content as last_message,
                m.sender as last_sender,
                m.is_from_me as last_is_from_me
            FROM chats c
        """

        if include_last_message:
            query += """
                LEFT JOIN messages m ON c.jid = m.chat_jid
                AND c.last_message_time = m.timestamp
            """

        query += " WHERE c.jid = ?"

        cursor.execute(query, (chat_jid,))
        chat_data = cursor.fetchone()

        if not chat_data:
            _refuse_unexplained_empty(f"chat with JID {chat_jid}")
            return None

        return Chat(
            jid=chat_data[0],
            name=chat_data[1],
            last_message_time=datetime.fromisoformat(chat_data[2])
            if chat_data[2]
            else None,
            last_message=chat_data[3],
            last_sender=chat_data[4],
            last_is_from_me=chat_data[5],
        )

    except sqlite3.Error as e:
        raise WhatsAppError(f"Could not read chat {chat_jid}: {e}") from e
    finally:
        if "conn" in locals():
            conn.close()


def get_direct_chat_by_contact(sender_phone_number: str) -> Optional[Chat]:
    """Get chat metadata by sender phone number."""
    try:
        conn = _open_message_store()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                c.jid,
                c.name,
                c.last_message_time,
                m.content as last_message,
                m.sender as last_sender,
                m.is_from_me as last_is_from_me
            FROM chats c
            LEFT JOIN messages m ON c.jid = m.chat_jid
                AND c.last_message_time = m.timestamp
            WHERE c.jid LIKE ? AND c.jid NOT LIKE '%@g.us'
            LIMIT 1
        """,
            (f"%{sender_phone_number}%",),
        )

        chat_data = cursor.fetchone()

        if not chat_data:
            _refuse_unexplained_empty(f"direct chat with {sender_phone_number}")
            return None

        return Chat(
            jid=chat_data[0],
            name=chat_data[1],
            last_message_time=datetime.fromisoformat(chat_data[2])
            if chat_data[2]
            else None,
            last_message=chat_data[3],
            last_sender=chat_data[4],
            last_is_from_me=chat_data[5],
        )

    except sqlite3.Error as e:
        raise WhatsAppError(
            f"Could not read the direct chat for {sender_phone_number}: {e}"
        ) from e
    finally:
        if "conn" in locals():
            conn.close()


def send_message(recipient: str, message: str) -> Tuple[bool, str]:
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"

        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {
            "recipient": recipient,
            "message": message,
        }

        response = requests.post(url, json=payload)

        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get(
                "message", "Unknown response"
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"

    except requests.RequestException as e:
        return False, _describe_bridge_call_failure(e)
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def send_file(recipient: str, media_path: str) -> Tuple[bool, str]:
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"

        if not media_path:
            return False, "Media path must be provided"

        if not os.path.isfile(media_path):
            return False, f"Media file not found: {media_path}"

        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {"recipient": recipient, "media_path": media_path}

        response = requests.post(url, json=payload)

        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get(
                "message", "Unknown response"
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"

    except requests.RequestException as e:
        return False, _describe_bridge_call_failure(e)
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def send_audio_message(recipient: str, media_path: str) -> Tuple[bool, str]:
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"

        if not media_path:
            return False, "Media path must be provided"

        if not os.path.isfile(media_path):
            return False, f"Media file not found: {media_path}"

        if not media_path.endswith(".ogg"):
            try:
                media_path = audio.convert_to_opus_ogg_temp(media_path)
            except Exception as e:
                return (
                    False,
                    f"Error converting file to opus ogg. You likely need to install ffmpeg: {str(e)}",
                )

        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {"recipient": recipient, "media_path": media_path}

        response = requests.post(url, json=payload)

        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get(
                "message", "Unknown response"
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"

    except requests.RequestException as e:
        return False, _describe_bridge_call_failure(e)
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def download_media(message_id: str, chat_jid: str) -> Optional[str]:
    """Download media from a message and return the local file path.

    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message

    Returns:
        The local file path if the download succeeded.

    Raises:
        WhatsAppError: if the download did not succeed. A failure is never returned
            as None, because the caller cannot tell that apart from a message that
            simply has no media attached.
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/download"
        payload = {"message_id": message_id, "chat_jid": chat_jid}

        response = requests.post(url, json=payload)

        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                return result.get("path")
            raise WhatsAppError(
                f"The bridge could not download media for message {message_id}: "
                f"{result.get('message', 'Unknown error')}"
            )

        raise WhatsAppError(
            f"The bridge returned HTTP {response.status_code} downloading media for "
            f"message {message_id}: {response.text}"
        )

    except requests.RequestException as e:
        raise WhatsAppError(_describe_bridge_call_failure(e)) from e
    except json.JSONDecodeError as e:
        raise WhatsAppError(
            f"The bridge returned an unreadable download response: {response.text}"
        ) from e
