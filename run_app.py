#!/usr/bin/env python3
"""
Script de inicialização do MEIControl
Corrige problemas de import e inicializa a aplicação
"""

import os
import sys
from pathlib import Path

# Adicionar diretório src ao path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# Configurar variáveis de ambiente
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('FLASK_DEBUG', 'False')

# Importar e executar aplicação
from main import app

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)

