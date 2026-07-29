package bridge

import (
	"context"
	"fmt"
	"os"
	"strings"
	"time"

	"go.mau.fi/whatsmeow"
	waProto "go.mau.fi/whatsmeow/binary/proto"
	"go.mau.fi/whatsmeow/types"
	"go.mau.fi/whatsmeow/types/events"
	waLog "go.mau.fi/whatsmeow/util/log"
	"google.golang.org/protobuf/proto"
)

// Extract text content from a message
func extractTextContent(msg *waProto.Message) string {
	if msg == nil {
		return ""
	}

	// Try to get text content
	if text := msg.GetConversation(); text != "" {
		return text
	} else if extendedText := msg.GetExtendedTextMessage(); extendedText != nil {
		return extendedText.GetText()
	}

	// For now, we're ignoring non-text messages
	return ""
}

// Function to send a WhatsApp message
func sendWhatsAppMessage(client *whatsmeow.Client, recipient string, message string, mediaPath string) (bool, string) {
	if !client.IsConnected() {
		return false, "Not connected to WhatsApp"
	}

	// Create JID for recipient
	var recipientJID types.JID
	var err error

	// Check if recipient is a JID
	isJID := strings.Contains(recipient, "@")

	if isJID {
		// Parse the JID string
		recipientJID, err = types.ParseJID(recipient)
		if err != nil {
			return false, fmt.Sprintf("Error parsing JID: %v", err)
		}
	} else {
		// Create JID from phone number
		recipientJID = types.JID{
			User:   recipient,
			Server: "s.whatsapp.net", // For personal chats
		}
	}

	msg := &waProto.Message{}

	// Check if we have media to send
	if mediaPath != "" {
		// Read media file
		mediaData, err := os.ReadFile(mediaPath)
		if err != nil {
			return false, fmt.Sprintf("Error reading media file: %v", err)
		}

		// Determine media type and mime type based on file extension
		fileExt := strings.ToLower(mediaPath[strings.LastIndex(mediaPath, ".")+1:])
		var mediaType whatsmeow.MediaType
		var mimeType string

		// Handle different media types
		switch fileExt {
		// Image types
		case "jpg", "jpeg":
			mediaType = whatsmeow.MediaImage
			mimeType = "image/jpeg"
		case "png":
			mediaType = whatsmeow.MediaImage
			mimeType = "image/png"
		case "gif":
			mediaType = whatsmeow.MediaImage
			mimeType = "image/gif"
		case "webp":
			mediaType = whatsmeow.MediaImage
			mimeType = "image/webp"

		// Audio types
		case "ogg":
			mediaType = whatsmeow.MediaAudio
			mimeType = "audio/ogg; codecs=opus"

		// Video types
		case "mp4":
			mediaType = whatsmeow.MediaVideo
			mimeType = "video/mp4"
		case "avi":
			mediaType = whatsmeow.MediaVideo
			mimeType = "video/avi"
		case "mov":
			mediaType = whatsmeow.MediaVideo
			mimeType = "video/quicktime"

		// Document types (for any other file type)
		default:
			mediaType = whatsmeow.MediaDocument
			mimeType = "application/octet-stream"
		}

		// Upload media to WhatsApp servers
		resp, err := client.Upload(context.Background(), mediaData, mediaType)
		if err != nil {
			return false, fmt.Sprintf("Error uploading media: %v", err)
		}

		fmt.Println("Media uploaded", resp)

		// Create the appropriate message type based on media type
		switch mediaType {
		case whatsmeow.MediaImage:
			msg.ImageMessage = &waProto.ImageMessage{
				Caption:       proto.String(message),
				Mimetype:      proto.String(mimeType),
				URL:           &resp.URL,
				DirectPath:    &resp.DirectPath,
				MediaKey:      resp.MediaKey,
				FileEncSHA256: resp.FileEncSHA256,
				FileSHA256:    resp.FileSHA256,
				FileLength:    &resp.FileLength,
			}
		case whatsmeow.MediaAudio:
			// Handle ogg audio files
			var seconds uint32 = 30 // Default fallback
			var waveform []byte = nil

			// Try to analyze the ogg file
			if strings.Contains(mimeType, "ogg") {
				analyzedSeconds, analyzedWaveform, err := analyzeOggOpus(mediaData)
				if err == nil {
					seconds = analyzedSeconds
					waveform = analyzedWaveform
				} else {
					return false, fmt.Sprintf("Failed to analyze Ogg Opus file: %v", err)
				}
			} else {
				fmt.Printf("Not an Ogg Opus file: %s\n", mimeType)
			}

			msg.AudioMessage = &waProto.AudioMessage{
				Mimetype:      proto.String(mimeType),
				URL:           &resp.URL,
				DirectPath:    &resp.DirectPath,
				MediaKey:      resp.MediaKey,
				FileEncSHA256: resp.FileEncSHA256,
				FileSHA256:    resp.FileSHA256,
				FileLength:    &resp.FileLength,
				Seconds:       proto.Uint32(seconds),
				PTT:           proto.Bool(true),
				Waveform:      waveform,
			}
		case whatsmeow.MediaVideo:
			msg.VideoMessage = &waProto.VideoMessage{
				Caption:       proto.String(message),
				Mimetype:      proto.String(mimeType),
				URL:           &resp.URL,
				DirectPath:    &resp.DirectPath,
				MediaKey:      resp.MediaKey,
				FileEncSHA256: resp.FileEncSHA256,
				FileSHA256:    resp.FileSHA256,
				FileLength:    &resp.FileLength,
			}
		case whatsmeow.MediaDocument:
			msg.DocumentMessage = &waProto.DocumentMessage{
				Title:         proto.String(mediaPath[strings.LastIndex(mediaPath, "/")+1:]),
				Caption:       proto.String(message),
				Mimetype:      proto.String(mimeType),
				URL:           &resp.URL,
				DirectPath:    &resp.DirectPath,
				MediaKey:      resp.MediaKey,
				FileEncSHA256: resp.FileEncSHA256,
				FileSHA256:    resp.FileSHA256,
				FileLength:    &resp.FileLength,
			}
		}
	} else {
		msg.Conversation = proto.String(message)
	}

	// Send message
	_, err = client.SendMessage(context.Background(), recipientJID, msg)

	if err != nil {
		return false, fmt.Sprintf("Error sending message: %v", err)
	}

	return true, fmt.Sprintf("Message sent to %s", recipient)
}

