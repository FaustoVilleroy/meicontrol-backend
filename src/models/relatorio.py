from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class RelatorioMensal(db.Model):
    __tablename__ = 'relatorios_mensais'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Período do relatório
    mes = db.Column(db.Integer, nullable=False)  # 1-12
    ano = db.Column(db.Integer, nullable=False)
    
    # Totais por categoria
    total_comercio = db.Column(db.Numeric(10, 2), default=0)
    total_industria = db.Column(db.Numeric(10, 2), default=0)
    total_servicos = db.Column(db.Numeric(10, 2), default=0)
    total_outros = db.Column(db.Numeric(10, 2), default=0)
    total_geral = db.Column(db.Numeric(10, 2), default=0)
    
    # Status do relatório
    status = db.Column(db.String(20), default='rascunho')  # rascunho, finalizado, enviado
    data_finalizacao = db.Column(db.DateTime)
    data_envio = db.Column(db.DateTime)
    
    # Arquivo do relatório
    arquivo_pdf_path = db.Column(db.String(500))
    arquivo_excel_path = db.Column(db.String(500))
    
    # Controle
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'mes': self.mes,
            'ano': self.ano,
            'total_comercio': float(self.total_comercio),
            'total_industria': float(self.total_industria),
            'total_servicos': float(self.total_servicos),
            'total_outros': float(self.total_outros),
            'total_geral': float(self.total_geral),
            'status': self.status,
            'data_finalizacao': self.data_finalizacao.isoformat() if self.data_finalizacao else None,
            'data_envio': self.data_envio.isoformat() if self.data_envio else None,
            'arquivo_pdf_path': self.arquivo_pdf_path,
            'arquivo_excel_path': self.arquivo_excel_path,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class DeclaracaoAnual(db.Model):
    __tablename__ = 'declaracoes_anuais'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Ano da declaração
    ano = db.Column(db.Integer, nullable=False)
    
    # Totais anuais por categoria
    total_comercio = db.Column(db.Numeric(10, 2), default=0)
    total_industria = db.Column(db.Numeric(10, 2), default=0)
    total_servicos = db.Column(db.Numeric(10, 2), default=0)
    total_geral = db.Column(db.Numeric(12, 2), default=0)
    
    # Informações adicionais
    teve_funcionario = db.Column(db.Boolean, default=False)
    
    # Status da declaração
    status = db.Column(db.String(20), default='rascunho')  # rascunho, finalizado, enviado
    data_finalizacao = db.Column(db.DateTime)
    data_envio = db.Column(db.DateTime)
    
    # Arquivo da declaração
    arquivo_pdf_path = db.Column(db.String(500))
    
    # Controle
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ano': self.ano,
            'total_comercio': float(self.total_comercio),
            'total_industria': float(self.total_industria),
            'total_servicos': float(self.total_servicos),
            'total_geral': float(self.total_geral),
            'teve_funcionario': self.teve_funcionario,
            'status': self.status,
            'data_finalizacao': self.data_finalizacao.isoformat() if self.data_finalizacao else None,
            'data_envio': self.data_envio.isoformat() if self.data_envio else None,
            'arquivo_pdf_path': self.arquivo_pdf_path,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

