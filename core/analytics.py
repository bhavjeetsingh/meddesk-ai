"""
CareFirst Medical Center - Analytics Dashboard
Track conversations, sentiment, appointments for reporting
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
from collections import Counter


ANALYTICS_FILE = "analytics_data.json"


def _load_data() -> Dict:
    """Load analytics data from file"""
    if os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE, "r") as f:
            return json.load(f)
    return {
        "sessions": [],
        "daily_stats": {},
        "sentiment_trends": [],
        "top_intents": [],
        "total_messages": 0,
        "total_sessions": 0,
    }


def _save_data(data: Dict):
    """Save analytics data to file"""
    with open(ANALYTICS_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def log_session(session_id: str, messages: int, duration: float, intents: List[str], sentiments: List[float]):
    """Log a completed session"""
    data = _load_data()
    today = datetime.now().strftime("%Y-%m-%d")

    session = {
        "session_id": session_id,
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "messages": messages,
        "duration_seconds": round(duration, 1),
        "intents": intents,
        "avg_sentiment": round(sum(sentiments) / len(sentiments), 2) if sentiments else 0.5,
    }
    data["sessions"].append(session)
    data["total_messages"] += messages
    data["total_sessions"] += 1

    # Update daily stats
    if today not in data["daily_stats"]:
        data["daily_stats"][today] = {"sessions": 0, "messages": 0, "avg_sentiment": 0}
    day = data["daily_stats"][today]
    day["sessions"] += 1
    day["messages"] += messages
    day["avg_sentiment"] = round(
        (day["avg_sentiment"] * (day["sessions"] - 1) + session["avg_sentiment"]) / day["sessions"], 2
    )

    # Update top intents
    for intent in intents:
        found = False
        for item in data["top_intents"]:
            if item["intent"] == intent:
                item["count"] += 1
                found = True
                break
        if not found:
            data["top_intents"].append({"intent": intent, "count": 1})
    data["top_intents"].sort(key=lambda x: x["count"], reverse=True)

    _save_data(data)


def get_dashboard_stats() -> Dict:
    """Get overall dashboard statistics"""
    data = _load_data()
    sessions = data.get("sessions", [])
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    today_sessions = [s for s in sessions if s["date"] == today]
    week_sessions = [s for s in sessions if s["date"] >= week_ago]

    total_messages_today = sum(s["messages"] for s in today_sessions)
    total_messages_week = sum(s["messages"] for s in week_sessions)

    avg_duration = 0
    if sessions:
        avg_duration = round(sum(s["duration_seconds"] for s in sessions) / len(sessions), 1)

    sentiments = [s["avg_sentiment"] for s in sessions if s.get("avg_sentiment")]
    avg_sentiment = round(sum(sentiments) / len(sentiments), 2) if sentiments else 0.5

    sentiment_label = "Positive" if avg_sentiment > 0.6 else "Neutral" if avg_sentiment > 0.4 else "Concerned"

    # Get last 7 days trend
    daily_trend = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        day_data = data["daily_stats"].get(d, {"sessions": 0, "messages": 0})
        daily_trend.append({
            "date": d,
            "label": (datetime.now() - timedelta(days=i)).strftime("%a"),
            "sessions": day_data["sessions"],
            "messages": day_data["messages"],
        })

    return {
        "total_sessions": data["total_sessions"],
        "total_messages": data["total_messages"],
        "sessions_today": len(today_sessions),
        "messages_today": total_messages_today,
        "sessions_this_week": len(week_sessions),
        "messages_this_week": total_messages_week,
        "avg_session_duration": avg_duration,
        "avg_sentiment": avg_sentiment,
        "sentiment_label": sentiment_label,
        "top_intents": data["top_intents"][:5],
        "daily_trend": daily_trend,
    }


def get_sentiment_distribution() -> Dict:
    """Get sentiment distribution across all sessions"""
    data = _load_data()
    sentiments = [s.get("avg_sentiment", 0.5) for s in data.get("sessions", [])]

    positive = sum(1 for s in sentiments if s > 0.6)
    neutral = sum(1 for s in sentiments if 0.4 <= s <= 0.6)
    concerned = sum(1 for s in sentiments if s < 0.4)
    total = len(sentiments) or 1

    return {
        "positive": positive,
        "neutral": neutral,
        "concerned": concerned,
        "positive_pct": round(positive / total * 100),
        "neutral_pct": round(neutral / total * 100),
        "concerned_pct": round(concerned / total * 100),
    }
