import paramiko
import re
import time

host = ''
user = ''
password = ''
PON = "2"
slotCard = "0/1"
vlanMGMT = (201, 200)
vlanPPPOE = (202, 201)
lineProfileID = "80"
lineProfileLEGADO = "82"
srvProfileID = "2"
vlanLEGADA = (3000, 205)

def read_serials(file_path):
    serials = []
    
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            match = re.search(r'onu \d+ type \S+ sn (\S+)', line)
            if match:
                serials.append(match.group(1))
    
    print(serials) 
    return serials

def analyzesBuffer(shell, command):
    shell.send(command)
    recv_data = ""
    stderr_data = ""
    
    while not recv_data.endswith('#'):
        if shell.recv_ready():
            recv_data += shell.recv(100000).decode()
        if shell.recv_stderr_ready():
            stderr_data += shell.recv_stderr(100000).decode()
        if 'error' in stderr_data.lower() or 'failure' in stderr_data.lower():
            raise Exception(stderr_data)
        time.sleep(0.1)
    return recv_data, stderr_data

try:
    print("Conectando-se ao equipamento...")
    with paramiko.SSHClient() as ssh:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, password=password)
        print("Conexão SSH estabelecida.")

        shell = ssh.invoke_shell()

        file_path = r"C:\Users\Telecom\Documents\teste-ztetson.txt"
        serials = read_serials(file_path)

        if not serials:
            print("Nenhum serial válido encontrado no arquivo.")
        else:
            # Variável para controlar se o "enable" e "config" foram enviados
            first_iteration = True

            for serial in serials:
                print(f"Processando serial: {serial}")

                # Comando para adicionar a ONU
                if first_iteration:
                    add_ont_command = (
                        "enable\n"
                        "config\n"
                        f"interface gpon {slotCard}\n"
                        f"ont add {PON} sn-auth {serial} omci ont-lineprofile-id {lineProfileLEGADO} "
                        f"ont-srvprofile-id {srvProfileID}\n\nquit\n"
                    )
                    first_iteration = False 
                else:
                    add_ont_command = (
                        "config\n"
                        f"interface gpon {slotCard}\n"
                        f"ont add {PON} sn-auth {serial} omci ont-lineprofile-id {lineProfileLEGADO} "
                        f"ont-srvprofile-id {srvProfileID}\n\nquit\n"
                    )

                try:
                    recv_data, stderr_data = analyzesBuffer(shell, add_ont_command)
                    print("Saída do comando 'add_ont_command':")
                    print(recv_data)
                except Exception as e:
                    if "SN already exists" in str(e):
                        print(f"Serial {serial} já existe, ignorando.")
                        continue
                    else:
                        print(f"Ocorreu um erro ao adicionar o serial {serial}: {e}")
                        continue

                display_ont_info_command = f"display ont info by-sn {serial} | no-more\n\n"
                recv_data, stderr_data = analyzesBuffer(shell, display_ont_info_command)
                print("Saída do comando 'display_ont_info_command':")
                print(recv_data)

                match = re.search(r'ONT-ID\s+:\s+(\d+)', recv_data)
                if match:
                    ont_id = match.group(1)
                    print(f"ID da ONT: {ont_id}")

                    service_port_commands = [
                        f"service-port vlan {vlanLEGADA[0]} gpon {slotCard}/{PON} ont {ont_id} "
                        f"gemport {vlanLEGADA[1]} multi-service user-vlan {vlanLEGADA[0]} tag-transform translate\n\nquit\n"
                    ]

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
