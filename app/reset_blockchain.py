# Script para resetar a coleção blockchain no MongoDB
import os
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def reset_blockchain():
    # Connect to MongoDB
    uri = os.getenv('MONGO_URI')
    
    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
    except Exception:
        client = MongoClient(uri)
    
    # Select the database
    db = client['banco_estabelecimentos']
    
    # Drop the blockchain collection
    try:
        db.blockchain.drop()
        print("✅ Coleção blockchain foi removida com sucesso!")
        print("A blockchain será reiniciada a partir do bloco genesis quando o aplicativo for iniciado.")
    except Exception as e:
        print(f"❌ Erro ao remover coleção blockchain: {str(e)}")
    
    # Close the connection
    client.close()

if __name__ == "__main__":
    print("⚠️ Atenção: Esta operação irá remover toda a blockchain existente.")
    confirm = input("Digite 'sim' para confirmar a reinicialização da blockchain: ")
    
    if confirm.lower() == 'sim':
        reset_blockchain()
    else:
        print("Operação cancelada.")
