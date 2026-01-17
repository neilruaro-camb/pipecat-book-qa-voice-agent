"""Book processor using Gemini File API for direct document understanding."""

import os
import tempfile
from typing import Optional, Dict, Any

from loguru import logger

from pipecat.services.google.gemini_live.file_api import GeminiFileAPI


class BookProcessor:
    """Handles book upload via Gemini File API."""

    # Max file size: 10MB (Gemini supports up to 2GB but we limit for reasonable response times)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self, api_key: str = None):
        """Initialize the book processor.

        Args:
            api_key: Google API key. If not provided, reads from GOOGLE_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self._file_api = None
        self.file_info: Optional[Dict[str, Any]] = None
        self.file_uri: Optional[str] = None
        self.mime_type: Optional[str] = None
        self.book_title: Optional[str] = None
        self._temp_file_path: Optional[str] = None

    @property
    def file_api(self) -> GeminiFileAPI:
        """Lazy initialization of Gemini File API client."""
        if self._file_api is None:
            if not self.api_key:
                raise ValueError("GOOGLE_API_KEY is required for file uploads")
            self._file_api = GeminiFileAPI(api_key=self.api_key)
        return self._file_api

    async def process_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Process an uploaded file by uploading to Gemini File API.

        Args:
            file_content: Raw bytes of the uploaded file.
            filename: Name of the uploaded file.

        Returns:
            Dict with file_uri, mime_type, and filename.
        """
        # Validate file size
        if len(file_content) > self.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Max size is {self.MAX_FILE_SIZE // (1024*1024)}MB")

        # Validate file type
        if not (filename.lower().endswith(".pdf") or filename.lower().endswith(".txt")):
            raise ValueError("Only PDF and TXT files are supported")

        self.book_title = filename

        # Determine mime type
        if filename.lower().endswith(".pdf"):
            self.mime_type = "application/pdf"
        else:
            self.mime_type = "text/plain"

        # Save to temp file for upload
        suffix = ".pdf" if filename.lower().endswith(".pdf") else ".txt"
        with tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False) as f:
            f.write(file_content)
            self._temp_file_path = f.name

        try:
            # Upload to Gemini File API
            logger.info(f"Uploading '{filename}' to Gemini File API...")
            self.file_info = await self.file_api.upload_file(
                self._temp_file_path,
                display_name=filename,
            )

            self.file_uri = self.file_info["file"]["uri"]
            logger.info(f"File uploaded successfully: {self.file_uri}")

            return {
                "file_uri": self.file_uri,
                "mime_type": self.mime_type,
                "filename": filename,
                "file_name": self.file_info["file"]["name"],
            }

        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            await self.clear()
            raise

    def get_file_uri(self) -> Optional[str]:
        """Get the Gemini file URI."""
        return self.file_uri

    def get_mime_type(self) -> Optional[str]:
        """Get the file mime type."""
        return self.mime_type

    def get_title(self) -> Optional[str]:
        """Get the current book title."""
        return self.book_title

    def has_file(self) -> bool:
        """Check if a file has been uploaded."""
        return self.file_uri is not None

    async def clear(self):
        """Clear the current book and delete from Gemini."""
        # Delete from Gemini if uploaded
        if self.file_info:
            try:
                file_name = self.file_info["file"]["name"]
                await self.file_api.delete_file(file_name)
                logger.info(f"Deleted file from Gemini: {file_name}")
            except Exception as e:
                logger.warning(f"Failed to delete file from Gemini: {e}")

        # Delete temp file
        if self._temp_file_path and os.path.exists(self._temp_file_path):
            try:
                os.unlink(self._temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")

        self.file_info = None
        self.file_uri = None
        self.mime_type = None
        self.book_title = None
        self._temp_file_path = None
