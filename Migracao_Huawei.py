import paramiko
import re
import time

# Variáveis estáticas
host = ''
user = ''
password = ''
PON = "0"
slotCard = "0/1"
vlanMGMT = (240, 21)
vlanPPPOE = (160, 20)
vlanMGMT_VOIP = (240, 21)
vlanPPPOE_VOIP = (161, 22)
lineProfileID = "5"
srvProfileID = "1"

# Funções para leitura e filtragem dos seriais
def read_and_filter_serials(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
        print(f"Total de linhas lidas: {len(lines)}")
        # Adaptando para extrair o serial da linha que começa com "onu"
        filtered_lines = []
        for line in lines:
            line = line.strip().upper()
            if line.startswith("ONU"):
                parts = line.split()
                if len(parts) > 1 and (parts[1].startswith("HWTC")):
                    filtered_lines.append(parts[1])
        print(f"Total de seriais filtrados: {len(filtered_lines)}")
        return filtered_lines
    except FileNotFoundError:
        print(f"Arquivo não encontrado: {file_path}")
        return []
    except Exception as e:
        print(f"Erro ao ler o arquivo: {e}")
        return []

# Função para executar um comando e capturar toda a saída
def analyzesBuffer(shell, command):
    shell.send(command)
    start_time = time.time()
    recv_data = ""
    stderr_data = ""
    while not recv_data.endswith('#'):
        if shell.recv_ready():
            recv_data += shell.recv(100000).decode()
            start_time = time.time()
        if shell.recv_stderr_ready():
            stderr_data += shell.recv_stderr(100000).decode()
            start_time = time.time()
        if 'error' in stderr_data.lower() or 'failure' in stderr_data.lower():
            raise Exception(stderr_data)
        else:
            time.sleep(0.1)
    return recv_data, stderr_data

try:
    print("Conectando-se ao equipamento")
    with paramiko.SSHClient() as ssh:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, password=password)
        print("Conexão SSH estabelecida.")

        shell = ssh.invoke_shell()

        file_path = r"C:\Users\Telecom\Downloads\OLT-067-TESTE.txt" 
        serials = read_and_filter_serials(file_path)
        
        if not serials:
            print("Nenhum serial válido encontrado no arquivo.")
        else:

            enable_executed = False  # Flag para controlar quando executar "enable"

            for serial in serials:
                print(f"Processando serial: {serial}")

                # Construção do comando add_ont_command
                if not enable_executed:
                    add_ont_command = (
                        "enable\n"
                        "config\n"
                        f"interface gpon {slotCard}\n"
                        f"ont add {PON} sn-auth {serial} omci ont-lineprofile-id {lineProfileID} ont-srvprofile-id {srvProfileID} desc 'milene_cristina_toloto_sattis_2'\n\n"
                        "quit\n"
                        "quit\n"
                    )
                    enable_executed = True
                else:
                    add_ont_command = (
                        "config\n"
                        f"interface gpon {slotCard}\n"
                        f"ont add {PON} sn-auth {serial} omci ont-lineprofile-id {lineProfileID} ont-srvprofile-id {srvProfileID} desc 'milene_cristina_toloto_sattis_2'\n\n"
                        "quit\n"
                        "quit\n"
                    )

                recv_data, stderr_data = analyzesBuffer(shell, add_ont_command)
                print("Saída do comando 'add_ont_command':")
                print(recv_data)

                # Comando para obter o ID da ONU pelo serial
                display_ont_info_command = f"display ont info by-sn {serial} | no-more\n\n"
                recv_data, stderr_data = analyzesBuffer(shell, display_ont_info_command)
                print("Saída do comando 'display_ont_info_command':")
                print(recv_data)

                # Extração do ID da ONU via regex
                match = re.search(r'ONT-ID\s+:\s+(\d+)', recv_data)
                if match:
                    ont_id = match.group(1)
                    print(f"ID da ONT: {ont_id}")

                    # Comandos para configurar os service-ports
                    service_port_commands = [
                        "config\n",
                        f"service-port vlan {vlanMGMT[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanMGMT[1]} multi-service user-vlan {vlanMGMT[0]} tag-transform translate\n\n",
                        f"service-port vlan {vlanPPPOE[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanPPPOE[1]} multi-service user-vlan {vlanPPPOE[0]} tag-transform translate\n\nquit\n"
                    ]
                    

                    for command in service_port_commands:
                        print("Cheguei aqui")
                        recv_data, stderr_data = analyzesBuffer(shell, command)
                        print(f"Saída do comando 'service_port_command':")
                        print(recv_data)
                else:
                    print(f"Não foi possível obter o ID da ONT para o serial {serial}")

except paramiko.SSHException as ex:
    print(f"Erro ao estabelecer conexão SSH: {ex}")

except Exception as ex:
    print(f"Ocorreu um erro: {ex}")

finally:
    try:
        shell.close()
    except:
        pass
    print("Conexão SSH fechada")
