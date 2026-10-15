#uvicorn main:app --reload

import re

REGEX_CARACTERES_ILEGAIS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

def recalcular_apresentados(match):
    """
    Captura os grupos da linha, recalcula o valor de 'Apresentados' 
    a partir de 'Aprovados' e '% rejeição', e remove a porcentagem.
    """
    prefixo = match.group(1)        # Texto antes de Apresentados (CNES + Nome ou 'Total')
    apres_original = match.group(2) # Valor de Apresentados (mesmo que esteja cortado)
    espacos = match.group(3)        # Espaçamento entre Apresentados e Aprovados
    aprov_str = match.group(4)      # Valor íntegro de Aprovados
    rejeicao_str = match.group(5)   # Porcentagem de rejeição (ex: 1,20)
    sufixo = match.group(6)         # Restante da linha (valores financeiros ou quebra de linha)

    try:
        aprovados = int(aprov_str)
        rejeicao = float(rejeicao_str.replace(',', '.'))
        taxa_aprovacao = 100.0 - rejeicao

        # Evita divisão por zero caso exista 100% de rejeição
        if taxa_aprovacao > 0:
            apres_corrigido = str(round((aprovados * 100.0) / taxa_aprovacao))
        else:
            apres_corrigido = apres_original
    except ValueError:
        apres_corrigido = apres_original

    # Retorna a linha com o 'Apresentados' reconstruído e sem a coluna de rejeição
    return f"{prefixo}{apres_corrigido}{espacos}{aprov_str}{sufixo}"


def limpar_relatorio_datasus(caminho_entrada, caminho_saida):

    with open(caminho_entrada, 'r', encoding='latin-1') as file:
        linhas = file.readlines()

    linhas_formatadas = []
    
    for linha in linhas:

        linha = REGEX_CARACTERES_ILEGAIS.sub(' ', linha)

        linha = linha.replace('%', ' ')
        linha = linha.replace('rejeição', '        ')
        linha = linha.replace('(www.gnostice.com)', '                  ')

        # 1. Linhas de Hospital (CNES): recalcula Apresentados e remove a % de rejeição
        if re.match(r'^\s*\d{7}\s+-', linha):
            linha = re.sub(
                r'(^\s*\d{7}\s+-.+?\s+)(\d+)(\s+)(\d+)\s+(\d{1,3},\d{2})(\s*.*)$',
                recalcular_apresentados,
                linha
            )

        # 2. Linhas de Total: recalcula Apresentados e remove a % de rejeição
        if 'Total' in linha:
            linha = re.sub(
                r'(Total\s+)(\d+)(\s+)(\d+)\s+(\d{1,3},\d{2})(\s+.*)$',
                recalcular_apresentados,
                linha
            )

        linhas_formatadas.append(linha)

    with open(caminho_saida, 'w', encoding='latin-1') as file:
        file.writelines(linhas_formatadas)