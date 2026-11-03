from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from starlette.background import BackgroundTask
import os
import uuid

from processador_txt import limpar_relatorio_datasus
from extrator_excel import transformar_txt_em_xlsx

app = FastAPI(title="Conversor DATASUS")

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
        <title>Conversor DATASUS</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { background-color: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center; width: 380px; }
            h2 { color: #333; margin-bottom: 10px; font-size: 22px; }
            p { color: #666; font-size: 14px; margin-bottom: 20px; line-height: 1.4; }
            
            input[type="file"] { display: none; }
            .custom-file-upload { border: 1px solid #ccc; display: inline-block; padding: 10px 15px; cursor: pointer; background-color: #f8f9fa; border-radius: 5px; font-size: 14px; color: #333; transition: 0.3s; width: 85%; margin-top: 10px; }
            .custom-file-upload:hover { background-color: #e2e6ea; border-color: #b3b3b3; }
            .file-name { display: block; margin-top: 8px; font-size: 12px; color: #888; margin-bottom: 15px; height: 15px; }
            
            .btn-green { background-color: #28a745; color: white; border: none; padding: 12px; border-radius: 5px; font-size: 16px; cursor: pointer; width: 100%; font-weight: 600; transition: 0.2s; }
            .btn-green:hover { background-color: #218838; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Conversor de Relatório DATASUS</h2>
            <p>Envie o relatório TXT bruto. O sistema limpará as rejeições, reconstruirá valores cortados e gerará a planilha Excel automaticamente.</p>
            <form action="/api/processar-completo" method="post" enctype="multipart/form-data">
                <label for="file-upload" class="custom-file-upload">Escolha arquivo</label>
                <input type="file" id="file-upload" name="file" accept=".txt" required onchange="updateFileName(this)">
                <span id="file-name" class="file-name">Nenhum arquivo escolhido</span>
                
                <button type="submit" class="btn-green">Limpar e Gerar Planilha</button>
            </form>
        </div>

        <script>
            function updateFileName(input) {
                const fileName = input.files.length > 0 ? input.files[0].name : "Nenhum arquivo escolhido";
                document.getElementById('file-name').textContent = fileName;
            }
        </script>
    </body>
    </html>
    """
    return html_content

@app.post("/api/processar-completo")
async def processar_completo(file: UploadFile = File(...)):
    pasta_temp = "arquivos_temp"
    os.makedirs(pasta_temp, exist_ok=True)
    
    id_unico = str(uuid.uuid4())
    caminho_bruto = os.path.join(pasta_temp, f"bruto_{id_unico}.txt")
    caminho_limpo = os.path.join(pasta_temp, f"limpo_{id_unico}.txt")
    caminho_excel = os.path.join(pasta_temp, f"dados_{id_unico}.xlsx")
    
    # 1. Salva o TXT original enviado pelo usuário
    with open(caminho_bruto, "wb") as buffer:
        buffer.write(await file.read())
        
    # 2. Executa a Etapa 1: Limpa o TXT e recalcula Apresentados
    limpar_relatorio_datasus(caminho_bruto, caminho_limpo)
    
    # 3. Executa a Etapa 2: Lê o TXT já limpo e transforma em Excel (.xlsx)
    transformar_txt_em_xlsx(caminho_limpo, caminho_excel)
    
    # 4. Agenda a destruição dos 3 arquivos após a conclusão do download
    tarefa_limpeza = BackgroundTask(
        remover_arquivos_temporarios, 
        [caminho_bruto, caminho_limpo, caminho_excel]
    )
    
    nome_base = os.path.splitext(file.filename)[0]
    
    return FileResponse(
        path=caminho_excel, 
        filename=f"tabela_{nome_base}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=tarefa_limpeza
    )