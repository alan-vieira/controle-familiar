from datetime import datetime
import re
from flask import Blueprint, request, jsonify
from flask_login import login_required
from connection import get_db_connection
from utils.date_utils import calcular_mes_vigente

despesas_bp = Blueprint('despesas', __name__)

# Valores válidos de categoria (alinhados com o schema.sql)
CATEGORIAS_VALIDAS = {
    'moradia',
    'alimentacao',
    'restaurante_lanche',
    'casa_utilidades',
    'saude',
    'transporte',
    'lazer_outros'
}

def normalizar_tipo_pg(tipo: str) -> str:
    t = tipo.lower().strip()
    if 'credito' in t or 'cartao' in t or 'cartão' in t:
        return 'credito'
    elif 'debito' in t or 'débito' in t:
        return 'debito'
    elif t in ('pix', 'dinheiro', 'outros'):
        return t
    return 'outros'

@despesas_bp.route('/despesas', methods=['GET', 'POST'])
@login_required 
def despesas():
    if request.method == 'GET':
        mes = request.args.get('mes_vigente')
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if mes:
                    cur.execute("""
                        SELECT d.*, c.nome AS colaborador_nome
                        FROM despesa d
                        JOIN colaborador c ON d.colaborador_id = c.id
                        WHERE d.mes_vigente = %s
                        ORDER BY d.data_compra DESC
                    """, (mes,))
                else:
                    cur.execute("""
                        SELECT d.*, c.nome AS colaborador_nome
                        FROM despesa d
                        JOIN colaborador c ON d.colaborador_id = c.id
                        ORDER BY d.data_compra DESC
                    """)
                rows = []
                for r in cur.fetchall():
                    row = dict(r)
                    if row.get('data_compra'):
                        # ✅ MANTIDO: Formato brasileiro DD/MM/YYYY para o frontend
                        row['data_compra'] = row['data_compra'].strftime('%d/%m/%Y')
                    rows.append(row)
                return jsonify(rows)
    else:  # POST
        data = request.json
        
        # Validações iniciais
        if not data:
            return jsonify({"error": "Dados JSON necessários"}), 400
            
        required_fields = ['data_compra', 'descricao', 'valor', 'tipo_pg', 'colaborador_id', 'categoria']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Campo obrigatório faltando: {field}"}), 400

        try:
            # ✅ POST aceita YYYY-MM-DD (padrão internacional para APIs)
            data_compra = datetime.strptime(data['data_compra'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Data inválida. Use YYYY-MM-DD."}), 400

        if data.get('valor', 0) <= 0:
            return jsonify({"error": "Valor deve ser maior que zero."}), 400

        tipo_pg = normalizar_tipo_pg(data['tipo_pg'])
        colab_id = data['colaborador_id']
        categoria = data.get('categoria')

        if not categoria or categoria not in CATEGORIAS_VALIDAS:
            return jsonify({"error": "Categoria inválida ou ausente."}), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verificar se colaborador existe
                cur.execute("SELECT id, nome, dia_fechamento FROM colaborador WHERE id = %s", (colab_id,))
                colab = cur.fetchone()
                if not colab:
                    return jsonify({"error": "Colaborador não encontrado"}), 400

                # Calcular mês vigente
                mes_vigente = calcular_mes_vigente(data_compra, tipo_pg, colab['dia_fechamento'])
                
                # Inserir despesa
                cur.execute("""
                    INSERT INTO despesa (
                        data_compra, mes_vigente, descricao, valor, tipo_pg, colaborador_id, categoria
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (data_compra, mes_vigente, data['descricao'], data['valor'], tipo_pg, colab_id, categoria))
                
                conn.commit()
                result = cur.fetchone()
                return jsonify({
                    "id": result['id'], 
                    "mes_vigente": mes_vigente,
                    "message": "Despesa criada com sucesso"
                }), 201

@despesas_bp.route('/despesas/<int:id>', methods=['PUT', 'DELETE'])
@login_required 
def despesa_id(id):
    if request.method == 'PUT':
        data = request.json
        
        # Validações
        if not data:
            return jsonify({"error": "Dados JSON necessários"}), 400
            
        required_fields = ['data_compra', 'descricao', 'valor', 'tipo_pg', 'colaborador_id', 'categoria']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Campo obrigatório faltando: {field}"}), 400

        try:
            # ✅ PUT também aceita YYYY-MM-DD
            data_compra = datetime.strptime(data['data_compra'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Data inválida. Use YYYY-MM-DD."}), 400

        if data.get('valor', 0) <= 0:
            return jsonify({"error": "Valor deve ser maior que zero."}), 400

        tipo_pg = normalizar_tipo_pg(data['tipo_pg'])
        colab_id = data['colaborador_id']
        categoria = data.get('categoria')

        if not categoria or categoria not in CATEGORIAS_VALIDAS:
            return jsonify({"error": "Categoria inválida ou ausente."}), 400

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verificar se colaborador existe
                cur.execute("SELECT dia_fechamento FROM colaborador WHERE id = %s", (colab_id,))
                colab = cur.fetchone()
                if not colab:
                    return jsonify({"error": "Colaborador não encontrado"}), 400

                # Verificar se despesa existe
                cur.execute("SELECT id FROM despesa WHERE id = %s", (id,))
                if not cur.fetchone():
                    return jsonify({"error": "Despesa não encontrada"}), 404

                # Calcular mês vigente
                mes_vigente = calcular_mes_vigente(data_compra, tipo_pg, colab['dia_fechamento'])
                
                # Atualizar despesa
                cur.execute("""
                    UPDATE despesa
                    SET data_compra=%s, mes_vigente=%s, descricao=%s, valor=%s, tipo_pg=%s, colaborador_id=%s, categoria=%s
                    WHERE id=%s
                """, (data_compra, mes_vigente, data['descricao'], data['valor'], tipo_pg, colab_id, categoria, id))
                
                conn.commit()
                return jsonify({
                    "message": "Despesa atualizada",
                    "mes_vigente": mes_vigente
                })
                
    else:  # DELETE
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verificar se despesa existe antes de deletar
                cur.execute("SELECT id FROM despesa WHERE id = %s", (id,))
                if not cur.fetchone():
                    return jsonify({"error": "Despesa não encontrada"}), 404
                    
                cur.execute("DELETE FROM despesa WHERE id=%s", (id,))
                conn.commit()
                return jsonify({"message": "Despesa deletada"})
