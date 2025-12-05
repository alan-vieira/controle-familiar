import os
from functools import wraps
from flask import request, jsonify
from jose import jwt


def require_supabase_auth(f):
    """Middleware para verificar autenticação com Supabase JWT"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({'error': 'Token de autorização ausente'}), 401

        try:
            # Expects "Bearer <token>" format
            token_parts = auth_header.split(' ')
            if len(token_parts) != 2 or token_parts[0].lower() != 'bearer':
                return jsonify({'error': 'Formato de token inválido'}), 401

            token = token_parts[1]

            # Decode the JWT token using Supabase's JWT secret
            payload = jwt.decode(
                token,
                os.getenv('SUPABASE_JWT_SECRET'),
                algorithms=['HS256'],
                audience='authenticated'
            )

            # Add user info to request context
            request.current_user = payload

            return f(*args, **kwargs)

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.JWTError as e:
            return jsonify({'error': f'Token inválido: {str(e)}'}), 401
        except Exception as e:
            return jsonify({'error': f'Erro na autenticação: {str(e)}'}), 401

    return decorated_function