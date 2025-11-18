from datetime import datetime
import re
from flask import Blueprint, request, jsonify
from connection import get_db_connection # Ajuste o caminho de importação
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
                    """, (mes,))
                else:
                    cur.execute("""
                        SELECT d.*, c.nome AS colaborador_nome
                        FROM despesa d
                        JOIN colaborador c ON d.colaborador_id = c.id
                    """)
                rows = []
                for r in cur.fetchall():
                    row = dict(r)
                    if row.get('data_compra'):
                        row['data_compra'] = row['data_compra'].strftime('%d/%m/%Y')
                    rows.append(row)
                return jsonify(rows)
    else: # POST
        data = request.json
        try:
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
                cur.execute("SELECT dia_fechamento FROM colaborador WHERE id = %s", (colab_id,))
                colab = cur.fetchone()
                if not colab:
                    return jsonify({"error": "Colaborador não encontrado"}), 400

                mes_vigente = calcular_mes_vigente(data_compra, tipo_pg, colab['dia_fechamento'])
                cur.execute("""
                    INSERT INTO despesa (
                        data_compra, mes_vigente, descricao, valor, tipo_pg, colaborador_id, categoria
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (data_compra, mes_vigente, data['descricao'], data['valor'], tipo_pg, colab_id, categoria))
                conn.commit()
                result = cur.fetchone()
                # Ajuste aqui: pegar o ID retornado da forma correta
                # Supondo que seu psycopg2 retorne um RealDictRow ou similar com 'id'
                # Se retornar uma tupla (id,), use result[0]
                # O mais comum com RETURNING é RealDictRow, então result['id'] deve funcionar
                return jsonify({"id": result['id'], "mes_vigente": mes_vigente}), 201

@despesas_bp.route('/despesas/<int:id>', methods=['PUT', 'DELETE'])
def despesa_id(id):
    if request.method == 'PUT':
        data = request.json
        try:
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
                cur.execute("SELECT dia_fechamento FROM colaborador WHERE id = %s", (colab_id,))
                colab = cur.fetchone()
                if not colab:
                    return jsonify({"error": "Colaborador não encontrado"}), 400

                mes_vigente = calcular_mes_vigente(data_compra, tipo_pg, colab['dia_fechamento'])
                cur.execute("""
                    UPDATE despesa
                    SET data_compra=%s, mes_vigente=%s, descricao=%s, valor=%s, tipo_pg=%s, colaborador_id=%s, categoria=%s
                    WHERE id=%s
                """, (data_compra, mes_vigente, data['descricao'], data['valor'], tipo_pg, colab_id, categoria, id))
                conn.commit()
                return jsonify({"message": "Atualizado"})
    else: # DELETE
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM despesa WHERE id=%s", (id,))
                conn.commit()
                return jsonify({"message": "Deletado"})
