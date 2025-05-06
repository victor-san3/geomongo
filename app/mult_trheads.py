import threading
import hashlib
import time
import datetime

import os
os.system('cls')
num_threads = os.cpu_count()
print(f"Número de threads disponíveis: {num_threads}")


def calcular_hash_sha256(input_string):
  """Calcula o hash SHA256 de uma string.

  Args:
    input_string: A string de entrada para calcular o hash.

  Returns:
    O hash SHA256 da string de entrada.
  """
  sha256_hash = hashlib.sha256()
  sha256_hash.update(input_string.encode('utf-8'))
  return sha256_hash.hexdigest()

def calcular_hash_intervalo(inicio, fim, tamanho, resultado):
  """Calcula o hash SHA256 para um intervalo de números e armazena o resultado se encontrado.

  Args:
    inicio: O número inicial do intervalo.
    fim: O número final do intervalo.
    tamanho: O tamanho do prefixo de zeros desejado.
    resultado: Uma lista para armazenar o resultado encontrado.
  """
  global solucao_encontrada  # Acessar a variável global
  for i in range(inicio, fim):
    if solucao_encontrada:  # Verificar se a solução foi encontrada
        return  # Encerrar a thread
    hash_calculado = calcular_hash_sha256("UNISO2025"+str(i))
    if hash_calculado[:tamanho] == "0"*tamanho:
      resultado.append((i, hash_calculado))
      solucao_encontrada = True  # Sinalizar que a solução foi encontrada
      return  # Encerra a thread se encontrar o hash
    
num_threads = 12  # Número de threads a serem usadas


tamanho=6            
intervalo = 120000000 // num_threads  # Tamanho do intervalo para cada thread
threads = []
resultado = []
solucao_encontrada = False  # Variável global para indicar se a solução foi encontrada


hora_inicio = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(hora_inicio)

for i in range(num_threads):
  inicio = i * intervalo
  fim = (i + 1) * intervalo
  thread = threading.Thread(target=calcular_hash_intervalo, args=(inicio, fim, tamanho, resultado))
  threads.append(thread)
  thread.start()

# Aguardar até que a solução seja encontrada ou todas as threads terminem
while not solucao_encontrada and any(thread.is_alive() for thread in threads):
    time.sleep(0.1)  # Aguardar um curto período antes de verificar novamente

# Aguardar todas as threads concluírem
for thread in threads:
  thread.join()


hora_fim = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(hora_fim)

# Verificar se o resultado foi encontrado
if resultado:
  for numero, hash_encontrado in resultado:
    print(f"Hash encontrado para UNISO2025{numero}: {hash_encontrado}")

else:
  print("Hash não encontrado.")
  
print(calcular_hash_sha256("UNISO2025"))

blockchain = [
    {
        'index': 0,
        'timestamp': '2024-04-20 10:00:00',
        'transacoes': ['A -> B: 10 BTC', 'C -> D: 5 BTC'],
        'hash_anterior': '000000',
        'nonce': 1234,
        'hash': 'abcd1234...'
    },
    ...
]