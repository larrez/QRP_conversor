#uvicorn main:app --reload

import re

REGEX_CARACTERES_ILEGAIS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

# Cabeçalho completo:  CNES - Nome   Apresentados   Aprovados   % rejeição
REGEX_CABECALHO_COMPLETO = re.compile(
    r'(^\s*\d{7}\s+-.+?\s+)(\d+)(\s+)(\d+)\s+(\d{1,3},\d{2})(\s*.*)$'
)
# Cabeçalho com a coluna Apresentados ausente:  CNES - Nome   Aprovados   % rejeição
REGEX_CABECALHO_SEM_APRESENTADOS = re.compile(
    r'(^\s*\d{7}\s+-.+?\s+)(\d+)\s+(\d{1,3},\d{2})(\s*.*)$'
)


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


def reconstruir_apresentados_ausente(match):
    """
    Trata cabeçalhos de hospital em que a coluna 'Apresentados' sumiu da linha
    (sobram só 'Aprovados' e '% rejeição'). Reconstrói 'Apresentados' a partir
    dessas duas colunas e devolve o cabeçalho no formato completo.
    """
    prefixo = match.group(1)
    aprov_str = match.group(2)
    rejeicao_str = match.group(3)
    sufixo = match.group(4)

    aprovados = int(aprov_str)
    taxa_aprovacao = 100.0 - float(rejeicao_str.replace(',', '.'))

    if taxa_aprovacao > 0:
        apres_corrigido = str(round((aprovados * 100.0) / taxa_aprovacao))
    else:
        # 100% de rejeição: não dá para reconstruir; mantém o único valor disponível
        apres_corrigido = aprov_str

    return f"{prefixo}{apres_corrigido}    {aprov_str}{sufixo}"


def limpar_relatorio_datasus(caminho_entrada, caminho_saida):

    with open(caminho_entrada, 'r', encoding='latin-1') as file:
        linhas_brutas = file.readlines()

    # Pré-passo: reconstrói linhas de CNES caso o OneView quebre o nome do hospital em 2 linhas
    linhas = []
    i = 0
    while i < len(linhas_brutas):
        linha_atual = linhas_brutas[i]
        # Se começa com CNES (7 dígitos + traço), mas não tem a % de rejeição na mesma linha
        if re.match(r'^\s*\d{7}\s+-', linha_atual) and not re.search(r'\d{1,3},\d{2}', linha_atual):
            if i + 1 < len(linhas_brutas):
                linha_atual = linha_atual.rstrip('\r\n') + ' ' + linhas_brutas[i + 1].lstrip()
                i += 1
        linhas.append(linha_atual)
        i += 1

    linhas_formatadas = []
    
    for linha in linhas:

        linha = REGEX_CARACTERES_ILEGAIS.sub(' ', linha)

        # Proteção contra exportação acidental com Separator Mode (#) do manual antigo
        linha = linha.replace('#', ' ')
        linha = linha.replace('%', ' ')
        linha = linha.replace('rejeição', '        ')
        
        # Remove qualquer menção ao domínio ou marca d'água gnostice
        linha = re.sub(r'\(?www\.gnostice\.com\)?|gnostice', '                  ', linha, flags=re.IGNORECASE)

        # 1. Linhas de Hospital (CNES): recalcula Apresentados e remove a % de rejeição
        if re.match(r'^\s*\d{7}\s+-', linha):
            linha, n = REGEX_CABECALHO_COMPLETO.subn(recalcular_apresentados, linha)
            if n == 0:
                linha = REGEX_CABECALHO_SEM_APRESENTADOS.sub(reconstruir_apresentados_ausente, linha)

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