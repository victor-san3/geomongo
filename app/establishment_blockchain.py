import hashlib
import time
import datetime
import json
import os
import threading
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

class Block:
    def __init__(self, index, timestamp, establishment_data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.establishment_data = establishment_data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        """Calcula o hash SHA256 do bloco usando a mesma lógica do blockchain.py"""
        data = str(self.index) + str(self.timestamp) + str(self.establishment_data) + str(self.previous_hash) + str(self.nonce)
        sha256_hash = hashlib.sha256()
        sha256_hash.update(data.encode('utf-8'))
        return sha256_hash.hexdigest()

    def mine_block(self, difficulty):
        """Minera o bloco usando múltiplas threads como no mult_threads.py"""
        num_threads = os.cpu_count()  # Obtém número de CPUs disponíveis
        intervalo = 120000000 // num_threads
        threads = []
        resultado = []
        self.solucao_encontrada = False  # Variável de controle para todas as threads

        def calcular_hash_intervalo(inicio, fim, target):
            """Função que cada thread executará para encontrar o hash"""
            for i in range(inicio, fim):
                if self.solucao_encontrada:
                    return
                
                self.nonce = i
                current_hash = self.calculate_hash()
                if current_hash[:difficulty] == target:
                    resultado.append((i, current_hash))
                    self.solucao_encontrada = True
                    return

        # Criar e iniciar as threads
        target = "0" * difficulty
        for i in range(num_threads):
            inicio = i * intervalo
            fim = (i + 1) * intervalo
            thread = threading.Thread(
                target=calcular_hash_intervalo,
                args=(inicio, fim, target)
            )
            threads.append(thread)
            thread.start()

        # Aguardar até que a solução seja encontrada ou todas as threads terminem
        while not self.solucao_encontrada and any(thread.is_alive() for thread in threads):
            time.sleep(0.1)

        # Aguardar todas as threads concluírem
        for thread in threads:
            thread.join()

        # Atualizar o hash se uma solução foi encontrada
        if resultado:
            self.nonce = resultado[0][0]
            self.hash = resultado[0][1]
            return True
        return False

    def to_dict(self):
        """Converte o bloco para dicionário para armazenamento no MongoDB"""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'establishment_data': self.establishment_data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'hash': self.hash
        }

class EstablishmentBlockchain:
    def __init__(self):
        # Carregar variáveis de ambiente
        load_dotenv()
        
        # Conectar ao MongoDB usando as configurações do app principal
        uri = os.getenv('MONGO_URI')
        
        try:
            self.client = MongoClient(uri, server_api=ServerApi('1'))
        except Exception:
            self.client = MongoClient(uri)
            
        self.db = self.client['banco_estabelecimentos']
        self.blockchain_collection = self.db['blockchain']
        self.difficulty = 6
        self.chain = self.load_chain_from_db()

    def load_chain_from_db(self):
        """Carrega a blockchain do MongoDB"""
        chain = []
        blocks = self.blockchain_collection.find().sort('index')
        
        for block_data in blocks:
            block = Block(
                block_data['index'],
                block_data['timestamp'],
                block_data['establishment_data'],
                block_data['previous_hash']
            )
            block.nonce = block_data['nonce']
            block.hash = block_data['hash']
            chain.append(block)
        
        if not chain:
            # Criar bloco genesis se a chain estiver vazia
            genesis_block = self.create_genesis_block()
            self.blockchain_collection.insert_one(genesis_block.to_dict())
            chain.append(genesis_block)
        
        return chain

    def create_genesis_block(self):
        """Cria o bloco genesis da blockchain"""
        return Block(0, str(datetime.datetime.now()), "Genesis Block", "0")

    def get_latest_block(self):
        """Retorna o último bloco da chain"""
        return self.chain[-1]

    def add_establishment(self, establishment_data):
        """Adiciona um novo estabelecimento à blockchain"""
        previous_block = self.get_latest_block()
        new_block = Block(
            len(self.chain),
            str(datetime.datetime.now()),
            establishment_data,
            previous_block.hash
        )
        
        # Registrar tempo de início da mineração
        hora_inicio = datetime.datetime.now()
        print(f"Iniciando mineração do bloco em: {hora_inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Minerar o bloco
        new_block.mine_block(self.difficulty)
        
        # Registrar tempo de fim da mineração
        hora_fim = datetime.datetime.now()
        print(f"Mineração concluída em: {hora_fim.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Tempo total de mineração: {(hora_fim - hora_inicio).total_seconds()} segundos")
        
        # Adicionar bloco à chain e ao banco de dados
        self.chain.append(new_block)
        block_data = new_block.to_dict()
        block_data['mining_start'] = hora_inicio.strftime('%Y-%m-%d %H:%M:%S')
        block_data['mining_end'] = hora_fim.strftime('%Y-%m-%d %H:%M:%S')
        block_data['mining_duration'] = (hora_fim - hora_inicio).total_seconds()
        
        self.blockchain_collection.insert_one(block_data)
        return new_block

    def find_establishment_block(self, establishment_id):
        """Encontra o bloco de um estabelecimento específico"""
        for block in self.chain:
            if isinstance(block.establishment_data, dict) and \
               block.establishment_data.get('establishment_id') == establishment_id:
                return block
        return None

    def is_chain_valid(self):
        """Valida toda a cadeia blockchain"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            # Verificar hash atual
            if current_block.hash != current_block.calculate_hash():
                return False

            # Verificar ligação com bloco anterior
            if current_block.previous_hash != previous_block.hash:
                return False

            # Verificar prova de trabalho
            if current_block.hash[:self.difficulty] != "0" * self.difficulty:
                return False

        return True

    def get_establishment_status(self, establishment_id):
        """Retorna o status de um estabelecimento na blockchain"""
        block = self.find_establishment_block(establishment_id)
        if not block:
            return {
                "status": "not_found",
                "message": "Estabelecimento não encontrado na blockchain"
            }
        
        # Get the block data from MongoDB to include mining_duration
        block_data = self.blockchain_collection.find_one({'hash': block.hash})
        block_dict = block.to_dict()
        
        # Add mining_duration if available in MongoDB
        if block_data and 'mining_duration' in block_data:
            block_dict['mining_duration'] = block_data['mining_duration']
        
        is_valid = self.is_chain_valid()
        return {
            "status": "valid" if is_valid else "invalid",
            "block": block_dict,
            "chain_valid": is_valid,
            "message": "Bloco válido na blockchain" if is_valid else "Blockchain corrompida"
        }

# Exemplo de uso
if __name__ == "__main__":
    # Inicializar blockchain
    blockchain = EstablishmentBlockchain()

    # Adicionar um estabelecimento de teste
    establishment_data = {
        "establishment_id": "123",
        "name": "Restaurante Exemplo",
        "address": "Rua Exemplo, 123",
        "type": "restaurant"
    }
    
    print("Adicionando estabelecimento à blockchain...")
    new_block = blockchain.add_establishment(establishment_data)
    print(f"Estabelecimento adicionado no bloco {new_block.index}")
    print(f"Hash do bloco: {new_block.hash}")

    # Verificar status do estabelecimento
    print("\nVerificando status do estabelecimento...")
    status = blockchain.get_establishment_status("123")
    print(json.dumps(status, indent=2))

    # Verificar validade da blockchain
    print("\nVerificando validade da blockchain...")
    is_valid = blockchain.is_chain_valid()
    print(f"Blockchain é válida: {is_valid}")