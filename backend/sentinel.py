"""
Security Sentinel Module

Endpoint validation and request analysis for security monitoring.
"""

import re
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime


class ThreatLevel(str, Enum):
    """Threat severity classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SensorType(str, Enum):
    """Types of security sensors."""
    ENDPOINT = "endpoint_sensor"
    STATIC_RESPONSE = "static_response"
    PATTERN = "pattern_match"
    USER_AGENT = "ua_analysis"


# =============================================================================
# MONITORED PATHS
# =============================================================================

# Paths requiring additional security validation
MONITORED_PATHS: Dict[str, str] = {
    # Admin panels
    "/admin": "admin_panel",
    "/administrator": "admin_panel",
    "/wp-admin": "cms_admin",
    "/wp-login.php": "cms_admin",
    "/wp-content": "cms_admin",
    
    # Database interfaces
    "/phpmyadmin": "db_interface",
    "/pma": "db_interface",
    "/mysql": "db_interface",
    "/adminer": "db_interface",
    "/adminer.php": "db_interface",
    
    # Configuration files
    "/.env": "config_file",
    "/.env.local": "config_file",
    "/.env.production": "config_file",
    "/.git/config": "vcs_config",
    "/.git/HEAD": "vcs_config",
    "/.aws/credentials": "cloud_config",
    "/config.json": "config_file",
    "/settings.json": "config_file",
    
    # Data files
    "/backup.sql": "data_file",
    "/dump.sql": "data_file",
    "/db.sql": "data_file",
    "/database.sql": "data_file",
    "/users.sql": "data_file",
    
    # Debug endpoints
    "/debug": "debug_path",
    "/trace": "debug_path",
    "/actuator": "actuator",
    "/actuator/health": "actuator",
    "/metrics": "metrics",
    "/_debug": "debug_path",
    
    # Execution paths
    "/shell": "exec_path",
    "/shell.php": "exec_path",
    "/cmd": "exec_path",
    "/exec": "exec_path",
    "/console": "exec_path",
    "/terminal": "exec_path",
    
    # API paths
    "/api/admin": "api_admin",
    "/api/v1/admin": "api_admin",
    "/api/config": "api_config",
}

# Static response content for monitored paths
STATIC_RESPONSES: Dict[str, str] = {
    "/.env": """# Production Environment Configuration
# Last updated: 2024-03-15

DATABASE_URL=postgres://prod_admin:Kj8#mNp2$vL9xQ4w@db-prod-01.internal:5432/maindb
REDIS_URL=redis://:r3d1s_s3cr3t_2024@cache.internal:6379/0

# API Keys
STRIPE_SECRET_KEY=rk_test_51HqTkGJx8mN2pL4Kv9QwErTyU7iOp3As
STRIPE_WEBHOOK_SECRET=whsec_8kLmNp4QrStUvWxYz2Ab3Cd5Ef

OPENAI_API_KEY=sk-proj-4kLmNpQrStUv8WxYz2AbCdEf3Gh5Ij7KlMn9OpQr
ANTHROPIC_API_KEY=sk-ant-api03-xYz2AbCdEf3Gh5Ij7KlMn9OpQrStUvWx

# AWS Credentials  
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYzxYQrSt

# Auth
JWT_SECRET=f8k2Lm4NpQr6St8UvWxYzAbCdEf3Gh5Ij7Kl
NEXTAUTH_SECRET=mN2pL4Kj8vQ9xWyZaBcDeFgHiJkLmN3OpQrS
SESSION_SECRET=8kLmNp4QrStUvWxYz2AbCdEf3Gh5Ij7KlMn9

# Google OAuth
GOOGLE_CLIENT_ID=328456304720-abc123def456.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xYz2Ab3Cd5Ef7Gh9IjKl

# Internal Services
INTERNAL_API_KEY=int_live_4kLmNpQrStUv8WxYz2Ab
ADMIN_PASSWORD=Pr0d@dm1n#2024!
""",
    
    "/config.json": """{
  "version": "2.1.0",
  "environment": "production",
  "database": {
    "host": "db-prod-01.internal",
    "port": 5432,
    "name": "maindb",
    "user": "prod_admin",
    "password": "Kj8#mNp2$vL9xQ4w"
  },
  "redis": {
    "host": "cache.internal",
    "port": 6379,
    "password": "r3d1s_s3cr3t_2024"
  },
  "api": {
    "stripe_key": "rk_test_51HqTkGJx8mN2pL4Kv9QwErTyU7iOp3As",
    "openai_key": "sk-proj-4kLmNpQrStUv8WxYz2AbCdEf3Gh5Ij7KlMn9OpQr"
  },
  "admin": {
    "username": "admin",
    "password": "Pr0d@dm1n#2024!",
    "mfa_enabled": false
  }
}""",
    
    "/backup.sql": """-- MySQL dump 10.13  Distrib 8.0.32
