# backend/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List, Optional
import os

from gemini_api import GeminiAPI
from youtube_service import YouTubeService

# Load environment variables
load_dotenv()

app = FastAPI(title="SHOWDESK API")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
gemini = GeminiAPI()
youtube = YouTubeService()

# In-memory session storage
# In production, use Redis or database
sessions = {}


# Request/Response models
class AnalyzeContentRequest(BaseModel):
    url: str


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    screenshot: Optional[str] = ""  # base64 image, optional


class GenerateSuggestionsRequest(BaseModel):
    session_id: str


# API Endpoints

@app.get("/")
def root():
    return {
        "message": "🚀 SHOWDESK API is running!",
        "version": "2.0",
        "features": ["content_analysis", "chat", "suggestions"],
        "status": "ready"
    }


@app.post("/api/analyze-content")
def analyze_content(request: AnalyzeContentRequest):
    """
    Analyze YouTube video and create learning session
    Returns subject info + suggested questions
    """
    print(f"📺 Analyzing: {request.url}")
    
    # Get transcript
    transcript_data = youtube.get_transcript(request.url)
    
    if not transcript_data.get("success"):
        raise HTTPException(status_code=400, detail=transcript_data.get("error"))
    
    # Detect subject using Gemini
    print("🔍 Detecting subject...")
    subject_info = gemini.detect_subject(transcript_data["full_text"])
    
    # Generate suggested questions immediately
    print("💡 Generating question suggestions...")
    suggestions = generate_question_suggestions(
        transcript_data["full_text"],
        subject_info
    )
    
    # Create learning session with chat history
    session_id = transcript_data["video_id"]
    sessions[session_id] = {
        "url": request.url,
        "transcript": transcript_data["full_text"],
        "subject": subject_info,
        "chat_history": [],  # Will store conversation
        "suggested_questions": suggestions,
        "transcript_segments": transcript_data["segments"]
    }
    
    print(f"✅ Session created: {session_id}")
    
    return {
        "success": True,
        "session_id": session_id,
        "subject": subject_info,
        "suggested_questions": suggestions,
        "message": f"Ready to chat about {subject_info['topic']}!",
        "transcript_preview": transcript_data["full_text"][:200] + "..."
    }


