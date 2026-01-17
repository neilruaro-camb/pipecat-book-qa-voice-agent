"""Progress tracker processors for sending status updates to the frontend."""

import time
from typing import Optional

from loguru import logger

from pipecat.frames.frames import (
    Frame,
    TranscriptionFrame,
    LLMFullResponseStartFrame,
    LLMFullResponseEndFrame,
    LLMTextFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
    TTSSpeakFrame,
    OutputTransportMessageFrame,
    InterimTranscriptionFrame,
    StartInterruptionFrame,
)
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection


class STTProgressProcessor(FrameProcessor):
    """Tracks STT progress - place after STT in pipeline.

    Handles:
    - InterimTranscriptionFrame: User is speaking
    - TranscriptionFrame: Final transcription received
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._user_message_id: int = 0

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, InterimTranscriptionFrame):
            # User is speaking - show listening state
            await self._send_status("listening", frame.text)

        elif isinstance(frame, TranscriptionFrame):
            # Final transcription received - STT complete
            self._user_message_id += 1
            await self._send_status("stt", frame.text)
            await self._send_log(f"STT: \"{frame.text[:50]}{'...' if len(frame.text) > 50 else ''}\"")
            # Send user transcript with unique ID
            await self._send_transcript("user", frame.text, final=True, message_id=self._user_message_id)
            # Immediately transition to LLM status
            await self._send_status("llm")
            await self._send_log("Sending to LLM...")

        # Always pass the frame through
        await self.push_frame(frame, direction)

    async def _send_status(self, status: str, text: Optional[str] = None):
        """Send a status update to the frontend."""
        message = {"type": "status", "status": status}
        if text:
            message["text"] = text
        logger.debug(f"Sending status: {status}")
        await self.push_frame(
            OutputTransportMessageFrame(message=message),
            FrameDirection.DOWNSTREAM,
        )

    async def _send_transcript(
        self,
        role: str,
        text: str,
        final: bool = True,
        message_id: Optional[int] = None
    ):
        """Send a transcript update to the frontend."""
        message = {
            "type": "transcript",
            "role": role,
            "text": text,
            "final": final,
            "timestamp": int(time.time() * 1000),  # Unix timestamp in milliseconds
        }
        if message_id is not None:
            message["messageId"] = message_id
        logger.info(f"Sending transcript: role={role}, final={final}, text_len={len(text)}, messageId={message_id}")
        await self.push_frame(
            OutputTransportMessageFrame(message=message),
            FrameDirection.DOWNSTREAM,
        )

    async def _send_log(self, text: str):
        """Send a log message to the frontend."""
        await self.push_frame(
            OutputTransportMessageFrame(message={"type": "log", "text": text}),
            FrameDirection.DOWNSTREAM,
        )


class LLMProgressProcessor(FrameProcessor):
    """Tracks LLM progress - place after LLM in pipeline.

    Handles:
    - LLMFullResponseStartFrame: LLM started generating
    - LLMTextFrame: Streaming text chunks
    - LLMFullResponseEndFrame: LLM finished
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._assistant_text: str = ""
        self._assistant_message_id: int = 0

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMFullResponseStartFrame):
            # LLM started streaming response - start new message
            self._assistant_text = ""
            self._assistant_message_id += 1
            await self._send_log("LLM streaming response...")

        elif isinstance(frame, LLMTextFrame):
            # Accumulate and stream assistant text
            self._assistant_text += frame.text
            # Send streaming update
            await self._send_transcript(
                "assistant",
                self._assistant_text,
                final=False,
                message_id=self._assistant_message_id
            )

        elif isinstance(frame, LLMFullResponseEndFrame):
            # LLM finished - mark message as final
            if self._assistant_text:
                await self._send_transcript(
                    "assistant",
                    self._assistant_text,
                    final=True,
                    message_id=self._assistant_message_id
                )
                await self._send_log(f"LLM complete: {len(self._assistant_text)} chars")
                self._assistant_text = ""
            await self._send_log("Sending to TTS...")

        # Always pass the frame through
        await self.push_frame(frame, direction)

    async def _send_transcript(
        self,
        role: str,
        text: str,
        final: bool = True,
        message_id: Optional[int] = None
    ):
        """Send a transcript update to the frontend."""
        message = {
            "type": "transcript",
            "role": role,
            "text": text,
            "final": final,
            "timestamp": int(time.time() * 1000),  # Unix timestamp in milliseconds
        }
        if message_id is not None:
            message["messageId"] = message_id
        logger.info(f"Sending transcript: role={role}, final={final}, text_len={len(text)}, messageId={message_id}")
        await self.push_frame(
            OutputTransportMessageFrame(message=message),
            FrameDirection.DOWNSTREAM,
        )

    async def _send_log(self, text: str):
        """Send a log message to the frontend."""
        await self.push_frame(
            OutputTransportMessageFrame(message={"type": "log", "text": text}),
            FrameDirection.DOWNSTREAM,
        )


class TTSStatusProcessor(FrameProcessor):
    """Processor to track TTS status and interruptions - place after TTS in pipeline."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._is_speaking = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, StartInterruptionFrame):
            # User interrupted the bot while it was speaking
            if self._is_speaking:
                self._is_speaking = False
                logger.debug("Bot interrupted by user")
                await self.push_frame(
                    OutputTransportMessageFrame(message={"type": "status", "status": "idle"}),
                    FrameDirection.DOWNSTREAM,
                )
                await self.push_frame(
                    OutputTransportMessageFrame(message={"type": "log", "text": "Interrupted by user"}),
                    FrameDirection.DOWNSTREAM,
                )

        elif isinstance(frame, TTSStartedFrame):
            if not self._is_speaking:
                self._is_speaking = True
                logger.debug("TTS started frame detected")
                # Send TTS status to frontend
                await self.push_frame(
                    OutputTransportMessageFrame(message={"type": "status", "status": "tts"}),
                    FrameDirection.DOWNSTREAM,
                )
                await self.push_frame(
                    OutputTransportMessageFrame(message={"type": "log", "text": "TTS speaking..."}),
                    FrameDirection.DOWNSTREAM,
                )

        elif isinstance(frame, TTSStoppedFrame):
            if self._is_speaking:
                self._is_speaking = False
                logger.debug("TTS stopped frame detected")
                await self.push_frame(
                    OutputTransportMessageFrame(message={"type": "status", "status": "idle"}),
                    FrameDirection.DOWNSTREAM,
                )
                await self.push_frame(
                    OutputTransportMessageFrame(message={"type": "log", "text": "Ready"}),
                    FrameDirection.DOWNSTREAM,
                )

        elif isinstance(frame, TTSSpeakFrame):
            # TTS is about to speak this text - also set status if not already speaking
            if not self._is_speaking:
                self._is_speaking = True
                logger.debug("TTS speak frame detected - setting speaking state")
                await self.push_frame(
                    OutputTransportMessageFrame(message={"type": "status", "status": "tts"}),
                    FrameDirection.DOWNSTREAM,
                )
            text_preview = frame.text[:30] + "..." if len(frame.text) > 30 else frame.text
            logger.debug(f"TTS speak frame: {text_preview}")
            await self.push_frame(
                OutputTransportMessageFrame(message={"type": "log", "text": f"TTS: \"{text_preview}\""}),
                FrameDirection.DOWNSTREAM,
            )

        await self.push_frame(frame, direction)
