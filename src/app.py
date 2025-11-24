# app.py
import os
from flask import Flask, jsonify
from flask_cors import CORS
<<<<<<< HEAD:app.py
from flask_jwt_extended import JWTManager
from config import SECRET_KEY
from datetime import timedelta
=======
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import logging
from src.models.connection import get_db_connection
from src.config.config import SECRET_KEY
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash
>>>>>>> 96d840c9ff079f97be4fef6024b42cde3b5975b9:src/app.py

# Importe seus blueprints
from blueprints.auth import auth_bp
from blueprints.colaboradores import colaboradores_bp
from blueprints.despesas import despesas_bp
from blueprints.rendas import rendas_bp
from blueprints.divisao import divisao_bp
from blueprints.resumo import resumo_bp

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['JWT_SECRET_KEY'] = SECRET_KEY
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

    # CORS — atenção: sem espaços na origem!
    CORS(app,
         origins=['https://controle-familiar-frontend.vercel.app'],
         supports_credentials=True,
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization'])

    # JWT
    jwt = JWTManager(app)

    # Rotas de saúde
    @app.route('/')
    def index():
        return jsonify({'status': 'healthy', 'message': 'Controle Familiar API'})

    @app.route('/health')
    def health():
        return jsonify({'status': 'OK'})

    # Registrar blueprints
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(colaboradores_bp, url_prefix='/api')
    app.register_blueprint(despesas_bp, url_prefix='/api')
    app.register_blueprint(rendas_bp, url_prefix='/api')
    app.register_blueprint(divisao_bp, url_prefix='/api')
    app.register_blueprint(resumo_bp, url_prefix='/api')

    return app

# Para Render
def application(environ, start_response):
    app = create_app()
    return app(environ, start_response)

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)