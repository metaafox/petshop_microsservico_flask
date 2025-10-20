import requests
import json
from datetime import datetime, timedelta

# ----------------------------------------------------
# CONFIGURAÇÕES DO ROBÔ (RPA)
# ----------------------------------------------------

# URL base do seu API Gateway (EXEMPLO! Substitua pela URL real após o deploy)
API_BASE_URL = "https://jqofdrde75.execute-api.us-east-2.amazonaws.com/prod"

# Simula a data de agendamento para o dia seguinte (data dinâmica)
data_agendamento = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

# ----------------------------------------------------
# 1. FUNÇÃO: Consultar Horários Disponíveis (GET)
# ----------------------------------------------------

def consultar_melhor_horario(especialidade="Odontologia", data=data_agendamento):
    """O robô consulta o endpoint para encontrar o primeiro horário disponível."""
    
    endpoint_url = f"{API_BASE_URL}/disponibilidade"
    params = {'especialidade': especialidade, 'data': data}
    
    print(f"\n[RPA] 🔄 Consultando: {especialidade} em {data}...")
    
    try:
        response = requests.get(endpoint_url, params=params)
        response.raise_for_status() # Levanta um erro para códigos 4xx/5xx
        
        data = response.json()
        
        if data.get('total_encontrado', 0) > 0:
            melhor_horario = data['horarios'][0] # O primeiro é o "melhor" (mais cedo)
            print(f"[RPA] ✅ Horário encontrado: {melhor_horario['horario']} com {melhor_horario['medico']}")
            return melhor_horario
        else:
            print(f"[RPA] ❌ Nenhuma disponibilidade encontrada para {especialidade} em {data}.")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"[RPA] 🛑 Erro ao consultar a API: {e}")
        return None

# ----------------------------------------------------
# 2. FUNÇÃO: Enviar o Agendamento (POST)
# ----------------------------------------------------

def enviar_agendamento_json(horario_info):
    """O robô envia o payload JSON para agendar o horário encontrado."""
    
    endpoint_url = f"{API_BASE_URL}/agendar"
    
    # Monta o payload JSON (corpo da requisição)
    payload = {
        "medico_id": horario_info['medico_id'],
        "data": horario_info['data'],
        "horario": horario_info['horario'],
        "cliente_nome": "Robo Automático",
        "pet_nome": "RPA_Pet_" + datetime.now().strftime('%H%M'),
        "contato": "5555-RPA-BOT"
    }
    
    print(f"[RPA] 📤 Tentando agendar: {payload['pet_nome']}...")
    
    try:
        # Usa o parâmetro 'json' do requests, que automaticamente:
        # 1. Converte o dicionário 'payload' para uma string JSON.
        # 2. Adiciona o cabeçalho 'Content-Type: application/json'.
        response = requests.post(endpoint_url, json=payload)
        
        if response.status_code == 201:
            print(f"[RPA] 🎉 SUCESSO! Agendado. Protocolo: {response.json()['detalhes']['protocolo']}")
            return True
        else:
            print(f"[RPA] ⚠️ FALHA no agendamento ({response.status_code}): {response.json().get('erro', response.text)}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[RPA] 🛑 Erro fatal na requisição POST: {e}")
        return False

# ----------------------------------------------------
# FLUXO PRINCIPAL DO RPA
# ----------------------------------------------------

if __name__ == '__main__':
    # 1. Definir o critério (Especialidade)
    especialidade_desejada = "Clinica Geral" 
    
    # 2. Consultar disponibilidade
    disponibilidade = consultar_melhor_horario(especialidade=especialidade_desejada)
    
    if disponibilidade:
        # 3. Se houver, enviar o agendamento
        print("\n[RPA] ➡️ Iniciando o POST de Agendamento...")
        enviar_agendamento_json(disponibilidade)
    else:
        print("\n[RPA] 💤 Finalizando: Nenhum horário para agendar.")