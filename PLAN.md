# CAMB AI + Pipecat Book Q&A Voice Agent - Implementation Plan

## Overview

A web app for marketing to demo CAMB TTS with a conversational book Q&A voice agent. Users upload a book (PDF/text), then have a voice conversation with the AI that can answer questions about the book and search the web for related topics.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Book Upload │  │ Connect/     │  │ Status Indicators      │ │
│  │ Component   │  │ Disconnect   │  │ STT → LLM → TTS        │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Chat Interface (transcript)                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↕ WebRTC                               │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (Python FastAPI)                     │
│  ┌────────────────────────────────────────────────────────────┐│
│  │                    Pipecat Pipeline                        ││
│  │  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌─────────────┐  ││
│  │  │Deepgram │→ │ Context │→ │ Gemini   │→ │  CAMB TTS   │  ││
│  │  │   STT   │  │  Aggr.  │  │Flash 2.5 │  │ mars-flash  │  ││
│  │  └─────────┘  └─────────┘  └──────────┘  └─────────────┘  ││
│  └────────────────────────────────────────────────────────────┘│
│  ┌────────────────────┐  ┌────────────────────────────────────┐│
│  │  Book RAG Storage  │  │  Function Calling: search_web()   ││
│  │  (in-memory/file)  │  │  via Exa API (LLM-controlled)     ││
│  └────────────────────┘  └────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Backend
- **Framework**: FastAPI + Pipecat
- **STT**: Deepgram (fast, accurate)
- **LLM**: Google Gemini 2.5 Flash (fast, function calling support)
- **TTS**: CAMB AI mars-flash (low latency, high quality)
- **Transport**: SmallWebRTC (browser-compatible)
- **Web Search**: Exa API (LLM-friendly, called via explicit function calling - NOT auto-triggered)

### Frontend
- **Framework**: React + Vite + TypeScript
- **Styling**: Tailwind CSS
- **WebRTC**: Native browser APIs
- **Audio**: Web Audio API

## Directory Structure

```
pipecat-web-app-example/
├── backend/
│   ├── bot.py                 # Main pipecat bot
│   ├── server.py              # FastAPI server with WebRTC endpoints
│   ├── book_processor.py      # PDF/text extraction and RAG
│   ├── web_search.py          # Exa web search function (explicit call)
│   ├── progress_tracker.py    # Custom processor for UI status updates
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── BookUpload.tsx
│   │   │   ├── VoiceControl.tsx    # Connect/Disconnect
│   │   │   ├── StatusIndicator.tsx # STT → LLM → TTS progress
│   │   │   └── ChatInterface.tsx   # Transcript display
│   │   ├── hooks/
│   │   │   └── useWebRTC.ts
│   │   └── styles/
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── docker-compose.yml
└── README.md
```

## Implementation Steps

### Phase 1: Backend Foundation

#### 1.1 Create FastAPI server with WebRTC endpoints
- `/api/upload-book` - POST endpoint for book upload
- `/api/offer` - WebRTC signaling endpoint
- `/api/status` - Health check
- Static file serving for frontend

#### 1.2 Implement book processor
- Extract text from PDF (PyPDF2) or plain text files
- Store book content in memory (per-session)
- Create system prompt with book context for RAG

#### 1.3 Build Pipecat pipeline
```python
Pipeline([
    transport.input(),           # WebRTC audio in
    stt,                         # Deepgram STT
    progress_tracker,            # Status updates to UI
    user_aggregator,             # Smart turn detection
    llm,                         # Gemini 2.5 Flash with function calling
    tts,                         # CAMB TTS mars-flash
    transport.output(),          # WebRTC audio out
    assistant_aggregator,
])
```

#### 1.4 Create progress tracker processor
- Send `OutputTransportMessageFrame` for status updates
- Track frames: `TranscriptionFrame` → `LLMFullResponseStartFrame` → `TTSStartedFrame`
- Emit JSON messages: `{"status": "stt"/"llm"/"tts", "text": "..."}`

