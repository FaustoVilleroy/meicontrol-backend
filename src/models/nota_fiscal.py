from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class NotaFiscal(db.Model):
    __tablename__ = 'notas_fiscais'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Dados da nota fiscal
    numero = db.Column(db.String(50))
    serie = db.Column(db.String(10))
    data_emissao = db.Column(db.Date, nullable=False)
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # entrada, saida
    categoria = db.Column(db.String(50))  # comércio, serviços, indústria
    
    # Arquivo da nota fiscal
    arquivo_path = db.Column(db.String(500), nullable=False)
    arquivo_nome = db.Column(db.String(200), nullable=False)
    arquivo_tipo = db.Column(db.String(20), nullable=False)  # pdf, jpg, png
    
    # Dados do fornecedor/cliente
    cnpj_cpf = db.Column(db.String(18))
    nome_razao_social = db.Column(db.String(200))
    
    # Status de processamento
    processada = db.Column(db.Boolean, default=False)
    associada_receita = db.Column(db.Boolean, default=False)
    associada_despesa = db.Column(db.Boolean, default=False)
    
    # Controle
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    receitas = db.relationship('Receita', backref='nota_fiscal', lazy=True)
    despesas = db.relationship('Despesa', backref='nota_fiscal', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'numero': self.numero,
            'serie': self.serie,
            'data_emissao': self.data_emissao.isoformat(),
            'valor_total': float(self.valor_total),
            'tipo': self.tipo,
            'categoria': self.categoria,
            'arquivo_path': self.arquivo_path,
            'arquivo_nome': self.arquivo_nome,
            'arquivo_tipo': self.arquivo_tipo,
            'cnpj_cpf': self.cnpj_cpf,
            'nome_razao_social': self.nome_razao_social,
            'processada': self.processada,
            'associada_receita': self.associada_receita,
            'associada_despesa': self.associada_despesa,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

