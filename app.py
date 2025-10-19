import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, jsonify, request
from datetime import datetime

app = Flask(__name__)
DB_FILE = 'db.json'

# --- CONFIGURAÇÕES DO SERVIDOR SMTP ---

SMTP_SERVER = "smtp.gmail.com"  
SMTP_PORT = 587                  
SMTP_USER = "lcfjuniorr@gmail.com"  
SMTP_PASSWORD = "koet rvoy xdmw bslh"       

# --- 1. Funções de DB (Data Access Layer) ---

def load_db():
    """Carrega o banco de dados (JSON) em memória."""
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("Atenção: Criando/Resetando estrutura do db.json.")
        return { "medicos": [], "horarios_disponiveis": [], "agendamentos": [] }

def save_db(db):
    """Salva o banco de dados (JSON) no arquivo."""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def get_medico_by_id(db, medico_id):
    """Retorna os dados de um médico pelo ID."""
    return next((m for m in db['medicos'] if m['id'] == medico_id), None)

# --- 2. Funções de Negócio (Notificação) ---

def enviar_notificacao(medico_email, detalhes_agendamento):
    """Envia a notificação de agendamento por e-mail."""
    
    # 1. Monta o corpo da mensagem
    medico_nome = detalhes_agendamento['medico_nome']
    data = detalhes_agendamento['data']
    horario = detalhes_agendamento['horario']
    pet_nome = detalhes_agendamento['pet_nome']
    cliente_nome = detalhes_agendamento['cliente_nome']
    
    assunto = f"NOVO AGENDAMENTO: Consulta de {pet_nome} ({data} às {horario})"
    
    corpo_html = f"""
    <html>
      <body>
        <h3>Novo Agendamento Confirmado</h3>
        <p>Olá, Dr(a). <strong>{medico_nome}</strong>,</p>
        <p>Foi agendada uma nova consulta em sua agenda:</p>
        <ul>
          <li><strong>Especialidade:</strong> {detalhes_agendamento['especialidade']}</li>
          <li><strong>Data:</strong> {data}</li>
          <li><strong>Horário:</strong> {horario}</li>
          <li><strong>Pet:</strong> {pet_nome}</li>
          <li><strong>Tutor:</strong> {cliente_nome}</li>
          <li><strong>Contato do Tutor:</strong> {detalhes_agendamento['contato']}</li>
        </ul>
        <p>Obrigado!</p>
      </body>
    </html>
    """
    
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = medico_email
    msg['Subject'] = assunto
    
    msg.attach(MIMEText(corpo_html, 'html'))
    
    # 2. Conecta e envia
    try:
        if not SMTP_PASSWORD or SMTP_PASSWORD == "SUA_SENHA_DE_APP_AQUI":
            raise ValueError("Credenciais SMTP não configuradas. Usando log de simulação.")
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, medico_email, msg.as_string())
            print(f"** [NOTIFICAÇÃO REAL ENVIADA] ** para: {medico_email}")
            
    except ValueError as ve:
        # Tratamento para credenciais de teste
        print("-" * 50)
        print(f"** [NOTIFICAÇÃO SIMULADA - FALTA CREDENCIAL] ** para: {medico_email}")
        print(f"Detalhes: {assunto}")
        print("-" * 50)
    except Exception as e:
        # Tratamento para falhas reais de SMTP
        print(f"ERRO AO ENVIAR E-MAIL REAL para {medico_email}: {e}")
        print(f"** [FALHA NA NOTIFICAÇÃO REAL] ** Informações do Agendamento: {assunto}")
        print("Verifique as configurações SMTP (servidor, porta, login e senha de app).")


# --- 3. Endpoints (Rotas) ---

