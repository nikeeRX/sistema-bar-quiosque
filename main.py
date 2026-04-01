from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text

app = FastAPI()

# --- CONEXÃO DEFINITIVA (AJUSTADA PARA O MODO TRANSACTION) ---
# Substitua SUA_SENHA_NOVA pela senha que você resetou no passo anterior
DATABASE_URL = "postgresql://postgres.zykgsosahlavullteema:SUA_SENHA_NOVA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require&supavisor_session_id=1"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return """
    <body style="background:#004795; font-family:Arial; display:flex; justify-content:center; align-items:center; height:100vh; margin:0;">
        <form action="/login" method="post" style="background:white; padding:30px; border-radius:15px; border:4px solid #f0ba00; width:300px; text-align:center;">
            <img src="https://logodownload.org/wp-content/uploads/2014/04/brahma-logo-1.png" width="80">
            <h2 style="color:#e21c21; margin:15px 0;">SISTEMA QUIOSQUE</h2>
            <input name="username" placeholder="Usuário" required style="width:100%; margin:10px 0; padding:12px; border:1px solid #ccc; border-radius:5px;">
            <input name="password" type="password" placeholder="Senha" required style="width:100%; margin:10px 0; padding:12px; border:1px solid #ccc; border-radius:5px;">
            <button style="width:100%; background:#e21c21; color:white; padding:12px; border:none; border-radius:5px; cursor:pointer; font-weight:bold; font-size:16px;">ENTRAR</button>
        </form>
    </body>
    """

@app.post("/login")
async def do_login(username: str = Form(...), password: str = Form(...)):
    try:
        with engine.connect() as conn:
            # Busca o usuário exato que inserimos via SQL no Supabase
            query = text("SELECT * FROM usuarios WHERE username = :u AND password = :p")
            user = conn.execute(query, {"u": username, "p": password}).fetchone()
            if user:
                return RedirectResponse(url="/estoque", status_code=303)
            return HTMLResponse("<script>alert('Usuário ou Senha Incorretos!'); window.location.href='/';</script>")
    except Exception as e:
        return f"<h3>Erro Crítico de Conexão:</h3><p>{str(e)}</p><br><a href='/'>Voltar e tentar novamente</a>"

@app.get("/estoque", response_class=HTMLResponse)
async def area_estoque():
    lista_html = ""
    try:
        with engine.connect() as conn:
            produtos = conn.execute(text("SELECT * FROM produtos ORDER BY nome")).fetchall()
            for p in produtos:
                promo_tag = "<b style='color:#e21c21;'>[PROMO]</b>" if p.em_promocao else ""
                lista_html += f"<tr><td>{p.codigo_barras}</td><td>{p.nome} {promo_tag}</td><td>R$ {p.preco_venda}</td><td>{p.estoque_atual}</td></tr>"
    except:
        lista_html = "<tr><td colspan='4'>Nenhum produto encontrado. Cadastre o primeiro abaixo!</td></tr>"

    return f"""
    <body style="background:#004795; color:white; font-family:Arial; padding:20px;">
        <div style="max-width:900px; margin:auto; background:white; color:#333; padding:25px; border-radius:15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
            <h1 style="color:#004795; border-bottom:3px solid #f0ba00; padding-bottom:10px;">📦 Gestão de Estoque</h1>
            
            <h3 style="margin-top:20px;">Cadastrar Novo Item</h3>
            <form action="/cadastrar" method="post" style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px;">
                <input name="cod" placeholder="Código de Barras" required style="padding:10px;">
                <input name="nome" placeholder="Nome do Produto" required style="padding:10px;">
                <input name="preco" placeholder="Preço (Ex: 15.90)" required style="padding:10px;">
                <input name="qtd" placeholder="Qtd Inicial" type="number" required style="padding:10px;">
                <label style="display:flex; align-items:center; gap:5px;"><input type="checkbox" name="promo"> Em Promoção?</label>
                <button style="background:#28a745; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">SALVAR PRODUTO</button>
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
            <br>
            <a href="/" style="color:#e21c21; font-weight:bold;">Sair do Sistema</a>
        </div>
    </body>
    """

@app.post("/cadastrar")
async def cadastrar(cod: str = Form(...), nome: str = Form(...), preco: float = Form(...), qtd: int = Form(...), promo: bool = Form(False)):
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO produtos (codigo_barras, nome, preco_venda, estoque_atual, em_promocao) VALUES (:c, :n, :p, :q, :pr)"),
                         {"c":cod, "n":nome, "p":preco, "q":qtd, "pr":promo})
        return RedirectResponse(url="/estoque", status_code=303)
    except Exception as e:
        return f"Erro ao salvar no banco: {str(e)}"