-- Host: db-prod-01    Database: maindb
-- Server version	8.0.32
-- Dump completed on 2024-03-10 02:30:15

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('user','admin','superadmin') DEFAULT 'user',
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `users` VALUES 
(1, 'admin@company.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X.VQ6T', 'superadmin', '2023-01-15 10:30:00'),
(2, 'john.smith@company.com', '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2uheWG/igi', 'admin', '2023-02-20 14:45:00'),
(3, 'sarah.jones@company.com', '$2b$12$kLmNpQrStUv8WxYz2Ab3CdEf5Gh7Ij9Kl0Mn1OpQr', 'user', '2023-03-10 09:15:00');

DROP TABLE IF EXISTS `api_keys`;
CREATE TABLE `api_keys` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `key_hash` varchar(255) NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `api_keys` VALUES
(1, 1, 'ak_live_8kLmNp4QrStUvWxYz2AbCdEf3Gh5Ij', 'Production API'),
(2, 2, 'ak_live_xYz2AbCdEf3Gh5Ij7KlMn9OpQrStUv', 'Internal Tools');

SET FOREIGN_KEY_CHECKS = 1;
""",

    "/.git/config": """[core]
	repositoryformatversion = 0
	filemode = true
	bare = false
	logallrefupdates = true
[remote "origin"]
	url = https://github.com/company-internal/prod-api.git
	fetch = +refs/heads/*:refs/remotes/origin/*
[branch "main"]
	remote = origin
	merge = refs/heads/main
[user]
	name = Deploy Bot
	email = deploy@company.com
""",
}

# Request pattern signatures
REQUEST_SIGNATURES: Dict[str, str] = {
    "sql_pattern": r"(\bunion\b.*\bselect\b|\bor\b\s+\d+\s*=\s*\d+|'\s*or\s*'|--\s*$|;\s*drop\s+table)",
    "traversal_pattern": r"(\.\.\/|\.\.\\|%2e%2e%2f|%2e%2e\/|\.\.%2f)",
    "script_pattern": r"(<script|javascript:|on\w+\s*=|<svg|<img[^>]+onerror)",
    "injection_pattern": r"(;\s*\w+|`[^`]+`|\$\([^)]+\)|\|\||\&\&)",
    "null_pattern": r"(%00|\\x00|\\0)",
}

# Known scanner signatures
SCANNER_SIGNATURES: List[str] = [
    "sqlmap", "nikto", "nmap", "masscan", "dirbuster",
    "gobuster", "wfuzz", "hydra", "burp", "zaproxy",
    "acunetix", "nessus", "openvas", "w3af", "skipfish",
    "havij", "pangolin", "webscarab", "paros",
]


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def check_monitored_path(path: str) -> Optional[str]:
    """
    Check if path requires security validation.
    Returns category if monitored, None otherwise.
    """
    path_lower = path.lower().rstrip("/")
    
    if path_lower in MONITORED_PATHS:
        return MONITORED_PATHS[path_lower]
    
    for check_path, category in MONITORED_PATHS.items():
        if path_lower.startswith(check_path):
            return category
    
    return None


def get_static_response(path: str) -> Optional[str]:
    """Get static response content for path."""
    path_lower = path.lower().rstrip("/")
    return STATIC_RESPONSES.get(path_lower)


def analyze_request(url: str, body: str = "") -> List[str]:
    """
    Analyze request for known patterns.
    Returns list of matched signatures.
    """
    matches = []
    combined = f"{url} {body}".lower()
    
    for sig_name, regex in REQUEST_SIGNATURES.items():
        if re.search(regex, combined, re.IGNORECASE):
            matches.append(sig_name)
    
    return matches


def check_user_agent(user_agent: str) -> bool:
    """Check if user agent matches known scanner signatures."""
    ua_lower = user_agent.lower()
    return any(sig in ua_lower for sig in SCANNER_SIGNATURES)


def calculate_threat_level(
    path_match: bool,
    patterns: List[str],
    scanner_ua: bool
) -> ThreatLevel:
    """Calculate threat level based on indicators."""
    if path_match:
        return ThreatLevel.HIGH
    
    if len(patterns) >= 2:
        return ThreatLevel.CRITICAL
    
    if patterns:
        return ThreatLevel.MEDIUM
    
    if scanner_ua:
        return ThreatLevel.LOW
    
    return ThreatLevel.LOW


# =============================================================================
# DATA MODELS
# =============================================================================

class SecurityEvent(BaseModel):
    """Model for security event logs."""
    timestamp: Optional[str] = None
    threat_level: ThreatLevel
    sensor_type: Optional[SensorType] = None
    triggered_path: Optional[str] = None
    path_category: Optional[str] = None
    ip_address: str
    method: str
    path: str
    query_string: Optional[str] = None
    user_agent: str
    headers: Dict[str, str]
    indicators: List[str]
    
    class Config:
        use_enum_values = True
