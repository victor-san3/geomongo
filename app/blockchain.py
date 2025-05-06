import hashlib
import time
import datetime
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

#Exemplo de uso
i=0
hash_calculado="UNISO2025"
i=0
tamanho=6

hora_inicio = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Formata o tempo de início
print(hora_inicio)
while hash_calculado[:tamanho] != "0"*tamanho:
  hash_calculado = calcular_hash_sha256("UNISO2025"+str(i))
  i += 1
  if i == 1000000000:
    print("Não encontrado")
    break
print(i)
hora_fim = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Formata o tempo de início
print(hora_fim)

print(f"O hash SHA256 de 'Exemplo de texto' é: {hash_calculado}")