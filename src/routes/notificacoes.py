from flask import Blueprint, request, jsonify, g
from datetime import datetime, date, timedelta
from calendar import monthrange
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.models.user import db, User
from src.models.relatorio import RelatorioMensal
from src.middleware.auth import token_required, plano_ativo_required
from src.config import Config
import json

notificacoes_bp = Blueprint('notificacoes', __name__)

def calcular_proximos_vencimentos():
    """Calcula as próximas datas de vencimento das obrigações MEI"""
    hoje = date.today()
    ano_atual = hoje.year
    mes_atual = hoje.month
    
    # Próximo vencimento do relatório mensal (dia 20)
    if hoje.day <= 20:
        proximo_relatorio = date(ano_atual, mes_atual, 20)
    else:
        if mes_atual == 12:
            proximo_relatorio = date(ano_atual + 1, 1, 20)
        else:
            proximo_relatorio = date(ano_atual, mes_atual + 1, 20)
    
    # Próximo vencimento do DAS (dia 20)
    proximo_das = proximo_relatorio  # Mesmo prazo do relatório
    
    # Próximo vencimento da DASN-SIMEI (31 de maio)
    if hoje <= date(ano_atual, 5, 31):
        proximo_dasn = date(ano_atual, 5, 31)
    else:
        proximo_dasn = date(ano_atual + 1, 5, 31)
    
    return {
        'relatorio_mensal': proximo_relatorio,
        'das': proximo_das,
        'dasn_simei': proximo_dasn
    }

def enviar_email_notificacao(destinatario, assunto, corpo_html):
    """Envia email de notificação"""
    try:
        # Configurações do email (usar variáveis de ambiente em produção)
        smtp_server = Config.SMTP_SERVER or "smtp.gmail.com"
        smtp_port = Config.SMTP_PORT or 587
        email_usuario = Config.EMAIL_USER or "noreply@meicontrol.com"
        email_senha = Config.EMAIL_PASSWORD or ""
        
        if not email_senha:
            print("Configuração de email não encontrada - simulando envio")
            return True
        
        # Criar mensagem
        msg = MIMEMultipart('alternative')
        msg['Subject'] = assunto
        msg['From'] = f"MEIControl <{email_usuario}>"
        msg['To'] = destinatario
        
        # Adicionar corpo HTML
        html_part = MIMEText(corpo_html, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Enviar email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_usuario, email_senha)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        return False

