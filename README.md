# Sistema de Estabelecimentos com MongoDB 🏪

Uma aplicação web simples e eficiente para gerenciar estabelecimentos no mapa, garantindo que eles estejam a pelo menos 2km de distância entre si.

## O que este sistema faz? 🎯

- ✅ Cadastra estabelecimentos com nome e localização no mapa
- ✅ Garante distância mínima de 2km entre estabelecimentos
- ✅ Mostra todos os estabelecimentos em um mapa interativo
- ✅ Permite buscar estabelecimentos próximos
- ✅ Gera relatórios de proximidade

## Tecnologias Utilizadas 🛠

- **Backend**: Python com Flask
- **Banco de Dados**: MongoDB
- **Interface**: HTML, Bootstrap 5
- **Mapas**: Leaflet.js

### Estrutura do Banco de Dados

O modelo de dados utiliza a estrutura GeoJSON para armazenamento de localizações:

```json
{
    "nome": String,
    "latitude": Number,
    "longitude": Number,
    "localizacao": {
        "type": "Point",
        "coordinates": [Number, Number]  // [longitude, latitude]
    }
}
```

O índice geoespacial é criado automaticamente na inicialização do aplicativo:

```python
colecao.create_index([('localizacao', GEOSPHERE)])
```

## Funcionalidades

- Registro de estabelecimentos com nome, latitude e longitude
- Validação de distância mínima (2km) entre estabelecimentos
- Edição e exclusão de estabelecimentos
- Visualização de todos os estabelecimentos em mapa interativo
- Relatórios geoespaciais:
  - Número de estabelecimentos em um raio de 10km
  - Lista de estabelecimentos em um raio de 5km de um estabelecimento específico
  - Estabelecimento mais próximo de um ponto de referência

## Funcionalidades Técnicas

### 1. Validação Geoespacial

A aplicação implementa uma validação de distância mínima usando a operação `$near` do MongoDB:

```python
proximos = colecao.find({
    'localizacao': {
        '$near': {
            '$geometry': localizacao,
            '$maxDistance': 2000  # 2km em metros
        }
    }
})
```

### 2. Consultas Geoespaciais

O sistema utiliza consultas geoespaciais avançadas do MongoDB para:

- Busca de estabelecimentos próximos usando `$near`
- Cálculo de distâncias usando a fórmula de Haversine
- Restrição de área geográfica usando `$maxDistance`

### 3. API REST

A aplicação expõe uma API REST para acesso aos dados geoespaciais:

- `GET /api/estabelecimentos`: Retorna GeoJSON com todos os estabelecimentos
- `POST /cadastro`: Cadastra um novo estabelecimento com validação geoespacial
- `DELETE /excluir/<nome>`: Remove um estabelecimento


## Como Instalar localmente? 🚀

1. Tenha instalado:
   - Python 3.7 ou superior
   - MongoDB

2. Clone o projeto e instale as dependências:
   ```bash
   # Instala as bibliotecas necessárias
   pip install -r requirements.txt
   ```

3. Configure o ambiente:
   ```bash
   # Copie o arquivo de configuração
   cp env.example .env
   ```


## Como Executar localmente? 🏃‍♂️

1. Inicie o MongoDB
2. Execute a aplicação:
   ```bash
   cd app
   python app.py
   ```
3. Abra no navegador: http://localhost:5000

## Estrutura do Projeto

- `/app` - Código fonte da aplicação
  - `app.py` - Aplicação Flask principal
  - `/templates` - Templates HTML
- `requirements.txt` - Dependências do projeto
- `.env` - Configurações de ambiente (deve ser criado a partir de env.example)

## Tecnologias Utilizadas

- Flask: Framework web
- MongoDB: Banco de dados para armazenar estabelecimentos
- PyMongo: Driver MongoDB para Python
- Leaflet: Biblioteca para mapas interativos
- Bootstrap: Para design responsivo

## Recursos Geoespaciais

A aplicação utiliza recursos geoespaciais do MongoDB para:
- Garantir distância mínima entre estabelecimentos (2km)
- Gerar relatórios baseados em distância
- Encontrar o estabelecimento mais próximo de um ponto de referência

## Desenvolvido por

Victor Sanchez e Leticia Ferrazzini.
