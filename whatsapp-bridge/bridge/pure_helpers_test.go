package bridge

import (
	"bytes"
	"encoding/binary"
	"testing"

	waProto "go.mau.fi/whatsmeow/binary/proto"
	"google.golang.org/protobuf/proto"
)

func TestExtractDirectPathFromURL(t *testing.T) {
	t.Run("strips the host and query parameters", func(t *testing.T) {
		got := extractDirectPathFromURL(
			"https://mmg.whatsapp.net/v/t62.7118-24/media.enc?ccb=11-4&oh=value",
		)
		want := "/v/t62.7118-24/media.enc"
		if got != want {
			t.Fatalf("extractDirectPathFromURL() = %q, want %q", got, want)
		}
	})

	t.Run("preserves an unrecognized URL", func(t *testing.T) {
		const input = "https://example.com/media.enc?token=value"
		if got := extractDirectPathFromURL(input); got != input {
			t.Fatalf("extractDirectPathFromURL() = %q, want %q", got, input)
		}
	})
}

func TestExtractTextContent(t *testing.T) {
	t.Run("conversation text", func(t *testing.T) {
		message := &waProto.Message{Conversation: proto.String("hello")}
		if got := extractTextContent(message); got != "hello" {
			t.Fatalf("extractTextContent() = %q, want %q", got, "hello")
		}
	})

	t.Run("extended text", func(t *testing.T) {
		message := &waProto.Message{
			ExtendedTextMessage: &waProto.ExtendedTextMessage{
				Text: proto.String("expanded"),
			},
		}
		if got := extractTextContent(message); got != "expanded" {
			t.Fatalf("extractTextContent() = %q, want %q", got, "expanded")
		}
	})

	t.Run("nil message", func(t *testing.T) {
		if got := extractTextContent(nil); got != "" {
			t.Fatalf("extractTextContent(nil) = %q, want empty text", got)
		}
	})
}

func TestAnalyzeOggOpusRejectsInvalidData(t *testing.T) {
	duration, waveform, err := analyzeOggOpus([]byte("not an ogg stream"))
	if err == nil {
		t.Fatal("analyzeOggOpus() accepted invalid data")
	}
	if duration != 0 || waveform != nil {
		t.Fatalf(
			"analyzeOggOpus() returned duration=%d waveform=%v for invalid data",
			duration,
			waveform,
		)
	}
}

func TestAnalyzeOggOpusReadsOpusHeadAndGranuleDuration(t *testing.T) {
	const (
		preSkip       = uint16(312)
		sampleRate    = uint32(48_000)
		durationInSec = uint64(2)
	)
	data := make([]byte, 47)
	copy(data[0:4], "OggS")
	binary.LittleEndian.PutUint64(
		data[6:14],
		durationInSec*uint64(sampleRate)+uint64(preSkip),
	)
	data[26] = 1
	data[27] = 19
	copy(data[28:36], "OpusHead")
	data[36] = 1
	data[37] = 1
	binary.LittleEndian.PutUint16(data[38:40], preSkip)
	binary.LittleEndian.PutUint32(data[40:44], sampleRate)

	duration, waveform, err := analyzeOggOpus(data)
	if err != nil {
		t.Fatalf("analyzeOggOpus() returned an error: %v", err)
	}
	if duration != uint32(durationInSec) {
		t.Fatalf(
			"analyzeOggOpus() duration = %d, want %d",
			duration,
			durationInSec,
		)
	}
	if len(waveform) != 64 {
		t.Fatalf("analyzeOggOpus() waveform = %d bytes, want 64", len(waveform))
	}
}

func TestPlaceholderWaveformIsStableAndBounded(t *testing.T) {
	first := placeholderWaveform(42)
	second := placeholderWaveform(42)

	if len(first) != 64 {
		t.Fatalf("placeholderWaveform() returned %d bytes, want 64", len(first))
	}
	if !bytes.Equal(first, second) {
		t.Fatal("placeholderWaveform() is not stable for the same duration")
	}
	for index, sample := range first {
		if sample > 100 {
			t.Fatalf("waveform[%d] = %d, want a value at most 100", index, sample)
		}
	}
}
