import os
import base64
import json
from dotenv import load_dotenv

load_dotenv()

# We will dynamically import the appropriate library depending on which key is available
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AWS_BEARER_TOKEN_BEDROCK = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_BEDROCK_MODEL = os.getenv("AWS_BEDROCK_MODEL", "meta.llama3-1-8b-instruct-v1:0")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "google/gemini-2.5-flash")

def get_client_type():
    if GEMINI_API_KEY and GEMINI_API_KEY.strip():
        return "gemini"
    elif AWS_BEARER_TOKEN_BEDROCK and AWS_BEARER_TOKEN_BEDROCK.strip():
        return "bedrock"
    elif OPENAI_API_KEY and OPENAI_API_KEY.strip():
        return "openai"
    return None

def call_llm(
    prompt: str,
    system_instruction: str = None,
    attachment_path: str = None,
    response_schema: dict = None,
    model: str = None,
    temperature: float = None
) -> str:
    """
    Unified LLM call supporting text, images, and PDFs.
    Returns the string output of the model (or structured JSON).
    """
    client_type = get_client_type()
    if not client_type:
        raise ValueError("No valid API keys found in .env (either GEMINI_API_KEY, AWS_BEARER_TOKEN_BEDROCK, or OPENAI_API_KEY must be set)")
        
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
        model_name = model if (model and model.strip()) else "gemini-2.5-flash"
        
        contents = []
        if file_bytes and mime_type:
            contents.append(types.Part.from_bytes(data=file_bytes, mime_type=mime_type))
        contents.append(prompt)
        
        config_args = {}
        if system_instruction:
            config_args["system_instruction"] = system_instruction
            
        if temperature is not None:
            config_args["temperature"] = temperature
            
        if response_schema:
            # We can request JSON output
            config_args["response_mime_type"] = "application/json"
            config_args["response_schema"] = response_schema
            
        config = types.GenerateContentConfig(**config_args)
        
        import time
        max_retries = 3
        retry_delay = 1.0
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config
                )
                return response.text
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[Gemini Warning] Attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise e

    elif client_type == "bedrock":
        import httpx
        
        # Determine model
        model_name = model if (model and model.strip()) else AWS_BEDROCK_MODEL
        
        # Bedrock Runtime Invoke API URL
        url = f"https://bedrock-runtime.{AWS_REGION}.amazonaws.com/model/{model_name}/invoke"
        
        headers = {
            "Authorization": f"Bearer {AWS_BEARER_TOKEN_BEDROCK}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Prepare payload depending on whether it's Llama or Claude
        if "llama" in model_name.lower():
            # Combine system instruction and prompt if available
            full_prompt = ""
            if system_instruction:
                full_prompt += f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_instruction}<|eot_id|>"
            full_prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
            
            payload = {
                "prompt": full_prompt,
                "max_gen_len": 2048,
                "temperature": temperature if temperature is not None else 0.7,
                "top_p": 0.9
            }
        elif "claude" in model_name.lower():
            messages = []
            if file_bytes and mime_type:
                base64_data = base64.b64encode(file_bytes).decode('utf-8')
                content_list = [
                    {
                        "type": "image" if mime_type.startswith("image/") else "document",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": base64_data
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
                messages.append({"role": "user", "content": content_list})
            else:
                messages.append({"role": "user", "content": prompt})
                
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": messages,
                "temperature": temperature if temperature is not None else 0.7
            }
            if system_instruction:
                payload["system"] = system_instruction
        elif "openai" in model_name.lower() or "gpt" in model_name.lower():
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            
            user_content = []
            if file_bytes and mime_type:
                base64_data = base64.b64encode(file_bytes).decode('utf-8')
                if mime_type.startswith('image/'):
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}
                    })
            user_content.append({"type": "text", "text": prompt})
            messages.append({"role": "user", "content": user_content})
            
            payload = {
                "messages": messages,
                "temperature": temperature if temperature is not None else 0.7,
                "max_tokens": 4096
            }
        else:
            # Generic/Titan fallback format
            payload = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 2048,
                    "temperature": temperature if temperature is not None else 0.7
                }
            }
            
        import time
        max_retries = 3
        retry_delay = 1.0
        res = None
        for attempt in range(max_retries):
            try:
                res = httpx.post(url, headers=headers, json=payload, timeout=60.0)
                if res.status_code == 200:
                    break
                elif res.status_code >= 500 and attempt < max_retries - 1:
                    print(f"[Bedrock Warning] Attempt {attempt + 1} failed with status {res.status_code}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise ValueError(f"Bedrock call failed (HTTP {res.status_code}): {res.text}")
            except (httpx.RequestError, httpx.TimeoutException) as req_err:
                if attempt < max_retries - 1:
                    print(f"[Bedrock Warning] Attempt {attempt + 1} failed due to network error: {req_err}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise req_err
                    
        res_data = res.json()
        
        # Parse output depending on model type
        val = None
        if "llama" in model_name.lower():
            val = res_data["generation"]
        elif "openai" in model_name.lower() or "gpt" in model_name.lower():
            val = res_data["choices"][0]["message"]["content"]
        elif "claude" in model_name.lower():
            val = res_data["content"][0]["text"]
        else:
            # General fallback check
            val = res_data.get("generation") or (res_data.get("results") and res_data["results"][0]["outputText"]) or json.dumps(res_data)

        import re
        if val:
            val = re.sub(r'<(reasoning|think)>.*?</\1>', '', val, flags=re.DOTALL).strip()
        return val

    elif client_type == "openai":
        import openai
        
        client = openai.OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        model_name = model if (model and model.strip()) else OPENAI_MODEL
        
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
        
        if temperature is not None:
            kwargs["temperature"] = temperature
            
        if response_schema:
            kwargs["response_format"] = {"type": "json_object"}
            # Guide prompt to conform to the schema
            schema_str = json.dumps(response_schema)
            messages.append({
                "role": "system",
                "content": f"You MUST respond ONLY with a JSON object conforming exactly to this schema:\n{schema_str}"
            })
            
        import time
        max_retries = 3
        retry_delay = 1.0
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    **kwargs
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[OpenAI Warning] Attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise e
