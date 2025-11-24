from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.models.connection import get_db_connection
import re
from psycopg2.extras import RealDictCursor

rendas_bp = Blueprint('rendas', __name__)

def validar_mes_ano(mes_ano):
    """Valida se o formato do mês_ano é YYYY-MM"""
    if not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', mes_ano):
        return False
    return True

def validar_renda_data(data):
    """Valida os dados da renda"""
    errors = []
    
    if not data:
        return ["Dados JSON necessários"]
    
    if 'colaborador_id' not in data or not isinstance(data['colaborador_id'], int):
        errors.append("colaborador_id é obrigatório e deve ser um número inteiro")
    
    if 'mes_ano' not in data or not validar_mes_ano(data['mes_ano']):
        errors.append("mes_ano é obrigatório e deve estar no formato YYYY-MM")
    
    if 'valor' not in data or not isinstance(data['valor'], (int, float)) or data['valor'] < 0:
        errors.append("valor é obrigatório e deve ser um número positivo")
    
    return errors

@rendas_bp.route('/rendas', methods=['GET', 'POST'])
@jwt_required()
def rendas():
    try:
        if request.method == 'GET':
            mes = request.args.get('mes')
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                if mes:
                    # Validar formato do mês no GET também
                    if not validar_mes_ano(mes):
                        return jsonify({"error": "Formato de mês inválido. Use YYYY-MM."}), 400
                    
                    cursor.execute("""
                        SELECT rm.*, c.nome 
                        FROM renda_mensal rm
                        JOIN colaborador c ON rm.colaborador_id = c.id
                        WHERE rm.mes_ano = %s
                        ORDER BY c.nome
                    """, (mes,))
                else:
                    cursor.execute("""
                        SELECT rm.*, c.nome 
                        FROM renda_mensal rm
                        JOIN colaborador c ON rm.colaborador_id = c.id
                        ORDER BY rm.mes_ano DESC, c.nome
                    """)
                
                rendas = [dict(r) for r in cursor.fetchall()]
                return jsonify({"rendas": rendas})
        
        else:  # POST
            data = request.get_json()
            
            # Validar dados
            errors = validar_renda_data(data)
            if errors:
                return jsonify({"errors": errors}), 400
            
            # Verificar se colaborador existe
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT id FROM colaborador WHERE id = %s", (data['colaborador_id'],))
                if not cursor.fetchone():
                    return jsonify({"error": "Colaborador não encontrado"}), 400
                
                # Inserir/atualizar renda
                cursor.execute("""
                    INSERT INTO renda_mensal (colaborador_id, mes_ano, valor)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (colaborador_id, mes_ano)
                    DO UPDATE SET valor = EXCLUDED.valor
                    RETURNING id
                """, (data['colaborador_id'], data['mes_ano'], data['valor']))
                
                conn.commit()
                result = cursor.fetchone()
                
                return jsonify({
                    "id": result['id'],
                    "message": "Renda registrada/atualizada com sucesso"
                }), 201
    
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@rendas_bp.route('/rendas/<int:id>', methods=['PUT', 'DELETE'])
@jwt_required()
def renda_id(id):
    try:
        if request.method == 'PUT':
            data = request.get_json()
            
            # Validar dados
            if not data or 'valor' not in data:
                return jsonify({"error": "Campo 'valor' é obrigatório"}), 400
            
            if not isinstance(data['valor'], (int, float)) or data['valor'] < 0:
                return jsonify({"error": "Valor deve ser um número positivo"}), 400
            
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                # Verificar se a renda existe
                cursor.execute("SELECT id FROM renda_mensal WHERE id = %s", (id,))
                if not cursor.fetchone():
                    return jsonify({"error": "Renda não encontrada"}), 404
                
                # Atualizar valor
                cursor.execute(
                    "UPDATE renda_mensal SET valor = %s WHERE id = %s",
                    (data['valor'], id)
                )
                conn.commit()
                
                return jsonify({
                    "message": "Renda atualizada com sucesso",
                    "valor": data['valor']
                })
        
        else:  # DELETE
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                # Verificar se a renda existe
                cursor.execute("SELECT id FROM renda_mensal WHERE id = %s", (id,))
                if not cursor.fetchone():
                    return jsonify({"error": "Renda não encontrada"}), 404
                
                cursor.execute("DELETE FROM renda_mensal WHERE id = %s", (id,))
                conn.commit()
                
                return jsonify({"message": "Renda deletada com sucesso"})
    
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500
