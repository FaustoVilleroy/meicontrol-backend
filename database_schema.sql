-- MEIControl Database Schema
-- PostgreSQL/Supabase Production Schema

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Tabela de usuários
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nome VARCHAR(255) NOT NULL,
    cnpj VARCHAR(18) UNIQUE NOT NULL,
    telefone VARCHAR(20),
    razao_social VARCHAR(255),
    nome_fantasia VARCHAR(255),
    categoria_mei VARCHAR(50) NOT NULL CHECK (categoria_mei IN ('comercio', 'servicos', 'industria', 'outros')),
    data_abertura DATE,
    plano VARCHAR(20) DEFAULT 'basico' CHECK (plano IN ('basico', 'avancado')),
    status_pagamento VARCHAR(20) DEFAULT 'ativo' CHECK (status_pagamento IN ('ativo', 'inadimplente', 'cancelado')),
    data_vencimento DATE,
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    configuracoes_notificacao JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de receitas
CREATE TABLE IF NOT EXISTS receitas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    descricao TEXT NOT NULL,
    valor DECIMAL(10,2) NOT NULL CHECK (valor > 0),
    data_receita DATE NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    forma_pagamento VARCHAR(50),
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de despesas
CREATE TABLE IF NOT EXISTS despesas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    descricao TEXT NOT NULL,
    valor DECIMAL(10,2) NOT NULL CHECK (valor > 0),
    data_despesa DATE NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    forma_pagamento VARCHAR(50),
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de notas fiscais
CREATE TABLE IF NOT EXISTS notas_fiscais (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    numero_nota VARCHAR(100),
    arquivo_path TEXT NOT NULL,
    arquivo_nome VARCHAR(255) NOT NULL,
    tipo_arquivo VARCHAR(10) NOT NULL,
    tamanho_arquivo INTEGER NOT NULL,
    dados_extraidos JSONB DEFAULT '{}',
    status_processamento VARCHAR(20) DEFAULT 'pendente',
    receita_id INTEGER REFERENCES receitas(id) ON DELETE SET NULL,
    despesa_id INTEGER REFERENCES despesas(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de relatórios mensais
CREATE TABLE IF NOT EXISTS relatorios_mensais (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    mes INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    ano INTEGER NOT NULL CHECK (ano >= 2020),
    total_receitas DECIMAL(10,2) DEFAULT 0,
    total_despesas DECIMAL(10,2) DEFAULT 0,
    saldo_mes DECIMAL(10,2) DEFAULT 0,
    dados_detalhados JSONB DEFAULT '{}',
    arquivo_pdf_path TEXT,
    arquivo_excel_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, mes, ano)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_receitas_user_data ON receitas(user_id, data_receita);
CREATE INDEX IF NOT EXISTS idx_despesas_user_data ON despesas(user_id, data_despesa);
CREATE INDEX IF NOT EXISTS idx_notas_fiscais_user ON notas_fiscais(user_id);
CREATE INDEX IF NOT EXISTS idx_relatorios_user_periodo ON relatorios_mensais(user_id, ano, mes);

-- Triggers para updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_receitas_updated_at BEFORE UPDATE ON receitas FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_despesas_updated_at BEFORE UPDATE ON despesas FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_notas_fiscais_updated_at BEFORE UPDATE ON notas_fiscais FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_relatorios_mensais_updated_at BEFORE UPDATE ON relatorios_mensais FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Dados iniciais (usuário admin)
INSERT INTO users (
    email, password_hash, nome, cnpj, categoria_mei, is_admin, plano
) VALUES (
    'admin@meicontrol.com.br',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5uDjO', -- senha: admin123
    'Administrador MEIControl',
    '12.345.678/0001-90',
    'servicos',
    TRUE,
    'avancado'
) ON CONFLICT (email) DO NOTHING;

-- Comentários nas tabelas
COMMENT ON TABLE users IS 'Tabela de usuários MEI cadastrados na plataforma';
COMMENT ON TABLE receitas IS 'Registro de receitas dos usuários MEI';
COMMENT ON TABLE despesas IS 'Registro de despesas dos usuários MEI';
COMMENT ON TABLE notas_fiscais IS 'Armazenamento e processamento de notas fiscais';
COMMENT ON TABLE relatorios_mensais IS 'Relatórios mensais obrigatórios gerados automaticamente';
