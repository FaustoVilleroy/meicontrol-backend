from supabase import create_client, Client
from src.config import Config

# Inicialização do cliente Supabase
supabase: Client = None

def init_supabase():
    global supabase
    if Config.SUPABASE_URL and Config.SUPABASE_KEY and Config.SUPABASE_URL != 'your_supabase_url_here':
        try:
            supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
            print("Supabase inicializado com sucesso")
        except Exception as e:
            print(f"Erro ao inicializar Supabase: {e}")
            supabase = None
    else:
        print("Supabase não configurado - usando SQLite local")
    return supabase

def get_supabase_client():
    global supabase
    if supabase is None:
        supabase = init_supabase()
    return supabase

