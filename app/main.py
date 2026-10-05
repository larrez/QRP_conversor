from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from starlette.background import BackgroundTask
import os
import uuid

from processador_txt import limpar_relatorio_datasus
from extrator_excel import transformar_txt_em_xlsx

app = FastAPI(title="Painel DATASUS - Seguro")

# --- FUNÇÃO DE SEGURANÇA (AUTODESTRUIÇÃO) ---
def remover_arquivos_temporarios(caminhos: list):
    """Varre a lista de caminhos e deleta os arquivos físicos do servidor."""
    for caminho in caminhos:
        try:
            if os.path.exists(caminho):
                os.remove(caminho)
                print(f"[SEGURANÇA] Arquivo destruído: {caminho}")
        except Exception as e:
            print(f"[ERRO] Falha ao remover {caminho}: {e}")

@app.get("/", response_class=HTMLResponse)
async def pagina_inicial():
    html_content = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Painel DATASUS</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .container { display: flex; gap: 20px; }
            .card { background-color: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center; width: 350px; }
            h2 { color: #333; margin-bottom: 10px; font-size: 22px; }
            p { color: #666; font-size: 14px; margin-bottom: 20px; }
            input[type=file] { margin: 15px 0; padding: 10px; border: 1px dashed #ccc; width: 90%; cursor: pointer; }
            .btn-blue { background-color: #007bff; color: white; border: none; padding: 12px; border-radius: 5px; font-size: 16px; cursor: pointer; width: 100%; margin-bottom: 10px; }
            .btn-blue:hover { background-color: #0056b3; }
            .btn-green { background-color: #28a745; color: white; border: none; padding: 12px; border-radius: 5px; font-size: 16px; cursor: pointer; width: 100%; }
            .btn-green:hover { background-color: #218838; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h2>1. Limpar Relatório (TXT)</h2>
                <p>Remove artefatos e a coluna de % de rejeição, mantendo o formato texto.</p>
                <form action="/api/limpar-txt" method="post" enctype="multipart/form-data">
                    <input type="file" name="file" accept=".txt" required>
                    <button type="submit" class="btn-blue">Processar TXT</button>
                </form>
            </div>

            <div class="card">
                <h2>2. Transformar em XLSX</h2>
                <p>Extrai valores e gera uma planilha limpa apenas com os dados dos Hospitais.</p>
                <form action="/api/gerar-excel" method="post" enctype="multipart/form-data">
                    <input type="file" name="file" accept=".txt" required>
                    <button type="submit" class="btn-green">Gerar Planilha Excel</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

@app.post("/api/limpar-txt")
async def limpar_txt(file: UploadFile = File(...)):
    pasta_temp = "arquivos_temp"
    os.makedirs(pasta_temp, exist_ok=True)
    
    id_unico = str(uuid.uuid4())
    caminho_entrada = os.path.join(pasta_temp, f"entrada_{id_unico}.txt")
    caminho_saida = os.path.join(pasta_temp, f"saida_{id_unico}.txt")
    
    with open(caminho_entrada, "wb") as buffer:
        buffer.write(await file.read())
        
    limpar_relatorio_datasus(caminho_entrada, caminho_saida)
    
    # Adiciona a tarefa de fundo diretamente na resposta do arquivo
    tarefa_limpeza = BackgroundTask(remover_arquivos_temporarios, [caminho_entrada, caminho_saida])
    
    return FileResponse(
        path=caminho_saida, 
        filename=f"limpo_{file.filename}", 
        media_type="text/plain",
        background=tarefa_limpeza
    )

@app.post("/api/gerar-excel")
async def gerar_excel(file: UploadFile = File(...)):
    pasta_temp = "arquivos_temp"
    os.makedirs(pasta_temp, exist_ok=True)
    
    id_unico = str(uuid.uuid4())
    caminho_entrada = os.path.join(pasta_temp, f"entrada_excel_{id_unico}.txt")
    caminho_saida = os.path.join(pasta_temp, f"dados_{id_unico}.xlsx")
    
    with open(caminho_entrada, "wb") as buffer:
        buffer.write(await file.read())
        
    transformar_txt_em_xlsx(caminho_entrada, caminho_saida)
    
    # Adiciona a tarefa de fundo diretamente na resposta do arquivo
    tarefa_limpeza = BackgroundTask(remover_arquivos_temporarios, [caminho_entrada, caminho_saida])
    
    return FileResponse(
        path=caminho_saida, 
        filename=f"tabela_{file.filename.replace('.txt', '.xlsx')}",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=tarefa_limpeza
    )