from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text

app = FastAPI()

# --- SUA URL DA RAILWAY (Mantenha a que deu certo!) ---
DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

@app.get("/", response_class=HTMLResponse)
async def area_estoque():
    lista_html = ""
    status_conexao = "<b style='color:green;'>✅ Banco Conectado</b>"
    
    try:
        with engine.connect() as conn:
            produtos = conn.execute(text("SELECT * FROM produtos ORDER BY nome")).fetchall()
            if not produtos:
                lista_html = "<tr><td colspan='5' style='padding:15px; text-align:center;'>Estoque vazio.</td></tr>"
            for p in produtos:
                lista_html += f"""
                <tr style='border-bottom: 1px solid #ddd;'>
                    <td style='padding:12px;'>{p.codigo_barras}</td>
                    <td style='padding:12px;'><b>{p.nome}</b></td>
                    <td style='padding:12px; color:#28a745; font-weight:bold;'>R$ {p.preco_venda}</td>
                    <td style='padding:12px; font-weight:bold;'>{p.estoque_atual} un.</td>
                    <td style='padding:12px; display:flex; gap:5px;'>
                        <form action='/ajustar/{p.id}/mais' method='post'><button style='background:#28a745; color:white; border:none; padding:5px 10px; cursor:pointer; border-radius:3px;'>+</button></form>
                        <form action='/ajustar/{p.id}/menos' method='post'><button style='background:#ffc107; color:black; border:none; padding:5px 10px; cursor:pointer; border-radius:3px;'>-</button></form>
                        <form action='/deletar/{p.id}' method='post'><button style='background:#dc3545; color:white; border:none; padding:5px 10px; cursor:pointer; border-radius:3px;'>🗑️</button></form>
                    </td>
                </tr>
                """
    except Exception as e:
        status_conexao = f"<b style='color:red;'>❌ Erro: {str(e)[:30]}</b>"

    return f"""
    <body style="background:#f0f2f5; font-family:Arial; padding:20px;">
        <div style="max-width:1000px; margin:auto; background:white; padding:25px; border-radius:15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:3px solid #004795; padding-bottom:10px; margin-bottom:20px;">
                <h1 style="color:#004795; margin:0;">🍺 Sistema de Estoque - Quiosque Brahma Riacho Mall</h1>
                {status_conexao}
            </div>
            
            <h3>Cadastrar Novo Item</h3>
            <form action="/cadastrar" method="post" style="display:grid; grid-template-columns: 2fr 2fr 1fr 1fr 1fr; gap:10px; margin-bottom:30px;">
                <input name="cod" placeholder="Cód. Barras" required style="padding:10px; border-radius:5px; border:1px solid #ccc;">
                <input name="nome" placeholder="Produto" required style="padding:10px; border-radius:5px; border:1px solid #ccc;">
                <input name="preco" placeholder="Preço (6,50)" required style="padding:10px; border-radius:5px; border:1px solid #ccc;">
                <input name="qtd" type="number" placeholder="Qtd" required style="padding:10px; border-radius:5px; border:1px solid #ccc;">
                <button style="background:#004795; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">SALVAR</button>
            </form>

            <table style="width:100%; border-collapse:collapse;">
                <tr style="background:#004795; color:white; text-align:left;">
                    <th style="padding:12px;">Cód</th><th style="padding:12px;">Nome</th><th style="padding:12px;">Preço</th><th style="padding:12px;">Qtd</th><th style="padding:12px;">Ações</th>
                </tr>
                {lista_html}
            </table>
        </div>
    </body>
    """

@app.post("/cadastrar")
async def cadastrar(cod: str = Form(...), nome: str = Form(...), preco: str = Form(...), qtd: int = Form(...)):
    try:
        p_limpo = float(preco.replace(',', '.'))
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO produtos (codigo_barras, nome, preco_venda, estoque_atual) VALUES (:c, :n, :p, :q)"), {"c":cod, "n":nome, "p":p_limpo, "q":qtd})
        return RedirectResponse(url="/", status_code=303)
    except: return "Erro ao salvar."

@app.post("/ajustar/{item_id}/{acao}")
async def ajustar(item_id: int, acao: str):
    operacao = "+ 1" if acao == "mais" else "- 1"
    with engine.begin() as conn:
        conn.execute(text(f"UPDATE produtos SET estoque_atual = estoque_atual {operacao} WHERE id = :id"), {"id": item_id})
    return RedirectResponse(url="/", status_code=303)

@app.post("/deletar/{item_id}")
async def deletar(item_id: int):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM produtos WHERE id = :id"), {"id": item_id})
    return RedirectResponse(url="/", status_code=303)