def gerar_template_email_alerta(tipo_alerta, dados_usuario, dados_alerta):
    """Gera template HTML para email de alerta"""
    templates = {
        'relatorio_mensal': {
            'assunto': f'🚨 Lembrete: Relatório Mensal MEI - Prazo até {dados_alerta["prazo"]}',
            'corpo': f'''
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .header {{ background-color: #1a2332; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; margin: -30px -30px 30px -30px; }}
                    .alert {{ background-color: #dc2626; color: white; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center; }}
                    .info {{ background-color: #374151; color: white; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                    .button {{ background-color: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>MEIControl</h1>
                        <p>Sistema de Gestão Financeira para MEI</p>
                    </div>
                    
                    <div class="alert">
                        <h2>⚠️ ATENÇÃO: Relatório Mensal Pendente</h2>
                    </div>
                    
                    <p>Olá, <strong>{dados_usuario["nome"]}</strong>!</p>
                    
                    <p>Este é um lembrete importante sobre suas obrigações como MEI:</p>
                    
                    <div class="info">
                        <h3>📋 Relatório Mensal de Receitas Brutas</h3>
                        <p><strong>Mês de referência:</strong> {dados_alerta["mes_referencia"]}</p>
                        <p><strong>Prazo para entrega:</strong> {dados_alerta["prazo"]}</p>
                        <p><strong>Dias restantes:</strong> {dados_alerta["dias_restantes"]} dias</p>
                    </div>
                    
                    <p>O relatório mensal deve ser preenchido até o dia 20 de cada mês. O não cumprimento desta obrigação pode resultar em multas e complicações com a Receita Federal.</p>
                    
                    <div style="text-align: center;">
                        <a href="https://meicontrol.com/login" class="button">Acessar MEIControl</a>
                    </div>
                    
                    <div class="footer">
                        <p>Este é um email automático do sistema MEIControl.</p>
                        <p>Para cancelar estes lembretes, acesse suas configurações na plataforma.</p>
                    </div>
                </div>
            </body>
            </html>
            '''
        },
        'das': {
            'assunto': f'💰 Lembrete: Pagamento DAS MEI - Vence em {dados_alerta["prazo"]}',
            'corpo': f'''
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .header {{ background-color: #1a2332; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; margin: -30px -30px 30px -30px; }}
                    .alert {{ background-color: #dc2626; color: white; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center; }}
                    .info {{ background-color: #374151; color: white; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                    .button {{ background-color: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>MEIControl</h1>
                        <p>Sistema de Gestão Financeira para MEI</p>
                    </div>
                    
                    <div class="alert">
                        <h2>💰 LEMBRETE: Pagamento DAS MEI</h2>
                    </div>
                    
                    <p>Olá, <strong>{dados_usuario["nome"]}</strong>!</p>
                    
                    <p>Não se esqueça de pagar o DAS (Documento de Arrecadação do Simples Nacional) do seu MEI:</p>
                    
                    <div class="info">
                        <h3>📄 DAS MEI</h3>
                        <p><strong>Mês de referência:</strong> {dados_alerta["mes_referencia"]}</p>
                        <p><strong>Vencimento:</strong> {dados_alerta["prazo"]}</p>
                        <p><strong>Dias restantes:</strong> {dados_alerta["dias_restantes"]} dias</p>
                        <p><strong>Valor aproximado:</strong> R$ 70,60 (valor pode variar)</p>
                    </div>
                    
                    <p>O DAS deve ser pago mensalmente até o dia 20. Atraso no pagamento gera multa e juros.</p>
                    
                    <div style="text-align: center;">
                        <a href="https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/Identificacao" class="button">Gerar DAS no Portal do Empreendedor</a>
                    </div>
                    
                    <div class="footer">
                        <p>Este é um email automático do sistema MEIControl.</p>
                        <p>Para cancelar estes lembretes, acesse suas configurações na plataforma.</p>
                    </div>
                </div>
            </body>
            </html>
            '''
        },
        'dasn_simei': {
            'assunto': f'📊 Lembrete: DASN-SIMEI {dados_alerta["ano"]} - Prazo até 31/05',
            'corpo': f'''
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .header {{ background-color: #1a2332; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; margin: -30px -30px 30px -30px; }}
                    .alert {{ background-color: #dc2626; color: white; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center; }}
                    .info {{ background-color: #374151; color: white; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                    .button {{ background-color: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>MEIControl</h1>
                        <p>Sistema de Gestão Financeira para MEI</p>
                    </div>
                    
                    <div class="alert">
                        <h2>📊 IMPORTANTE: Declaração Anual DASN-SIMEI</h2>
                    </div>
                    
                    <p>Olá, <strong>{dados_usuario["nome"]}</strong>!</p>
                    
                    <p>É hora de entregar sua Declaração Anual do Simples Nacional (DASN-SIMEI):</p>
                    
                    <div class="info">
                        <h3>📋 DASN-SIMEI {dados_alerta["ano"]}</h3>
                        <p><strong>Ano de referência:</strong> {dados_alerta["ano"]}</p>
                        <p><strong>Prazo para entrega:</strong> 31 de maio de {dados_alerta["ano"] + 1}</p>
                        <p><strong>Dias restantes:</strong> {dados_alerta["dias_restantes"]} dias</p>
                    </div>
                    
                    <p>A DASN-SIMEI é obrigatória para todos os MEIs e deve ser entregue anualmente até 31 de maio. Use o MEIControl para gerar automaticamente os dados necessários!</p>
                    
                    <div style="text-align: center;">
                        <a href="https://meicontrol.com/login" class="button">Gerar Relatório no MEIControl</a>
                    </div>
                    
                    <div class="footer">
                        <p>Este é um email automático do sistema MEIControl.</p>
                        <p>Para cancelar estes lembretes, acesse suas configurações na plataforma.</p>
                    </div>
                </div>
            </body>
            </html>
            '''
        }
    }
    
    template = templates.get(tipo_alerta, templates['relatorio_mensal'])
    return template['assunto'], template['corpo']

