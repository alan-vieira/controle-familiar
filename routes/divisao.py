from flask import Blueprint, request, jsonify
from flask_login import login_required
from connection import get_db_connection
from datetime import date
import re

divisao_bp = Blueprint('divisao', __name__)

def validar_mes_ano(mes_ano):
    """Valida se o formato do mês_ano é YYYY-MM"""
    if not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', mes_ano):
        return False
    return True

@divisao_bp.route('/divisao/<mes_ano>', methods=['GET'])
@login_required
def obter_status_divisao(mes_ano):
    try:
        # Validar formato do mês_ano
        if not validar_mes_ano(mes_ano):
            return jsonify({"error": "Formato de mês inválido. Use YYYY-MM."}), 400
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT paga, data_acerto FROM divisao_mensal WHERE mes_ano = %s", (mes_ano,))
                row = cur.fetchone()
                if row:
                    return jsonify({
                        "mes_ano": mes_ano,
                        "paga": row['paga'],
                        "data_acerto": row['data_acerto'].isoformat() if row['data_acerto'] else None
                    })
                else:
                    # Retornar status padrão para mês não registrado
                    return jsonify({
                        "mes_ano": mes_ano, 
                        "paga": False, 
                        "data_acerto": None,
                        "message": "Mês não registrado na divisão"
                    })
    
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@divisao_bp.route('/divisao/<mes_ano>/marcar-pago', methods=['POST'])
@login_required
def marcar_divisao_como_paga(mes_ano):
    try:
        # Validar formato do mês_ano
        if not validar_mes_ano(mes_ano):
            return jsonify({"error": "Formato de mês inválido. Use YYYY-MM."}), 400
        
        data = request.get_json() or {}
        data_acerto = data.get('data_acerto')
        
        # Validar data_acerto se for fornecida
        if data_acerto:
            try:
                # Validar formato YYYY-MM-DD
                date.fromisoformat(data_acerto)
            except ValueError:
                return jsonify({"error": "data_acerto deve estar no formato YYYY-MM-DD"}), 400
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO divisao_mensal (mes_ano, paga, data_acerto)
                    VALUES (%s, true, %s)
                    ON CONFLICT (mes_ano)
                    DO UPDATE SET paga = true, data_acerto = EXCLUDED.data_acerto
                    RETURNING mes_ano, paga, data_acerto
                """, (mes_ano, data_acerto))
                
                conn.commit()
                result = cur.fetchone()
                
                return jsonify({
                    "mes_ano": result['mes_ano'],
                    "paga": result['paga'],
                    "data_acerto": result['data_acerto'].isoformat() if result['data_acerto'] else None,
                    "message": "Divisão marcada como paga"
                }), 200
    
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@divisao_bp.route('/divisao/<mes_ano>/desmarcar-pago', methods=['POST'])
@login_required
def desmarcar_divisao_como_paga(mes_ano):
    try:
        # Validar formato do mês_ano
        if not validar_mes_ano(mes_ano):
            return jsonify({"error": "Formato de mês inválido. Use YYYY-MM."}), 400
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE divisao_mensal 
                    SET paga = false, data_acerto = NULL 
                    WHERE mes_ano = %s
                    RETURNING mes_ano, paga, data_acerto
                """, (mes_ano,))
                
                conn.commit()
                
                # Verificar se algum registro foi atualizado
                if cur.rowcount == 0:
                    # Se não existia registro, criar um com paga = false
                    cur.execute("""
                        INSERT INTO divisao_mensal (mes_ano, paga) 
                        VALUES (%s, false)
                        RETURNING mes_ano, paga, data_acerto
                    """, (mes_ano,))
                    conn.commit()
                
                result = cur.fetchone()
                
                return jsonify({
                    "mes_ano": result['mes_ano'],
                    "paga": result['paga'],
                    "data_acerto": result['data_acerto'],
                    "message": "Divisão desmarcada como paga"
                }), 200
    
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500
