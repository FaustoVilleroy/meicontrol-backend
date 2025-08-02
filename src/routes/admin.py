from flask import Blueprint, request, jsonify, g
from datetime import datetime, date, timedelta
from calendar import monthrange
from sqlalchemy import func, extract, and_
from src.models.user import db, User
from src.models.financeiro import Receita, Despesa
from src.models.nota_fiscal import NotaFiscal
from src.models.relatorio import RelatorioMensal
from src.middleware.auth import token_required
import json

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator para verificar se o usuário é administrador"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.current_user.is_admin:
            return jsonify({'error': 'Acesso negado. Privilégios de administrador necessários.'}), 403
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin/dashboard', methods=['GET'])
@token_required
@admin_required
def dashboard_admin():
    """Dashboard principal do administrador"""
    try:
        hoje = date.today()
        inicio_mes = date(hoje.year, hoje.month, 1)
        
        # Métricas gerais
        total_usuarios = User.query.count()
        usuarios_ativos = User.query.filter_by(is_active=True).count()
        usuarios_inativos = total_usuarios - usuarios_ativos
        
        # Usuários por plano
        usuarios_basico = User.query.filter_by(plano='basico', is_active=True).count()
        usuarios_avancado = User.query.filter_by(plano='avancado', is_active=True).count()
        
        # Usuários por status de pagamento
        usuarios_adimplentes = User.query.filter_by(status_pagamento='ativo', is_active=True).count()
        usuarios_inadimplentes = User.query.filter_by(status_pagamento='inadimplente', is_active=True).count()
        
        # Novos usuários no mês
        novos_usuarios_mes = User.query.filter(
            User.created_at >= inicio_mes,
            User.created_at < date(hoje.year, hoje.month + 1 if hoje.month < 12 else hoje.year + 1, 1)
        ).count()
        
        # Receita estimada mensal (baseada nos planos)
        receita_basico = usuarios_basico * 29.90
        receita_avancado = usuarios_avancado * 59.90
        receita_total_estimada = receita_basico + receita_avancado
        
        # Métricas de uso
        total_receitas_cadastradas = Receita.query.count()
        total_despesas_cadastradas = Despesa.query.count()
        total_notas_fiscais = NotaFiscal.query.count()
        total_relatorios_gerados = RelatorioMensal.query.count()
        
        # Atividade no mês atual
        receitas_mes = Receita.query.filter(
            Receita.created_at >= inicio_mes
        ).count()
        
        despesas_mes = Despesa.query.filter(
            Despesa.created_at >= inicio_mes
        ).count()
        
        notas_mes = NotaFiscal.query.filter(
            NotaFiscal.created_at >= inicio_mes
        ).count()
        
        relatorios_mes = RelatorioMensal.query.filter(
            RelatorioMensal.created_at >= inicio_mes
        ).count()
        
        # Top categorias MEI
        categorias_mei = db.session.query(
            User.categoria_mei,
            func.count(User.id).label('count')
        ).filter(User.is_active == True).group_by(User.categoria_mei).all()
        
        dashboard_data = {
            'metricas_gerais': {
                'total_usuarios': total_usuarios,
                'usuarios_ativos': usuarios_ativos,
                'usuarios_inativos': usuarios_inativos,
                'novos_usuarios_mes': novos_usuarios_mes,
                'taxa_crescimento': round((novos_usuarios_mes / max(total_usuarios - novos_usuarios_mes, 1)) * 100, 2)
            },
            'distribuicao_planos': {
                'basico': usuarios_basico,
                'avancado': usuarios_avancado,
                'percentual_basico': round((usuarios_basico / max(usuarios_ativos, 1)) * 100, 1),
                'percentual_avancado': round((usuarios_avancado / max(usuarios_ativos, 1)) * 100, 1)
            },
            'status_pagamento': {
                'adimplentes': usuarios_adimplentes,
                'inadimplentes': usuarios_inadimplentes,
                'taxa_inadimplencia': round((usuarios_inadimplentes / max(usuarios_ativos, 1)) * 100, 2)
            },
            'receita_estimada': {
                'mensal_total': round(receita_total_estimada, 2),
                'anual_estimada': round(receita_total_estimada * 12, 2),
                'receita_basico': round(receita_basico, 2),
                'receita_avancado': round(receita_avancado, 2)
            },
            'metricas_uso': {
                'total_receitas': total_receitas_cadastradas,
                'total_despesas': total_despesas_cadastradas,
                'total_notas_fiscais': total_notas_fiscais,
                'total_relatorios': total_relatorios_gerados,
                'media_receitas_por_usuario': round(total_receitas_cadastradas / max(usuarios_ativos, 1), 2),
                'media_despesas_por_usuario': round(total_despesas_cadastradas / max(usuarios_ativos, 1), 2)
            },
            'atividade_mensal': {
                'receitas_mes': receitas_mes,
                'despesas_mes': despesas_mes,
                'notas_mes': notas_mes,
                'relatorios_mes': relatorios_mes
            },
            'categorias_mei': [
                {'categoria': cat[0] or 'Não informado', 'quantidade': cat[1]}
                for cat in categorias_mei
            ]
        }
        
        return jsonify(dashboard_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/usuarios', methods=['GET'])
@token_required
@admin_required
def listar_usuarios():
    """Listar todos os usuários com filtros"""
    try:
        # Parâmetros de filtro
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        plano = request.args.get('plano')
        status = request.args.get('status')
        categoria = request.args.get('categoria')
        busca = request.args.get('busca')
        
        # Query base
        query = User.query
        
        # Aplicar filtros
        if plano:
            query = query.filter(User.plano == plano)
        
        if status:
            if status == 'ativo':
                query = query.filter(User.is_active == True)
            elif status == 'inativo':
                query = query.filter(User.is_active == False)
            elif status == 'adimplente':
                query = query.filter(User.status_pagamento == 'ativo')
            elif status == 'inadimplente':
                query = query.filter(User.status_pagamento == 'inadimplente')
        
        if categoria:
            query = query.filter(User.categoria_mei == categoria)
        
        if busca:
            query = query.filter(
                db.or_(
                    User.nome.ilike(f'%{busca}%'),
                    User.email.ilike(f'%{busca}%'),
                    User.cnpj.ilike(f'%{busca}%')
                )
            )
        
        # Ordenar por data de criação (mais recentes primeiro)
        query = query.order_by(User.created_at.desc())
        
        # Paginação
        usuarios_paginados = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Preparar dados para resposta
        usuarios_lista = []
        for usuario in usuarios_paginados.items:
            # Calcular estatísticas do usuário
            receitas_count = Receita.query.filter_by(user_id=usuario.id).count()
            despesas_count = Despesa.query.filter_by(user_id=usuario.id).count()
            notas_count = NotaFiscal.query.filter_by(user_id=usuario.id).count()
            relatorios_count = RelatorioMensal.query.filter_by(user_id=usuario.id).count()
            
            usuario_data = usuario.to_dict()
            usuario_data.update({
                'estatisticas': {
                    'receitas': receitas_count,
                    'despesas': despesas_count,
                    'notas_fiscais': notas_count,
                    'relatorios': relatorios_count
                }
            })
            usuarios_lista.append(usuario_data)
        
        return jsonify({
            'usuarios': usuarios_lista,
            'total': usuarios_paginados.total,
            'pages': usuarios_paginados.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/usuario/<int:user_id>', methods=['GET'])
@token_required
@admin_required
def detalhes_usuario(user_id):
    """Obter detalhes completos de um usuário"""
    try:
        usuario = User.query.get_or_404(user_id)
        
        # Estatísticas detalhadas
        receitas = Receita.query.filter_by(user_id=user_id).all()
        despesas = Despesa.query.filter_by(user_id=user_id).all()
        notas_fiscais = NotaFiscal.query.filter_by(user_id=user_id).all()
        relatorios = RelatorioMensal.query.filter_by(user_id=user_id).order_by(RelatorioMensal.ano.desc(), RelatorioMensal.mes.desc()).all()
        
        # Calcular totais
        total_receitas = sum(float(r.valor) for r in receitas)
        total_despesas = sum(float(d.valor) for d in despesas)
        
        # Atividade por mês (últimos 12 meses)
        hoje = date.today()
        atividade_mensal = []
        
        for i in range(12):
            mes_ref = hoje.replace(day=1) - timedelta(days=i*30)
            mes_inicio = mes_ref.replace(day=1)
            mes_fim = mes_ref.replace(day=monthrange(mes_ref.year, mes_ref.month)[1])
            
            receitas_mes = Receita.query.filter(
                Receita.user_id == user_id,
                Receita.data_receita >= mes_inicio,
                Receita.data_receita <= mes_fim
            ).count()
            
            despesas_mes = Despesa.query.filter(
                Despesa.user_id == user_id,
                Despesa.data_despesa >= mes_inicio,
                Despesa.data_despesa <= mes_fim
            ).count()
            
            atividade_mensal.append({
                'mes': f"{mes_ref.month:02d}/{mes_ref.year}",
                'receitas': receitas_mes,
                'despesas': despesas_mes
            })
        
        detalhes = {
            'usuario': usuario.to_dict(),
            'estatisticas': {
                'total_receitas_valor': round(total_receitas, 2),
                'total_despesas_valor': round(total_despesas, 2),
                'saldo_total': round(total_receitas - total_despesas, 2),
                'quantidade_receitas': len(receitas),
                'quantidade_despesas': len(despesas),
                'quantidade_notas_fiscais': len(notas_fiscais),
                'quantidade_relatorios': len(relatorios)
            },
            'atividade_mensal': list(reversed(atividade_mensal)),
            'ultimos_relatorios': [
                {
                    'id': r.id,
                    'mes': r.mes,
                    'ano': r.ano,
                    'total_receitas': float(r.total_receitas),
                    'total_despesas': float(r.total_despesas),
                    'saldo_mes': float(r.saldo_mes),
                    'created_at': r.created_at.strftime('%d/%m/%Y %H:%M')
                }
                for r in relatorios[:5]
            ]
        }
        
        return jsonify(detalhes), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/usuario/<int:user_id>/status', methods=['PUT'])
@token_required
@admin_required
def alterar_status_usuario(user_id):
    """Alterar status de um usuário (ativar/desativar)"""
    try:
        dados = request.get_json()
        usuario = User.query.get_or_404(user_id)
        
        novo_status = dados.get('is_active')
        if novo_status is not None:
            usuario.is_active = novo_status
        
        novo_status_pagamento = dados.get('status_pagamento')
        if novo_status_pagamento in ['ativo', 'inadimplente', 'cancelado']:
            usuario.status_pagamento = novo_status_pagamento
        
        novo_plano = dados.get('plano')
        if novo_plano in ['basico', 'avancado']:
            usuario.plano = novo_plano
        
        usuario.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Status do usuário atualizado com sucesso',
            'usuario': usuario.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/metricas/financeiras', methods=['GET'])
@token_required
@admin_required
def metricas_financeiras():
    """Métricas financeiras da plataforma"""
    try:
        # Parâmetros
        periodo = request.args.get('periodo', '12')  # meses
        meses = int(periodo)
        
        hoje = date.today()
        metricas_mensais = []
        
        for i in range(meses):
            # Calcular mês de referência
            if hoje.month - i <= 0:
                mes_ref = 12 + (hoje.month - i)
                ano_ref = hoje.year - 1
            else:
                mes_ref = hoje.month - i
                ano_ref = hoje.year
            
            inicio_mes = date(ano_ref, mes_ref, 1)
            fim_mes = date(ano_ref, mes_ref, monthrange(ano_ref, mes_ref)[1])
            
            # Usuários ativos no mês
            usuarios_ativos_mes = User.query.filter(
                User.is_active == True,
                User.created_at <= fim_mes
            ).count()
            
            # Novos usuários no mês
            novos_usuarios = User.query.filter(
                User.created_at >= inicio_mes,
                User.created_at <= fim_mes
            ).count()
            
            # Usuários por plano no final do mês
            usuarios_basico = User.query.filter(
                User.plano == 'basico',
                User.is_active == True,
                User.created_at <= fim_mes
            ).count()
            
            usuarios_avancado = User.query.filter(
                User.plano == 'avancado',
                User.is_active == True,
                User.created_at <= fim_mes
            ).count()
            
            # Receita estimada
            receita_mes = (usuarios_basico * 29.90) + (usuarios_avancado * 59.90)
            
            # Taxa de churn (usuários que cancelaram)
            usuarios_cancelados = User.query.filter(
                User.status_pagamento == 'cancelado',
                User.updated_at >= inicio_mes,
                User.updated_at <= fim_mes
            ).count()
            
            churn_rate = round((usuarios_cancelados / max(usuarios_ativos_mes, 1)) * 100, 2)
            
            metricas_mensais.append({
                'mes': f"{mes_ref:02d}/{ano_ref}",
                'usuarios_ativos': usuarios_ativos_mes,
                'novos_usuarios': novos_usuarios,
                'usuarios_basico': usuarios_basico,
                'usuarios_avancado': usuarios_avancado,
                'receita_estimada': round(receita_mes, 2),
                'usuarios_cancelados': usuarios_cancelados,
                'churn_rate': churn_rate
            })
        
        # Reverter para ordem cronológica
        metricas_mensais.reverse()
        
        # Calcular totais
        receita_total_periodo = sum(m['receita_estimada'] for m in metricas_mensais)
        usuarios_finais = metricas_mensais[-1]['usuarios_ativos'] if metricas_mensais else 0
        usuarios_iniciais = metricas_mensais[0]['usuarios_ativos'] if metricas_mensais else 0
        crescimento_periodo = round(((usuarios_finais - usuarios_iniciais) / max(usuarios_iniciais, 1)) * 100, 2)
        
        return jsonify({
            'metricas_mensais': metricas_mensais,
            'resumo_periodo': {
                'receita_total': round(receita_total_periodo, 2),
                'crescimento_usuarios': crescimento_periodo,
                'usuarios_inicio': usuarios_iniciais,
                'usuarios_fim': usuarios_finais,
                'media_churn': round(sum(m['churn_rate'] for m in metricas_mensais) / max(len(metricas_mensais), 1), 2)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/metricas/uso', methods=['GET'])
@token_required
@admin_required
def metricas_uso():
    """Métricas de uso da plataforma"""
    try:
        hoje = date.today()
        inicio_mes = date(hoje.year, hoje.month, 1)
        
        # Métricas de engajamento
        usuarios_com_receitas = db.session.query(Receita.user_id).distinct().count()
        usuarios_com_despesas = db.session.query(Despesa.user_id).distinct().count()
        usuarios_com_notas = db.session.query(NotaFiscal.user_id).distinct().count()
        usuarios_com_relatorios = db.session.query(RelatorioMensal.user_id).distinct().count()
        
        usuarios_ativos_total = User.query.filter_by(is_active=True).count()
        
        # Funcionalidades mais usadas
        funcionalidades = [
            {
                'nome': 'Receitas',
                'usuarios_ativos': usuarios_com_receitas,
                'percentual_uso': round((usuarios_com_receitas / max(usuarios_ativos_total, 1)) * 100, 1),
                'total_registros': Receita.query.count()
            },
            {
                'nome': 'Despesas',
                'usuarios_ativos': usuarios_com_despesas,
                'percentual_uso': round((usuarios_com_despesas / max(usuarios_ativos_total, 1)) * 100, 1),
                'total_registros': Despesa.query.count()
            },
            {
                'nome': 'Notas Fiscais',
                'usuarios_ativos': usuarios_com_notas,
                'percentual_uso': round((usuarios_com_notas / max(usuarios_ativos_total, 1)) * 100, 1),
                'total_registros': NotaFiscal.query.count()
            },
            {
                'nome': 'Relatórios',
                'usuarios_ativos': usuarios_com_relatorios,
                'percentual_uso': round((usuarios_com_relatorios / max(usuarios_ativos_total, 1)) * 100, 1),
                'total_registros': RelatorioMensal.query.count()
            }
        ]
        
        # Atividade no mês atual
        atividade_mes = {
            'receitas_criadas': Receita.query.filter(Receita.created_at >= inicio_mes).count(),
            'despesas_criadas': Despesa.query.filter(Despesa.created_at >= inicio_mes).count(),
            'notas_enviadas': NotaFiscal.query.filter(NotaFiscal.created_at >= inicio_mes).count(),
            'relatorios_gerados': RelatorioMensal.query.filter(RelatorioMensal.created_at >= inicio_mes).count()
        }
        
        # Top categorias de receitas/despesas
        top_categorias_receitas = db.session.query(
            Receita.categoria,
            func.count(Receita.id).label('count'),
            func.sum(Receita.valor).label('total')
        ).group_by(Receita.categoria).order_by(func.count(Receita.id).desc()).limit(5).all()
        
        top_categorias_despesas = db.session.query(
            Despesa.categoria,
            func.count(Despesa.id).label('count'),
            func.sum(Despesa.valor).label('total')
        ).group_by(Despesa.categoria).order_by(func.count(Despesa.id).desc()).limit(5).all()
        
        return jsonify({
            'engajamento': {
                'usuarios_ativos_total': usuarios_ativos_total,
                'funcionalidades': funcionalidades
            },
            'atividade_mensal': atividade_mes,
            'top_categorias': {
                'receitas': [
                    {
                        'categoria': cat[0] or 'Não informado',
                        'quantidade': cat[1],
                        'valor_total': float(cat[2] or 0)
                    }
                    for cat in top_categorias_receitas
                ],
                'despesas': [
                    {
                        'categoria': cat[0] or 'Não informado',
                        'quantidade': cat[1],
                        'valor_total': float(cat[2] or 0)
                    }
                    for cat in top_categorias_despesas
                ]
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/exportar/usuarios', methods=['GET'])
@token_required
@admin_required
def exportar_usuarios():
    """Exportar lista de usuários em CSV"""
    try:
        import csv
        import io
        
        # Buscar todos os usuários
        usuarios = User.query.all()
        
        # Criar CSV em memória
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Cabeçalho
        writer.writerow([
            'ID', 'Nome', 'Email', 'CNPJ', 'Categoria MEI', 'Plano',
            'Status Pagamento', 'Ativo', 'Data Criação', 'Última Atualização'
        ])
        
        # Dados
        for usuario in usuarios:
            writer.writerow([
                usuario.id,
                usuario.nome,
                usuario.email,
                usuario.cnpj,
                usuario.categoria_mei or '',
                usuario.plano,
                usuario.status_pagamento,
                'Sim' if usuario.is_active else 'Não',
                usuario.created_at.strftime('%d/%m/%Y %H:%M'),
                usuario.updated_at.strftime('%d/%m/%Y %H:%M')
            ])
        
        # Preparar resposta
        output.seek(0)
        csv_data = output.getvalue()
        output.close()
        
        return jsonify({
            'message': 'Exportação concluída',
            'csv_data': csv_data,
            'total_usuarios': len(usuarios)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

