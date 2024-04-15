#importando bibliotecas
import paramiko
import re
import time

#declarando variaveis estáticas 
host = ''
user = ''
password = ''
PON = "11"
slotCard = "0/2"
vlanMGMT = (201, 200)
vlanPPPOE = (202, 201)
vlanMGMT_VOIP = (201, 202)
vlanPPPOE_VOIP = (202, 203)
vlanVOIP_VOIP = (203, 204)
lineProfileID = "80" # perfil pppoe novo
lineProfileID_VOIP = "81" # perfil voip novo
line_profile_number = "3" #perfil que eu quero que seja alterado

# inicializando a execução
try:
    print("Conectando-se ao equipamento")
    with paramiko.SSHClient() as ssh: # instanciando a variavel ssh dentro desse bloco de codigo 
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # define que se a chave do host estiver ausente ele deve adicionar automaticamente

        ssh.connect(host, username=user, password=password) #iniciando conexão ssh de acordo com os parâmetros informados
        print("Conexão SSH estabelecida.")

        shell = ssh.invoke_shell()# instanciando o shell com a função invoke_shell criando um shell interativo

        def analyzesBuffer(command):# criando função que será rodada sendo passado como parâmetro o comando 
            shell.send(command) # enviando o comando
            start_time = time.time() # inicializando o contador
            recv_data = "" #inicializando a variavel para receber os dados
            stderr_data = "" #inicializando a variavel para receber os erros
            while not recv_data.endswith('#'): #enquanto não receber o final da string como # ou seja marcando o fim do bloco de configuração do equipamento
                if shell.recv_ready(): #se o shell receber status prontp
                    recv_data += shell.recv(100000).decode() # vai ler os dados traduzindo com o limite de 100000 bytes
                    start_time = time.time() #incrementa o contador
                if shell.recv_stderr_ready(): # se receber o campo de erro como pornto
                    stderr_data += shell.recv_stderr(100000).decode() # vai ler os dados traduzindo com o limite de 100000 bytes
                    start_time = time.time() # inicialando o contador
                if 'error' in stderr_data.lower() or 'failure' in stderr_data.lower(): # se na saída do campo de erros entra os seguintes valores "error" ou "failure" ele chama o exeption  e passa como parâmetro o erro
                    raise Exception(stderr_data) 

                else:
                    time.sleep(0.1) # caso não estiver pronto ele segura 0.1 milisegundos
            return recv_data, stderr_data # se esiver ok ele retorna na função os dados retornados e o erro

        display_command = ( # monta o primeiro comando, verificando todas as onts da PON
            "enable\n"
            f"display current-configuration | section include gpon {slotCard}\s "
            f"| include \"ont add {PON}\s\" | no-more\n\n"
        )

        recv_data, stderr_data = analyzesBuffer(display_command) # roda a função com o comando como parâmetro e passa nas variaveis de recebimento de dados e de erros

        print("Saída do comando 'display_command':") 
        print(recv_data)#Pegando a saida para printar o que recebe no terminal 

        ont_ids = [] # criando array de ont 
        for line in recv_data.split('\n'): # pegando os dados recebidos, formatando como linhas e analisando cada linha
            match = re.search(r'ont add \d+ (\d+).*ont-lineprofile-id\s{}\b'.format(line_profile_number), line) # pegando o ont id e o id do line profile
            if match: 
                ont_id = match.group(1)
                ont_ids.append(ont_id) # aribui os valores adiquiridos no grupo 1 para o ont_ids ou seja adiciona no array
 
        print("IDs de ONT encontrados:")
        for ont_id in ont_ids: # itera sobre o id das ont's
            print(f"ID da ONT: {ont_id}")

            display_service_command = f"display current-configuration | section include service-port | include \"gpon {slotCard}/{PON} ont {ont_id}\s\"\n\n"
            recv_data, stderr_data = analyzesBuffer(display_service_command) # monta e executa o comando para mostrar os service-ports de acordo com o ont id


            print("Saída do comando 'display_service_command':")
            print(recv_data)

            if 'vlan 1000' in recv_data or 'vlan 666' in recv_data: # verifica se tem a vlan 1000 ou a 666 nas linhas dos service-port passando para o próximo loop
                print("Ont pulando devido à presença de vlan 1000 ou vlan 666")
                continue 

            service_port_ids = re.findall(r'service-port (\d+)', recv_data)#

            print("IDs dos service-ports encontrados:")
            print(service_port_ids)

            undo_commands = [] # lista dos comandos de exclusão dos service-ports

            for i, service_port_id in enumerate(service_port_ids): # itera sobre os ids e enumera as posições, adiciona no array de exclusão e  
                if i == 0:
                    undo_commands.append(f"config\nundo service-port {service_port_id}\n")
                else:
                    undo_commands.append(f"undo service-port {service_port_id}\n")

            num_lines = len(service_port_ids)

            if num_lines < 2 or num_lines > 3:
                print("Número de service-port incorretos") #Verificando o número de linhas dos service, caso for fora do padrão ele passa para o próximo e não chega e excluir nada
                continue

            for undo_command in undo_commands: # roda a lista de undo service-ports
                recv_data, stderr_data = analyzesBuffer(undo_command)
                print(recv_data)

            interface_gpon_command = f"interface gpon {slotCard}\n"

            num_lines = len(service_port_ids)# le o numero de ids de service-ports, se forem 2 ele modifica o perfil para o router_1g monta os comandos para gerencia e pppoe, se forem 3 ele cria do voip
        

            if num_lines == 2:
                ont_modify_command = f"ont modify {PON} {ont_id} ont-lineprofile-id {lineProfileID}\n\nquit\n"
                add_service_commands = [
                    f"service-port vlan {vlanMGMT[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanMGMT[1]} multi-service user-vlan {vlanMGMT[0]} tag-transform translate\n\n",
                    f"service-port vlan {vlanPPPOE[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanPPPOE[1]} multi-service user-vlan {vlanPPPOE[0]} tag-transform translate\n\nquit\n"
                ]
            elif num_lines == 3:
                ont_modify_command = f"ont modify {PON} {ont_id} ont-lineprofile-id {lineProfileID_VOIP}\n\nquit\n"
                add_service_commands = [
                    f"service-port vlan {vlanMGMT_VOIP[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanMGMT_VOIP[1]} multi-service user-vlan {vlanMGMT_VOIP[0]} tag-transform translate\n\n",
                    f"service-port vlan {vlanPPPOE_VOIP[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanPPPOE_VOIP[1]} multi-service user-vlan {vlanPPPOE_VOIP[0]} tag-transform translate\n\n",
                    f"service-port vlan {vlanVOIP_VOIP[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanVOIP_VOIP[1]} multi-service user-vlan {vlanVOIP_VOIP[0]} tag-transform translate\n\nquit\n"
                ]

            all_commands = [interface_gpon_command, ont_modify_command] + add_service_commands 
            for command in all_commands: # roda os comandos em ordem 
                recv_data, stderr_data = analyzesBuffer(command)
                print(f"Comando enviado: {recv_data}")


except paramiko.SSHException as ex:
    print(f"Erro ao estabelecer conexão SSH: {ex}") # 

except Exception as ex:
    print(f"Ocorreu um erro: {ex}")

finally:
    shell.close()
    print("Conexão SSH fechada")
