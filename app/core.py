import subprocess
import os

def converter_qrp_para_csv(caminho_qrp: str, caminho_csv: str) -> bool:
    """
    invoca o CLI em delphi para converter um arquivo qrp em csv
    """
    cli_path = os.path.abspath(os.path.join( 'cli', 'qrp2csv.exe'))

    comando = [cli_path, caminho_qrp, caminho_csv]

    try: 
        resultado = subprocess.run(comando, capture_output = True, text = True, timeout = 30)
        if resultado.returncode == 0:
            return True
        else:
            print(f"Erro no CLI delphi: {resultado.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("Erro: O processo de conversão excedeu o tempo limite.")
        return False
    except FileNotFoundError:
        print(f"Erro: O arquivo {cli_path} não foi encontrado.")
        return False
    