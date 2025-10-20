import json
import boto3
from decimal import Decimal # Necessário para lidar com números no DynamoDB


# --- Configurações ---
DB_FILE = 'db.json'
DYNAMODB_TABLE_NAME = 'PetShopTable'
AWS_REGION = 'us-east-2' # Mude para a sua região AWS!

# Inicializa o cliente DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

def load_local_db():
    """Carrega o db.json em memória."""
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar {DB_FILE}: {e}")
        return None

def migrate_data(data):
    """Transforma e carrega os dados no DynamoDB."""
    if not data:
        print("Nenhum dado para migrar.")
        return

    medicos = data.get('medicos', [])
    horarios = data.get('horarios_disponiveis', [])
    agendamentos = data.get('agendamentos', [])
    
    # Lista de itens a serem carregados
    items_to_put = []

    # 1. Migrar Médicos
    for medico in medicos:
        # Define a Chave Primária (PK) e Chave de Classificação (SK)
        items_to_put.append({
            'PK': f'MEDICO#{medico["id"]}',
            'SK': 'INFO',
            'nome': medico['nome'],
            'especialidade': medico['especialidade'],
            'email': medico['email']
        })

    # 2. Migrar Horários Disponíveis
    for h in horarios:
        # Chave para consulta por Horário
        items_to_put.append({
            'PK': f'HORARIO#{h["data"]}',
            'SK': f'MEDICO#{h["medico_id"]}#{h["horario"]}',
            'medico_id': h['medico_id'],
            'horario': h['horario'],
            'data': h['data'],
            'disponivel': h['disponivel']
        })

    # 3. Migrar Agendamentos (Se houver)
    for ag in agendamentos:
        # Chave para consulta de Agendamentos (ex: por ID)
        items_to_put.append({
            'PK': f'AGENDAMENTO#{ag["id"]}',
            'SK': 'INFO',
            'medico_id': ag['medico_id'],
            'data': ag['data'],
            'horario': ag['horario'],
            'pet_nome': ag['pet_nome'],
            'cliente_nome': ag['cliente_nome'],
            'contato': ag['contato'],
            'timestamp': ag['timestamp']
        })


    # Carregar em lote (Batch write) para eficiência
    print(f"Iniciando migração de {len(items_to_put)} itens para {DYNAMODB_TABLE_NAME}...")
    try:
        with table.batch_writer() as batch:
            for item in items_to_put:
                # O DynamoDB não gosta de float, então convertemos para Decimal (melhor prática)
                # Embora nosso JSON só tenha strings e booleans, é bom saber.
                item = json.loads(json.dumps(item), parse_float=Decimal)
                batch.put_item(Item=item)
        print("Migração concluída com sucesso!")
    except Exception as e:
        print(f"Falha na migração para o DynamoDB: {e}")


if __name__ == '__main__':
    local_data = load_local_db()
    if local_data:
        migrate_data(local_data)