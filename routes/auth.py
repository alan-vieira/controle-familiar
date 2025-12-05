# routes/auth.py
import os
import requests
from flask import Blueprint, request, jsonify
from jose import jwt
import json
from app.middleware.auth import require_supabase_auth

auth_bp = Blueprint('auth', __name__)

def get_supabase_user_info(access_token):
    """Obtém informações do usuário do Supabase usando o token de acesso do Google"""
    supabase_url = os.getenv('SUPABASE_URL')
    headers = {
        'Authorization': f'Bearer {access_token}',
        'apikey': os.getenv('SUPABASE_ANON_KEY')
    }

    # Fazendo uma requisição para obter informações do usuário autenticado
    response = requests.get(f'{supabase_url}/auth/v1/user', headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return None

@auth_bp.route('/auth/google', methods=['POST'])
def google_auth():
    """Rota para autenticação com Google - recebe ID token do Google e faz login no Supabase"""
    try:
        data = request.get_json()
        google_id_token = data.get('token')

        if not google_id_token:
            return jsonify({'error': 'Token do Google é necessário'}), 400

        # Configuração do Supabase para autenticação com Google
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')

        if not supabase_url or not supabase_anon_key:
            return jsonify({'error': 'Configurações do Supabase ausentes'}), 500

        # Faz a requisição para o Supabase para autenticar com o ID token do Google
        headers = {
            'apikey': supabase_anon_key,
            'Content-Type': 'application/json'
        }

        # O Supabase tem uma rota específica para autenticação OAuth com ID token
        auth_response = requests.post(
            f'{supabase_url}/auth/v1/verify',
            headers=headers,
            json={
                'type': 'id_token',
                'token': google_id_token,
                'provider': 'google'
            }
        )

        if auth_response.status_code in [200, 201]:
            auth_data = auth_response.json()
            return jsonify({
                'user': auth_data.get('user'),
                'access_token': auth_data.get('access_token'),
                'refresh_token': auth_data.get('refresh_token')
            })
        else:
            # Se o método acima não funcionar, tentamos o método alternativo
            # Enviar o token como parte da URL de callback
            auth_response_alt = requests.post(
                f'{supabase_url}/auth/v1/token?grant_type=id_token',
                headers=headers,
                json={
                    'provider': 'google',
                    'id_token': google_id_token
                }
            )

            if auth_response_alt.status_code in [200, 201]:
                auth_data = auth_response_alt.json()
                return jsonify({
                    'user': auth_data.get('user'),
                    'access_token': auth_data.get('access_token'),
                    'refresh_token': auth_data.get('refresh_token')
                })
            else:
                print(f"Erro na autenticação com o Google: {auth_response.text}")
                return jsonify({'error': 'Falha na autenticação com o Google', 'details': auth_response.text}), 401

    except Exception as e:
        print(f"Exceção durante autenticação com Google: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/auth/me', methods=['GET'])
@require_supabase_auth
def get_user():
    """Rota protegida para obter informações do usuário autenticado"""
    try:
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(' ')[1] if auth_header else None

        if not token:
            return jsonify({'error': 'Token ausente'}), 401

        # Decodificar o token JWT para obter informações do usuário
        payload = jwt.decode(
            token,
            os.getenv('SUPABASE_JWT_SECRET'),
            algorithms=['HS256'],
            audience='authenticated'
        )

        return jsonify({
            'user_id': payload.get('sub'),
            'email': payload.get('email'),
            'role': payload.get('role'),
            'exp': payload.get('exp')
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/auth/logout', methods=['POST'])
@require_supabase_auth
def logout():
    """Rota para logout (apenas para limpar o lado do cliente)"""
    return jsonify({'message': 'Logout realizado com sucesso'})