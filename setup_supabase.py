#!/usr/bin/env python3
"""
Script para configurar o banco Supabase via API REST
"""

import requests
import json

# Configurações do Supabase
SUPABASE_URL = "https://eegmhbgojrenntzvtdkf.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVlZ21oYmdvanJlbm50enZ0ZGtmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzk2NDA0MiwiZXhwIjoyMDY5NTQwMDQyfQ._34Pj8D9fHLs7aghSagob59vS4gU9MgF9CEHmmkUhHg"

headers = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}

def test_connection():
    """Testa conexão com Supabase"""
    try:
        response = requests.get(f"{SUPABASE_URL}/rest/v1/", headers=headers)
        print(f"Status da conexão: {response.status_code}")
        if response.status_code == 200:
            print("✅ Conexão com Supabase estabelecida com sucesso!")
            return True
        else:
            print(f"❌ Erro na conexão: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

def create_user_table():
    """Cria tabela de usuários"""
    sql = """
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
    """
    
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
            headers=headers,
            json={"sql": sql}
        )
        print(f"Criação da tabela users: {response.status_code}")
        if response.status_code in [200, 201]:
            print("✅ Tabela users criada com sucesso!")
        else:
            print(f"❌ Erro ao criar tabela users: {response.text}")
    except Exception as e:
        print(f"❌ Erro ao criar tabela users: {e}")

def main():
    print("🚀 Configurando banco Supabase...")
    
    if test_connection():
        create_user_table()
        print("\n✅ Configuração do Supabase concluída!")
    else:
        print("\n❌ Falha na configuração do Supabase")

if __name__ == "__main__":
    main()
