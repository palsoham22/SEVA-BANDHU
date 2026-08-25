import os
import google.generativeai as genai
from groq import Groq
from .prompts import get_system_prompt
from .context import get_customer_context

def init_gemini():
    api_key = os.environ.get("AI_API_KEY")
    if not api_key:
        return False
    genai.configure(api_key=api_key)
    return True

def get_gemini_response(system_prompt, message_text, history):
    model_name = os.environ.get("AI_MODEL_NAME", "gemini-3.6-flash")
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.4,
        )
    )
    chat = model.start_chat(history=history if history else [])
    response = chat.send_message(message_text)
    return response.text

def get_groq_response(system_prompt, message_text, history):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not configured")
        
    client = Groq(api_key=api_key)
    
    # Convert history format (Gemini uses role="user"/"model", parts=[{"text": ...}])
    # Groq uses role="user"/"assistant", content="..."
    groq_messages = [{"role": "system", "content": system_prompt}]
    
    if history:
        for msg in history:
            role = "assistant" if msg.get("role") == "model" else "user"
            text = ""
            if "parts" in msg and len(msg["parts"]) > 0:
                text = msg["parts"][0].get("text", "")
            if text:
                groq_messages.append({"role": role, "content": text})
                
    groq_messages.append({"role": "user", "content": message_text})
    
    chat_completion = client.chat.completions.create(
        messages=groq_messages,
        model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
        temperature=0.4,
        max_tokens=1024,
    )
    
    return chat_completion.choices[0].message.content

def handle_chat_message(customer_username, message_text, history=None):
    """
    Handles a customer chat message using Groq for fast responses,
    falling back to Gemini if Groq is unavailable.
    """
    try:
        context_data = get_customer_context(customer_username)
        if not context_data:
            return "I'm sorry, I couldn't retrieve your account details."
        system_prompt = get_system_prompt(context_data)
    except Exception as e:
        print(f"AI context failed: {e}")
        return "I'm sorry, I couldn't retrieve your account details right now. Please try again later."
    
    # Groq is the primary provider because it responds faster for chat.
    if os.environ.get("GROQ_API_KEY"):
        try:
            return get_groq_response(system_prompt, message_text, history)
        except Exception as e:
            print(f"Groq API failed: {e}. Falling back to Gemini.")
    
    if init_gemini():
        try:
            return get_gemini_response(system_prompt, message_text, history)
        except Exception as e:
            print(f"Gemini API failed: {e}")

    return "I'm sorry, both our primary and backup AI systems are temporarily unavailable. Please try again later."
