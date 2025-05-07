from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import GEOSPHERE
import math
import os
import datetime
import json
from dotenv import load_dotenv
from establishment_blockchain import EstablishmentBlockchain, Block

# Carregar variáveis de ambiente
load_dotenv()

# Inicializar app Flask
app = Flask(__name__)
# Ensure we have a secret key for sessions
app.secret_key = os.getenv('SECRET_KEY', 'dev_secret_key_for_blockchain_demo')

# Habilitar CORS para API
@app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

# Conectar ao MongoDB
uri = os.getenv('MONGO_URI')

# Use a versão mais recente da ServerApi se disponível, mas com fallback para compatibilidade
try:
    client = MongoClient(uri, server_api=ServerApi('1'))
except Exception:
    client = MongoClient(uri)

# Verificar conexão com ping no servidor
try:
    # First try to ping
    client.admin.command('ping')
    print("Ping bem sucedido ao MongoDB!")
    
    # If ping works, try to access the database
    db = client['banco_estabelecimentos']
    print("Banco de dados selecionado com sucesso!")
    
    # Try to access the collection
    colecao = db['estabelecimentos']
    print("Coleção selecionada com sucesso!")
    
    # Try to create the index
    colecao.create_index([('localizacao', GEOSPHERE)])
    print("Índice geoespacial criado com sucesso!")
    
    print("Conectado com sucesso ao MongoDB!")
except Exception as e:
    print(f"Erro detalhado de conexão com MongoDB: {str(e)}")
    print(f"Tipo do erro: {type(e).__name__}")
    import traceback
    print("Stack trace:")
    print(traceback.format_exc())
    raise e

# Fórmula de Haversine para calcular distância entre dois pontos em km
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371  # Raio da Terra em quilômetros
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

# Função para converter documento MongoDB para dict serializável
def converter_para_dict(documento):
    if documento is None:
        return None
    
    # Cria uma cópia do documento para não modificar o original
    resultado = {}
    for chave, valor in documento.items():
        # Converte _id para string
        if chave == '_id':
            resultado[chave] = str(valor)
        else:
            resultado[chave] = valor
    return resultado

# Rota da página inicial
@app.route('/')
def index():
    return render_template('index.html')

# Rota para adicionar estabelecimento
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastrar_estabelecimento():
    if request.method == 'POST':
        nome = request.form.get('nome')
        latitude = float(request.form.get('latitude'))
        longitude = float(request.form.get('longitude'))
        
        # Verificar se já existe um estabelecimento com o mesmo nome
        existente = colecao.find_one({'nome': nome})
        if existente:
            flash('Um estabelecimento com este nome já existe!', 'danger')
            return redirect(url_for('cadastrar_estabelecimento'))
        
        # Criar ponto GeoJSON para a localização
        localizacao = {
            'type': 'Point',
            'coordinates': [longitude, latitude]  # Formato GeoJSON é [longitude, latitude]
        }
        
        # Verificar distância de todos os outros estabelecimentos (deve ser pelo menos 2km)
        proximos = colecao.find({
            'localizacao': {
                '$near': {
                    '$geometry': localizacao,
                    '$maxDistance': 2000  # 2km em metros
                }
            }
        })
        
        if len(list(proximos)) > 0:
            flash('Não é possível cadastrar! Existe um estabelecimento a menos de 2km de distância.', 'danger')
            return redirect(url_for('cadastrar_estabelecimento'))
        
        # Inserir o novo estabelecimento
        estabelecimento = {
            'nome': nome,
            'latitude': latitude,
            'longitude': longitude,
            'localizacao': localizacao
        }
        # Inserir no MongoDB
        result = colecao.insert_one(estabelecimento)
        
        # Registrar na blockchain de forma assíncrona
        blockchain = EstablishmentBlockchain()
        establishment_data = {
            'establishment_id': str(result.inserted_id),
            'nome': nome,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': str(datetime.datetime.now())
        }
        blockchain.add_establishment_async(establishment_data)
        
        flash('Estabelecimento cadastrado com sucesso! A mineração na blockchain foi iniciada em segundo plano.', 'success')
    
    return render_template('cadastro.html')

# Visualizar todos os estabelecimentos
@app.route('/estabelecimentos')
def listar_estabelecimentos():
    estabelecimentos_raw = list(colecao.find())
    estabelecimentos = [converter_para_dict(e) for e in estabelecimentos_raw]
    return render_template('estabelecimentos.html', estabelecimentos=estabelecimentos)

