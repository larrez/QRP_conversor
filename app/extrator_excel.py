import re
import pandas as pd
from openpyxl.utils import get_column_letter

def transformar_txt_em_xlsx(caminho_entrada, caminho_saida):
    with open(caminho_entrada, 'r', encoding='latin-1') as file:
        linhas = file.readlines()

    dados_excel = []
    
    competencia = "Não identificada"
    ignorar_bloco = False
    cnes_atual = None
    nome_hospital = None
    apres = None
    aprov = None

    padrao_moeda = re.compile(r'\b\d{1,3}(?:\.\d{3})*,\d{2}\b')

    for linha in linhas:
        if "Competência:" in linha:
            match_comp = re.search(r'Competência:\s*(\d{2}/\d{4})', linha)
            if match_comp:
                competencia = match_comp.group(1)
        
        if 'Total do Município' in linha or 'Total do Gestor' in linha:
            ignorar_bloco = True
            cnes_atual = None  
            continue
        
        match_cnes = re.match(r'^\s*(\d{7})\s+-\s+(.*?)\s+(\d+)\s+(\d+)\s*$', linha)
        if match_cnes:
            ignorar_bloco = False  
            cnes_atual = match_cnes.group(1)
            nome_hospital = match_cnes.group(2).strip()
            apres = match_cnes.group(3)
            aprov = match_cnes.group(4)
            continue
        
        if not ignorar_bloco and cnes_atual:
            if linha.strip().startswith('Total'):
                valores = padrao_moeda.findall(linha)
                
                if len(valores) >= 3:
                    # Captura apenas os valores "Próprios" e o Total, ignorando "Terceiros"
                    if len(valores) == 3:
                        hosp_prop, prof_prop, total_cnes = valores[0], valores[1], valores[2]
                    elif len(valores) >= 5:
                        hosp_prop, prof_prop, total_cnes = valores[0], valores[2], valores[-1]
                    else:
                        hosp_prop, prof_prop, total_cnes = valores[0], valores[1], valores[-1]

                    dados_excel.append({
                        "Competência": competencia,
                        "CNES": cnes_atual,
                        "Nome do Hospital": nome_hospital,
                        "Apresentados": apres,
                        "Aprovados": aprov,
                        "Serv. Hospitalar": hosp_prop,
                        "Serv. Profissional": prof_prop,
                        "Total CNES": total_cnes
                    })
                    
                    cnes_atual = None

    # Cria a tabela de dados
    df = pd.DataFrame(dados_excel)

    # Inicia a gravação do arquivo Excel aplicando formatação
    with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatório')
        worksheet = writer.sheets['Relatório']

        # Itera por todas as colunas para ajustar a largura automaticamente
        for i, col in enumerate(df.columns):
            # Encontra o maior tamanho de texto na coluna (dados vs título)
            tamanho_maximo_dado = df[col].astype(str).str.len().max()
            tamanho_cabecalho = len(col)
            largura_ideal = max(tamanho_maximo_dado, tamanho_cabecalho) + 2 # +2 para dar uma margem visual
            
            # Converte o índice numérico da coluna para letra (ex: 1 -> A, 2 -> B)
            letra_coluna = get_column_letter(i + 1)
            
            # Aplica a largura na planilha
            worksheet.column_dimensions[letra_coluna].width = largura_ideal