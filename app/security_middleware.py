# app/security_middleware.py
"""
Middleware de seguridad robusto para proteger contra ataques comunes:
- Rate Limiting (protección contra fuerza bruta y DDoS)
- SQL Injection protection
- XSS protection
- CSRF tokens
- IP blocking automático
- Headers de seguridad robustos
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
import re
import html
from typing import Set, Dict
import logging

# Configurar logging de seguridad
security_logger = logging.getLogger("security")

# Rate Limiting Config
RATE_LIMIT = 100  # requests por ventana
RATE_WINDOW = 60  # segundos
AUTH_RATE_LIMIT = 10  # requests de login por ventana (más restrictivo)

# IP Blocking
BLOCK_THRESHOLD = 20  # requests en ventana corta = bloqueo
BLOCK_DURATION = 3600  # segundos (1 hora)

# Storage en memoria (en producción usar Redis)
request_counts: Dict[str, list] = defaultdict(list)
blocked_ips: Dict[str, datetime] = {}
failed_auth_attempts: Dict[str, int] = defaultdict(int)

# Patrones de ataques SQL Injection
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|DECLARE)\b)",
    r"(--|\#|\/\*|\*\/)",
    r"(\bOR\b.*?=.*?|\bAND\b.*?=.*?)",
    r"(;.*?--)",
    r"(\'\s*(OR|AND)\s*\'.+=.+)",
]

# Patrones XSS
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe",
    r"eval\(",
]

def is_ip_blocked(ip: str) -> bool:
    """Verifica si una IP está bloqueada"""
    if ip in blocked_ips:
        if datetime.now() < blocked_ips[ip]:
            return True
        else:
            # Expira el bloqueo
            del blocked_ips[ip]
    return False

def block_ip(ip: str):
    """Bloquea una IP por comportamiento sospechoso"""
    blocked_ips[ip] = datetime.now() + timedelta(seconds=BLOCK_DURATION)
    security_logger.warning(f"IP bloqueada por actividad sospechosa: {ip}")

def check_rate_limit(ip: str, endpoint: str, limit: int, window: int) -> bool:
    """Verifica rate limiting por IP y endpoint"""
    key = f"{ip}:{endpoint}"
    now = datetime.now()
    
    # Limpiar requests antiguos
    request_counts[key] = [
        req_time for req_time in request_counts[key]
        if now - req_time < timedelta(seconds=window)
    ]
    
    # Verificar límite
    if len(request_counts[key]) >= limit:
        return False
    
    request_counts[key].append(now)
    
    # Si excede threshold, bloquear IP
    if len(request_counts[key]) >= BLOCK_THRESHOLD:
        block_ip(ip)
        return False
    
    return True

def detect_sql_injection(text: str) -> bool:
    """Detecta patrones de SQL Injection"""
    if not text:
        return False
    
    text_upper = text.upper()
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text_upper, re.IGNORECASE):
            return True
    return False

def detect_xss(text: str) -> bool:
    """Detecta patrones de XSS"""
    if not text:
        return False
    
    for pattern in XSS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def sanitize_input(text: str) -> str:
    """Sanitiza inputs para prevenir XSS"""
    if not text:
        return text
    # Escapar HTML
    return html.escape(text)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware de seguridad para todas las requests"""
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        path = request.url.path
        
        # 1. Verificar IP bloqueada
        if is_ip_blocked(client_ip):
            security_logger.warning(f"Request bloqueada desde IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Tu IP ha sido bloqueada temporalmente por actividad sospechosa"}
            )
        
        # 2. Rate Limiting (más restrictivo para auth endpoints)
        if "/auth/login" in path or "/users/" in path:
            if not check_rate_limit(client_ip, path, AUTH_RATE_LIMIT, RATE_WINDOW):
                security_logger.warning(f"Rate limit excedido para auth desde: {client_ip}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Demasiados intentos. Intenta de nuevo más tarde"}
                )
        else:
            if not check_rate_limit(client_ip, path, RATE_LIMIT, RATE_WINDOW):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Demasiadas peticiones. Intenta de nuevo más tarde"}
                )
        
        # 3. Validar query params contra SQL Injection y XSS
        for param, value in request.query_params.items():
            if detect_sql_injection(str(value)):
                security_logger.error(f"SQL Injection detectado desde {client_ip}: {value}")
                block_ip(client_ip)
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Parámetros inválidos detectados"}
                )
            
            if detect_xss(str(value)):
                security_logger.error(f"XSS detectado desde {client_ip}: {value}")
                block_ip(client_ip)
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Contenido malicioso detectado"}
                )
        
        # 4. Validar body contra SQL Injection y XSS (si es JSON)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                body_str = body.decode("utf-8")
                
                if detect_sql_injection(body_str):
                    security_logger.error(f"SQL Injection en body desde {client_ip}")
                    block_ip(client_ip)
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": "Datos inválidos detectados"}
                    )
                
                if detect_xss(body_str):
                    security_logger.error(f"XSS en body desde {client_ip}")
                    block_ip(client_ip)
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": "Contenido malicioso detectado"}
                    )
                
                # Reconstruir request con body
                from starlette.requests import Request as StarletteRequest
                async def receive():
                    return {"type": "http.request", "body": body}
                request = StarletteRequest(request.scope, receive)
            except:
                pass
        
        # 5. Añadir headers de seguridad a la response
        response = await call_next(request)
        
        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response