#### 1.5 Implement web search function (Exa - explicit function call)
```python
# Registered as a tool the LLM can choose to call
search_web_function = FunctionSchema(
    name="search_web",
    description="Search the web for information not found in the book. Only use when the user asks about something outside the book's content.",
    properties={
        "query": {"type": "string", "description": "The search query"}
    },
    required=["query"]
)

async def search_web(params: FunctionCallParams):
    query = params.arguments["query"]
    results = await exa_client.search_and_contents(query, num_results=3)
    await params.result_callback({"results": format_results(results)})

llm.register_function("search_web", search_web)
```

### Phase 2: Frontend Implementation

#### 2.1 Create React app with Vite
- TypeScript configuration
- Tailwind CSS setup
- Basic layout structure

#### 2.2 Book upload component
- Drag-and-drop file upload
- Accept PDF and TXT files
- Show upload progress and confirmation
- Store book ID for session

#### 2.3 WebRTC hook
```typescript
useWebRTC({
  onConnected: () => void,
  onDisconnected: () => void,
  onMessage: (msg: StatusMessage) => void,
  onTranscript: (text: string, role: 'user' | 'assistant') => void
})
```

#### 2.4 Voice control component
- Large "Connect" button (green)
- "Disconnect" button (red) when connected
- Microphone permission handling
- Visual feedback for audio input levels

#### 2.5 Status indicator component
- Three-stage progress: STT → LLM → TTS
- Visual highlighting of current stage
- Pulse/glow animation for active stage

#### 2.6 Chat interface component
- Scrolling transcript view
- User messages (right-aligned, blue)
- Assistant messages (left-aligned, gray)
- Auto-scroll to latest message

### Phase 3: Integration & Polish

#### 3.1 Connect frontend to backend
- Book upload → backend storage
- WebRTC negotiation flow
- Status message handling
- Transcript synchronization

#### 3.2 Add guardrails to system prompt
```python
SYSTEM_PROMPT = f"""You are a helpful assistant that answers questions about this book:

{book_content}

IMPORTANT RULES:
1. Primarily answer questions about the book above
2. You have access to a search_web function - ONLY use it when the user explicitly asks about something not covered in the book
3. Keep responses concise (under 100 words) since they will be spoken aloud
4. Do not discuss topics completely unrelated to the book or its themes
5. If asked about something outside your scope, politely redirect to book-related topics
6. Never use emojis or special characters in your responses
"""
```

#### 3.3 Error handling
- Connection failures
- Microphone permission denied
- Backend errors
- Network interruptions

#### 3.4 UI polish
- Loading states
- Responsive design
- Keyboard accessibility
- Visual feedback for all interactions

## API Keys Required

| Service | Environment Variable | Purpose |
|---------|---------------------|---------|
| CAMB AI | `CAMB_API_KEY` | TTS |
| Deepgram | `DEEPGRAM_API_KEY` | STT |
| Google AI | `GOOGLE_API_KEY` | Gemini 2.5 Flash LLM |
| Exa | `EXA_API_KEY` | Web search (explicit function call) |

## Key Files to Reference

From pipecat repo:
- `/pipecat/examples/foundational/camb-webrtc-voice-agent.py` - WebRTC + CAMB pattern
- `/pipecat/examples/foundational/07zg-interruptible-camb.py` - Smart turn detection
- `/pipecat/examples/foundational/33-gemini-rag.py` - RAG pattern with Gemini
- `/pipecat/examples/foundational/14-function-calling.py` - Function calling pattern
- `/pipecat/examples/foundational/26e-gemini-live-google-search.py` - Gemini search reference

## Notes

- Use `mars-flash` model for low latency (22.05kHz sample rate)
- WebRTC STUN server: `stun:stun.l.google.com:19302`
- Book content stored in-memory per session (not persistent)
- Smart turn detection via `LocalSmartTurnAnalyzerV3` for natural conversation
- Web search is **explicitly controlled** via function calling - LLM decides when to call it based on user query, not auto-triggered
