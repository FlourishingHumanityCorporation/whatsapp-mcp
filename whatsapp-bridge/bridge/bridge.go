package bridge

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/mdp/qrterminal"
	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/store/sqlstore"
	"go.mau.fi/whatsmeow/types/events"
	waLog "go.mau.fi/whatsmeow/util/log"
)

// DefaultRESTPort is the historical REST port. It is not owned in the workspace
// port registry and collides with other local services, so it can be overridden.
const DefaultRESTPort = 8080

// restPort resolves the REST port from WHATSAPP_BRIDGE_PORT.
//
// An unusable value is an error rather than a fallback to the default: silently
// serving on a port the operator did not choose is how a bridge ends up looking
// healthy while nothing can reach it.
func restPort() (int, error) {
	raw := os.Getenv("WHATSAPP_BRIDGE_PORT")
	if raw == "" {
		return DefaultRESTPort, nil
	}

	port, err := strconv.Atoi(raw)
	if err != nil || port < 1 || port > 65535 {
		return 0, fmt.Errorf("WHATSAPP_BRIDGE_PORT must be a port number between 1 and 65535, got %q", raw)
	}

	return port, nil
}

func Run() {
	// Set up logger
	logger := waLog.Stdout("Client", "INFO", true)
	logger.Infof("Starting WhatsApp client...")

	// Check the REST port before touching WhatsApp, so a conflict is reported
	// without first walking the operator through a QR scan. The port is only
	// claimed once connected: holding it through the pairing wait would accept
	// connections meant for whatever else uses it, and answer none of them.
	port, err := restPort()
	if err != nil {
		logger.Errorf("%v", err)
		return
	}

	if err := ensureRESTPortFree(port); err != nil {
		logger.Errorf("%v", err)
		logger.Errorf(
			"Set WHATSAPP_BRIDGE_PORT to a free port and point the MCP server at it "+
				"with WHATSAPP_BRIDGE_URL=http://localhost:<port>/api",
		)
		return
	}

	// Create database connection for storing session data
	dbLog := waLog.Stdout("Database", "INFO", true)

	// Create directory for database if it doesn't exist
	if err := os.MkdirAll("store", 0755); err != nil {
		logger.Errorf("Failed to create store directory: %v", err)
		return
	}

	container, err := sqlstore.New(context.Background(), "sqlite3", "file:store/whatsapp.db?_foreign_keys=on", dbLog)
	if err != nil {
		logger.Errorf("Failed to connect to database: %v", err)
		return
	}

	// Get device store - This contains session information
	deviceStore, err := container.GetFirstDevice(context.Background())
	if err != nil {
		if err == sql.ErrNoRows {
			// No device exists, create one
			deviceStore = container.NewDevice()
			logger.Infof("Created new device")
		} else {
			logger.Errorf("Failed to get device: %v", err)
			return
		}
	}

	// Create client instance
	client := whatsmeow.NewClient(deviceStore, logger)
	if client == nil {
		logger.Errorf("Failed to create WhatsApp client")
		return
	}

	// Initialize message store
	messageStore, err := NewMessageStore()
	if err != nil {
		logger.Errorf("Failed to initialize message store: %v", err)
		return
	}
	defer messageStore.Close()

	// Setup event handling for messages and history sync
	client.AddEventHandler(func(evt interface{}) {
		switch v := evt.(type) {
		case *events.Message:
			// Process regular messages
			handleMessage(client, messageStore, v, logger)

		case *events.HistorySync:
			// Process history sync events
			handleHistorySync(client, messageStore, v, logger)

		case *events.Connected:
			logger.Infof("Connected to WhatsApp")

		case *events.LoggedOut:
			logger.Warnf("Device logged out, please scan QR code to log in again")
		}
	})

	// Create channel to track connection success
	connected := make(chan bool, 1)

	// Connect to WhatsApp
	if client.Store.ID == nil {
		// No ID stored, this is a new client, need to pair with phone
		qrChan, _ := client.GetQRChannel(context.Background())
		err = client.Connect()
		if err != nil {
			logger.Errorf("Failed to connect: %v", err)
			return
		}

		// Print QR code for pairing with phone
		for evt := range qrChan {
			if evt.Event == "code" {
				fmt.Println("\nScan this QR code with your WhatsApp app:")
				qrterminal.GenerateHalfBlock(evt.Code, qrterminal.L, os.Stdout)
				// Also save QR data to file for external QR generation
				os.WriteFile("/tmp/whatsapp-qr.txt", []byte(evt.Code), 0644)
				fmt.Println("\nQR data saved to /tmp/whatsapp-qr.txt")
			} else if evt.Event == "success" {
				connected <- true
				break
			}
		}

		// Wait for connection
		select {
		case <-connected:
			fmt.Println("\nSuccessfully connected and authenticated!")
		case <-time.After(3 * time.Minute):
			logger.Errorf("Timeout waiting for QR code scan")
			return
		}
	} else {
		// Already logged in, just connect
		err = client.Connect()
		if err != nil {
			logger.Errorf("Failed to connect: %v", err)
			return
		}
		connected <- true
	}

	// Wait a moment for connection to stabilize
	time.Sleep(2 * time.Second)

	if !client.IsConnected() {
		logger.Errorf("Failed to establish stable connection")
		return
	}

	fmt.Println("\n✓ Connected to WhatsApp! Type 'help' for commands.")

	// Start REST API server on the port checked before pairing
	listener, err := bindRESTListener(port)
	if err != nil {
		// Continuing would leave a connected bridge whose send, download and health
		// endpoints are unreachable, with the reason in a log nobody reads.
		logger.Errorf("%v", err)
		client.Disconnect()
		return
	}
	defer listener.Close()

	startRESTServer(client, messageStore, listener)

	// Create a channel to keep the main goroutine alive
	exitChan := make(chan os.Signal, 1)
	signal.Notify(exitChan, syscall.SIGINT, syscall.SIGTERM)

	fmt.Println("REST server is running. Press Ctrl+C to disconnect and exit.")

	// Wait for termination signal
	<-exitChan

	fmt.Println("Disconnecting...")
	// Disconnect client
	client.Disconnect()
}
