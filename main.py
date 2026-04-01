from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text

app = FastAPI()

# URL Direta - Porta 5432 (A que funcionou!)
DATABASE_URL = "postgresql://postgres:Somdeboas2026@db.zykgsosahlavullteema.supabase.co:5432/postgres?sslmode=require"
engine = create_engine(DATABASE_URL)

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return """
    <body style="background:#004795; font-family:Arial; display:flex; justify-content:center; align-items:center; height:100vh;">
        <form action="/login" method="post" style="background:white; padding:30px; border-radius:10px; border:3px solid #f0ba00;">
            <h2 style="color:#e21c21; text-align:center;">QUIOSQUE LOGIN</h2>
            <input name="username" placeholder="Usuário" style="display:block; width:100%; margin:10px 0; padding:10px;">
            <input name="password" type="password" placeholder="Senha" style="display:block; width:100%; margin:10px 0; padding:10px;">
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
        return f"Erro Interno: {str(e)}"

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
        <h1>CONTROLE DE ESTOQUE - QUIOSQUE</h1>
        <div style="background:white; color:#333; padding:20px; border-radius:8px;">
            <h3>CADASTRAR PRODUTO</h3>
            <form action="/cadastrar" method="post" style="display:flex; gap:10px; flex-wrap:wrap;">
                <input name="cod" placeholder="Código" required>
                <input name="nome" placeholder="Nome/Descrição" required>
                <input name="preco" placeholder="Preço" required>
                <input name="qtd" placeholder="Estoque Inicial" required>
                <label style="color:#333"><input type="checkbox" name="promo"> Promoção?</label>
                <button style="background:green; color:white;">SALVAR</button>
            </form>
            <hr>
            <table border="1" style="width:100%; text-align:left;">
                <tr style="background:#ddd;"><th>Cód</th><th>Produto</th><th>Preço</th><th>Estoque</th></tr>
                {lista_html}
            </table>
        </div>
    </body>
    """

@app.post("/cadastrar")
async def cadastrar(cod: str = Form(...), nome: str = Form(...), preco: float = Form(...), qtd: int = Form(...), promo: bool = Form(False)):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO produtos (codigo_barras, nome, preco_venda, estoque_atual, em_promocao) VALUES (:c, :n, :p, :q, :pr)"),
                     {"c":cod, "n":nome, "p":preco, "q":qtd, "pr":promo})
    return RedirectResponse(url="/estoque", status_code=303)
