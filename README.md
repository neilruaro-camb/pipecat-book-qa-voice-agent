# Book Q&A Voice Agent

A voice AI web app for Q&A conversations about uploaded books. Powered by CAMB AI TTS + Pipecat + Gemini Flash.

## Features

- **Book Upload**: Upload PDF or TXT files directly to Gemini's File API (up to 10MB)
- **Native Document Understanding**: Gemini reads your documents directly - no text extraction needed
- **Voice Conversation**: Real-time voice chat with the AI using WebRTC
- **Pipeline Status**: Visual indicators showing STT -> LLM -> TTS progress
- **Web Search**: AI can search the web when asked about topics outside the document
- **Chat Interface**: Full conversation transcript displayed in real-time

## Tech Stack

- **Backend**: Python + FastAPI + Pipecat
- **Frontend**: React + Vite + TypeScript + Tailwind CSS
- **STT**: Deepgram
- **LLM**: Google Gemini Flash 2.5
- **TTS**: CAMB AI (mars-flash model)
- **Transport**: WebRTC (SmallWebRTC)

## Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 18+
- API keys for:
  - [CAMB AI](https://camb.ai) - `CAMB_API_KEY`
  - [Deepgram](https://deepgram.com) - `DEEPGRAM_API_KEY`
  - [Google AI](https://aistudio.google.com/apikey) - `GOOGLE_API_KEY`
  - [Exa](https://exa.ai) (optional, for web search) - `EXA_API_KEY`

### Backend Setup

```bash
cd backend

# Copy environment file and add your API keys
cp .env.example .env
# Edit .env with your API keys

# Install dependencies and run the server
uv run server.py
```

The backend will start on http://localhost:7860

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend will start on http://localhost:3000

### Production Build

```bash
cd frontend
npm run build
```

The built files will be in `frontend/dist/` and automatically served by the backend.

## Usage

1. Open http://localhost:3000 (or http://localhost:7860 if using production build)
2. Upload a book (PDF or TXT file)
3. Click the green microphone button to connect
4. Start asking questions about the book
5. The AI will respond using voice

## Architecture

```
Frontend (React)
    │
    ├── Book Upload → POST /api/session/{id}/upload-book
    │
    └── WebRTC Audio ←→ /api/offer
                           │
                           ↓
Backend (Pipecat Pipeline)
    │
    ├── Deepgram STT (speech → text)
    ├── Progress Tracker (status updates → frontend)
    ├── Gemini Flash LLM (text → response)
    │   └── Function Calling → Exa Web Search
    └── CAMB TTS (response → speech)
```

## API Endpoints

- `POST /api/session` - Create a new session
- `POST /api/session/{id}/upload-book` - Upload a book for the session
- `POST /api/session/{id}/clear-book` - Clear the uploaded book
- `POST /api/offer` - WebRTC signaling endpoint
- `GET /api/health` - Health check

## Customization

### Change TTS Voice

Edit `backend/bot.py`:
```python
tts = CambTTSService(
    api_key=os.getenv("CAMB_API_KEY"),
    model="mars-flash",  # or "mars-pro" for higher quality
    voice_id=YOUR_VOICE_ID,  # Get from CAMB AI dashboard
)
```

### Adjust Guardrails

Edit the system prompt in `backend/bot.py` in the `get_system_prompt()` function.

### Disable Web Search

Remove the `search_web` function registration and tools from `backend/bot.py`.

## Troubleshooting

**Microphone not working?**
- Make sure you've granted microphone permissions in your browser
- Check that no other application is using the microphone

**Connection failing?**
- Verify all API keys are set correctly in `.env`
- Check the backend console for error messages

**Audio choppy or delayed?**
- Try using a different browser (Chrome recommended)
- Check your network connection
