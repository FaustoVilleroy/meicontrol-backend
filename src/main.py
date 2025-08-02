from flask import Flask
from flask_cors import CORS
import os
import sys
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
        sys.path.append(os.path.dirname(__file__))
        
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
