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
vlanMGMT_VOIP = (240, 203)
vlanPPPOE_VOIP = (160, 202)
vlanVOIP = (161, 204)
lineProfileID = "5"
srvProfileID = "1"
lineProfileID_VOIP = "81"

# Funções para leitura e filtragem dos seriais
def filter_Serials(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
        print(f"Total de linhas lidas: {len(lines)}")
        
        filtered_lines = []
        for line in lines:
            line = line.strip().upper()
            if line.startswith("ONU"):
                parts = line.split()
                if len(parts) > 1 and (parts[1].startswith("HWTC")):
                    serial = parts[1]
                    # Procurar pelo flow-profile
                    flow_profile_match = re.search(r'FLOW-PROFILE\s+(\S+)', line, re.IGNORECASE)
                    if flow_profile_match:
                        flow_profile = flow_profile_match.group(1).lower()
                    else:
                        flow_profile = None
                    filtered_lines.append((serial, flow_profile))
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
    print("Conectando-se ao equipamento...")
    with paramiko.SSHClient() as ssh:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, password=password)
        print("Conexão SSH estabelecida.")

        shell = ssh.invoke_shell()

        file_path = r"C:\Users\Telecom\Downloads\OLT-64-PERFIS-HUAWEI.txt"
        serials_and_profiles = filter_Serials(file_path)
        
        if not serials_and_profiles:
            print("Nenhum serial válido encontrado no arquivo.")
        else:
            # Flag para controlar quando executar o comando "enable"
            enable_executed = False  

            for serial, flow_profile in serials_and_profiles:
                print(f"Processando serial: {serial} com flow-profile: {flow_profile}")

                # Definir o lineProfileID de acordo se for router ou router voip
                if flow_profile in ["router_1g_huawei", "router_1g_huawei_default_voip", "router_1g_huawei_telefonia"]:
                    lineProfileID_current = lineProfileID_VOIP
                elif flow_profile in ["router_1g_huawei_dados", "router_1g_huawei_default"]:
                    lineProfileID_current = lineProfileID
                else:
                    print(f"Perfil incorreto para o serial: {serial} ont pulando")
                    continue

                # Montando o comando para add ont
                if not enable_executed:
                    add_ont_command = (
                        "enable\n"
                        "config\n"
                        f"interface gpon {slotCard}\n"
                        f"ont add {PON} sn-auth {serial} omci ont-lineprofile-id {lineProfileID_current} ont-srvprofile-id {srvProfileID} desc 'milene_cristina_toloto_sattis_2'\n\n"
                        "quit\n"
                        "quit\n"
                    )
                    enable_executed = True
                else:
                    add_ont_command = (
                        "config\n"
                        f"interface gpon {slotCard}\n"
                        f"ont add {PON} sn-auth {serial} omci ont-lineprofile-id {lineProfileID_current} ont-srvprofile-id {srvProfileID} desc 'milene_cristina_toloto_sattis_2'\n\n"
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

                    # Montando comandos para configurar os services
                    if flow_profile in ["router_1g_huawei", "router_1g_huawei_default_voip", "router_1g_huawei_telefonia"]:
                        service_port_commands = [
                            "config\n",
                            f"service-port vlan {vlanMGMT_VOIP[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanMGMT_VOIP[1]} multi-service user-vlan {vlanMGMT_VOIP[0]} tag-transform translate\n\n",
                            f"service-port vlan {vlanPPPOE_VOIP[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanPPPOE_VOIP[1]} multi-service user-vlan {vlanPPPOE_VOIP[0]} tag-transform translate\n\n",
                            f"service-port vlan {vlanVOIP[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanVOIP[1]} multi-service user-vlan {vlanVOIP[0]} tag-transform translate\n\nquit\n"
                        ]
                    else:
                        service_port_commands = [
                            "config\n",
                            f"service-port vlan {vlanMGMT[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanMGMT[1]} multi-service user-vlan {vlanMGMT[0]} tag-transform translate\n\n",
                            f"service-port vlan {vlanPPPOE[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanPPPOE[1]} multi-service user-vlan {vlanPPPOE[0]} tag-transform translate\n\nquit\n"
                        ]
                    #
                    for command in service_port_commands:
                        print("Executando comando:", command)
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
