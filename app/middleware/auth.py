# app/middleware/auth.py
from functools import wraps
from flask import request, jsonify
from jose import jwt, JWTError
import os

def require_supabase_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return jsonify({"error": "Token ausente"}), 401

        token = auth.split(" ")[1]
        try:
            jwt.decode(
                token,
                os.getenv("SUPABASE_JWT_SECRET"),
                algorithms=["HS256"],
                audience="authenticated",
                issuer=f"{os.getenv('SUPABASE_URL')}/"
            )
            # Opcional: extrair user_id com `payload = jwt.decode(...)` e usar em logs ou allowlist
        except JWTError:
            return jsonify({"error": "Token inválido"}), 401

        return f(*args, **kwargs)
    return decorated
