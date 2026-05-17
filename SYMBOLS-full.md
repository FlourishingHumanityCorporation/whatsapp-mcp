# whatsapp-mcp Symbol Reference

Auto-generated symbol index for Claude Code navigation.
Regenerate with: `regenerate-symbols` or `/symbols`

---

## 1. Whatsapp Mcp Server

**whatsapp-mcp-server/audio.py**

| Symbol | Type | Line | Description |
|--------|------|------|-------------|
| `convert_to_opus_ogg(input_file, output_file = None, bitrate = '32k', sample_rate = 24000)` | function | 5 | Convert an audio file to Opus format in an Ogg container. |
| `convert_to_opus_ogg_temp(input_file, bitrate = '32k', sample_rate = 24000)` | function | 64 | Convert an audio file to Opus format in an Ogg container ... |

**whatsapp-mcp-server/main.py**

| Symbol | Type | Line | Description |
|--------|------|------|-------------|
| `search_contacts(query: str) -> List[Dict[str, Any]]` | function | 22 | Search WhatsApp contacts by name or phone number. |
| `list_messages(after: Optional[str] = None, before: Optional[str] = None, sender_phone_number: Optional[str] = None, chat_jid: Optional[str] = None, query: Optional[str] = None, limit: int = 20, page: int = 0, include_context: bool = True, context_before: int = 1, context_after: int = 1) -> List[Dict[str, Any]]` | function | 32 | Get WhatsApp messages matching specified criteria with op... |
| `list_chats(query: Optional[str] = None, limit: int = 20, page: int = 0, include_last_message: bool = True, sort_by: str = 'last_active') -> List[Dict[str, Any]]` | function | 73 | Get WhatsApp chats matching specified criteria. |
| `get_chat(chat_jid: str, include_last_message: bool = True) -> Dict[str, Any]` | function | 99 | Get WhatsApp chat metadata by JID. |
| `get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]` | function | 110 | Get WhatsApp chat metadata by sender phone number. |
| `get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]` | function | 120 | Get all WhatsApp chats involving the contact. |
| `get_last_interaction(jid: str) -> str` | function | 132 | Get most recent WhatsApp message involving the contact. |
| `get_message_context(message_id: str, before: int = 5, after: int = 5) -> Dict[str, Any]` | function | 142 | Get context around a specific WhatsApp message. |
| `send_message(recipient: str, message: str) -> Dict[str, Any]` | function | 158 | Send a WhatsApp message to a person or group. For group c... |
| `send_file(recipient: str, media_path: str) -> Dict[str, Any]` | function | 187 | Send a file such as a picture, raw audio, video or docume... |
| `send_audio_message(recipient: str, media_path: str) -> Dict[str, Any]` | function | 207 | Send any audio file as a WhatsApp audio message to the sp... |
| `download_media(message_id: str, chat_jid: str) -> Dict[str, Any]` | function | 225 | Download media from a WhatsApp message and get the local ... |

**whatsapp-mcp-server/whatsapp.py**

| Symbol | Type | Line | Description |
|--------|------|------|-------------|
| `MESSAGES_DB_PATH` | constant | 10 |  |
| `WHATSAPP_API_BASE_URL` | constant | 11 |  |
| `Message` | class | 14 |  |
| `Chat` | class | 25 |  |
| `is_group() -> bool` | method | 34 | Determine if chat is a group based on JID pattern. |
| `Contact` | class | 39 |  |
| `MessageContext` | class | 45 |  |
| `get_sender_name(sender_jid: str) -> str` | function | 50 |  |
| `format_message(message: Message, show_chat_info: bool = True) -> None` | function | 94 | Print a single message with consistent formatting. |
| `format_messages_list(messages: List[Message], show_chat_info: bool = True) -> None` | function | 114 |  |
| `list_messages(after: Optional[str] = None, before: Optional[str] = None, sender_phone_number: Optional[str] = None, chat_jid: Optional[str] = None, query: Optional[str] = None, limit: int = 20, page: int = 0, include_context: bool = True, context_before: int = 1, context_after: int = 1) -> List[Message]` | function | 124 | Get messages matching the specified criteria with optiona... |
| `get_message_context(message_id: str, before: int = 5, after: int = 5) -> MessageContext` | function | 226 | Get context around a specific message. |
| `list_chats(query: Optional[str] = None, limit: int = 20, page: int = 0, include_last_message: bool = True, sort_by: str = 'last_active') -> List[Chat]` | function | 319 | Get chats matching the specified criteria. |
| `search_contacts(query: str) -> List[Contact]` | function | 393 | Search contacts by name or phone number. |
| `get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Chat]` | function | 435 | Get all chats involving the contact. |
| `get_last_interaction(jid: str) -> str` | function | 486 | Get most recent message involving the contact. |
| `get_chat(chat_jid: str, include_last_message: bool = True) -> Optional[Chat]` | function | 535 | Get chat metadata by JID. |
| `get_direct_chat_by_contact(sender_phone_number: str) -> Optional[Chat]` | function | 583 | Get chat metadata by sender phone number. |
| `send_message(recipient: str, message: str) -> Tuple[bool, str]` | function | 625 |  |
| `send_file(recipient: str, media_path: str) -> Tuple[bool, str]` | function | 653 |  |
| `send_audio_message(recipient: str, media_path: str) -> Tuple[bool, str]` | function | 687 |  |
| `download_media(message_id: str, chat_jid: str) -> Optional[str]` | function | 727 | Download media from a message and return the local file p... |

---