# Excluir estabelecimento
@app.route('/excluir/<nome>', methods=['POST'])
def excluir_estabelecimento(nome):
    colecao.delete_one({'nome': nome})
    flash('Estabelecimento excluído com sucesso!', 'success')
    return redirect(url_for('listar_estabelecimentos'))

# Verificar status do estabelecimento na blockchain
@app.route('/verificar-blockchain/<establishment_id>')
def verificar_blockchain(establishment_id):
    blockchain = EstablishmentBlockchain()
    status = blockchain.get_establishment_status(establishment_id)
    
    if status['status'] == 'not_found':
        flash('Estabelecimento não encontrado na blockchain', 'warning')
    elif not status['chain_valid']:
        flash('Atenção: A blockchain está corrompida!', 'danger')
    else:
        flash('Estabelecimento verificado na blockchain com sucesso!', 'success')
    
    return jsonify(status)

# Buscar estabelecimentos próximos
@app.route('/busca-proximos', methods=['GET', 'POST'])
def buscar_proximos():
    # Converter estabelecimentos para dicionários serializáveis
    estabelecimentos_raw = list(colecao.find())
    estabelecimentos = [converter_para_dict(e) for e in estabelecimentos_raw]
    
    resultados = []
    estabelecimento_selecionado = None
    raio = 5  # valor padrão
    
    if request.method == 'POST':
        estabelecimento_selecionado = request.form.get('estabelecimento')
        raio = int(request.form.get('raio', 5))
        estabelecimento_raw = colecao.find_one({'nome': estabelecimento_selecionado})
        estabelecimento = converter_para_dict(estabelecimento_raw)
        
        if estabelecimento:
            localizacao = estabelecimento_raw['localizacao']  # Usar o documento original para consulta
            
            # Encontrar estabelecimentos no raio especificado
            proximos_raw = colecao.find({
                'nome': {'$ne': estabelecimento_selecionado},  # Excluir o estabelecimento atual
                'localizacao': {
                    '$near': {
                        '$geometry': localizacao,
                        '$maxDistance': raio * 1000  # converter km para metros
                    }
                }
            })
            
            for proximo_raw in proximos_raw:
                # Converter para dicionário serializável
                proximo = converter_para_dict(proximo_raw)
                
                # Calcular distância exata
                distancia = calcular_distancia(
                    estabelecimento['latitude'], estabelecimento['longitude'],
                    proximo['latitude'], proximo['longitude']
                )
                
                proximo['distancia'] = round(distancia, 2)  # Arredondar para 2 casas decimais
                resultados.append(proximo)
    
    return render_template('busca_proximos.html', estabelecimentos=estabelecimentos, 
                          resultados=resultados, estabelecimento_selecionado=estabelecimento_selecionado,
                          raio=raio)

# API para obter estabelecimentos em formato GeoJSON para visualização no mapa
@app.route('/api/estabelecimentos')
def obter_estabelecimentos():
    # Aqui não precisamos do _id, então podemos excluí-lo diretamente na consulta
    estabelecimentos = list(colecao.find({}, {
        '_id': 0,
        'nome': 1,
        'latitude': 1,
        'longitude': 1
    }))
    
    features = []
    for e in estabelecimentos:
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [e['longitude'], e['latitude']]
            },
            'properties': {
                'name': e['nome']
            }
        })
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return jsonify(geojson)

