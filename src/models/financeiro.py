from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class Receita(db.Model):
    __tablename__ = 'receitas'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Dados da receita
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data_receita = db.Column(db.Date, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)  # comércio, serviços, indústria, outros
    
    # Comprovantes
    comprovante_path = db.Column(db.String(500))
    nota_fiscal_id = db.Column(db.Integer, db.ForeignKey('notas_fiscais.id'))
    
    # Controle
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'descricao': self.descricao,
            'valor': float(self.valor),
            'data_receita': self.data_receita.isoformat(),
            'categoria': self.categoria,
            'comprovante_path': self.comprovante_path,
            'nota_fiscal_id': self.nota_fiscal_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Despesa(db.Model):
    __tablename__ = 'despesas'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Dados da despesa
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data_despesa = db.Column(db.Date, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)  # material, equipamento, servicos, outros
    
    # Comprovantes
    comprovante_path = db.Column(db.String(500))
    nota_fiscal_id = db.Column(db.Integer, db.ForeignKey('notas_fiscais.id'))
    
    # Controle
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'descricao': self.descricao,
            'valor': float(self.valor),
            'data_despesa': self.data_despesa.isoformat(),
            'categoria': self.categoria,
            'comprovante_path': self.comprovante_path,
            'nota_fiscal_id': self.nota_fiscal_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

