#!/usr/bin/env python3
"""
Script de configuração para produção do MEIControl
Configura banco de dados, variáveis de ambiente e prepara para deploy
"""

import os
import sys
import subprocess
import json
from datetime import datetime

def print_step(step, message):
    """Print formatted step message"""
    print(f"\n🔧 STEP {step}: {message}")
    print("=" * 50)

def create_production_env():
    """Create production environment file"""
    print_step(1, "Configurando variáveis de ambiente de produção")
    
    env_content = """# MEIControl - Configurações de Produção
# Gerado automaticamente em {timestamp}

# Configurações básicas
SECRET_KEY=meicontrol-super-secret-key-production-2025
FLASK_ENV=production
FLASK_DEBUG=False
PORT=5001

# Banco de dados (Supabase)
DATABASE_URL=postgresql://postgres:[SENHA]@db.[PROJETO].supabase.co:5432/postgres
SUPABASE_URL=https://[PROJETO].supabase.co
SUPABASE_KEY=[SUA_CHAVE_SUPABASE]

# Email (Gmail SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=noreply@meicontrol.com.br
EMAIL_PASSWORD=[APP_PASSWORD]

# Pagamentos
STRIPE_SECRET_KEY=sk_live_[SUA_CHAVE_STRIPE]
STRIPE_PUBLISHABLE_KEY=pk_live_[SUA_CHAVE_STRIPE]
PAGARME_API_KEY=[SUA_CHAVE_PAGARME]

# URLs de produção
FRONTEND_URL=https://meicontrol.vercel.app
BACKEND_URL=https://meicontrol-api.railway.app

# Configurações de segurança
CORS_ORIGINS=https://meicontrol.vercel.app,https://www.meicontrol.com.br
ALLOWED_HOSTS=meicontrol-api.railway.app,www.meicontrol.com.br

# Configurações de upload
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=/tmp/uploads
""".format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    with open('/home/ubuntu/meicontrol/.env.production', 'w') as f:
        f.write(env_content)
    
    print("✅ Arquivo .env.production criado")
    return True

def create_database_schema():
    """Create database schema SQL"""
    print_step(2, "Gerando schema do banco de dados")
    
    schema_sql = """-- MEIControl Database Schema
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
"""

    with open('/home/ubuntu/meicontrol/database_schema.sql', 'w') as f:
        f.write(schema_sql)
    
    print("✅ Schema do banco de dados gerado: database_schema.sql")
    return True

def create_dockerfile():
    """Create optimized Dockerfile for production"""
    print_step(3, "Criando Dockerfile otimizado para produção")
    
    dockerfile_content = """# MEIControl Backend - Production Dockerfile
FROM python:3.11-slim

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY src/ ./src/
COPY .env.production .env

# Criar diretório de uploads
RUN mkdir -p /app/uploads

# Expor porta
EXPOSE 5001

# Configurar usuário não-root
RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

# Comando de inicialização
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "--timeout", "120", "src.main:app"]
"""

    with open('/home/ubuntu/meicontrol/Dockerfile', 'w') as f:
        f.write(dockerfile_content)
    
    print("✅ Dockerfile criado")
    return True

def create_docker_compose():
    """Create docker-compose for local testing"""
    print_step(4, "Criando docker-compose para testes locais")
    
    compose_content = """version: '3.8'

services:
  # Backend Flask
  backend:
    build: .
    ports:
      - "5001:5001"
    environment:
      - DATABASE_URL=postgresql://postgres:meicontrol123@db:5432/meicontrol
      - FLASK_ENV=production
    depends_on:
      - db
    volumes:
      - ./uploads:/app/uploads
    restart: unless-stopped

  # Frontend React (para testes locais)
  frontend:
    build: 
      context: ./meicontrol-frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://localhost:5001/api
    depends_on:
      - backend
    restart: unless-stopped

  # Banco PostgreSQL
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=meicontrol
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=meicontrol123
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database_schema.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped

  # Redis para cache (opcional)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

volumes:
  postgres_data:
"""

    with open('/home/ubuntu/meicontrol/docker-compose.yml', 'w') as f:
        f.write(compose_content)
    
    print("✅ docker-compose.yml criado")
    return True

def create_frontend_dockerfile():
    """Create Dockerfile for frontend"""
    print_step(5, "Criando Dockerfile para frontend React")
    
    frontend_dockerfile = """# MEIControl Frontend - Production Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Copiar package files
COPY package.json pnpm-lock.yaml ./

# Instalar pnpm e dependências
RUN npm install -g pnpm && pnpm install

# Copiar código fonte
COPY . .

# Build da aplicação
RUN pnpm run build

# Estágio de produção com Nginx
FROM nginx:alpine

# Copiar arquivos buildados
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar configuração customizada do Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expor porta
EXPOSE 80

# Comando de inicialização
CMD ["nginx", "-g", "daemon off;"]
"""

    with open('/home/ubuntu/meicontrol-frontend/Dockerfile', 'w') as f:
        f.write(frontend_dockerfile)
    
    # Criar configuração do Nginx
    nginx_config = """server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Configuração para SPA (Single Page Application)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache para assets estáticos
    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Compressão gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
}
"""

    with open('/home/ubuntu/meicontrol-frontend/nginx.conf', 'w') as f:
        f.write(nginx_config)
    
    print("✅ Dockerfile e configuração Nginx para frontend criados")
    return True

