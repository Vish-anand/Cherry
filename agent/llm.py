import os
import base64
import json
from dotenv import load_dotenv

load_dotenv()

# We will dynamically import the appropriate library depending on which key is available
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "google/gemini-2.5-flash")

def get_client_type():
    if GEMINI_API_KEY and GEMINI_API_KEY.strip():
        return "gemini"
    elif OPENAI_API_KEY and OPENAI_API_KEY.strip():
        return "openai"
    return None

def call_llm(prompt: str, system_instruction: str = None, attachment_path: str = None, response_schema: dict = None) -> str:
    """
    Unified LLM call supporting text, images, and PDFs.
    Returns the string output of the model (or structured JSON).
    """
    client_type = get_client_type()
    if not client_type:
        raise ValueError("No valid API keys found in .env (either GEMINI_API_KEY or OPENAI_API_KEY must be set)")
        
    mime_type = None
    file_bytes = None
    
    if attachment_path and os.path.exists(attachment_path):
        ext = os.path.splitext(attachment_path)[1].lower()
        if ext in ['.jpg', '.jpeg']:
            mime_type = 'image/jpeg'
        elif ext == '.png':
            mime_type = 'image/png'
        elif ext == '.webp':
            mime_type = 'image/webp'
        elif ext == '.pdf':
            mime_type = 'application/pdf'
            
        if mime_type:
            with open(attachment_path, "rb") as f:
                file_bytes = f.read()

    if client_type == "gemini":
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        model_name = "gemini-2.5-flash"
        
        contents = []
        if file_bytes and mime_type:
            contents.append(types.Part.from_bytes(data=file_bytes, mime_type=mime_type))
        contents.append(prompt)
        
        config_args = {}
        if system_instruction:
            config_args["system_instruction"] = system_instruction
            
        if response_schema:
            # We can request JSON output
            config_args["response_mime_type"] = "application/json"
            config_args["response_schema"] = response_schema
            
        config = types.GenerateContentConfig(**config_args)
        
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config
        )
        return response.text

    elif client_type == "openai":
        import openai
        
        client = openai.OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
            
        user_content = []
        if file_bytes and mime_type:
            base64_data = base64.b64encode(file_bytes).decode('utf-8')
            # For OpenRouter/OpenAI multimodal requests
            if mime_type.startswith('image/'):
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}
                })
            elif mime_type == 'application/pdf':
                # OpenRouter supports inline PDFs for Gemini models via document block
                user_content.append({
                    "type": "text",
                    "text": f"[Attached Document: {os.path.basename(attachment_path)} (PDF Base64 Encoded)]"
                })
                # Add text placeholder or raw text if pypdf extracts it, or base64 if model supports it
                # For safety, let's extract PDF text to append in prompt:
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(attachment_path)
                    pdf_text = ""
                    for page in reader.pages:
                        pdf_text += page.extract_text() or ""
                    user_content.append({
                        "type": "text",
                        "text": f"--- Extracted PDF Content ---\n{pdf_text}\n--- End Extracted PDF Content ---"
                    })
                except Exception as e:
                    user_content.append({
                        "type": "text",
                        "text": f"Error extracting PDF: {str(e)}"
                    })
                    
        user_content.append({"type": "text", "text": prompt})
        messages.append({"role": "user", "content": user_content})
        
        kwargs = {}
        # Limit max_tokens to prevent OpenRouter 402 pre-authorization blocks on free accounts
        kwargs["max_tokens"] = 4000
        
        if response_schema:
            kwargs["response_format"] = {"type": "json_object"}
            # Guide prompt to conform to the schema
            schema_str = json.dumps(response_schema)
            messages.append({
                "role": "system",
                "content": f"You MUST respond ONLY with a JSON object conforming exactly to this schema:\n{schema_str}"
            })
            
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