# API endpoint for creating establishments
@app.route('/api/cadastro', methods=['POST'])
def api_cadastrar_estabelecimento():
    try:
        # Obter dados do formulário
        nome = request.form.get('nome')
        latitude = float(request.form.get('latitude'))
        longitude = float(request.form.get('longitude'))
        
        # Verificar se já existe um estabelecimento com o mesmo nome
        existente = colecao.find_one({'nome': nome})
        if existente:
            return jsonify({'success': False, 'message': 'Um estabelecimento com este nome já existe!'}), 400
        
        # Criar ponto GeoJSON para a localização
        localizacao = {
            'type': 'Point',
            'coordinates': [longitude, latitude]  # Formato GeoJSON é [longitude, latitude]
        }
        
        # Verificar distância de todos os outros estabelecimentos (deve ser pelo menos 2km)
        proximos = colecao.find({
            'localizacao': {
                '$near': {
                    '$geometry': localizacao,
                    '$maxDistance': 2000  # 2km em metros
                }
            }
        })
        
        if len(list(proximos)) > 0:
            return jsonify({'success': False, 'message': 'Não é possível cadastrar! Existe um estabelecimento a menos de 2km de distância.'}), 400
        
        # Inserir o novo estabelecimento
        estabelecimento = {
            'nome': nome,
            'latitude': latitude,
            'longitude': longitude,
            'localizacao': localizacao
        }
        
        # Corrigido: Inserir apenas uma vez
        result = colecao.insert_one(estabelecimento)
        
        # Registrar na blockchain de forma assíncrona
        blockchain = EstablishmentBlockchain()
        establishment_data = {
            'establishment_id': str(result.inserted_id),
            'nome': nome,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': str(datetime.datetime.now())
        }
        blockchain.add_establishment_async(establishment_data)
        
        return jsonify({'success': True, 'message': 'Estabelecimento cadastrado com sucesso! A mineração na blockchain foi iniciada em segundo plano.'}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao cadastrar: {str(e)}'}), 500

# API endpoint for deleting establishments
@app.route('/api/excluir/<nome>', methods=['POST', 'DELETE'])
def api_excluir_estabelecimento(nome):
    try:
        result = colecao.delete_one({'nome': nome})
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': f'Estabelecimento {nome} excluído com sucesso!'}), 200
        else:
            return jsonify({'success': False, 'message': 'Estabelecimento não encontrado.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao excluir: {str(e)}'}), 500

# API endpoint for finding nearby establishments
@app.route('/api/busca-proximos', methods=['POST'])
def api_busca_proximos():
    resultados = []
    try:
        estabelecimento_nome = request.form.get('estabelecimento')
        raio = float(request.form.get('raio'))
        
        # Converter raio de km para metros (para consulta geoespacial)
        raio_metros = raio * 1000
        
        # Buscar estabelecimento selecionado
        estabelecimento = colecao.find_one({'nome': estabelecimento_nome})
        
        if not estabelecimento:
            return jsonify({'success': False, 'message': 'Estabelecimento não encontrado'}), 404
        
        # Buscar estabelecimentos próximos usando consulta geoespacial
        proximos_cursor = colecao.find({
            'nome': {'$ne': estabelecimento_nome},  # Excluir o próprio estabelecimento
            'localizacao': {
                '$near': {
                    '$geometry': estabelecimento['localizacao'],
                    '$maxDistance': raio_metros
                }
            }
        })
        
        # Processar resultados
        for proximo in proximos_cursor:
            # Calcular distância exata
            distancia = calcular_distancia(
                estabelecimento['latitude'], estabelecimento['longitude'],
                proximo['latitude'], proximo['longitude']
            )
            
            resultados.append({
                'nome': proximo['nome'],
                'latitude': proximo['latitude'],
                'longitude': proximo['longitude'],
                'distancia': round(distancia, 2)  # Arredondar para 2 casas decimais
            })
        
        return jsonify({'success': True, 'resultados': resultados}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro na busca: {str(e)}'}), 500

@app.route('/api/estabelecimentos-geolocalizacao')
def api_estabelecimentos_geolocalizacao():
    # Use the existing obter_estabelecimentos function to get GeoJSON data
    geojson_data = obter_estabelecimentos().json
    
    # Convert from GeoJSON to a simpler format for the map
    estabelecimentos_json = []
    for feature in geojson_data['features']:
        estabelecimentos_json.append({
            'nome': feature['properties']['name'],
            'latitude': feature['geometry']['coordinates'][1],  # GeoJSON uses [longitude, latitude]
            'longitude': feature['geometry']['coordinates'][0]
        })
    
    # Return as JSON response
    return jsonify(estabelecimentos_json)

# Blockchain validation routes
@app.route('/blockchain-validation')
def validate_blockchain():
    blockchain = EstablishmentBlockchain()
    blocks = []
    
    for block in blockchain.chain:
        blocks.append(block.to_dict())
    
    # Check if validation was performed
    chain_status = session.pop('chain_status', None)
    validation_errors = session.pop('validation_errors', None)
    tampered_blocks = session.pop('tampered_blocks', [])
    
    return render_template(
        'blockchain_validation.html', 
        blocks=blocks, 
        chain_status=chain_status,
        validation_errors=validation_errors,
        tampered_blocks=tampered_blocks
    )

@app.route('/validate-blockchain', methods=['POST'])
def perform_blockchain_validation():
    blockchain = EstablishmentBlockchain()
    is_valid = blockchain.is_chain_valid()
    validation_errors = []
    
    # If blockchain is invalid, find the specific issues
    if not is_valid:
        validation_errors = get_blockchain_validation_errors(blockchain)
    
    # Store validation results in session for the redirect
    session['chain_status'] = is_valid
    session['validation_errors'] = validation_errors
    
    if is_valid:
        flash('Blockchain validada com sucesso! Todos os blocos estão íntegros.', 'success')
    else:
        flash('ALERTA: Foram encontradas inconsistências na blockchain!', 'danger')
    
    return redirect(url_for('validate_blockchain'))

def get_blockchain_validation_errors(blockchain):
    """Identify specific validation errors in the blockchain"""
    errors = []
    tampered_blocks = set()  # Keep track of tampered block indices
    
    for i in range(1, len(blockchain.chain)):
        current_block = blockchain.chain[i]
        previous_block = blockchain.chain[i-1]
        
        block_has_error = False
        
        # Check current hash
        calculated_hash = current_block.calculate_hash()
        if current_block.hash != calculated_hash:
            errors.append(f"Bloco #{current_block.index}: Hash calculado não corresponde ao hash armazenado.")
            tampered_blocks.add(current_block.index)
            block_has_error = True
            # Add more detail to help understand the tampering
            errors.append(f"  - Hash armazenado: {current_block.hash[:10]}...")
            errors.append(f"  - Hash calculado: {calculated_hash[:10]}...")
        
        # Check previous hash
        if current_block.previous_hash != previous_block.hash:
            errors.append(f"Bloco #{current_block.index}: Referência ao hash anterior inválida.")
            tampered_blocks.add(current_block.index)
            block_has_error = True
            # Add more detail
            errors.append(f"  - Hash anterior armazenado: {current_block.previous_hash[:10]}...")
            errors.append(f"  - Hash do bloco anterior: {previous_block.hash[:10]}...")
        
        # Check proof of work
        if current_block.hash[:blockchain.difficulty] != "0" * blockchain.difficulty:
            errors.append(f"Bloco #{current_block.index}: Prova de trabalho inválida.")
            tampered_blocks.add(current_block.index)
            block_has_error = True
            # Add more detail
            errors.append(f"  - Prefixo atual: {current_block.hash[:blockchain.difficulty]}")
            errors.append(f"  - Prefixo esperado: {'0' * blockchain.difficulty}")
        
        # If there was an error, provide info about the block
        if block_has_error:
            if isinstance(current_block.establishment_data, dict) and 'nome' in current_block.establishment_data:
                errors.append(f"  - Nome do estabelecimento: {current_block.establishment_data['nome']}")
    
    # Include tampered block indices in session
    session['tampered_blocks'] = list(tampered_blocks)
    
    return errors

@app.route('/tamper-block', methods=['POST'])
def tamper_block():
    """Tamper with a block to demonstrate blockchain validation"""
    block_index = int(request.form.get('block_index'))
    
    blockchain = EstablishmentBlockchain()
    
    # Find and tamper the block
    if 0 <= block_index < len(blockchain.chain):
        # Modify the block in MongoDB
        block = blockchain.chain[block_index]
        
        # Simple tampering: change the establishment name
        if isinstance(block.establishment_data, dict) and 'nome' in block.establishment_data:
            tampered_data = block.establishment_data.copy()
            tampered_data['nome'] = tampered_data['nome'] + " (Adulterado)"
            
            # Update in MongoDB without recalculating hash (this breaks the chain)
            blockchain.blockchain_collection.update_one(
                {'index': block_index},
                {'$set': {'establishment_data': tampered_data}}
            )
            
            flash(f'Bloco #{block_index} foi adulterado para demonstração. Valide a blockchain para ver o resultado.', 'warning')
        else:
            flash('Não foi possível adulterar este bloco.', 'danger')
    else:
        flash('Índice de bloco inválido.', 'danger')
    
    return redirect(url_for('validate_blockchain'))

@app.route('/restore-blockchain')
def restore_blockchain():
    """Restore the blockchain to its original state after tampering"""
    blockchain = EstablishmentBlockchain()
    
    # For each block in the chain, recalculate its hash and update in MongoDB
    for i in range(len(blockchain.chain)):
        block = blockchain.chain[i]
        original_hash = block.calculate_hash()
        
        # Update the hash in MongoDB
        blockchain.blockchain_collection.update_one(
            {'index': block.index},
            {'$set': {'hash': original_hash}}
        )
    
    flash('Blockchain restaurada ao estado original.', 'success')
    return redirect(url_for('validate_blockchain'))

if __name__ == '__main__':
    # Em ambiente Docker, sempre usar 0.0.0.0 como host
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)