import re

# Caracteres de controle ilegais para o openpyxl/XML (exceto \t, \n, \r, que são válidos)
REGEX_CARACTERES_ILEGAIS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

def limpar_relatorio_datasus(caminho_entrada, caminho_saida):

    with open(caminho_entrada, 'r', encoding='latin-1') as file:
        linhas = file.readlines()

    linhas_formatadas = []
    
    for linha in linhas:
        # 0. Remove caracteres de controle invisíveis (ex: \x0c de quebra de página)
        #    Substitui por espaço para não desalinhar as colunas
        linha = REGEX_CARACTERES_ILEGAIS.sub(' ', linha)

        linha = linha.replace('%', ' ')
        linha = linha.replace('rejeição', '        ')
        linha = linha.replace('(www.gnostice.com)', '                  ')

        if re.match(r'^\s*\d{7}\s+-', linha):
            linha = re.sub(r'(^\s*\d{7}\s+-.+?\s+\d+\s+\d+)\s+\d{1,3},\d{2}(\s*.*)$', r'\1\2', linha)

        if 'Total' in linha:
            linha = re.sub(r'(Total\s+\d+\s+\d+)\s+\d{1,3},\d{2}(\s+)', r'\1\2', linha)

        linhas_formatadas.append(linha)

    with open(caminho_saida, 'w', encoding='latin-1') as file:
        file.writelines(linhas_formatadas)