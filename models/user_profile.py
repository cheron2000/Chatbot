"""User profile management for personalized AI behavior."""
import json
import os
import threading
from datetime import datetime, timezone
from typing import Optional


def get_profile_path(session_id: str) -> str:
    """Get the path to a user's profile file."""
    profile_dir = "user_profiles"
    os.makedirs(profile_dir, exist_ok=True)
    return os.path.join(profile_dir, f"{session_id}_profile.json")


def load_profile(session_id: str) -> dict:
    """
    Load user profile from disk.
    
    Returns:
        dict with keys: expertise, communication_style, topics, updated_at
    """
    path = get_profile_path(session_id)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "expertise": "unknown",
            "communication_style": "brief",
            "topics": [],
            "updated_at": None
        }


def save_profile(session_id: str, profile: dict) -> None:
    """Save user profile to disk."""
    path = get_profile_path(session_id)
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def build_system_prompt(profile: dict) -> str:
    """
    Build a system prompt based on user profile.
    
    Args:
        profile: User profile dict
        
    Returns:
        System prompt string to prepend to context
    """
    if not profile or profile.get("expertise") == "unknown":
        return ""
    
    parts = []
    
    # Expertise level
    expertise = profile.get("expertise", "unknown")
    if expertise != "unknown":
        parts.append(f"User expertise level: {expertise}")
    
    # Communication style
    style = profile.get("communication_style", "brief")
    if style == "detailed":
        parts.append("Provide detailed, comprehensive explanations.")
    elif style == "brief":
        parts.append("Keep responses concise and to the point.")
    elif style == "technical":
        parts.append("Use technical language and include implementation details.")
    
    # Topics of interest
    topics = profile.get("topics", [])
    if topics:
        parts.append(f"User is interested in: {', '.join(topics[:5])}")
    
    if not parts:
        return ""
    
    return "[User Profile]\n" + "\n".join(parts)


def update_profile_async(session_id: str, conversation_history: list) -> None:
    """
    Update user profile based on conversation history in background thread.
    
    Args:
        session_id: Session identifier
        conversation_history: List of message dicts with 'role' and 'content'
    """
    def _update():
        try:
            profile = load_profile(session_id)
            
            # Simple heuristic-based profile update
            user_messages = [msg["content"].lower() for msg in conversation_history if msg["role"] == "user"]
            all_text = " ".join(user_messages[-5:])  # Last 5 messages
            
            # Detect expertise level
            if any(word in all_text for word in ["api", "algorithm", "architecture", "implementation", "optimize"]):
                profile["expertise"] = "advanced"
            elif any(word in all_text for word in ["how to", "what is", "explain", "tutorial", "beginner"]):
                profile["expertise"] = "beginner"
            else:
                profile["expertise"] = "intermediate"
            
            # Detect communication style preference
            if any(word in all_text for word in ["detail", "explain more", "comprehensive", "thoroughly"]):
                profile["communication_style"] = "detailed"
            elif any(word in all_text for word in ["quick", "brief", "summarize", "tldr", "short"]):
                profile["communication_style"] = "brief"
            elif any(word in all_text for word in ["technical", "code", "implementation", "function"]):
                profile["communication_style"] = "technical"
            
            # Extract topics (simple keyword detection)
            topic_keywords = {
                "python": ["python", "flask", "django"],
                "javascript": ["javascript", "js", "node", "react", "vue"],
                "database": ["database", "sql", "mongodb", "postgres"],
                "ai": ["ai", "machine learning", "llm", "model"],
                "web": ["web", "html", "css", "frontend", "backend"],
                "devops": ["docker", "kubernetes", "deployment", "ci/cd"],
            }
            
            detected_topics = []
            for topic, keywords in topic_keywords.items():
                if any(kw in all_text for kw in keywords):
                    detected_topics.append(topic)
            
            if detected_topics:
                # Merge with existing topics
                existing = set(profile.get("topics", []))
                existing.update(detected_topics)
                profile["topics"] = list(existing)[:10]  # Keep top 10
            
            save_profile(session_id, profile)
            
            print(f"[PROFILE] Updated for session {session_id[:8]}… | expertise={profile['expertise']} | style={profile['communication_style']} | topics={profile['topics']}")
        except Exception as e:
            print(f"[WARN] Profile update failed: {e}")
    
    # Run in background thread
    t = threading.Thread(target=_update, daemon=True)
    t.start()


def delete_profile(session_id: str) -> None:
    """Delete user profile."""
    path = get_profile_path(session_id)
    if os.path.exists(path):
        os.remove(path)
        print(f"[PROFILE] Deleted profile for session {session_id[:8]}…")
