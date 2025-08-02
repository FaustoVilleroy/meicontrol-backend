from flask import Blueprint, request, jsonify, g, send_file
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from src.models.user import db
from src.models.nota_fiscal import NotaFiscal
from src.models.financeiro import Receita, Despesa
from src.middleware.auth import token_required, plano_ativo_required, verificar_limite_notas_fiscais
from src.config import Config
import mimetypes

notas_fiscais_bp = Blueprint('notas_fiscais', __name__)

def allowed_file(filename):
    """Verifica se o arquivo é permitido"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Determina o tipo do arquivo"""
    extension = filename.rsplit('.', 1)[1].lower()
    if extension == 'pdf':
        return 'pdf'
    elif extension in ['jpg', 'jpeg', 'png']:
        return 'imagem'
    return 'desconhecido'

def extract_text_from_pdf(file_path):
    """Extrai texto de PDF (implementação básica)"""
    try:
        import PyPDF2
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        print(f"Erro ao extrair texto do PDF: {e}")
        return ""

def process_nota_fiscal_text(text):
    """Processa texto da nota fiscal para extrair informações"""
    import re
    
    info = {
        'numero': None,
        'valor_total': None,
        'cnpj_cpf': None,
        'nome_razao_social': None,
        'data_emissao': None
    }
    
    # Buscar número da nota fiscal
    numero_match = re.search(r'(?:nota fiscal|nf|n°|número)[:\s]*(\d+)', text, re.IGNORECASE)
    if numero_match:
        info['numero'] = numero_match.group(1)
    
    # Buscar valor total
    valor_match = re.search(r'(?:total|valor total|total geral)[:\s]*r?\$?\s*(\d+[.,]\d{2})', text, re.IGNORECASE)
    if valor_match:
        valor_str = valor_match.group(1).replace(',', '.')
        try:
            info['valor_total'] = float(valor_str)
        except ValueError:
            pass
    
    # Buscar CNPJ/CPF
    cnpj_match = re.search(r'(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})', text)
    if cnpj_match:
        info['cnpj_cpf'] = cnpj_match.group(1)
    else:
        cpf_match = re.search(r'(\d{3}\.?\d{3}\.?\d{3}-?\d{2})', text)
        if cpf_match:
            info['cnpj_cpf'] = cpf_match.group(1)
    
    # Buscar data de emissão
    data_match = re.search(r'(?:data|emissão|emitida)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})', text, re.IGNORECASE)
    if data_match:
        try:
            data_str = data_match.group(1)
            # Tentar diferentes formatos de data
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y']:
                try:
                    info['data_emissao'] = datetime.strptime(data_str, fmt).date()
                    break
                except ValueError:
                    continue
        except:
            pass
    
    return info

