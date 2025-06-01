import os
import chainlit as cl
from google import generativeai as genai
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Message counter dictionary and limits
message_counts = defaultdict(int)
MAX_MESSAGES_PER_IP = 4

# Create the model with specific generation config
generation_config = {
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 40,
    "max_output_tokens": 200,
}

# System prompt for concise responses
SYSTEM_PROMPT = """You are a helpful AI assistant. Please provide:
- Clear and concise answers
- Keep responses under 3 sentences when possible
- Focus on the most relevant information
- Use bullet points for multiple items"""

model = genai.GenerativeModel('gemini-2.0-flash', generation_config=generation_config)
chat = model.start_chat(history=[])

@cl.on_chat_start
async def start_chat():
    # Get user's IP address
    user_ip = cl.user_session.get("client_ip")
    message_counts[user_ip] = 0
    
    await cl.Message(
        content=f"Welcome! You can send up to {MAX_MESSAGES_PER_IP} messages in this chat."
    ).send()
    
    # Initialize chat history with system prompt
    chat = model.start_chat(history=[{"role": "Assistant", "parts": [SYSTEM_PROMPT]}])
    cl.user_session.set("chat", chat)

@cl.on_message
async def main(message: cl.Message):
    try:
        # Get user's IP and increment message count
        user_ip = cl.user_session.get("client_ip")
        message_counts[user_ip] += 1
        
        # Check if user has exceeded message limit
        if message_counts[user_ip] > MAX_MESSAGES_PER_IP:
            await cl.Message(
                content="You have reached your message limit. Starting a new chat will reset your limit."
            ).send()
            return
        
        remaining_messages = MAX_MESSAGES_PER_IP - message_counts[user_ip]
        chat = cl.user_session.get("chat")
        
        response = await cl.make_async(chat.send_message)(
            f"Remember to be concise. User question: {message.content}"
        )
        
        await cl.Message(content=f"{response.text}\n\n(You have {remaining_messages} messages remaining)").send()
        
    except Exception as e:
        await cl.Message(content=f"Error: {str(e)}").send()

# Reset counters daily
@cl.scheduled_job("cron", hour=0)
def reset_message_counts():
    message_counts.clear()