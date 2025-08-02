from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from sqlalchemy import func, extract
from src.models.user import db
from src.models.financeiro import Receita, Despesa
from src.middleware.auth import token_required, plano_ativo_required
import calendar

financeiro_bp = Blueprint('financeiro', __name__)

@financeiro_bp.route('/receitas', methods=['POST'])
@plano_ativo_required
def criar_receita():
    """Criar nova receita"""
    try:
        data = request.get_json()
        
        # Validação dos campos obrigatórios
        required_fields = ['descricao', 'valor', 'data_receita', 'categoria']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} é obrigatório'}), 400
        
        # Validar categoria
        categorias_validas = ['comercio', 'servicos', 'industria', 'outros']
        if data['categoria'] not in categorias_validas:
            return jsonify({'error': 'Categoria inválida'}), 400
        
        # Validar valor
        try:
            valor = float(data['valor'])
            if valor <= 0:
                return jsonify({'error': 'Valor deve ser maior que zero'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Valor inválido'}), 400
        
        # Validar data
        try:
            data_receita = datetime.strptime(data['data_receita'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Data inválida. Use o formato YYYY-MM-DD'}), 400
        
        # Criar receita
        receita = Receita(
            user_id=g.current_user.id,
            descricao=data['descricao'],
            valor=valor,
            data_receita=data_receita,
            categoria=data['categoria'],
            comprovante_path=data.get('comprovante_path')
        )
        
        db.session.add(receita)
        db.session.commit()
        
        return jsonify({
            'message': 'Receita criada com sucesso',
            'receita': receita.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@financeiro_bp.route('/receitas', methods=['GET'])
@plano_ativo_required
def listar_receitas():
    """Listar receitas do usuário"""
    try:
        # Parâmetros de filtro
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        mes = request.args.get('mes', type=int)
        ano = request.args.get('ano', type=int)
        categoria = request.args.get('categoria')
        
        # Query base
        query = Receita.query.filter_by(user_id=g.current_user.id)
        
        # Aplicar filtros
        if mes and ano:
            query = query.filter(
                extract('month', Receita.data_receita) == mes,
                extract('year', Receita.data_receita) == ano
            )
        elif ano:
            query = query.filter(extract('year', Receita.data_receita) == ano)
        
        if categoria:
            query = query.filter(Receita.categoria == categoria)
        
        # Ordenar por data mais recente
        query = query.order_by(Receita.data_receita.desc())
        
        # Paginação
        receitas_paginadas = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'receitas': [receita.to_dict() for receita in receitas_paginadas.items],
            'total': receitas_paginadas.total,
            'pages': receitas_paginadas.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@financeiro_bp.route('/receitas/<int:receita_id>', methods=['PUT'])
@plano_ativo_required
def atualizar_receita(receita_id):
    """Atualizar receita"""
    try:
        receita = Receita.query.filter_by(
            id=receita_id, user_id=g.current_user.id
        ).first()
        
        if not receita:
            return jsonify({'error': 'Receita não encontrada'}), 404
        
        data = request.get_json()
        
        # Atualizar campos permitidos
        if 'descricao' in data:
            receita.descricao = data['descricao']
        
        if 'valor' in data:
            try:
                valor = float(data['valor'])
                if valor <= 0:
                    return jsonify({'error': 'Valor deve ser maior que zero'}), 400
                receita.valor = valor
            except (ValueError, TypeError):
                return jsonify({'error': 'Valor inválido'}), 400
        
        if 'data_receita' in data:
            try:
                receita.data_receita = datetime.strptime(data['data_receita'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Data inválida. Use o formato YYYY-MM-DD'}), 400
        
        if 'categoria' in data:
            categorias_validas = ['comercio', 'servicos', 'industria', 'outros']
            if data['categoria'] not in categorias_validas:
                return jsonify({'error': 'Categoria inválida'}), 400
            receita.categoria = data['categoria']
        
        receita.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Receita atualizada com sucesso',
            'receita': receita.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@financeiro_bp.route('/receitas/<int:receita_id>', methods=['DELETE'])
@plano_ativo_required
def deletar_receita(receita_id):
    """Deletar receita"""
    try:
        receita = Receita.query.filter_by(
            id=receita_id, user_id=g.current_user.id
        ).first()
        
        if not receita:
            return jsonify({'error': 'Receita não encontrada'}), 404
        
        db.session.delete(receita)
        db.session.commit()
        
        return jsonify({'message': 'Receita deletada com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@financeiro_bp.route('/despesas', methods=['POST'])
@plano_ativo_required
def criar_despesa():
    """Criar nova despesa"""
    try:
        data = request.get_json()
        
        # Validação dos campos obrigatórios
        required_fields = ['descricao', 'valor', 'data_despesa', 'categoria']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} é obrigatório'}), 400
        
        # Validar categoria
        categorias_validas = ['material', 'equipamento', 'servicos', 'outros']
        if data['categoria'] not in categorias_validas:
            return jsonify({'error': 'Categoria inválida'}), 400
        
        # Validar valor
        try:
            valor = float(data['valor'])
            if valor <= 0:
                return jsonify({'error': 'Valor deve ser maior que zero'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Valor inválido'}), 400
        
        # Validar data
        try:
            data_despesa = datetime.strptime(data['data_despesa'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Data inválida. Use o formato YYYY-MM-DD'}), 400
        
        # Criar despesa
        despesa = Despesa(
            user_id=g.current_user.id,
            descricao=data['descricao'],
            valor=valor,
            data_despesa=data_despesa,
            categoria=data['categoria'],
            comprovante_path=data.get('comprovante_path')
        )
        
        db.session.add(despesa)
        db.session.commit()
        
        return jsonify({
            'message': 'Despesa criada com sucesso',
            'despesa': despesa.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@financeiro_bp.route('/despesas', methods=['GET'])
@plano_ativo_required
def listar_despesas():
    """Listar despesas do usuário"""
    try:
        # Parâmetros de filtro
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        mes = request.args.get('mes', type=int)
        ano = request.args.get('ano', type=int)
        categoria = request.args.get('categoria')
        
        # Query base
        query = Despesa.query.filter_by(user_id=g.current_user.id)
        
        # Aplicar filtros
        if mes and ano:
            query = query.filter(
                extract('month', Despesa.data_despesa) == mes,
                extract('year', Despesa.data_despesa) == ano
            )
        elif ano:
            query = query.filter(extract('year', Despesa.data_despesa) == ano)
        
        if categoria:
            query = query.filter(Despesa.categoria == categoria)
        
        # Ordenar por data mais recente
        query = query.order_by(Despesa.data_despesa.desc())
        
        # Paginação
        despesas_paginadas = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'despesas': [despesa.to_dict() for despesa in despesas_paginadas.items],
            'total': despesas_paginadas.total,
            'pages': despesas_paginadas.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@financeiro_bp.route('/dashboard', methods=['GET'])
@plano_ativo_required
def dashboard():
    """Dashboard com resumo financeiro"""
    try:
        # Parâmetros
        mes = request.args.get('mes', datetime.now().month, type=int)
        ano = request.args.get('ano', datetime.now().year, type=int)
        
        # Receitas do mês por categoria
        receitas_mes = db.session.query(
            Receita.categoria,
            func.sum(Receita.valor).label('total')
        ).filter(
            Receita.user_id == g.current_user.id,
            extract('month', Receita.data_receita) == mes,
            extract('year', Receita.data_receita) == ano
        ).group_by(Receita.categoria).all()
        
        # Despesas do mês por categoria
        despesas_mes = db.session.query(
            Despesa.categoria,
            func.sum(Despesa.valor).label('total')
        ).filter(
            Despesa.user_id == g.current_user.id,
            extract('month', Despesa.data_despesa) == mes,
            extract('year', Despesa.data_despesa) == ano
        ).group_by(Despesa.categoria).all()
        
        # Total de receitas e despesas do mês
        total_receitas_mes = sum([r.total for r in receitas_mes])
        total_despesas_mes = sum([d.total for d in despesas_mes])
        
        # Receitas dos últimos 12 meses
        receitas_12_meses = []
        for i in range(12):
            data_ref = datetime.now() - timedelta(days=30*i)
            mes_ref = data_ref.month
            ano_ref = data_ref.year
            
            total = db.session.query(func.sum(Receita.valor)).filter(
                Receita.user_id == g.current_user.id,
                extract('month', Receita.data_receita) == mes_ref,
                extract('year', Receita.data_receita) == ano_ref
            ).scalar() or 0
            
            receitas_12_meses.append({
                'mes': mes_ref,
                'ano': ano_ref,
                'nome_mes': calendar.month_name[mes_ref],
                'total': float(total)
            })
        
        receitas_12_meses.reverse()
        
        # Receitas por categoria (ano atual)
        receitas_ano_categoria = db.session.query(
            Receita.categoria,
            func.sum(Receita.valor).label('total')
        ).filter(
            Receita.user_id == g.current_user.id,
            extract('year', Receita.data_receita) == ano
        ).group_by(Receita.categoria).all()
        
        return jsonify({
            'mes_atual': {
                'mes': mes,
                'ano': ano,
                'receitas_por_categoria': [
                    {'categoria': r.categoria, 'total': float(r.total)}
                    for r in receitas_mes
                ],
                'despesas_por_categoria': [
                    {'categoria': d.categoria, 'total': float(d.total)}
                    for d in despesas_mes
                ],
                'total_receitas': float(total_receitas_mes),
                'total_despesas': float(total_despesas_mes),
                'saldo': float(total_receitas_mes - total_despesas_mes)
            },
            'receitas_12_meses': receitas_12_meses,
            'receitas_ano_categoria': [
                {'categoria': r.categoria, 'total': float(r.total)}
                for r in receitas_ano_categoria
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

