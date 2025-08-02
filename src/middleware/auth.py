from functools import wraps
from flask import request, jsonify, g
import jwt
from src.models.user import User
from src.config import Config
from datetime import datetime

def token_required(f):
    """Decorator para verificar token JWT"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token não fornecido'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            user_id = payload['user_id']
            
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'Usuário não encontrado'}), 404
            
            if not user.is_active:
                return jsonify({'error': 'Conta desativada'}), 401
            
            # Adicionar usuário ao contexto da requisição
            g.current_user = user
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    """Decorator para verificar se o usuário é admin"""
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        if not g.current_user.is_admin:
            return jsonify({'error': 'Acesso negado. Privilégios de administrador necessários'}), 403
        
        return f(*args, **kwargs)
    
    return decorated

def plano_ativo_required(f):
    """Decorator para verificar se o plano está ativo"""
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        user = g.current_user
        
        # Verificar se o plano está ativo
        if user.status_pagamento != 'ativo':
            return jsonify({
                'error': 'Plano inativo. Regularize seu pagamento para continuar usando o sistema',
                'status_pagamento': user.status_pagamento
            }), 402  # Payment Required
        
        # Verificar se não está vencido
        if user.data_vencimento and user.data_vencimento < datetime.now().date():
            user.status_pagamento = 'vencido'
            from src.models.user import db
            db.session.commit()
            
            return jsonify({
                'error': 'Plano vencido. Renove sua assinatura para continuar',
                'data_vencimento': user.data_vencimento.isoformat()
            }), 402  # Payment Required
        
        return f(*args, **kwargs)
    
    return decorated

def plano_avancado_required(f):
    """Decorator para verificar se o usuário tem plano avançado"""
    @wraps(f)
    @plano_ativo_required
    def decorated(*args, **kwargs):
        if g.current_user.plano != 'avancado':
            return jsonify({
                'error': 'Esta funcionalidade requer o plano avançado',
                'plano_atual': g.current_user.plano
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated

def verificar_limite_notas_fiscais(user):
    """Verifica se o usuário atingiu o limite de notas fiscais do plano"""
    from src.models.nota_fiscal import NotaFiscal
    
    if user.plano == 'avancado':
        return True  # Plano avançado tem limite ilimitado
    
    # Plano básico: limite de 50 notas fiscais por mês
    from datetime import datetime
    inicio_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    count = NotaFiscal.query.filter(
        NotaFiscal.user_id == user.id,
        NotaFiscal.created_at >= inicio_mes
    ).count()
    
    return count < 50

