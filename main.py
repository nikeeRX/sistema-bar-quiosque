from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text

app = FastAPI()

# --- NOVA CONEXÃO HTTP (PARA PULAR FIREWALL DE EMPRESA) ---
# Se a senha real for Somdeboas2026, substitua abaixo. Note o .zykgsosahlavullteema no usuário.
DATABASE_URL = "postgresql://postgres.zykgsosahlavullteema:Somdeboas23@aws-0-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require"
engine = create_engine(DATABASE_URL)

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return """
    <body style="background:#004795; font-family:Arial; display:flex; justify-content:center; align-items:center; height:100vh;">
        <form action="/login" method="post" style="background:white; padding:30px; border-radius:10px; border:3px solid #f0ba00;">
            <h2 style="color:#e21c21; text-align:center;">QUIOSQUE LOGIN</h2>
            <input name="username" placeholder="Usuário" required style="display:block; width:100%; margin:10px 0; padding:10px;">
            <input name="password" type="password" placeholder="Senha" required style="display:block; width:100%; margin:10px 0; padding:10px;">
            <button style="width:100%; background:#e21c21; color:white; padding:10px; border:none; cursor:pointer; font-weight:bold;">ENTRAR</button>
        </form>
    </body>
    """

@app.post("/login")
async def do_login(username: str = Form(...), password: str = Form(...)):
    try:
        with engine.connect() as conn:
            query = text("SELECT * FROM usuarios WHERE username = :u AND password = :p")
            user = conn.execute(query, {"u": username, "p": password}).fetchone()
            if user:
                return RedirectResponse(url="/estoque", status_code=303)
            return HTMLResponse("<script>alert('Acesso Negado'); window.location.href='/';</script>")
    except Exception as e:
        return f"Erro de Conexão: Tabela não encontrada ou senha incorreta. ({str(e)})"

@app.get("/estoque", response_class=HTMLResponse)
async def area_estoque():
    # Busca produtos para listar na tela
    lista_html = ""
    with engine.connect() as conn:
        produtos = conn.execute(text("SELECT * FROM produtos ORDER BY nome")).fetchall()
        for p in produtos:
            promo_tag = "<span style='color:red;'>🔥 PROMO</span>" if p.em_promocao else ""
            lista_html += f"<tr><td>{p.codigo_barras}</td><td>{p.nome} {promo_tag}</td><td>R$ {p.preco_venda}</td><td><b>{p.estoque_atual}</b></td></tr>"

    return f"""
    <body style="background:#004795; color:white; font-family:Arial; padding:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #f0ba00;">
            <h1>CONTROLE DE ESTOQUE - QUIOSQUE</h1>
            <a href="/" style="color:white; text-decoration:none;">SAIR (ESC)</a>
        </div>
        
        <div style="background:white; color:#333; padding:20px; border-radius:8px; margin-top:20px;">
            <h3>CADASTRAR PRODUTO (Estoque Real e Promoção)</h3>
            <form action="/cadastrar" method="post" style="display:flex; gap:10px; flex-wrap:wrap;">
                <input name="cod" placeholder="Código" required style="padding:8px; width:150px;">
                <input name="nome" placeholder="Nome/Descrição" required style="padding:8px; width:250px;">
                <input name="preco" placeholder="Preço (Ex: 12.50)" required style="padding:8px; width:120px;">
                <input name="qtd" placeholder="Estoque Inicial" required style="padding:8px; width:120px;">
                <label style="color:#333"><input type="checkbox" name="promo"> Item em Promoção?</label>
                <button style="background:green; color:white; padding:8px 15px; border:none; cursor:pointer; font-weight:bold;">SALVAR</button>
            </form>
            <hr style="margin:20px 0;">
            <table border="1" style="width:100%; text-align:left; border-collapse:collapse;">
                <tr style="background:#ddd;">
                    <th style="padding:10px;">Cód</th>
                    <th style="padding:10px;">Produto</th>
                    <th style="padding:10px;">Preço</th>
                    <th style="padding:10px;">Estoque</th>
                </tr>
                {lista_html}
            </table>
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
        return f"Erro ao cadastrar produto: {str(e)}"
