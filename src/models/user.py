from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    telefone = db.Column(db.String(20))
    
    # Informações do MEI
    razao_social = db.Column(db.String(200))
    nome_fantasia = db.Column(db.String(200))
    categoria_mei = db.Column(db.String(50))  # comércio, serviços, indústria
    data_abertura = db.Column(db.Date)
    
    # Plano de assinatura
    plano = db.Column(db.String(20), default='basico')  # basico, avancado
    status_pagamento = db.Column(db.String(20), default='ativo')  # ativo, inadimplente, cancelado
    data_vencimento = db.Column(db.Date)
    
    # Controle de acesso
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Configurações de notificação
    configuracoes_notificacao = db.Column(db.Text)  # JSON com configurações
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    receitas = db.relationship('Receita', backref='usuario', lazy=True)
    despesas = db.relationship('Despesa', backref='usuario', lazy=True)
    notas_fiscais = db.relationship('NotaFiscal', backref='usuario', lazy=True)
    relatorios = db.relationship('RelatorioMensal', backref='usuario', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'nome': self.nome,
            'cnpj': self.cnpj,
            'telefone': self.telefone,
            'razao_social': self.razao_social,
            'nome_fantasia': self.nome_fantasia,
            'categoria_mei': self.categoria_mei,
            'data_abertura': self.data_abertura.isoformat() if self.data_abertura else None,
            'plano': self.plano,
            'status_pagamento': self.status_pagamento,
            'data_vencimento': self.data_vencimento.isoformat() if self.data_vencimento else None,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

