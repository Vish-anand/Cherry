import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from agent.llm import call_llm

class TestLiveVoice(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        from app import ACTIVE_SESSIONS
        self.test_token = "test-session-token"
        ACTIVE_SESSIONS.add(self.test_token)
        self.client.cookies.set("session_id", self.test_token)

    @patch('google.genai.Client')
    def test_audio_mime_types(self, mock_genai_client_class):
        """Test that llm.py resolves audio attachments to correct MIME types for Gemini."""
        mock_client_instance = MagicMock()
        mock_genai_client_class.return_value = mock_client_instance
        
        # Write dummy audio files
        dummy_files = {
            'test.webm': 'audio/webm',
            'test.wav': 'audio/wav',
            'test.mp3': 'audio/mpeg',
            'test.ogg': 'audio/ogg',
            'test.m4a': 'audio/mp4'
        }
        
        for filename, expected_mime in dummy_files.items():
            with open(filename, 'wb') as f:
                f.write(b'DUMMY_AUDIO_BYTES')
                
            try:
                # Call call_llm with attachment_path
                with patch('agent.llm.get_client_type', return_value='gemini'):
                    call_llm(
                        prompt="Test prompt",
                        attachment_path=filename,
                        model="gemini-2.5-flash"
                    )
                    
                    # Verify generated model request has correct mime type
                    args, kwargs = mock_client_instance.models.generate_content.call_args
                    contents = kwargs.get('contents') if kwargs and 'contents' in kwargs else (args[0] if len(args) > 0 else [])
                    audio_part = next((p for p in contents if hasattr(p, 'inline_data') and p.inline_data and p.inline_data.mime_type == expected_mime), None)
                    self.assertIsNotNone(audio_part, f"Failed to find part with MIME type {expected_mime} for file {filename}")
            finally:
                if os.path.exists(filename):
                    os.remove(filename)

    @patch('app.run_agent_generator')
    def test_chat_audio_endpoint(self, mock_generator):
        """Test that POST /api/chat/audio transcribes audio and invokes generator with text prompt."""
        mock_generator.return_value = [
            {"type": "status", "content": "Thinking..."},
            {"type": "final_answer", "content": "Done speaking."}
        ]
        
        # Mock both the audio conversion (pydub) and transcription (speech_recognition)
        with patch('pydub.AudioSegment') as mock_pydub, \
             patch('speech_recognition.Recognizer') as mock_recognizer_class, \
             patch('speech_recognition.AudioFile') as mock_audio_file:
            
            # Simulate successful conversion
            mock_seg = MagicMock()
            mock_pydub.from_file.return_value = mock_seg
            
            # Simulate successful transcription
            mock_recognizer = MagicMock()
            mock_recognizer_class.return_value = mock_recognizer
            mock_recognizer.recognize_google.return_value = "Hello Cherry"
            
            # Mock the audio file context manager
            mock_audio_file.return_value.__enter__ = MagicMock()
            mock_audio_file.return_value.__exit__ = MagicMock(return_value=False)
            
            # Send a mock audio upload request
            audio_data = b"AUDIO_MOCK_CONTENT"
            files = {"audio": ("microphone.webm", audio_data, "audio/webm")}
            data = {
                "conversation_id": "test_voice_conv",
                "model": "gemini-2.5-flash",
                "temperature": "0.7",
                "voice_mode": "true"
            }
            
            response = self.client.post("/api/chat/audio", data=data, files=files)
            self.assertEqual(response.status_code, 200)
            
            # Verify generator was called with the transcribed text as prompt
            mock_generator.assert_called_once()
            call_kwargs = mock_generator.call_args[1]
            self.assertEqual(call_kwargs.get("conversation_id"), "test_voice_conv")
            self.assertEqual(call_kwargs.get("user_prompt"), "Hello Cherry")
            self.assertIsNone(call_kwargs.get("attachment_path"))  # No audio attachment now
    
    @patch('app.run_agent_generator')
    def test_chat_audio_transcription_failure(self, mock_generator):
        """Test that POST /api/chat/audio returns error when transcription fails."""
        # No mocks for pydub/sr — let them fail naturally with fake data
        
        audio_data = b"INVALID_AUDIO"
        files = {"audio": ("microphone.webm", audio_data, "audio/webm")}
        data = {"conversation_id": "test_voice_conv"}
        
        response = self.client.post("/api/chat/audio", data=data, files=files)
        self.assertEqual(response.status_code, 200)
        
        # Should contain an error SSE event
        body = response.text
        self.assertIn("error", body)
        
        # Agent generator should NOT have been called
        mock_generator.assert_not_called()

    def test_public_routes(self):
        """Verify that public paths like home portfolio are always accessible."""
        # Unset test cookie to simulate anonymous request
        self.client.cookies.clear()
        
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Vishnu", response.text)

        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Vishnu's Console", response.text)

    def test_login_auth_flow(self):
        """Verify the password verification, redirect triggers, and session logouts."""
        from app import CHERRY_PASSWORD, ACTIVE_SESSIONS
        self.client.cookies.clear()
        
        # 1. Accessing dashboard without auth redirects to login page
        response = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers.get("location"), "/login")
        
        # 2. Accessing API endpoint without auth returns 401 JSON
        response = self.client.get("/api/conversations")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Unauthorized", response.text)
        
        # 3. Post wrong password returns 401 error
        response = self.client.post("/api/login", json={"password": "wrong-password-123"})
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid password", response.text)
        
        # 4. Post correct password succeeds and sets session
        response = self.client.post("/api/login", json={"password": CHERRY_PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Authenticated", response.text)
        self.assertTrue("session_id" in self.client.cookies)
        
        # 5. Accessing dashboard with auth succeeds
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        
        # 6. Logging out deletes the session
        response = self.client.post("/api/logout")
        self.assertEqual(response.status_code, 200)
        self.assertFalse("session_id" in self.client.cookies)
        
        # 7. Accessing dashboard again is now blocked
        response = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 307)

if __name__ == '__main__':
    unittest.main()
