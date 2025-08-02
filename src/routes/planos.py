from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import jwt
import stripe
from src.models.user import db, User
from src.config import Config

planos_bp = Blueprint('planos', __name__)

# Configurar Stripe
stripe.api_key = Config.STRIPE_SECRET_KEY

# Definição dos planos
PLANOS = {
    'basico': {
        'nome': 'Básico',
        'preco': 29.90,
        'descricao': 'Gestão financeira básica, relatórios mensais e anuais',
        'funcionalidades': [
            'Registro de receitas e despesas',
            'Dashboard básico',
            'Relatório mensal MEI',
            'Declaração anual DASN-SIMEI',
            'Suporte por email'
        ],
        'limite_notas_fiscais': 50
    },
    'avancado': {
        'nome': 'Avançado',
        'preco': 59.90,
        'descricao': 'Todos os recursos + integrações avançadas e suporte prioritário',
        'funcionalidades': [
            'Todos os recursos do plano básico',
            'Upload ilimitado de notas fiscais',
            'Integração com APIs de NF-e/NFS-e',
            'Relatórios avançados com gráficos',
            'Alertas automáticos por WhatsApp',
            'Suporte prioritário',
            'Backup automático na nuvem'
        ],
        'limite_notas_fiscais': -1  # Ilimitado
    }
}

def verificar_token():
    """Função auxiliar para verificar token JWT"""
    token = request.headers.get('Authorization')
    if not token:
        return None, jsonify({'error': 'Token não fornecido'}), 401
    
    if token.startswith('Bearer '):
        token = token[7:]
    
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        user = User.query.get(user_id)
        if not user:
            return None, jsonify({'error': 'Usuário não encontrado'}), 404
        return user, None, None
    except jwt.ExpiredSignatureError:
        return None, jsonify({'error': 'Token expirado'}), 401
    except jwt.InvalidTokenError:
        return None, jsonify({'error': 'Token inválido'}), 401

@planos_bp.route('/planos', methods=['GET'])
def listar_planos():
    """Lista todos os planos disponíveis"""
    return jsonify({'planos': PLANOS}), 200

@planos_bp.route('/plano-atual', methods=['GET'])
def plano_atual():
    """Retorna o plano atual do usuário"""
    user, error_response, status_code = verificar_token()
    if error_response:
        return error_response, status_code
    
    plano_info = PLANOS.get(user.plano, {})
    
    return jsonify({
        'plano_atual': user.plano,
        'status_pagamento': user.status_pagamento,
        'data_vencimento': user.data_vencimento.isoformat() if user.data_vencimento else None,
        'plano_info': plano_info
    }), 200

@planos_bp.route('/alterar-plano', methods=['POST'])
def alterar_plano():
    """Altera o plano do usuário"""
    user, error_response, status_code = verificar_token()
    if error_response:
        return error_response, status_code
    
    data = request.get_json()
    novo_plano = data.get('plano')
    
    if novo_plano not in PLANOS:
        return jsonify({'error': 'Plano inválido'}), 400
    
    if user.plano == novo_plano:
        return jsonify({'error': 'Usuário já possui este plano'}), 400
    
    try:
        # Atualizar plano do usuário
        user.plano = novo_plano
        user.updated_at = datetime.utcnow()
        
        # Se for upgrade, manter data de vencimento atual
        # Se for downgrade, aplicar imediatamente
        if novo_plano == 'basico' and user.plano == 'avancado':
            user.data_vencimento = datetime.now().date()
        
        db.session.commit()
        
        return jsonify({
            'message': f'Plano alterado para {PLANOS[novo_plano]["nome"]} com sucesso',
            'plano_atual': novo_plano,
            'plano_info': PLANOS[novo_plano]
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@planos_bp.route('/criar-checkout-session', methods=['POST'])
def criar_checkout_session():
    """Cria uma sessão de checkout do Stripe"""
    user, error_response, status_code = verificar_token()
    if error_response:
        return error_response, status_code
    
    data = request.get_json()
    plano = data.get('plano')
    
    if plano not in PLANOS:
        return jsonify({'error': 'Plano inválido'}), 400
    
    try:
        plano_info = PLANOS[plano]
        
        # Criar sessão de checkout do Stripe
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': f'MEIControl - Plano {plano_info["nome"]}',
                        'description': plano_info['descricao'],
                    },
                    'unit_amount': int(plano_info['preco'] * 100),  # Stripe usa centavos
                    'recurring': {
                        'interval': 'month',
                    },
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.host_url + 'pagamento-sucesso?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.host_url + 'pagamento-cancelado',
            client_reference_id=str(user.id),
            metadata={
                'user_id': user.id,
                'plano': plano
            }
        )
        
        return jsonify({
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@planos_bp.route('/webhook-stripe', methods=['POST'])
def webhook_stripe():
    """Webhook para receber notificações do Stripe"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # Verificar assinatura do webhook (em produção, configurar endpoint_secret)
        # event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        
        # Para desenvolvimento, processar diretamente
        import json
        event = json.loads(payload)
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session['metadata']['user_id']
            plano = session['metadata']['plano']
            
            # Atualizar usuário
            user = User.query.get(user_id)
            if user:
                user.plano = plano
                user.status_pagamento = 'ativo'
                user.data_vencimento = datetime.now().date() + timedelta(days=30)
                user.updated_at = datetime.utcnow()
                db.session.commit()
        
        elif event['type'] == 'invoice.payment_failed':
            # Marcar usuário como inadimplente
            customer_id = event['data']['object']['customer']
            # Buscar usuário pelo customer_id do Stripe
            # user = User.query.filter_by(stripe_customer_id=customer_id).first()
            # if user:
            #     user.status_pagamento = 'inadimplente'
            #     db.session.commit()
            pass
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@planos_bp.route('/verificar-acesso', methods=['GET'])
def verificar_acesso():
    """Verifica se o usuário tem acesso às funcionalidades"""
    user, error_response, status_code = verificar_token()
    if error_response:
        return error_response, status_code
    
    # Verificar se o plano está ativo
    acesso_liberado = user.status_pagamento == 'ativo'
    
    # Verificar se não está vencido
    if user.data_vencimento and user.data_vencimento < datetime.now().date():
        acesso_liberado = False
        user.status_pagamento = 'vencido'
        db.session.commit()
    
    plano_info = PLANOS.get(user.plano, {})
    
    return jsonify({
        'acesso_liberado': acesso_liberado,
        'plano': user.plano,
        'status_pagamento': user.status_pagamento,
        'data_vencimento': user.data_vencimento.isoformat() if user.data_vencimento else None,
        'funcionalidades': plano_info.get('funcionalidades', []),
        'limite_notas_fiscais': plano_info.get('limite_notas_fiscais', 0)
    }), 200

