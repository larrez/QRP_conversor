#uvicorn main:app --reload

import re

def limpar_relatorio_datasus(caminho_entrada, caminho_saida):
    # Utilizamos 'latin-1' para evitar o erro de caracteres especiais (como o 'ç')
    with open(caminho_entrada, 'r', encoding='latin-1') as file:
        linhas = file.readlines()

    linhas_formatadas = []
    
    for linha in linhas:
        # 1. Limpeza Global de Cabeçalhos e Artefactos de Conversão
        # Substitui o símbolo '%' por um espaço, independentemente de onde esteja flutuando
        linha = linha.replace('%', ' ')
        
        # Remove a palavra 'rejeição', substituindo por espaços para manter o alinhamento do cabeçalho
        linha = linha.replace('rejeição', '        ')
        
        # Remove a marca d'água do software de PDF para não desalinhar as linhas de dados
        linha = linha.replace('(www.gnostice.com)', '                  ')

        # 2. Limpeza da linha do Hospital (CNES)
        # Identifica linhas que começam com o código do CNES (7 dígitos + traço)
        if re.match(r'^\s*\d{7}\s+-', linha):
            # O regex abaixo procura a sequência: [Texto do Hospital] -> [Inteiro Apres] -> [Inteiro Aprov].
            # Se logo a seguir existir um número decimal do tipo X,XX (a percentagem), ele apaga-o.
            # Se não existir (como no caso do Sta Maria em Araripina), a linha fica intacta.
            linha = re.sub(r'(^\s*\d{7}\s+-.+?\s+\d+\s+\d+)\s+\d{1,3},\d{2}(\s*.*)$', r'\1\2', linha)

        # 3. Limpeza da linha de 'Total'
        # Identifica a linha de Total e remove a percentagem de rejeição (ex: 1,20) antes dos valores financeiros
        if 'Total' in linha:
            # Captura o texto até ao valor de 'Aprov' (Grupo 1) e os espaços a seguir à percentagem (Grupo 2).
            # A percentagem (ex: \d{1,3},\d{2}) é ignorada/apagada na substituição, puxando o valor financeiro.
            linha = re.sub(r'(Total\s+\d+\s+\d+)\s+\d{1,3},\d{2}(\s+)', r'\1\2', linha)

        linhas_formatadas.append(linha)

    # Guarda o ficheiro final limpo
    with open(caminho_saida, 'w', encoding='latin-1') as file:
        file.writelines(linhas_formatadas)