@app.post("/api/chat")
def chat(request: ChatRequest):
    """
    Chat about the learning content
    Context-aware conversation using full tutorial knowledge + chat history
    """
    session = sessions.get(request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    print(f"💬 User: {request.message}")
    
    # Build conversation context
    # Include previous chat history for continuity
    chat_context = ""
    if session["chat_history"]:
        chat_context = "PREVIOUS CONVERSATION:\n"
        for msg in session["chat_history"][-6:]:  # Last 3 exchanges
            role = "User" if msg["role"] == "user" else "Assistant"
            chat_context += f"{role}: {msg['content']}\n"
        chat_context += "\n"
    
    # Build the full prompt
    prompt = f"""You are SHOWDESK, a helpful AI learning assistant having a conversation with a student.

LEARNING CONTEXT:
- Subject: {session['subject']['subject']}
- Topic: {session['subject']['topic']}
- Level: {session['subject']['level']}
- Key Concepts: {', '.join(session['subject']['concepts'])}

TUTORIAL/VIDEO CONTENT (for reference):
{session['transcript'][:3000]}...

{chat_context}

CURRENT USER MESSAGE: {request.message}

INSTRUCTIONS:
- Answer naturally and conversationally
- Reference the tutorial content when relevant
- Be encouraging and helpful
- If they're confused, break it down simply
- If they're doing well, acknowledge it
- Adapt your explanation style to the subject ({session['subject']['subject']})
- Keep responses focused and not too long (2-4 paragraphs max)

Your response:"""
    
    # Generate response (with or without screenshot)
    if request.screenshot and len(request.screenshot) > 100:
        print("📸 Analyzing with screenshot...")
        response_text = gemini.generate_with_image(prompt, request.screenshot)
    else:
        print("💭 Generating text response...")
        response_text = gemini.generate_text(prompt)
    
    # Add to chat history
    session["chat_history"].append({
        "role": "user",
        "content": request.message
    })
    session["chat_history"].append({
        "role": "assistant",
        "content": response_text
    })
    
    print(f"✅ Response generated ({len(response_text)} chars)")
    
    return {
        "success": True,
        "response": response_text,
        "chat_history": session["chat_history"],
        "message_count": len(session["chat_history"])
    }


@app.post("/api/generate-suggestions")
def get_suggestions(request: GenerateSuggestionsRequest):
    """
    Generate fresh question suggestions based on current chat context
    These evolve as the conversation progresses
    """
    session = sessions.get(request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    print("💡 Generating new suggestions based on conversation...")
    
    suggestions = generate_contextual_suggestions(
        session["transcript"],
        session["subject"],
        session["chat_history"]
    )
    
    session["suggested_questions"] = suggestions
    
    return {
        "success": True,
        "suggestions": suggestions
    }


@app.get("/api/session/{session_id}")
def get_session(session_id: str):
    session = sessions.get(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "subject": session['subject'],
        "message_count": len(session['chat_history']),
        "suggested_questions": session.get('suggested_questions', []),
        "url": session['url']
    }

@app.get("/api/session/{session_id}/history")
def get_chat_history(session_id: str):
    session = sessions.get(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "chat_history": session['chat_history'],
        "subject": session['subject']
    }


@app.delete("/api/session/{session_id}")
def clear_session(session_id: str):
    """Clear/reset a learning session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"success": True, "message": "Session cleared"}
    
    raise HTTPException(status_code=404, detail="Session not found")


# Helper functions

def generate_question_suggestions(transcript: str, subject_info: dict) -> List[str]:
    """
    Generate initial suggested questions when content is first analyzed
    These give users ideas of what they can ask
    """
    prompt = f"""Based on this educational content, generate 5 example questions a student might want to ask.

SUBJECT: {subject_info['subject']}
TOPIC: {subject_info['topic']}
LEVEL: {subject_info['level']}

CONTENT PREVIEW:
{transcript[:1500]}

Generate questions that:
1. Help understand key concepts
2. Clarify confusing parts
3. Connect to real-world applications
4. Are natural and conversational
5. Are appropriate for the subject ({subject_info['subject']})

Examples for coding: "How does this work?", "Why use this instead of X?", "Can you show a simpler example?"
Examples for history: "What caused this?", "Who were the key figures?", "How did this affect...?"
Examples for language: "How do I pronounce this?", "When do I use this grammar?", "Can you give more examples?"
Examples for science: "Why does this happen?", "What's a real-world example?", "How does this relate to...?"

Return ONLY a JSON array of 5 questions, nothing else:
["Question 1", "Question 2", "Question 3", "Question 4", "Question 5"]"""
    
    response = gemini.generate_text(prompt)
    
    # Parse JSON response
    import json
    try:
        cleaned = response.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('```')[1]
            if cleaned.startswith('json'):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        
        suggestions = json.loads(cleaned)
        return suggestions if isinstance(suggestions, list) else []
    except:
        # Fallback suggestions
        return [
            "Can you explain the main concept?",
            "How does this work in practice?",
            "What are the key points I should remember?",
            "Can you give me another example?",
            "What's the most important thing to understand?"
        ]


def generate_contextual_suggestions(transcript: str, subject_info: dict, chat_history: List[dict]) -> List[str]:
    """
    Generate new suggestions based on the current conversation
    These evolve as the student learns
    """
    # Build recent conversation context
    recent_context = ""
    if chat_history:
        recent_context = "RECENT CONVERSATION:\n"
        for msg in chat_history[-4:]:  # Last 2 exchanges
            role = "Student" if msg["role"] == "user" else "Assistant"
            recent_context += f"{role}: {msg['content'][:100]}...\n"
    
    prompt = f"""Based on the learning conversation so far, suggest 5 new questions the student might want to ask next.

SUBJECT: {subject_info['subject']}
TOPIC: {subject_info['topic']}

{recent_context}

Generate questions that:
1. Build on what they've already asked
2. Deepen understanding
3. Explore related concepts
4. Help them apply the knowledge
5. Are natural follow-ups

Return ONLY a JSON array of 5 questions:
["Question 1", "Question 2", "Question 3", "Question 4", "Question 5"]"""
    
    response = gemini.generate_text(prompt)
    
    # Parse JSON response
    import json
    try:
        cleaned = response.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('```')[1]
            if cleaned.startswith('json'):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        
        suggestions = json.loads(cleaned)
        return suggestions if isinstance(suggestions, list) else []
    except:
        # Fallback suggestions based on subject
        fallbacks = {
            'coding': [
                "How can I use this in my own project?",
                "What are common mistakes to avoid?",
                "Are there alternative approaches?",
                "Can you show me a more complex example?",
                "How does this relate to other concepts?"
            ],
            'history': [
                "What happened next?",
                "How did this impact modern times?",
                "What were the long-term effects?",
                "Who opposed this and why?",
                "Are there any interesting details I should know?"
            ],
            'language': [
                "Can you give me more practice examples?",
                "What are common mistakes learners make?",
                "How is this used in everyday conversation?",
                "Are there any exceptions to this rule?",
                "Can you explain the cultural context?"
            ],
            'science': [
                "What are the practical applications?",
                "How does this connect to what I already know?",
                "What are some common misconceptions?",
                "Can you explain this with an analogy?",
                "What would happen if...?"
            ]
        }
        
        return fallbacks.get(subject_info['subject'], fallbacks['coding'])


if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🚀 SHOWDESK API v2.0 - Chat Edition")
    print("=" * 50)
    print("📝 Features:")
    print("  ✓ Content Analysis")
    print("  ✓ Conversational Chat")
    print("  ✓ Auto Question Suggestions")
    print("  ✓ Screenshot Support")
    print("=" * 50)
    print("🔧 Make sure .env has GEMINI_API_KEY!")
    print("🌐 Starting on http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)