from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text

app = FastAPI()

# Na Railway, a conexão padrão funciona de primeira!
DATABASE_URL = "postgresql://postgres:8eb8lVhLxEZIQjU7@db.zykgsosahlavullteema.supabase.co:5432/postgres?sslmode=require"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

@app.get("/", response_class=HTMLResponse)
async def area_estoque():
    lista_html = ""
    status_conexao = "<b style='color:green;'>✅ Banco Conectado</b>"
    
    try:
        with engine.connect() as conn:
            produtos = conn.execute(text("SELECT * FROM produtos ORDER BY nome")).fetchall()
            if not produtos:
                lista_html = "<tr><td colspan='4' style='padding:10px;'>Nenhum produto no banco.</td></tr>"
            for p in produtos:
                promo_tag = "<b style='color:#e21c21;'>[PROMO]</b>" if p.em_promocao else ""
                lista_html += f"<tr><td style='padding:10px;'>{p.codigo_barras}</td><td style='padding:10px;'>{p.nome} {promo_tag}</td><td style='padding:10px;'>R$ {p.preco_venda}</td><td style='padding:10px;'>{p.estoque_atual}</td></tr>"
    except Exception as e:
        status_conexao = f"<b style='color:red;'>❌ Erro de Conexão: {str(e)[:50]}...</b>"
        lista_html = "<tr><td colspan='4' style='padding:10px;'>Erro ao carregar dados. Tente atualizar a página.</td></tr>"

    return f"""
    <body style="background:#004795; color:white; font-family:Arial; padding:20px; margin:0;">
        <div style="max-width:900px; margin:auto; background:white; color:#333; padding:25px; border-radius:15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:3px solid #f0ba00; padding-bottom:10px;">
                <h1 style="color:#004795; margin:0;">📦 Painel de Estoque</h1>
                <div>{status_conexao}</div>
            </div>
            
            <h3 style="margin-top:20px;">Cadastrar Novo Item</h3>
            <form action="/cadastrar" method="post" style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px;">
                <input name="cod" placeholder="Código de Barras" required style="padding:10px;">
                <input name="nome" placeholder="Nome do Produto" required style="padding:10px;">
                <input name="preco" placeholder="Preço (Ex: 15,90)" required style="padding:10px;">
                <input name="qtd" placeholder="Qtd Inicial" type="number" required style="padding:10px;">
                <label style="display:flex; align-items:center; gap:5px;"><input type="checkbox" name="promo"> Em Promoção?</label>
                <button style="background:#28a745; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer; padding:10px;">SALVAR PRODUTO</button>
            </form>

            <h3 style="margin-top:30px;">Inventário Real</h3>
            <table border="1" style="width:100%; border-collapse:collapse; text-align:left;">
                <tr style="background:#f0ba00; color:#004795;">
                    <th style="padding:10px;">Cód</th>
                    <th style="padding:10px;">Descrição</th>
                    <th style="padding:10px;">Valor</th>
                    <th style="padding:10px;">Estoque</th>
                </tr>
                {lista_html}
            </table>
        </div>
    </body>
    """

@app.post("/cadastrar")
async def cadastrar(cod: str = Form(...), nome: str = Form(...), preco: str = Form(...), qtd: int = Form(...), promo: bool = Form(False)):
    try:
        # TRATAMENTO DA VÍRGULA: Transforma 15,90 em 15.90 antes de salvar
        preco_limpo = float(preco.replace(',', '.'))
        
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO produtos (codigo_barras, nome, preco_venda, estoque_atual, em_promocao) VALUES (:c, :n, :p, :q, :pr)"),
                         {"c":cod, "n":nome, "p":preco_limpo, "q":qtd, "pr":promo})
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        return f"<h3>Erro ao salvar:</h3><p>{str(e)}</p><a href='/'>Voltar e tentar usar PONTO no preço</a>"
