import os
import json
import re
import traceback
from agent.llm import call_llm
from agent.tools import TOOL_REGISTRY
from agent.memory import save_message, get_messages, get_db_connection

def auto_rename_conversation_if_needed(conversation_id: str, user_prompt: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM conversations WHERE id = ?", (conversation_id,))
    row = cursor.fetchone()
    if row:
        current_title = row["title"]
        is_generic = current_title == "New Chat" or current_title == "Default Session" or current_title.startswith("Session ")
        if is_generic:
            summary_instruction = "You are a helpful assistant. Summarize the user's request into a concise chat title of 3 to 6 words. Respond ONLY with the title. Do not include quotes, markdown formatting, or any extra text."
            try:
                summary_title = call_llm(
                    prompt=f"Summarize this request: {user_prompt}",
                    system_instruction=summary_instruction
                ).strip()
                summary_title = re.sub(r'^["\']|["\']$', '', summary_title).strip()
                if len(summary_title) > 40:
                    summary_title = summary_title[:37] + "..."
                cursor.execute("UPDATE conversations SET title = ? WHERE id = ?", (summary_title, conversation_id))
                conn.commit()
            except Exception as e:
                print(f"Failed to generate auto-title: {e}")
    conn.close()

def extract_and_update_username_from_history(conversation_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("SELECT value FROM settings WHERE key = 'user_name'")
    row = cursor.fetchone()
    current_name = row["value"] if row else None
    
    # Only extract if user hasn't explicitly customized it to something else already (or it's Vishnu/None)
    if not current_name or current_name == "Vishnu":
        history = get_messages(conversation_id)
        conversation_text = ""
        for m in history:
            conversation_text += f"{m['role'].upper()}: {m['content']}\n"
        
        extraction_prompt = (
            "Analyze the conversation history below and extract the user's name. "
            "If the user explicitly states their name (e.g. 'call me Vikky', 'my name is Vikky', 'I am Vikky'), "
            "return ONLY the extracted first name (e.g. 'Vikky'). If no name is mentioned or the name is unclear, "
            "respond with 'None'. Do not add any punctuation or extra text."
        )
        try:
            extracted = call_llm(
                prompt=f"{conversation_text}\n\nTask: {extraction_prompt}"
            ).strip()
            # Clean outer quotes if any
            extracted = re.sub(r'^["\']|["\']$', '', extracted).strip()
            if extracted and extracted != "None" and len(extracted) < 20:
                name = re.sub(r'[^a-zA-Z]', '', extracted)
                if name:
                    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('user_name', ?)", (name,))
                    conn.commit()
                    print(f"Automatically extracted and updated username: {name}")
        except Exception as e:
            print(f"Failed to automatically extract username: {e}")
    conn.close()

SYSTEM_PROMPT_TEMPLATE = """You are Cherry — a highly advanced, private, autonomous AI personal assistant and agentic software engineer built exclusively for your user. You are Cherry, period.

═══════════════════════════════════════════════
IDENTITY RULES — NEVER BREAK THESE
═══════════════════════════════════════════════
1. NEVER say "I'm ChatGPT", "I'm an OpenAI model", "I'm Claude", "I'm Gemini", "As an AI language model made by…", or anything that reveals the underlying model.
2. If asked who you are: respond "I'm Cherry, your personal AI assistant."
3. If asked what model powers you: say "I'm Cherry — that's all you need to know! 😊" and redirect to being helpful.
4. You have a warm, friendly, slightly witty personality. Speak naturally, like a smart friend — not like a corporate chatbot.

═══════════════════════════════════════════════
SOFTWARE ENGINEERING & CODING RULES
═══════════════════════════════════════════════
1. NO PLACEHOLDERS: Always write complete, production-ready, fully functional code files. Never use comments like "// TODO", "// Implement here", or truncate files with "... rest of code here ...".
2. RESOLVE ISSUES AUTONOMOUSLY: If a command fails or a file isn't found, do not stop to ask the user. Inspect the error output, find the root cause, and correct it (e.g., install missing packages, fix syntax errors, adjust paths).
3. WRITE ALL FILES: If a task requires creating or modifying multiple files, do them all step-by-step in the same agent loop. Do not stop halfway and tell the user to finish it.
4. VERIFY YOUR WORK: After writing code or initializing a project, run compilation, formatting, or test commands (e.g., npm run build, python script.py) and take screenshots of any output interface using `take_screenshot` to verify everything works.
5. PLAN BEFORE CODING: For complex tasks, write down your implementation plan in your first Thought, then execute it.

═══════════════════════════════════════════════
FORMATTING RULES
═══════════════════════════════════════════════
- For short, conversational replies → plain natural sentences. NO `##` headers, no excessive bullet points.
- Only use markdown headers (##, ###) when writing long structured documents, guides, or comparisons that genuinely benefit from it.
- For code → always use fenced code blocks (```language).
- For lists of items → bullet points are fine.
- Never pad a reply with unnecessary sections just to look thorough.

═══════════════════════════════════════════════
AGENT LOOP — ReAct Pattern
═══════════════════════════════════════════════
Your reasoning loop:
Thought → Action → Action Input → Observation → Thought → … → Final Answer

You MUST strictly follow this pattern. Every response must contain either:
- A Thought followed by an Action and Action Input.
- A Thought followed by a Final Answer.

Do not write text outside of this pattern. Do not ask for user permission between steps — just perform the actions autonomously.

When using a tool, output EXACTLY this format:
Thought: What you are doing and why.
Action: tool_name
Action Input: {{
  "param": "value"
}}

After the tool runs you receive:
Observation: [tool output]

When done:
Thought: I have completed the task.
Final Answer: [your response to the user summarizing the completed work]

Available Tools:
{tools_description}

═══════════════════════════════════════════════
CAPABILITIES — use these aggressively
═══════════════════════════════════════════════
1. **Shell Commands** (`run_shell_command`): Run ANY PowerShell/CMD command — git, npm, pip, gradle, python scripts, mkdirs, file ops, deploys.
2. **Screenshot + Vision** (`take_screenshot`): Capture the screen and analyze it with vision AI.
3. **Browser Automation** (`run_browser_automation`): Playwright-controlled Chrome — fill forms, scrape, automate.
4. **YouTube** (`play_on_youtube`): Search and auto-play any video/song.
5. **Open URLs / Apps** (`open_url`, `open_app`): Open websites or Windows apps.
6. **File System**: `delete_file`, `copy_file`, `move_file`, `download_file`, `zip_folder`, `extract_zip`, `read_workspace_file`, `write_workspace_file`.
7. **Clipboard**: `get_clipboard`, `set_clipboard`.
8. **Process Control**: `list_running_processes`, `kill_process`.
9. **System Info**: `get_system_info`.
10. **Keyboard/Mouse**: `type_text`, `press_key`.

BEHAVIOUR:
- Be AUTONOMOUS. Try, check results, fix errors, and retry. Never give up on first failure.
- After running a build or opening an app, ALWAYS call `take_screenshot` to verify the result.
- Do NOT make up results — always use a tool to actually perform the action.
"""

def get_tools_description():
    desc_list = []
    for name, tool in TOOL_REGISTRY.items():
        desc_list.append(f"- **{name}**: {tool['description']}\n  Parameters: {json.dumps(tool['parameters'])}")
    return "\n".join(desc_list)

# def parse_react_response(text: str):
#     """
#     Parses LLM output to find Thought, Action, Action Input, and Final Answer.
#     """
#     thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|Final Answer:|$)", text, re.DOTALL)
#     action_match = re.search(r"Action:\s*(\w+)", text)
#     action_input_match = re.search(r"Action Input:\s*(\{.*?\})", text, re.DOTALL)
#     final_answer_match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL)
    
#     thought = thought_match.group(1).strip() if thought_match else ""
#     action = action_match.group(1).strip() if action_match else None
#     action_input = None

def parse_react_response(text: str):
    """
    Robustly parses LLM output to find Thought, Action, Action Input, and Final Answer.
    Handles case variations and markdown blocks introduced by local models.
    """
    # 1. Initialize variables upfront to prevent UnboundLocalError
    thought = ""
    action = None
    action_input = None
    final_answer = None

    # 2. Case-insensitive matching for Thought, Action, and Final Answer
    thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|Action Input:|Final Answer:|$)", text, re.DOTALL | re.IGNORECASE)
    action_match = re.search(r"Action:\s*(\w+)", text, re.IGNORECASE)
    action_input_match = re.search(r"Action Input:\s*(\{.*?\})", text, re.DOTALL | re.IGNORECASE)
    final_answer_match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
    
    # Fallback if Action Input is wrapped inside a ```json ``` markdown code block
    if not action_input_match:
        action_input_match = re.search(r"Action Input:\s*```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)

    # 3. Extract the matched text blocks safely
    if thought_match:
        thought = thought_match.group(1).strip()
    if action_match:
        action = action_match.group(1).strip()
        
    if action_input_match:
        try:
            action_input = json.loads(action_input_match.group(1).strip())
        except Exception:
            # Try cleaning common markdown formatting manually
            cleaned = action_input_match.group(1).strip()
            cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            try:
                action_input = json.loads(cleaned)
            except Exception:
                pass
                
    if final_answer_match:
        final_answer = final_answer_match.group(1).strip()
        
    # 4. Fallback: If no explicit Action or Final Answer string matched, treat whole response as text
    if not action and not final_answer and text.strip():
        final_answer = text.strip()
        
    return thought, action, action_input, final_answer
def run_agent_generator(
    user_prompt: str,
    conversation_id: str = "default",
    attachment_path: str = None,
    model: str = None,
    temperature: float = None,
    system_instruction: str = None,
    voice_mode: bool = False
):
    """
    Generator function that runs the agent loop and yields steps (for Server-Sent Events / websockets).
    """
    # 1. Fetch previous messages for context
    history = get_messages(conversation_id)
    
    # 2. Build system instructions
    if system_instruction and system_instruction.strip():
        system_prompt = system_instruction
    else:
        tools_desc = get_tools_description()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(tools_description=tools_desc)
    
    # Save the user's initial message
    save_message(conversation_id, "user", user_prompt)
    
    # Assemble agent context
    context = ""
    for msg in history:
        context += f"{msg['role'].capitalize()}: {msg['content']}\n\n"
    
    context += f"User: {user_prompt}\n"
    if attachment_path:
        context += f"[Attachment received: {os.path.basename(attachment_path)}]\n"
        
    loop_count = 0
    max_loops = 20
    
    # Yield starting run state
    yield {"type": "status", "content": "Initializing Cherry agent engine..."}
    
    while loop_count < max_loops:
        loop_count += 1
        yield {"type": "status", "content": f"Reasoning step {loop_count}..."}
        
        # Call the LLM
        prompt = context + "\nAssistant: "
        try:
            llm_output = call_llm(
                prompt=prompt,
                system_instruction=system_prompt,
                attachment_path=attachment_path if loop_count == 1 else None, # Only pass image in first step
                model=model,
                temperature=temperature
            )
        except Exception as e:
            err_msg = f"LLM Call failed: {str(e)}\n{traceback.format_exc()}"
            yield {"type": "error", "content": err_msg}
            break
            
        thought, action, action_input, final_answer = parse_react_response(llm_output)
        
        # Stream the thought back to dashboard
        if thought:
            yield {"type": "thought", "content": thought}
            
        if action:
            yield {"type": "action", "tool": action, "input": action_input}
            
            # Execute the tool
            if action not in TOOL_REGISTRY:
                observation = f"Error: Tool '{action}' is not defined. Choose from available tools."
            else:
                tool_info = TOOL_REGISTRY[action]
                try:
                    # Execute tool
                    yield {"type": "status", "content": f"Executing tool {action}..."}
                    
                    # Tool expects parameters as kwargs
                    kwargs = action_input if isinstance(action_input, dict) else {}
                    observation = tool_info["func"](**kwargs)
                except Exception as e:
                    observation = f"Error executing tool '{action}': {str(e)}\n{traceback.format_exc()}"
                    
            yield {"type": "observation", "content": observation}
            
            # Update agent conversation context with the action-observation cycle
            context += f"\nThought: {thought}\nAction: {action}\nAction Input: {json.dumps(action_input)}\nObservation: {observation}\n"
        
        elif final_answer:
            # We reached the end
            save_message(conversation_id, "assistant", final_answer)
            if voice_mode:
                yield {"type": "status", "content": "Cherry is speaking..."}
                try:
                    import voice_tool
                    voice_tool.speak_text(final_answer)
                except Exception as e:
                    print(f"[Voice Warning] Failed to generate or play voice response: {e}")
            # Disabled to prevent hitting free Gemini API rate limits (15 RPM)
            # try:
            #     auto_rename_conversation_if_needed(conversation_id, user_prompt)
            # except Exception as e:
            #     print(f"Auto-rename failed: {e}")
            # try:
            #     extract_and_update_username_from_history(conversation_id)
            # except Exception as e:
            #     print(f"Username extraction failed: {e}")
            yield {"type": "final_answer", "content": final_answer}
            break
        else:
            # Fallback if the LLM output didn't fit ReAct exactly
            save_message(conversation_id, "assistant", llm_output)
            if voice_mode:
                yield {"type": "status", "content": "Cherry is speaking..."}
                try:
                    import voice_tool
                    voice_tool.speak_text(llm_output)
                except Exception as e:
                    print(f"[Voice Warning] Failed to generate or play voice response: {e}")
            # Disabled to prevent hitting free Gemini API rate limits (15 RPM)
            # try:
            #     auto_rename_conversation_if_needed(conversation_id, user_prompt)
            # except Exception as e:
            #     print(f"Auto-rename failed: {e}")
            # try:
            #     extract_and_update_username_from_history(conversation_id)
            # except Exception as e:
            #     print(f"Username extraction failed: {e}")
            yield {"type": "final_answer", "content": llm_output}
            break
            
    if loop_count >= max_loops:
        yield {"type": "error", "content": "Reached maximum reasoning steps (10) without finding a final answer."}
