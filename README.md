# Estabelecimentos com Blockchain

Sistema de gerenciamento de estabelecimentos com registro em blockchain.

## Funcionalidades

- Cadastro de estabelecimentos com validação de distância
- Registro de estabelecimentos em blockchain
- Validação da cadeia de blocos
- Visualização do status da blockchain para cada estabelecimento
- Mineração multi-thread de blocos
- Interface interativa para verificação da blockchain

## Requisitos

- Python 3.8+
- MongoDB
- Variáveis de ambiente configuradas

## Instalação

1. Clone o repositório:
```bash
git clone <repository-url>
cd <project-directory>
git checkout feature/blockchain
```

2. Crie um ambiente virtual e ative-o:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
Crie um arquivo `.env` com:
```
MONGO_URI=sua_uri_do_mongodb
SECRET_KEY=sua_chave_secreta
```

5. Execute a aplicação:
```bash
python app/app.py
```

## Estrutura da Blockchain

- Cada estabelecimento é registrado como um bloco na blockchain
- Prova de trabalho com 6 zeros iniciais
- Mineração distribuída usando múltiplas threads
- Validação completa da cadeia
- Armazenamento persistente no MongoDB

## Uso

1. Acesse a aplicação em `http://localhost:5000`
2. Cadastre um novo estabelecimento
3. Verifique o status da blockchain clicando no botão "Verificar Blockchain"
4. Visualize os detalhes do bloco no modal

## Desenvolvimento

Para contribuir com novas features:

1. Crie uma nova branch:
```bash
git checkout -b feature/nova-funcionalidade
```

2. Faça suas alterações e commit:
```bash
git add .
git commit -m "Descrição das alterações"
```

3. Push para o repositório:
```bash
git push origin feature/nova-funcionalidade
```

4. Crie um Pull Request para a branch main