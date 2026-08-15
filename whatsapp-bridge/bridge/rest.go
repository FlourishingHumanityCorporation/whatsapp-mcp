package bridge

import (
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"time"

	"go.mau.fi/whatsmeow"
)

// SendMessageResponse represents the response for the send message API
type SendMessageResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
}

// SendMessageRequest represents the request body for the send message API
type SendMessageRequest struct {
	Recipient string `json:"recipient"`
	Message   string `json:"message"`
	MediaPath string `json:"media_path,omitempty"`
}

// DownloadMediaRequest represents the request body for the download media API
type DownloadMediaRequest struct {
	MessageID string `json:"message_id"`
	ChatJID   string `json:"chat_jid"`
}

// DownloadMediaResponse represents the response for the download media API
type DownloadMediaResponse struct {
	Success  bool   `json:"success"`
	Message  string `json:"message"`
	Filename string `json:"filename,omitempty"`
	Path     string `json:"path,omitempty"`
}

// HealthResponse reports whether the bridge can currently reach WhatsApp, and how
// recent the stored history is. Readers of the local store need this: without it a
// stale or empty answer is indistinguishable from a bridge that is not connected.
type HealthResponse struct {
	Connected       bool   `json:"connected"`
	LoggedIn        bool   `json:"logged_in"`
	LastMessageTime string `json:"last_message_time,omitempty"`
}

// ensureRESTPortFree reports whether another service already answers on the port.
//
// It dials rather than test-binding, because on macOS a bind CANNOT detect this.
// Measured 2026-08-15 against a service holding 0.0.0.0:8080: binding ":8080"
// succeeded because a bare port takes the IPv6 wildcard, a different address
// family; and binding "127.0.0.1:8080" also succeeded, because BSD SO_REUSEADDR
// allows a specific address beside a bound wildcard. Both left two services
// sharing one port, with the winner decided by name resolution and match
// specificity. Connecting is a positive check, so it does not care how the other
// listener was bound.
//
// This is a guard against an operator mistake on a single-user machine, not
// against a racing adversary: a service that binds without accepting is missed,
// and the port could be taken between this check and the bind below.
func ensureRESTPortFree(port int) error {
	address := fmt.Sprintf("127.0.0.1:%d", port)

	connection, err := net.DialTimeout("tcp", address, 500*time.Millisecond)
	if err != nil {
		// Nothing accepted, which is what we want.
		return nil
	}
	connection.Close()

	return fmt.Errorf(
		"another service is already answering on %s, so the bridge would share the "+
			"port with it instead of owning it", address,
	)
}

// bindRESTListener claims the REST port on loopback.
//
// The address is 127.0.0.1 rather than a bare ":port" so that an unauthenticated
// API which can send messages does not listen on every interface, including the
// LAN.
func bindRESTListener(port int) (net.Listener, error) {
	serverAddr := fmt.Sprintf("127.0.0.1:%d", port)

	listener, err := net.Listen("tcp", serverAddr)
	if err != nil {
		return nil, fmt.Errorf("could not bind the REST API to %s: %w", serverAddr, err)
	}

	return listener, nil
}

// Start a REST API server to expose the WhatsApp client functionality
func startRESTServer(client *whatsmeow.Client, messageStore *MessageStore, listener net.Listener) {
	// Handler for sending messages
	http.HandleFunc("/api/send", func(w http.ResponseWriter, r *http.Request) {
		// Only allow POST requests
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Parse the request body
		var req SendMessageRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid request format", http.StatusBadRequest)
			return
		}

		// Validate request
		if req.Recipient == "" {
			http.Error(w, "Recipient is required", http.StatusBadRequest)
			return
		}

		if req.Message == "" && req.MediaPath == "" {
			http.Error(w, "Message or media path is required", http.StatusBadRequest)
			return
		}

		fmt.Println("Received request to send message", req.Message, req.MediaPath)

		// Send the message
		success, message := sendWhatsAppMessage(client, req.Recipient, req.Message, req.MediaPath)
		fmt.Println("Message sent", success, message)
		// Set response headers
		w.Header().Set("Content-Type", "application/json")

		// Set appropriate status code
		if !success {
			w.WriteHeader(http.StatusInternalServerError)
		}

		// Send response
		json.NewEncoder(w).Encode(SendMessageResponse{
			Success: success,
			Message: message,
		})
	})

	// Handler for reporting bridge liveness
	http.HandleFunc("/api/health", func(w http.ResponseWriter, r *http.Request) {
		// Only allow GET requests
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		response := HealthResponse{
			Connected: client.IsConnected(),
			LoggedIn:  client.IsLoggedIn(),
		}

		// Staleness is reported when it can be read; failing to read it must not
		// take down the liveness answer the caller actually asked for.
		lastMessageTime, err := messageStore.GetLastMessageTime()
		if err != nil {
			fmt.Printf("Health check could not read last message time: %v\n", err)
		} else if !lastMessageTime.IsZero() {
			response.LastMessageTime = lastMessageTime.Format(time.RFC3339)
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	})

	// Handler for downloading media
	http.HandleFunc("/api/download", func(w http.ResponseWriter, r *http.Request) {
		// Only allow POST requests
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Parse the request body
		var req DownloadMediaRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid request format", http.StatusBadRequest)
			return
		}

		// Validate request
		if req.MessageID == "" || req.ChatJID == "" {
			http.Error(w, "Message ID and Chat JID are required", http.StatusBadRequest)
			return
		}

		// Download the media
		success, mediaType, filename, path, err := downloadMedia(client, messageStore, req.MessageID, req.ChatJID)

		// Set response headers
		w.Header().Set("Content-Type", "application/json")

		// Handle download result
		if !success || err != nil {
			errMsg := "Unknown error"
			if err != nil {
				errMsg = err.Error()
			}

			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(DownloadMediaResponse{
				Success: false,
				Message: fmt.Sprintf("Failed to download media: %s", errMsg),
			})
			return
		}

		// Send successful response
		json.NewEncoder(w).Encode(DownloadMediaResponse{
			Success:  true,
			Message:  fmt.Sprintf("Successfully downloaded %s media", mediaType),
			Filename: filename,
			Path:     path,
		})
	})

	// Start the server on the already-bound listener
	fmt.Printf("Starting REST API server on %s...\n", listener.Addr())

	// Serve in a goroutine so it doesn't block, now that the port is ours
	go func() {
		if err := http.Serve(listener, nil); err != nil {
			fmt.Printf("REST API server error: %v\n", err)
		}
	}()
}