def update_backend_for_production():
    """Update backend configuration for production"""
    print_step(6, "Atualizando backend para produção")
    
    # Atualizar main.py para produção
    main_py_content = """from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configurações de produção
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key')
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))
    
    # CORS configurado para produção
    cors_origins = os.getenv('CORS_ORIGINS', '*').split(',')
    CORS(app, origins=cors_origins, supports_credentials=True)
    
    # Importar e registrar blueprints
    try:
        from routes.auth import auth_bp
        from routes.financeiro import financeiro_bp
        from routes.notas_fiscais import notas_fiscais_bp
        from routes.relatorios import relatorios_bp
        from routes.notificacoes import notificacoes_bp
        from routes.admin import admin_bp
        
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        app.register_blueprint(financeiro_bp, url_prefix='/api/financeiro')
        app.register_blueprint(notas_fiscais_bp, url_prefix='/api/notas-fiscais')
        app.register_blueprint(relatorios_bp, url_prefix='/api/relatorios')
        app.register_blueprint(notificacoes_bp, url_prefix='/api/notificacoes')
        app.register_blueprint(admin_bp, url_prefix='/api/admin')
        
    except ImportError as e:
        print(f"Erro ao importar blueprints: {e}")
    
    # Rota de health check
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'MEIControl API'}, 200
    
    @app.route('/')
    def root():
        return {
            'message': 'MEIControl API',
            'version': '1.0.0',
            'status': 'running'
        }
    
    return app

# Criar instância da aplicação
app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
"""

    with open('/home/ubuntu/meicontrol/src/main.py', 'w') as f:
        f.write(main_py_content)
    
    print("✅ Backend atualizado para produção")
    return True

def create_deployment_guide():
    """Create deployment guide"""
    print_step(7, "Criando guia de deploy")
    
    guide_content = """# 🚀 MEIControl - Guia de Deploy em Produção

## Pré-requisitos
- Conta no Supabase (banco de dados)
- Conta no Railway/Render (backend)
- Conta no Vercel/Netlify (frontend)

## 1. Configurar Supabase

### 1.1 Criar Projeto
1. Acesse https://supabase.com
2. Crie novo projeto
3. Anote a URL e API Key

### 1.2 Executar Schema
1. Vá em SQL Editor no Supabase
2. Execute o conteúdo de `database_schema.sql`
3. Verifique se as tabelas foram criadas

## 2. Deploy do Backend (Railway)

### 2.1 Preparar Repositório
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin [SEU_REPO]
git push -u origin main
```

### 2.2 Deploy no Railway
1. Acesse https://railway.app
2. Conecte seu repositório GitHub
3. Configure variáveis de ambiente:
   - DATABASE_URL: [URL do Supabase]
   - SECRET_KEY: [Chave secreta]
   - FLASK_ENV: production

### 2.3 Configurar Domínio
1. Gere domínio público no Railway
2. Anote a URL (ex: meicontrol-api.railway.app)

## 3. Deploy do Frontend (Vercel)

### 3.1 Build e Deploy
```bash
cd meicontrol-frontend
npm run build
```

### 3.2 Deploy no Vercel
1. Acesse https://vercel.com
2. Importe o projeto
3. Configure variável de ambiente:
   - VITE_API_URL: [URL do Railway]

## 4. Testes Finais

### 4.1 Verificar APIs
- GET /health (deve retornar status healthy)
- POST /api/auth/register (teste de cadastro)

### 4.2 Testar Frontend
- Acesso à página de login
- Cadastro de usuário
- Dashboard funcionando

## 5. Monitoramento

### 5.1 Logs
- Railway: Logs automáticos
- Vercel: Function logs

### 5.2 Uptime
- Configure alertas de uptime
- Monitor de performance

## URLs de Exemplo
- Backend: https://meicontrol-api.railway.app
- Frontend: https://meicontrol.vercel.app
- Banco: [Supabase Dashboard]

## Comandos Úteis

### Teste Local com Docker
```bash
docker-compose up -d
```

### Deploy Manual
```bash
# Backend
docker build -t meicontrol-backend .
docker run -p 5001:5001 meicontrol-backend

# Frontend
cd meicontrol-frontend
npm run build
npx serve dist
```

## Troubleshooting

### Erro de CORS
- Verificar CORS_ORIGINS no backend
- Confirmar URL do frontend nas variáveis

### Erro de Banco
- Verificar DATABASE_URL
- Confirmar schema executado no Supabase

### Build Falha
- Verificar todas as dependências
- Conferir variáveis de ambiente
"""

    with open('/home/ubuntu/DEPLOY_GUIDE.md', 'w') as f:
        f.write(guide_content)
    
    print("✅ Guia de deploy criado: DEPLOY_GUIDE.md")
    return True

def main():
    """Main setup function"""
    print("🚀 MEIControl - Setup de Produção")
    print("=" * 50)
    
    try:
        # Execute all setup steps
        create_production_env()
        create_database_schema()
        create_dockerfile()
        create_docker_compose()
        create_frontend_dockerfile()
        update_backend_for_production()
        create_deployment_guide()
        
        print("\n" + "=" * 50)
        print("✅ SETUP DE PRODUÇÃO CONCLUÍDO COM SUCESSO!")
        print("=" * 50)
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. Criar conta no Supabase e executar database_schema.sql")
        print("2. Fazer deploy do backend no Railway/Render")
        print("3. Fazer deploy do frontend no Vercel/Netlify")
        print("4. Configurar variáveis de ambiente de produção")
        print("5. Testar aplicação completa")
        print("\n📖 Consulte DEPLOY_GUIDE.md para instruções detalhadas")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO durante setup: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

