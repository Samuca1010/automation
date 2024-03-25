import paramiko
import re
import time

host = '192.168.73.4'
user = 'root'
password = '******'
PON = "12"
slotCard = "0/1"
vlanMGMT = (240, 2)
vlanPPPOE = (160, 1)
vlanVOIP = (161, 10)
lineProfileID = "1"

try:
    print("Conectando-se ao equipamento")
    with paramiko.SSHClient() as ssh:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(host, username=user, password=password)
        print("Conexão SSH estabelecida.")

        shell = ssh.invoke_shell()

        def analyzesBuffer(command):
            shell.send(command)
            start_time = time.time()
            recv_data = ""
            while not recv_data.endswith('#'):
                if shell.recv_ready():
                    recv_data += shell.recv(100000).decode()
                    start_time = time.time()
                    if "error" in recv_data.lower():
                        raise Exception("Erro ao rodar o código")
                    start_time = time.time()
                else:
                    if time.time() - start_time > 1.0: 
                        break 
                    time.sleep(0.1)
            return recv_data

        display_command = (
            "enable\n"
            f"display current-configuration | section include gpon {slotCard} "
            f"| include \"ont add {PON}\" | no-more\n\n"
        )

        recv_data = analyzesBuffer(display_command)

        print("Saída do comando 'display_command':")
        print(recv_data)

        ont_ids = re.findall(r'ont add \d+ (\d+)', recv_data)

        print("IDs de ONT encontrados:")
        for ont_id in ont_ids:
            print(f"ID da ONT: {ont_id}")

            display_service_command = f"display current-configuration | section include service-port | include \"gpon {slotCard}/{PON} ont {ont_id}\"\n\n"
            recv_data = analyzesBuffer(display_service_command)

            print("Saída do comando 'display_service_command':")
            print(recv_data)

            service_port_ids = re.findall(r'service-port (\d+)', recv_data)

            print("IDs dos service-ports encontrados:")
            print(service_port_ids)

            undo_commands = []

            for i, service_port_id in enumerate(service_port_ids):
                if i == 0:
                    undo_commands.append(f"config\nundo service-port {service_port_id}\n")
                else:
                    undo_commands.append(f"undo service-port {service_port_id}\n")

            for undo_command in undo_commands:
                recv_data = analyzesBuffer(undo_command)
                print(recv_data)

            interface_gpon_command = f"interface gpon {slotCard}\n"
            ont_modify_command = f"ont modify {PON} {ont_id} ont-lineprofile-id {lineProfileID}\n\nquit\n"

          
            add_service_commands = []
            num_lines = len(service_port_ids)

            if num_lines == 2:
                add_service_commands.append(f"service-port vlan {vlanMGMT[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanMGMT[1]} multi-service user-vlan {vlanMGMT[0]} tag-transform translate\n\n")
                add_service_commands.append(f"service-port vlan {vlanPPPOE[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanPPPOE[1]} multi-service user-vlan {vlanPPPOE[0]} tag-transform translate\n\nquit\n")

            elif num_lines == 3:
                add_service_commands.append(f"service-port vlan {vlanMGMT[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanMGMT[1]} multi-service user-vlan {vlanMGMT[0]} tag-transform translate\n\n")
                add_service_commands.append(f"service-port vlan {vlanPPPOE[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanPPPOE[1]} multi-service user-vlan {vlanPPPOE[0]} tag-transform translate\n\n")
                add_service_commands.append(f"service-port vlan {vlanVOIP[0]} gpon {slotCard}/{PON} ont {ont_id} gemport {vlanVOIP[1]} multi-service user-vlan {vlanVOIP[0]} tag-transform translate\n\nquit\n")

            
            all_commands = [interface_gpon_command, ont_modify_command] + add_service_commands
            for command in all_commands:
                recv_data = analyzesBuffer(command)
                print(f"Comando enviado: {recv_data}")

except paramiko.SSHException as ex:
    print(f"Erro ao estabelecer conexão SSH: {ex}")

except Exception as ex:
    print(f"Ocorreu um erro: {ex}")

finally:
    shell.close()    
    print("Conexão SSH fechada")