@app.route('/disponibilidade', methods=['GET'])
def consultar_disponibilidade():
    """
    Consulta a disponibilidade de horários.
    Filtros: especialidade, data, medico_id.
    Retorna a lista ordenada (o "melhor" horário é o primeiro).
    """
    db = load_db()
    
    especialidade_filtro = request.args.get('especialidade', '').lower()
    data_filtro = request.args.get('data') 
    medico_filtro = request.args.get('medico_id')
    
    horarios_filtrados = []
    medicos_validos = db['medicos']
    
    # 1. Filtra os médicos pela especialidade e/ou ID
    if especialidade_filtro:
        medicos_validos = [m for m in medicos_validos if m['especialidade'].lower() == especialidade_filtro]
    if medico_filtro:
        medicos_validos = [m for m in medicos_validos if m['id'] == medico_filtro]
        
    medicos_ids_validos = {m['id']: m for m in medicos_validos}

    # 2. Itera sobre os horários e aplica os filtros
    for h in db['horarios_disponiveis']:
        
        if h['medico_id'] not in medicos_ids_validos:
            continue
            
        if data_filtro and h['data'] != data_filtro:
            continue
            
        if not h['disponivel']:
            continue
            
        # 3. Adiciona o horário formatado
        medico_info = medicos_ids_validos[h['medico_id']]
        
        horarios_filtrados.append({
            "medico": medico_info['nome'],
            "especialidade": medico_info['especialidade'],
            "data": h['data'],
            "horario": h['horario'],
            "medico_id": h['medico_id']
        })

    if not horarios_filtrados:
        return jsonify({"mensagem": "Nenhum horário disponível encontrado para os critérios selecionados."}), 404

    # Retorna a lista ordenada (o "melhor" horário é o primeiro)
    return jsonify({
        "total_encontrado": len(horarios_filtrados),
        "horarios": sorted(horarios_filtrados, key=lambda x: (x['data'], x['horario']))
    })


@app.route('/agendar', methods=['POST'])
def agendar_consulta():
    """
    Agenda uma consulta:
    1. Marca o horário como indisponível.
    2. Salva o agendamento no DB.
    3. Notifica o médico por e-mail (simulado ou real).
    """
    db = load_db()
    dados_agendamento = request.json

    required_fields = ['medico_id', 'data', 'horario', 'cliente_nome', 'pet_nome', 'contato']
    if not all(field in dados_agendamento for field in required_fields):
        return jsonify({"erro": "Dados incompletos. Verifique os campos obrigatórios."}), 400

    medico_id = dados_agendamento['medico_id']
    data_agenda = dados_agendamento['data']
    horario_agenda = dados_agendamento['horario']

    # 1. Busca o horário e o médico
    horario_encontrado = next((
        h for h in db['horarios_disponiveis']
        if (h['medico_id'] == medico_id and 
            h['data'] == data_agenda and 
            h['horario'] == horario_agenda and 
            h['disponivel'])
    ), None)

    if not horario_encontrado:
        return jsonify({"erro": "Horário não encontrado ou já agendado."}), 404

    medico = get_medico_by_id(db, medico_id)
    if not medico:
        return jsonify({"erro": "Médico não encontrado."}), 404
        
    # 2. Realiza o Agendamento (Persistência NoSQL)
    novo_agendamento = {
        "id": len(db['agendamentos']) + 1,
        "timestamp": datetime.now().isoformat(),
        "medico_nome": medico['nome'],
        "especialidade": medico['especialidade'],
        **dados_agendamento
    }
    db['agendamentos'].append(novo_agendamento)
    horario_encontrado['disponivel'] = False 
    save_db(db)

    # 3. Notificação do Médico
    enviar_notificacao(medico['email'], novo_agendamento)
    
    return jsonify({
        "mensagem": "Agendamento realizado com sucesso!",
        "detalhes": {
            "protocolo": novo_agendamento['id'],
            "medico": medico['nome'],
            "especialidade": medico['especialidade'],
            "data": data_agenda,
            "horario": horario_agenda,
            "pet": dados_agendamento['pet_nome']
        }
    }), 201

if __name__ == '__main__':
    # Instruções de Execução:
    # 1. Certifique-se de que você tem Flask instalado (pip install Flask)
    # 2. Execute o servidor: python app.py
    # 3. A API estará disponível em: http://127.0.0.1:5000/
    print("\nIniciando o Microsserviço Flask...")
    app.run(debug=True)