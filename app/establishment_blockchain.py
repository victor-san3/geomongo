import hashlib
import time
import datetime
import json
import os
import threading
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

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
        # Converte bloco para dict do MongoDB
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
        
        # Conectar ao MongoDB
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
        # Carrega blockchain do MongoDB
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
        genesis_block = Block(0, str(datetime.datetime.now()), "Genesis Block", "0")
        # Mine the genesis block to ensure it passes validation
        print("Minerando bloco genesis...")
        genesis_block.mine_block(self.difficulty)
        print(f"Bloco genesis minerado com hash: {genesis_block.hash}")
        return genesis_block

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
        
    def add_establishment_async(self, establishment_data):
        """Adiciona um novo estabelecimento à blockchain de forma assíncrona"""
        # Criar um registro temporário na blockchain com status 'pending'
        previous_block = self.get_latest_block()
        new_block_index = len(self.chain)
        
        # Registro temporário
        temp_block_data = {
            'index': new_block_index,
            'timestamp': str(datetime.datetime.now()),
            'establishment_data': establishment_data,
            'previous_hash': previous_block.hash,
            'status': 'pending',
            'mining_start': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Inserir o registro temporário
        temp_block_id = self.blockchain_collection.insert_one(temp_block_data).inserted_id
        
        # Iniciar a mineração em uma thread separada
        def mine_in_background():
            try:
                # Criar o bloco
                new_block = Block(
                    new_block_index,
                    temp_block_data['timestamp'],
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
                
                # Adicionar bloco à chain
                self.chain.append(new_block)
                
                # Atualizar registro
                block_data = new_block.to_dict()
                block_data['mining_start'] = hora_inicio.strftime('%Y-%m-%d %H:%M:%S')
                block_data['mining_end'] = hora_fim.strftime('%Y-%m-%d %H:%M:%S')
                block_data['mining_duration'] = (hora_fim - hora_inicio).total_seconds()
                block_data['status'] = 'completed'
                
                self.blockchain_collection.update_one(
                    {'_id': temp_block_id},
                    {'$set': block_data}
                )
                
                print(f"Bloco {new_block_index} adicionado à blockchain com sucesso!")
            except Exception as e:
                print(f"Erro durante a mineração do bloco: {str(e)}")
                # Atualizar o status para 'failed' em caso de erro
                self.blockchain_collection.update_one(
                    {'_id': temp_block_id},
                    {'$set': {'status': 'failed', 'error': str(e)}}
                )
        
        # Iniciar a thread de mineração
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(mine_in_background)
        
        return {
            'status': 'pending',
            'message': 'Estabelecimento adicionado. Mineração iniciada em segundo plano.',
            'block_index': new_block_index
        }

    def find_establishment_block(self, establishment_id):
        """Encontra o bloco de um estabelecimento específico"""
        for block in self.chain:
            if isinstance(block.establishment_data, dict) and \
               block.establishment_data.get('establishment_id') == establishment_id:
                return block
        return None

    def is_chain_valid(self):
        """Valida toda a cadeia blockchain"""
        # If the blockchain has only the genesis block, it's valid
        if len(self.chain) <= 1:
            return True
            
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
        # Primeiro, verificar se existe um bloco pendente para este estabelecimento
        pending_block = self.blockchain_collection.find_one({
            'establishment_data.establishment_id': establishment_id,
            'status': 'pending'
        })
        
        if pending_block:
            return {
                "status": "pending",
                "message": "Estabelecimento está sendo minerado na blockchain",
                "block": pending_block
            }
        
        # Verificar se existe um bloco com erro
        failed_block = self.blockchain_collection.find_one({
            'establishment_data.establishment_id': establishment_id,
            'status': 'failed'
        })
        
        if failed_block:
            return {
                "status": "failed",
                "message": "Houve um erro na mineração do bloco",
                "block": failed_block,
                "error": failed_block.get('error', 'Erro desconhecido')
            }
        
        # Buscar o bloco completo
        block = self.find_establishment_block(establishment_id)
        if not block:
            return {
                "status": "not_found",
                "message": "Estabelecimento não encontrado na blockchain"
            }
        
        # Buscar dados do bloco com mining_duration
        block_data = self.blockchain_collection.find_one({'hash': block.hash})
        block_dict = block.to_dict()
        
        # Adicionar mining_duration se disponível
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