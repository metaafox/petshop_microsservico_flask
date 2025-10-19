Microsserviço de Agendamento para Pet Shop
Este é um microsserviço Python desenvolvido com o framework Flask para gerenciar o agendamento de consultas veterinárias em um Pet Shop. Ele simula uma API RESTful completa com persistência NoSQL (usando um arquivo JSON) e inclui um sistema de notificação por e-mail para o médico (via SMTP).

🚀 Funcionalidades
Consulta de Disponibilidade (GET /disponibilidade): Retorna os horários livres, permitindo filtros por Especialidade, Data e ID do Médico. O primeiro horário retornado é o "melhor" (o mais cedo).

Agendamento (POST /agendar): Permite ao cliente reservar um horário.

Persistência de Dados: Usa o arquivo db.json para simular um banco de dados NoSQL, atualizando o status de disponibilidade do horário e salvando o agendamento.

Notificação do Médico: Envia um e-mail de notificação (via SMTP) para o médico responsável imediatamente após a confirmação do agendamento.

5 Especialidades Suportadas: Clínica Geral, Odontologia, Ortopedia, Cardiologia e Dermatologia.
