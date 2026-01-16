"""
Security Alert Module

Sends real-time alerts to Discord when security events are detected.
"""

import os
import httpx
from datetime import datetime
from typing import Optional


DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


async def send_security_alert(
    threat_level: str,
    path: str,
    ip_address: str,
    category: Optional[str] = None,
    user_agent: Optional[str] = None,
    indicators: Optional[list] = None
) -> bool:
    """
    Send a security alert to Discord.
    
    Returns True if alert was sent successfully, False otherwise.
    """
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ Discord webhook not configured, skipping alert")
        return False
    
    # Color based on threat level
    colors = {
        "low": 0x3498db,      # Blue
        "medium": 0xf39c12,   # Orange
        "high": 0xe74c3c,     # Red
        "critical": 0x8e44ad  # Purple
    }
    
    # Emoji based on threat level
    emojis = {
        "low": "🔵",
        "medium": "🟠", 
        "high": "🔴",
        "critical": "🟣"
    }
    
    color = colors.get(threat_level, 0xe74c3c)
    emoji = emojis.get(threat_level, "🚨")
    
    # Build embed fields
    fields = [
        {
            "name": "🎯 Path",
            "value": f"`{path}`",
            "inline": True
        },
        {
            "name": "🌐 Source IP",
            "value": f"`{ip_address}`",
            "inline": True
        },
        {
            "name": "⚠️ Level",
            "value": f"**{threat_level.upper()}**",
            "inline": True
        }
    ]
    
    if category:
        fields.append({
            "name": "📁 Category",
            "value": f"`{category}`",
            "inline": True
        })
    
    if user_agent:
        ua_display = user_agent[:50] + "..." if len(user_agent) > 50 else user_agent
        fields.append({
            "name": "🖥️ Client",
            "value": f"`{ua_display}`",
            "inline": False
        })
    
    if indicators:
        fields.append({
            "name": "🔍 Details",
            "value": ", ".join([f"`{i}`" for i in indicators[:5]]),
            "inline": False
        })
    
    payload = {
        "embeds": [
            {
                "title": f"{emoji} Security Alert - Unauthorized Access Attempt",
                "description": f"A suspicious request was detected and logged.",
                "color": color,
                "fields": fields,
                "footer": {
                    "text": "Security Monitoring System"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                DISCORD_WEBHOOK_URL,
                json=payload,
                timeout=10.0
            )
            
            if response.status_code == 204:
                print(f"✅ Alert sent for {path}")
                return True
            else:
                print(f"❌ Alert failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Alert error: {e}")
        return False
