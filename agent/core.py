import os
import json
import re
import traceback
from agent.llm import call_llm
from agent.tools import TOOL_REGISTRY
from agent.memory import save_message, get_messages

SYSTEM_PROMPT_TEMPLATE = """You are Cherry, a highly advanced autonomous AI personal assistant and developer. You have access to tools to interact with the system, organize documents, search the web, and run browser scripts.

Your loop follows this cycle:
Thought -> Action -> Action Input -> Observation -> Thought -> ... -> Final Answer

When you need to use a tool, you MUST output it in this exact format (with no extra characters before or after the JSON in Action Input):
Thought: Describe what you are trying to accomplish and why you are choosing the next tool.
Action: name_of_tool_to_call
Action Input: {{
  "param_name": "param_value"
}}

Ensure the Action Input is valid, parseable JSON. Do not surround the Action Input block with markdown code fences (like ```json).

After you yield an Action and Action Input, the system will execute it and provide the result back to you as:
Observation: The output result of the tool execution.

Once you have all the information required, output your final response:
Thought: I have solved the task or collected the necessary details.
Final Answer: Write your detailed final response here.

Available Tools:
{tools_description}

Guidelines:
1. Workspace: Use workspace tools to inspect and modify local files.
2. System controls: You can set laptop volume using adjust_system_volume.
3. Multimodal: To classify and index document uploads or incoming receipts/marklists, call classify_and_organize_document.
4. Portal Result Check: To check portal results or fill forms behind logins, write a playwright python script and execute it using run_browser_automation.
5. If a download is requested (like YouTube), use download_youtube_video.
6. Try to be autonomous and verify your actions. If a script fails, read the output logs, fix the code, and try again.
"""

def get_tools_description():
    desc_list = []
    for name, tool in TOOL_REGISTRY.items():
        desc_list.append(f"- **{name}**: {tool['description']}\n  Parameters: {json.dumps(tool['parameters'])}")
    return "\n".join(desc_list)

def parse_react_response(text: str):
    """
    Parses LLM output to find Thought, Action, Action Input, and Final Answer.
    """
    thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|Final Answer:|$)", text, re.DOTALL)
    action_match = re.search(r"Action:\s*(\w+)", text)
    action_input_match = re.search(r"Action Input:\s*(\{.*?\})", text, re.DOTALL)
    final_answer_match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL)
    
    thought = thought_match.group(1).strip() if thought_match else ""
    action = action_match.group(1).strip() if action_match else None
    action_input = None
    
    if action_input_match:
        try:
            action_input = json.loads(action_input_match.group(1).strip())
        except Exception:
            # Try cleaning common markdown formatting
            cleaned = action_input_match.group(1).strip()
            cleaned = re.sub(r"^```json\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            try:
                action_input = json.loads(cleaned)
            except Exception:
                pass
                
    final_answer = final_answer_match.group(1).strip() if final_answer_match else None
    return thought, action, action_input, final_answer

def run_agent_generator(user_prompt: str, conversation_id: str = "default", attachment_path: str = None):
    """
    Generator function that runs the agent loop and yields steps (for Server-Sent Events / websockets).
    """
    # 1. Fetch previous messages for context
    history = get_messages(conversation_id)
    
    # 2. Build system instructions
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
    max_loops = 10
    
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
                attachment_path=attachment_path if loop_count == 1 else None # Only pass image in first step
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
            yield {"type": "final_answer", "content": final_answer}
            break
        else:
            # Fallback if the LLM output didn't fit ReAct exactly
            save_message(conversation_id, "assistant", llm_output)
            yield {"type": "final_answer", "content": llm_output}
            break
            
    if loop_count >= max_loops:
        yield {"type": "error", "content": "Reached maximum reasoning steps (10) without finding a final answer."}
