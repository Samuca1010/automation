import pandas as pd
import os
import codecs
import numpy as np

def encontrar_olts_sem_parks(caminho_arquivo):
    """Encontra OLTs sem 'PARKS', agrupando por ponto_acesso."""
    try:
        if not os.path.exists(caminho_arquivo):
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho_arquivo}")

        with codecs.open(caminho_arquivo, 'r', encoding='utf-8-sig') as arquivo:
            linhas = arquivo.readlines()
            linhas_a_pular = 0
            for linha in linhas:
                if linha.strip() == "":
                    linhas_a_pular += 1
                else:
                    break
        print(f"Linhas a pular: {linhas_a_pular}")

        with codecs.open(caminho_arquivo, 'r', encoding='utf-8-sig') as arquivo:
            df = pd.read_csv(arquivo, skiprows=linhas_a_pular, usecols=[0, 1], names=["fabricante", "ponto_acesso"], engine='python', header=None, sep=None, na_values=['', 'A definir', np.nan])
        
        df.columns = [col.lower() for col in df.columns]

        # Agrupamento e verificação Otimizada
        olts_sem_parks = []
        for olt, grupo in df.groupby('ponto_acesso'):
            if not (grupo['fabricante'] == 'PARKS').any():
                olts_sem_parks.append(olt)

        return olts_sem_parks

    except FileNotFoundError as e:
        print(f"Erro: Arquivo não encontrado: {e}")
        return None
    except pd.errors.ParserError as e:
        print(f"Erro: Erro ao analisar o CSV. Verifique o delimitador e a formatação do arquivo: {e}")
        return None
    except Exception as e:
        print(f"Erro: Ocorreu um erro inesperado: {e}")
        return None

# Exemplo de uso
caminho_arquivo = "C:/Users/Telecom/Downloads/relatorio_onus_olt.csv"
olts_sem_parks = encontrar_olts_sem_parks(caminho_arquivo)

if olts_sem_parks is not None:
    if olts_sem_parks:
        print("\nOLTs sem fabricante PARKS:")
        for olt in olts_sem_parks:
            print(olt)
    else:
        print("\nTodas as OLTs possuem pelo menos um fabricante PARKS.")
else:
    print("\nNão foi possível processar o arquivo.")