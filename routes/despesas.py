from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from database import get_db_connection
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

despesas_bp = Blueprint('despesas', __name__)

@despesas_bp.route('/api/despesas', methods=['GET'])
@login_required
def despesas():
    try:
        logger.info("GET /api/despesas - Iniciando")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)  # Isso retorna dicionários
        
        cursor.execute("""
            SELECT d.*, c.nome as colaborador_nome 
            FROM despesa d 
            JOIN colaborador c ON d.colaborador_id = c.id 
            ORDER BY d.data_compra DESC
        """)
        despesas = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Já são dicionários, só precisamos converter datas e decimais
        for despesa in despesas:
            if despesa.get('data_compra'):
                despesa['data_compra'] = despesa['data_compra'].isoformat()
            if despesa.get('valor'):
                despesa['valor'] = float(despesa['valor'])
        
        logger.info(f"GET /api/despesas - Encontrados {len(despesas)} registros")
        return jsonify(despesas)
        
    except Exception as e:
        logger.error(f"ERRO GET /api/despesas: {str(e)}", exc_info=True)
        return jsonify({'error': 'Erro ao buscar despesas'}), 500

@despesas_bp.route('/api/despesas', methods=['POST'])
@login_required
def criar_despesa():
    try:
        data = request.get_json()
        logger.info(f"POST /api/despesas - Dados: {data}")
        
        if not data:
            return jsonify({'error': 'Dados JSON inválidos'}), 400
        
        # Campos obrigatórios
        required = ['data_compra', 'descricao', 'valor', 'tipo_pg', 'colaborador_id', 'categoria']
        missing = [field for field in required if field not in data or data[field] in [None, '']]
        
        if missing:
            return jsonify({'error': f'Campos obrigatórios faltando: {missing}'}), 400
        
        # Validar valores
        try:
            valor = float(data['valor'])
            colaborador_id = int(data['colaborador_id'])
        except (ValueError, TypeError):
            return jsonify({'error': 'valor ou colaborador_id inválidos'}), 400
        
        # Tipos de pagamento válidos
        tipos_pg_validos = ['credito', 'debito', 'pix', 'dinheiro', 'outros']
        if data['tipo_pg'] not in tipos_pg_validos:
            return jsonify({'error': f'tipo_pg inválido. Use: {tipos_pg_validos}'}), 400
        
        # Categorias válidas
        categorias_validas = [
            'moradia', 'alimentacao', 'restaurante_lanche', 
            'casa_utilidades', 'saude', 'transporte', 'lazer_outros'
        ]
        if data['categoria'] not in categorias_validas:
            return jsonify({'error': f'categoria inválida. Use: {categorias_validas}'}), 400
        
        # Processar data e calcular mes_vigente
        data_compra = data['data_compra']
        if 'T' in data_compra:
            data_compra = data_compra.split('T')[0]
        
        data_obj = datetime.strptime(data_compra, '%Y-%m-%d')
        mes_vigente = data_obj.strftime('%Y-%m')
        
        # Inserir no banco
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO despesa 
               (data_compra, mes_vigente, descricao, valor, tipo_pg, colaborador_id, categoria) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (data_compra, mes_vigente, data['descricao'], valor, data['tipo_pg'], colaborador_id, data['categoria'])
        )
        
        conn.commit()
        despesa_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        response_data = {
            'id': despesa_id,
            'data_compra': data_compra,
            'mes_vigente': mes_vigente,
            'descricao': data['descricao'],
            'valor': valor,
            'tipo_pg': data['tipo_pg'],
            'colaborador_id': colaborador_id,
            'categoria': data['categoria'],
            'message': 'Despesa criada com sucesso'
        }
        
        logger.info(f"POST /api/despesas - Sucesso: {response_data}")
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"ERRO POST /api/despesas: {str(e)}", exc_info=True)
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500