@notas_fiscais_bp.route('/notas-fiscais/upload', methods=['POST'])
@plano_ativo_required
def upload_nota_fiscal():
    """Upload de nota fiscal"""
    try:
        # Verificar limite do plano
        if not verificar_limite_notas_fiscais(g.current_user):
            return jsonify({
                'error': 'Limite de notas fiscais atingido para o seu plano. Faça upgrade para o plano avançado.'
            }), 403
        
        # Verificar se há arquivo
        if 'arquivo' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['arquivo']
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Tipo de arquivo não permitido. Use PDF, JPG, PNG ou JPEG'}), 400
        
        # Dados adicionais do formulário
        tipo = request.form.get('tipo', 'entrada')  # entrada ou saida
        categoria = request.form.get('categoria', '')
        
        # Gerar nome único para o arquivo
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Garantir que o diretório de upload existe
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        # Salvar arquivo
        file_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Determinar tipo do arquivo
        file_type = get_file_type(filename)
        
        # Processar arquivo para extrair informações
        extracted_info = {}
        if file_type == 'pdf':
            text = extract_text_from_pdf(file_path)
            if text:
                extracted_info = process_nota_fiscal_text(text)
        
        # Criar registro da nota fiscal
        nota_fiscal = NotaFiscal(
            user_id=g.current_user.id,
            numero=extracted_info.get('numero'),
            data_emissao=extracted_info.get('data_emissao') or datetime.now().date(),
            valor_total=extracted_info.get('valor_total') or 0,
            tipo=tipo,
            categoria=categoria,
            arquivo_path=file_path,
            arquivo_nome=filename,
            arquivo_tipo=file_type,
            cnpj_cpf=extracted_info.get('cnpj_cpf'),
            nome_razao_social=extracted_info.get('nome_razao_social'),
            processada=bool(extracted_info.get('numero'))
        )
        
        db.session.add(nota_fiscal)
        db.session.commit()
        
        return jsonify({
            'message': 'Nota fiscal enviada com sucesso',
            'nota_fiscal': nota_fiscal.to_dict(),
            'informacoes_extraidas': extracted_info
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@notas_fiscais_bp.route('/notas-fiscais', methods=['GET'])
@plano_ativo_required
def listar_notas_fiscais():
    """Listar notas fiscais do usuário"""
    try:
        # Parâmetros de filtro
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        tipo = request.args.get('tipo')
        categoria = request.args.get('categoria')
        processada = request.args.get('processada', type=bool)
        
        # Query base
        query = NotaFiscal.query.filter_by(user_id=g.current_user.id)
        
        # Aplicar filtros
        if tipo:
            query = query.filter(NotaFiscal.tipo == tipo)
        
        if categoria:
            query = query.filter(NotaFiscal.categoria == categoria)
        
        if processada is not None:
            query = query.filter(NotaFiscal.processada == processada)
        
        # Ordenar por data mais recente
        query = query.order_by(NotaFiscal.created_at.desc())
        
        # Paginação
        notas_paginadas = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'notas_fiscais': [nota.to_dict() for nota in notas_paginadas.items],
            'total': notas_paginadas.total,
            'pages': notas_paginadas.pages,
            'current_page': page,
            'per_page': per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notas_fiscais_bp.route('/notas-fiscais/<int:nota_id>', methods=['GET'])
@plano_ativo_required
def obter_nota_fiscal(nota_id):
    """Obter detalhes de uma nota fiscal"""
    try:
        nota = NotaFiscal.query.filter_by(
            id=nota_id, user_id=g.current_user.id
        ).first()
        
        if not nota:
            return jsonify({'error': 'Nota fiscal não encontrada'}), 404
        
        return jsonify({'nota_fiscal': nota.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notas_fiscais_bp.route('/notas-fiscais/<int:nota_id>/download', methods=['GET'])
@plano_ativo_required
def download_nota_fiscal(nota_id):
    """Download do arquivo da nota fiscal"""
    try:
        nota = NotaFiscal.query.filter_by(
            id=nota_id, user_id=g.current_user.id
        ).first()
        
        if not nota:
            return jsonify({'error': 'Nota fiscal não encontrada'}), 404
        
        if not os.path.exists(nota.arquivo_path):
            return jsonify({'error': 'Arquivo não encontrado'}), 404
        
        # Determinar o tipo MIME
        mimetype = mimetypes.guess_type(nota.arquivo_path)[0]
        
        return send_file(
            nota.arquivo_path,
            as_attachment=True,
            download_name=nota.arquivo_nome,
            mimetype=mimetype
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notas_fiscais_bp.route('/notas-fiscais/<int:nota_id>', methods=['PUT'])
@plano_ativo_required
def atualizar_nota_fiscal(nota_id):
    """Atualizar informações da nota fiscal"""
    try:
        nota = NotaFiscal.query.filter_by(
            id=nota_id, user_id=g.current_user.id
        ).first()
        
        if not nota:
            return jsonify({'error': 'Nota fiscal não encontrada'}), 404
        
        data = request.get_json()
        
        # Atualizar campos permitidos
        allowed_fields = [
            'numero', 'serie', 'valor_total', 'tipo', 'categoria',
            'cnpj_cpf', 'nome_razao_social'
        ]
        
        for field in allowed_fields:
            if field in data:
                setattr(nota, field, data[field])
        
        if 'data_emissao' in data:
            try:
                nota.data_emissao = datetime.strptime(data['data_emissao'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Data inválida. Use o formato YYYY-MM-DD'}), 400
        
        nota.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Nota fiscal atualizada com sucesso',
            'nota_fiscal': nota.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@notas_fiscais_bp.route('/notas-fiscais/<int:nota_id>', methods=['DELETE'])
@plano_ativo_required
def deletar_nota_fiscal(nota_id):
    """Deletar nota fiscal"""
    try:
        nota = NotaFiscal.query.filter_by(
            id=nota_id, user_id=g.current_user.id
        ).first()
        
        if not nota:
            return jsonify({'error': 'Nota fiscal não encontrada'}), 404
        
        # Remover arquivo do disco
        if os.path.exists(nota.arquivo_path):
            os.remove(nota.arquivo_path)
        
        db.session.delete(nota)
        db.session.commit()
        
        return jsonify({'message': 'Nota fiscal deletada com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@notas_fiscais_bp.route('/notas-fiscais/<int:nota_id>/associar', methods=['POST'])
@plano_ativo_required
def associar_nota_fiscal(nota_id):
    """Associar nota fiscal a receita ou despesa"""
    try:
        nota = NotaFiscal.query.filter_by(
            id=nota_id, user_id=g.current_user.id
        ).first()
        
        if not nota:
            return jsonify({'error': 'Nota fiscal não encontrada'}), 404
        
        data = request.get_json()
        tipo_associacao = data.get('tipo')  # 'receita' ou 'despesa'
        item_id = data.get('item_id')
        
        if tipo_associacao == 'receita':
            receita = Receita.query.filter_by(
                id=item_id, user_id=g.current_user.id
            ).first()
            
            if not receita:
                return jsonify({'error': 'Receita não encontrada'}), 404
            
            receita.nota_fiscal_id = nota.id
            nota.associada_receita = True
            
        elif tipo_associacao == 'despesa':
            despesa = Despesa.query.filter_by(
                id=item_id, user_id=g.current_user.id
            ).first()
            
            if not despesa:
                return jsonify({'error': 'Despesa não encontrada'}), 404
            
            despesa.nota_fiscal_id = nota.id
            nota.associada_despesa = True
            
        else:
            return jsonify({'error': 'Tipo de associação inválido'}), 400
        
        nota.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': f'Nota fiscal associada à {tipo_associacao} com sucesso',
            'nota_fiscal': nota.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@notas_fiscais_bp.route('/notas-fiscais/sugestoes-associacao', methods=['GET'])
@plano_ativo_required
def sugestoes_associacao():
    """Sugerir associações automáticas baseadas em valores e datas"""
    try:
        # Buscar notas fiscais não associadas
        notas_nao_associadas = NotaFiscal.query.filter_by(
            user_id=g.current_user.id,
            associada_receita=False,
            associada_despesa=False
        ).filter(NotaFiscal.valor_total > 0).all()
        
        sugestoes = []
        
        for nota in notas_nao_associadas:
            # Buscar receitas/despesas com valores similares e datas próximas
            if nota.tipo == 'entrada':
                # Buscar receitas
                receitas = Receita.query.filter_by(
                    user_id=g.current_user.id,
                    nota_fiscal_id=None
                ).filter(
                    Receita.valor.between(
                        nota.valor_total * 0.9,
                        nota.valor_total * 1.1
                    )
                ).all()
                
                for receita in receitas:
                    # Calcular diferença de dias
                    diff_dias = abs((receita.data_receita - nota.data_emissao).days)
                    if diff_dias <= 7:  # Até 7 dias de diferença
                        sugestoes.append({
                            'nota_fiscal': nota.to_dict(),
                            'item_sugerido': receita.to_dict(),
                            'tipo': 'receita',
                            'confianca': max(0, 100 - diff_dias * 10),
                            'motivo': f'Valor similar (R$ {receita.valor}) e data próxima ({diff_dias} dias)'
                        })
            
            else:
                # Buscar despesas
                despesas = Despesa.query.filter_by(
                    user_id=g.current_user.id,
                    nota_fiscal_id=None
                ).filter(
                    Despesa.valor.between(
                        nota.valor_total * 0.9,
                        nota.valor_total * 1.1
                    )
                ).all()
                
                for despesa in despesas:
                    diff_dias = abs((despesa.data_despesa - nota.data_emissao).days)
                    if diff_dias <= 7:
                        sugestoes.append({
                            'nota_fiscal': nota.to_dict(),
                            'item_sugerido': despesa.to_dict(),
                            'tipo': 'despesa',
                            'confianca': max(0, 100 - diff_dias * 10),
                            'motivo': f'Valor similar (R$ {despesa.valor}) e data próxima ({diff_dias} dias)'
                        })
        
        # Ordenar por confiança
        sugestoes.sort(key=lambda x: x['confianca'], reverse=True)
        
        return jsonify({'sugestoes': sugestoes[:10]}), 200  # Limitar a 10 sugestões
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