// Extract media info from a message
func extractMediaInfo(msg *waProto.Message) (mediaType string, filename string, url string, mediaKey []byte, fileSHA256 []byte, fileEncSHA256 []byte, fileLength uint64) {
	if msg == nil {
		return "", "", "", nil, nil, nil, 0
	}

	// Check for image message
	if img := msg.GetImageMessage(); img != nil {
		return "image", "image_" + time.Now().Format("20060102_150405") + ".jpg",
			img.GetURL(), img.GetMediaKey(), img.GetFileSHA256(), img.GetFileEncSHA256(), img.GetFileLength()
	}

	// Check for video message
	if vid := msg.GetVideoMessage(); vid != nil {
		return "video", "video_" + time.Now().Format("20060102_150405") + ".mp4",
			vid.GetURL(), vid.GetMediaKey(), vid.GetFileSHA256(), vid.GetFileEncSHA256(), vid.GetFileLength()
	}

	// Check for audio message
	if aud := msg.GetAudioMessage(); aud != nil {
		return "audio", "audio_" + time.Now().Format("20060102_150405") + ".ogg",
			aud.GetURL(), aud.GetMediaKey(), aud.GetFileSHA256(), aud.GetFileEncSHA256(), aud.GetFileLength()
	}

	// Check for document message
	if doc := msg.GetDocumentMessage(); doc != nil {
		filename := doc.GetFileName()
		if filename == "" {
			filename = "document_" + time.Now().Format("20060102_150405")
		}
		return "document", filename,
			doc.GetURL(), doc.GetMediaKey(), doc.GetFileSHA256(), doc.GetFileEncSHA256(), doc.GetFileLength()
	}

	return "", "", "", nil, nil, nil, 0
}

// Handle regular incoming messages with media support
func handleMessage(client *whatsmeow.Client, messageStore *MessageStore, msg *events.Message, logger waLog.Logger) {
	// Save message to database
	chatJID := msg.Info.Chat.String()
	sender := msg.Info.Sender.User

	// Get appropriate chat name (pass nil for conversation since we don't have one for regular messages)
	name := GetChatName(client, messageStore, msg.Info.Chat, chatJID, nil, sender, logger)

	// Update chat in database with the message timestamp (keeps last message time updated)
	err := messageStore.StoreChat(chatJID, name, msg.Info.Timestamp)
	if err != nil {
		logger.Warnf("Failed to store chat: %v", err)
	}

	// Extract text content
	content := extractTextContent(msg.Message)

	// Extract media info
	mediaType, filename, url, mediaKey, fileSHA256, fileEncSHA256, fileLength := extractMediaInfo(msg.Message)

	// Skip if there's no content and no media
	if content == "" && mediaType == "" {
		return
	}

	// Store message in database
	err = messageStore.StoreMessage(
		msg.Info.ID,
		chatJID,
		sender,
		content,
		msg.Info.Timestamp,
		msg.Info.IsFromMe,
		mediaType,
		filename,
		url,
		mediaKey,
		fileSHA256,
		fileEncSHA256,
		fileLength,
	)

	if err != nil {
		logger.Warnf("Failed to store message: %v", err)
	} else {
		// Log message reception
		timestamp := msg.Info.Timestamp.Format("2006-01-02 15:04:05")
		direction := "←"
		if msg.Info.IsFromMe {
			direction = "→"
		}

		// Log based on message type
		if mediaType != "" {
			fmt.Printf("[%s] %s %s: [%s: %s] %s\n", timestamp, direction, sender, mediaType, filename, content)
		} else if content != "" {
			fmt.Printf("[%s] %s %s: %s\n", timestamp, direction, sender, content)
		}
	}
}
