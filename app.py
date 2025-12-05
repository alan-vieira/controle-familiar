# app.py
import os
from flask import Flask, jsonify
from flask_cors import CORS

# Importação dos blueprints
from routes.colaboradores import colaboradores_bp
from routes.despesas import despesas_bp
from routes.rendas import rendas_bp
from routes.divisao import divisao_bp
from routes.resumo import resumo_bp
from routes.auth import auth_bp

def create_app():
    app = Flask(__name__)

    # Configuração do CORS — CORRIGIDO: sem espaço na URL!
    CORS(app,
         origins=["https://controle-familiar-frontend.vercel.app"],
         supports_credentials=True,
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"])

    # Rotas de saúde
    @app.route('/')
    def index():
        return jsonify({
            'status': 'healthy',
            'message': 'Controle Familiar API'
        })

    @app.route('/health')
    def health():
        return jsonify({'status': 'OK'})

    # Registro dos blueprints
    app.register_blueprint(colaboradores_bp, url_prefix='/api')
    app.register_blueprint(despesas_bp, url_prefix='/api')
    app.register_blueprint(rendas_bp, url_prefix='/api')
    app.register_blueprint(divisao_bp, url_prefix='/api')
    app.register_blueprint(resumo_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api')

    return app


application = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port)
