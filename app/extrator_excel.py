import re
import pandas as pd
from openpyxl.utils import get_column_letter

PADRAO_MOEDA = re.compile(r'\b\d{1,3}(?:\.\d{3})*,\d{2}\b')
PADRAO_CNES = re.compile(r'^\s*(\d{7})\s+-\s+(.*?)\s+(\d+)\s+(\d+)\s*$')
PADRAO_LETRAS = re.compile(r'[A-Za-zÀ-ÿ]')


def _valores_com_posicao(linha):
    """Retorna [(coluna_final_do_valor, 'texto_do_valor'), ...] de uma linha."""
    return [(m.end(), m.group()) for m in PADRAO_MOEDA.finditer(linha)]


def _extrair_totais_cnes(linhas_bloco):
    """
    Localiza a linha 'Total' do hospital e devolve (hosp_prop, prof_prop, total_cnes).

    Em alguns blocos o PDF/relatório quebra a linha 'Total' em pedaços: o rótulo
    fica sozinho (ou com só o 1º valor) e os demais valores caem numa linha
    anterior, sem rótulo. Nesse caso juntamos os pedaços e ordenamos pela posição
    horizontal, que é a ordem real das colunas.
    """
    idx_total = next(
        (i for i, l in enumerate(linhas_bloco) if l.strip().startswith('Total')), None
    )
    if idx_total is None:
        return None

    candidatos = _valores_com_posicao(linhas_bloco[idx_total])

    if len(candidatos) < 3:
        # Linha 'Total' fragmentada: procura valores órfãos entre 'Complemento Local' e 'Total'
        idx_local = max(
            (i for i, l in enumerate(linhas_bloco[:idx_total])
             if l.strip().startswith('Complemento Local')),
            default=-1
        )
        for linha in linhas_bloco[idx_local + 1:idx_total]:
            if not PADRAO_LETRAS.search(linha):
                candidatos += _valores_com_posicao(linha)
        candidatos.sort(key=lambda c: c[0])

    valores = [v for _, v in candidatos]
    if len(valores) < 3:
        return None

    # Captura apenas os valores "Próprios" e o Total, ignorando "Terceiros"
    if len(valores) == 3:
        return valores[0], valores[1], valores[2]
    elif len(valores) >= 5:
        return valores[0], valores[2], valores[-1]
    return valores[0], valores[1], valores[-1]


def _para_float(valor_br):
    return float(valor_br.replace('.', '').replace(',', '.'))


def transformar_txt_em_xlsx(caminho_entrada, caminho_saida):
    with open(caminho_entrada, 'r', encoding='latin-1') as file:
        linhas = file.readlines()

    # --- 1. Divide o relatório em blocos, um por hospital ---
    blocos = []
    bloco_atual = None
    competencia = "Não identificada"

    for linha in linhas:
        if "Competência:" in linha:
            match_comp = re.search(r'Competência:\s*(\d{2}/\d{4})', linha)
            if match_comp:
                competencia = match_comp.group(1)

        if 'Total do Município' in linha or 'Total do Gestor' in linha:
            bloco_atual = None   # tudo daqui até o próximo hospital é total agregado
            continue

        match_cnes = PADRAO_CNES.match(linha)
        if match_cnes:
            bloco_atual = {
                "competencia": competencia,
                "cnes": match_cnes.group(1),
                "nome": match_cnes.group(2).strip(),
                "apres": match_cnes.group(3),
                "aprov": match_cnes.group(4),
                "linhas": [],
            }
            blocos.append(bloco_atual)
            continue

        if bloco_atual is not None:
            bloco_atual["linhas"].append(linha)

    # --- 2. Extrai os totais de cada hospital ---
    dados_excel = []
    avisos = []

    for b in blocos:
        totais = _extrair_totais_cnes(b["linhas"])
        if totais is None:
            avisos.append(f"CNES {b['cnes']} ({b['nome']}): linha 'Total' não encontrada/incompleta")
            continue

        hosp_prop, prof_prop, total_cnes = totais

        # Confere: Hospitalar + Profissional deve fechar com o Total
        if abs(_para_float(hosp_prop) + _para_float(prof_prop) - _para_float(total_cnes)) > 0.01:
            avisos.append(f"CNES {b['cnes']} ({b['nome']}): {hosp_prop} + {prof_prop} != {total_cnes}")

        dados_excel.append({
            "Competência": b["competencia"],
            "CNES": b["cnes"],
            "Nome do Hospital": b["nome"],
            "Apresentados": b["apres"],
            "Aprovados": b["aprov"],
            "Serv. Hospitalar": hosp_prop,
            "Serv. Profissional": prof_prop,
            "Total CNES": total_cnes
        })

    for aviso in avisos:
        print(f"[AVISO] {aviso}")

    # Cria a tabela de dados
    df = pd.DataFrame(dados_excel)

    # Inicia a gravação do arquivo Excel aplicando formatação
    with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatório')
        worksheet = writer.sheets['Relatório']

        # Itera por todas as colunas para ajustar a largura automaticamente
        for i, col in enumerate(df.columns):
            tamanho_maximo_dado = df[col].astype(str).str.len().max()
            tamanho_cabecalho = len(col)
            largura_ideal = max(tamanho_maximo_dado, tamanho_cabecalho) + 2

            letra_coluna = get_column_letter(i + 1)
            worksheet.column_dimensions[letra_coluna].width = largura_ideal

    return avisos