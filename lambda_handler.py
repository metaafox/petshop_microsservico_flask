import json
import boto3
from decimal import Decimal
from datetime import datetime

# --- Configurações AWS ---
DYNAMODB_TABLE_NAME = 'PetShopTable'
AWS_REGION = 'us-east-2' # Use a mesma região que usou na migração

# Inicializa o cliente DynamoDB (será reutilizado em execuções subsequentes da Lambda)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

# --- Funções CRUD no DynamoDB (Substituem load_db/save_db) ---

def handle_get_disponibilidade(query_params):
    """
    Simula a lógica de consulta, buscando horários disponíveis no DynamoDB.
    (Implementação simplificada: busca todos os horários disponíveis. O filtro de especialidade é mais complexo no DynamoDB, mas vamos simplificar a busca inicial.)
    """
    # 1. Parâmetros (simplificados)
    especialidade_filtro = query_params.get('especialidade', '').lower()
    data_filtro = query_params.get('data')

    # 2. Busca no DynamoDB
    # Em DynamoDB, a melhor prática é usar Indexes (GSI) para filtros.
    # Aqui, vamos fazer uma busca simples (Scan), que não é ideal para produção, mas funciona para este exercício.
    try:
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('disponivel').eq(True)
        )
        horarios_disponiveis = response.get('Items', [])
        
        # 3. Filtragem em memória (para simplificar a lógica do DynamoDB)
        horarios_filtrados = []
        for item in horarios_disponiveis:
            
            # Garante que é um item de 'horario' e aplica os filtros
            if not item['PK'].startswith('HORARIO#'):
                continue
                
            if especialidade_filtro:
                # É necessário buscar os dados do médico para filtrar por especialidade
                # Para simplificar, assumimos que você fará essa busca no item INFO do médico, 
                # mas vamos pular esse complexo JOIN por enquanto e focar nas chaves PK/SK.
                # Para o MVP, a filtragem de especialidade no GET pode ser simplificada ou removida.
                # Vamos focar em retornar TUDO que está disponível.
                pass 
            
            # Filtro por Data
            if data_filtro and item.get('data') != data_filtro:
                continue

            # Formata a saída (DynamoDB usa Decimal, convertemos para float/str)
            horarios_filtrados.append({
                "medico_id": item['medico_id'],
                "data": str(item['data']), # Converte Decimal para string se houver
                "horario": item['horario'],
                "disponivel": item['disponivel']
            })

        # Ordena por Data e Horário (como no Flask)
        horarios_filtrados.sort(key=lambda x: (x['data'], x['horario']))

        return {
            "total_encontrado": len(horarios_filtrados),
            "horarios": horarios_filtrados
        }

    except Exception as e:
        print(f"Erro na consulta DynamoDB: {e}")
        return {"erro": "Erro interno na consulta de disponibilidade"}, 500


def handle_post_agendar(body):
    """
    Implementa a lógica de agendamento (POST).
    """
    required_fields = ['medico_id', 'data', 'horario', 'cliente_nome', 'pet_nome', 'contato']
    if not all(field in body for field in required_fields):
        return {"erro": "Dados incompletos."}, 400

    medico_id = body['medico_id']
    data_agenda = body['data']
    horario_agenda = body['horario']
    
    # 1. Chaves para o item de horário
    horario_pk = f'HORARIO#{data_agenda}'
    horario_sk = f'MEDICO#{medico_id}#{horario_agenda}'
    
    try:
        # 2. Transação para: Marcar como indisponível E pegar dados do médico (Se necessário, em um ambiente real seria uma transação)

        # Atualiza a disponibilidade para FALSE (Atomic Update)
        update_response = table.update_item(
            Key={'PK': horario_pk, 'SK': horario_sk},
            # Verifica se o horário está disponível antes de marcar
            ConditionExpression='disponivel = :true_val',
            UpdateExpression='SET disponivel = :false_val',
            ExpressionAttributeValues={
                ':false_val': False,
                ':true_val': True
            },
            ReturnValues="ALL_NEW"
        )
        
        # 3. Se a atualização foi bem-sucedida, cria o registro de agendamento
        if update_response.get('Attributes'):
            novo_agendamento = {
                'PK': f'AGENDAMENTO#{datetime.now().isoformat()}', # PK único baseado no tempo
                'SK': 'INFO',
                'medico_id': medico_id,
                'data': data_agenda,
                'horario': horario_agenda,
                'pet_nome': body['pet_nome'],
                'cliente_nome': body['cliente_nome'],
                # Adicione mais campos aqui se precisar dos dados do médico para a notificação
                'status': 'AGENDADO'
            }
            
            table.put_item(Item=novo_agendamento)
            
            # --- Próximo passo real: Publicar no SNS para notificação ---
            # Aqui, você faria a chamada ao Boto3 SNS. Por enquanto, retornamos o sucesso.
            
            return {
                "mensagem": "Agendamento realizado com sucesso! Notificação em processamento.",
                "detalhes": novo_agendamento
            }, 201
        
        else:
            # Condição de Falha (Item não encontrado ou indisponível)
            return {"erro": "Horário não encontrado ou já foi agendado."}, 404

    except boto3.exceptions.botocore.exceptions.ClientError as e:
        # Lidar com falha de condição (o horário não estava disponível)
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
             return {"erro": "Horário não encontrado ou já foi agendado."}, 404
        else:
            print(f"Erro no DynamoDB durante o agendamento: {e}")
            return {"erro": "Erro interno ao processar agendamento."}, 500
    except Exception as e:
        print(f"Erro geral: {e}")
        return {"erro": "Erro interno no servidor."}, 500


# --- O Handler Principal da AWS Lambda ---

def lambda_handler(event, context):
    """
    Função principal que a AWS Lambda irá invocar.
    Ela roteia a requisição HTTP.
    """
    # Analisa o corpo da requisição do API Gateway
    http_method = event.get('httpMethod', 'GET') # Assume GET se não especificado
    path = event.get('path')

    # Tenta obter query parameters ou o body (depende da configuração do API Gateway)
    query_params = event.get('queryStringParameters', {}) or {}
    body = {}
    if event.get('body'):
        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError:
            pass # Ignora se o corpo não for JSON válido

    # --- ROTEAMENTO ---
    if path == '/disponibilidade' and http_method == 'GET':
        result, status_code = handle_get_disponibilidade(query_params), 200
        
    elif path == '/agendar' and http_method == 'POST':
        result, status_code = handle_post_agendar(body)
        
    else:
        result, status_code = {"erro": "Rota não encontrada."}, 404

    # --- Formatação da Resposta para o API Gateway ---
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps(result, cls=DecimalEncoder) # Usa DecimalEncoder para DynamoDB
    }

# Classe auxiliar para lidar com números decimais do DynamoDB
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)