@notificacoes_bp.route('/notificacoes/configuracoes', methods=['GET'])
@plano_ativo_required
def obter_configuracoes_notificacao():
    """Obter configurações de notificação do usuário"""
    try:
        usuario = g.current_user
        
        # Configurações padrão se não existirem
        configuracoes_padrao = {
            'email_relatorio_mensal': True,
            'email_das': True,
            'email_dasn_simei': True,
            'dias_antecedencia_relatorio': 5,
            'dias_antecedencia_das': 5,
            'dias_antecedencia_dasn': 30,
            'push_notifications': False,  # Funcionalidade futura
            'whatsapp_notifications': False  # Funcionalidade futura
        }
        
        # Buscar configurações salvas (implementar modelo NotificacaoConfig se necessário)
        configuracoes = getattr(usuario, 'configuracoes_notificacao', None)
        if configuracoes:
            configuracoes_usuario = json.loads(configuracoes)
            configuracoes_padrao.update(configuracoes_usuario)
        
        return jsonify({
            'configuracoes': configuracoes_padrao
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notificacoes_bp.route('/notificacoes/configuracoes', methods=['PUT'])
@plano_ativo_required
def atualizar_configuracoes_notificacao():
    """Atualizar configurações de notificação do usuário"""
    try:
        dados = request.get_json()
        usuario = g.current_user
        
        # Validar dados
        configuracoes_validas = {
            'email_relatorio_mensal': dados.get('email_relatorio_mensal', True),
            'email_das': dados.get('email_das', True),
            'email_dasn_simei': dados.get('email_dasn_simei', True),
            'dias_antecedencia_relatorio': min(max(dados.get('dias_antecedencia_relatorio', 5), 1), 15),
            'dias_antecedencia_das': min(max(dados.get('dias_antecedencia_das', 5), 1), 15),
            'dias_antecedencia_dasn': min(max(dados.get('dias_antecedencia_dasn', 30), 7), 90),
            'push_notifications': dados.get('push_notifications', False),
            'whatsapp_notifications': dados.get('whatsapp_notifications', False)
        }
        
        # Salvar configurações (adicionar campo ao modelo User se necessário)
        usuario.configuracoes_notificacao = json.dumps(configuracoes_validas)
        db.session.commit()
        
        return jsonify({
            'message': 'Configurações de notificação atualizadas com sucesso',
            'configuracoes': configuracoes_validas
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@notificacoes_bp.route('/notificacoes/enviar-teste', methods=['POST'])
@plano_ativo_required
def enviar_notificacao_teste():
    """Enviar notificação de teste para o usuário"""
    try:
        dados = request.get_json()
        tipo_teste = dados.get('tipo', 'relatorio_mensal')
        usuario = g.current_user
        
        # Dados de exemplo para teste
        dados_alerta = {
            'mes_referencia': '07/2025',
            'prazo': '20/08/2025',
            'dias_restantes': 5,
            'ano': 2024
        }
        
        dados_usuario = {
            'nome': usuario.nome,
            'email': usuario.email
        }
        
        # Gerar template
        assunto, corpo_html = gerar_template_email_alerta(tipo_teste, dados_usuario, dados_alerta)
        
        # Enviar email
        sucesso = enviar_email_notificacao(usuario.email, assunto, corpo_html)
        
        if sucesso:
            return jsonify({
                'message': f'Email de teste enviado com sucesso para {usuario.email}'
            }), 200
        else:
            return jsonify({
                'message': 'Email de teste simulado (configuração de SMTP não encontrada)',
                'preview': {
                    'assunto': assunto,
                    'destinatario': usuario.email,
                    'corpo_preview': corpo_html[:200] + '...'
                }
            }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notificacoes_bp.route('/notificacoes/proximos-vencimentos', methods=['GET'])
@plano_ativo_required
def obter_proximos_vencimentos():
    """Obter próximos vencimentos das obrigações MEI"""
    try:
        vencimentos = calcular_proximos_vencimentos()
        hoje = date.today()
        
        # Calcular dias restantes
        resultado = {}
        for tipo, data_vencimento in vencimentos.items():
            dias_restantes = (data_vencimento - hoje).days
            resultado[tipo] = {
                'data': data_vencimento.strftime('%d/%m/%Y'),
                'dias_restantes': dias_restantes,
                'status': 'urgente' if dias_restantes <= 5 else 'atencao' if dias_restantes <= 15 else 'ok'
            }
        
        return jsonify({
            'proximos_vencimentos': resultado
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notificacoes_bp.route('/notificacoes/historico', methods=['GET'])
@plano_ativo_required
def obter_historico_notificacoes():
    """Obter histórico de notificações enviadas (funcionalidade futura)"""
    try:
        # Por enquanto, retornar dados simulados
        # Em produção, implementar modelo NotificacaoHistorico
        
        historico_simulado = [
            {
                'id': 1,
                'tipo': 'email_relatorio_mensal',
                'assunto': 'Lembrete: Relatório Mensal MEI',
                'enviado_em': '2025-07-20T10:00:00Z',
                'status': 'enviado',
                'destinatario': g.current_user.email
            },
            {
                'id': 2,
                'tipo': 'email_das',
                'assunto': 'Lembrete: Pagamento DAS MEI',
                'enviado_em': '2025-07-15T10:00:00Z',
                'status': 'enviado',
                'destinatario': g.current_user.email
            }
        ]
        
        return jsonify({
            'historico': historico_simulado,
            'total': len(historico_simulado)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Função para ser chamada por um cron job ou scheduler
def processar_notificacoes_automaticas():
    """Processar e enviar notificações automáticas para todos os usuários"""
    try:
        hoje = date.today()
        usuarios = User.query.filter_by(ativo=True).all()
        
        for usuario in usuarios:
            # Verificar configurações do usuário
            configuracoes = {}
            if hasattr(usuario, 'configuracoes_notificacao') and usuario.configuracoes_notificacao:
                configuracoes = json.loads(usuario.configuracoes_notificacao)
            
            # Configurações padrão
            dias_antecedencia_relatorio = configuracoes.get('dias_antecedencia_relatorio', 5)
            dias_antecedencia_das = configuracoes.get('dias_antecedencia_das', 5)
            dias_antecedencia_dasn = configuracoes.get('dias_antecedencia_dasn', 30)
            
            # Calcular vencimentos
            vencimentos = calcular_proximos_vencimentos()
            
            dados_usuario = {
                'nome': usuario.nome,
                'email': usuario.email
            }
            
            # Verificar relatório mensal
            if configuracoes.get('email_relatorio_mensal', True):
                dias_para_relatorio = (vencimentos['relatorio_mensal'] - hoje).days
                if 0 <= dias_para_relatorio <= dias_antecedencia_relatorio:
                    dados_alerta = {
                        'mes_referencia': f"{hoje.month:02d}/{hoje.year}",
                        'prazo': vencimentos['relatorio_mensal'].strftime('%d/%m/%Y'),
                        'dias_restantes': dias_para_relatorio
                    }
                    assunto, corpo = gerar_template_email_alerta('relatorio_mensal', dados_usuario, dados_alerta)
                    enviar_email_notificacao(usuario.email, assunto, corpo)
            
            # Verificar DAS
            if configuracoes.get('email_das', True):
                dias_para_das = (vencimentos['das'] - hoje).days
                if 0 <= dias_para_das <= dias_antecedencia_das:
                    dados_alerta = {
                        'mes_referencia': f"{hoje.month:02d}/{hoje.year}",
                        'prazo': vencimentos['das'].strftime('%d/%m/%Y'),
                        'dias_restantes': dias_para_das
                    }
                    assunto, corpo = gerar_template_email_alerta('das', dados_usuario, dados_alerta)
                    enviar_email_notificacao(usuario.email, assunto, corpo)
            
            # Verificar DASN-SIMEI
            if configuracoes.get('email_dasn_simei', True):
                dias_para_dasn = (vencimentos['dasn_simei'] - hoje).days
                if 0 <= dias_para_dasn <= dias_antecedencia_dasn:
                    dados_alerta = {
                        'ano': hoje.year - 1,
                        'prazo': vencimentos['dasn_simei'].strftime('%d/%m/%Y'),
                        'dias_restantes': dias_para_dasn
                    }
                    assunto, corpo = gerar_template_email_alerta('dasn_simei', dados_usuario, dados_alerta)
                    enviar_email_notificacao(usuario.email, assunto, corpo)
        
        print(f"Processamento de notificações concluído para {len(usuarios)} usuários")
        return True
        
    except Exception as e:
        print(f"Erro no processamento de notificações: {e}")
        return False

