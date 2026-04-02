from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware
from datetime import date

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_secret")

# --- CONEXÃO OFICIAL ---
DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

CSS = """
<style>
    :root { --azul: #004795; --vermelho: #e21c21; --dourado: #f0ba00; --gelo: #f4f4f4; }
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', Arial; background: var(--azul); margin: 0; color: white; min-height: 100vh; display: flex; flex-direction: column; }
    .main-container { flex: 1; display: flex; align-items: center; justify-content: center; padding: 20px; width: 100%; }
    .card { background: white; color: #333; padding: 25px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); width: 100%; max-width: 850px; text-align: center; }
    .btn { display: block; width: 100%; padding: 15px; margin: 10px 0; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; text-decoration: none; font-size: 16px; transition: 0.2s; text-align: center; }
    .btn-azul { background: var(--azul); color: white; }
    .btn-vermelho { background: var(--vermelho); color: white; }
    input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; color: #333; }
    th, td { padding: 12px; border-bottom: 1px solid #eee; text-align: left; }
    .b-vendas { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; margin-top: 15px; }
    .prod-card { background: #fff; border: 2px solid #ddd; padding: 10px; border-radius: 10px; cursor: pointer; transition: 0.3s; color: #333; }
    .prod-card:hover { border-color: var(--vermelho); transform: scale(1.05); }
    .gift-icon { font-size: 20px; cursor: help; }
</style>
"""

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return f"<html><head>{CSS}</head><body><div class='main-container'><div class='card'><img src='https://logodownload.org/wp-content/uploads/2014/07/brahma-logo-2.png' width='120'><h2>Quiosque Riacho Mall</h2><form action='/login' method='post'><input name='user' placeholder='Usuário'><input name='pw' type='password' placeholder='Senha'><button class='btn btn-azul'>ENTRAR</button></form></div></div></body></html>"

@app.post("/login")
async def login(request: Request, user: str = Form(...), pw: str = Form(...)):
    if (user == "admin" and pw == "1234") or (user == "garcom" and pw == "chopp") or (user == "portaria" and pw == "riacho"):
        request.session["user"] = user
        return RedirectResponse(url="/central", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.get("/central", response_class=HTMLResponse)
async def central(request: Request):
    if "user" not in request.session: return RedirectResponse(url="/")
    return f"<html><head>{CSS}</head><body><div class='main-container'><div class='card'><h3>Painel de Controle</h3><a href='/cadastro' class='btn btn-vermelho'>➕ NOVO CADASTRO</a><a href='/buscar' class='btn btn-azul'>🔍 BUSCAR CLIENTE / ABRIR COMANDA</a><a href='/vendas' class='btn btn-azul' style='background:#555'>🛒 IR PARA VENDAS</a><br><a href='/' style='color:gray; text-decoration:none;'>Sair</a></div></div></body></html>"

@app.get("/buscar", response_class=HTMLResponse)
async def tela_busca(q: str = ""):
    resultados = ""
    hoje = date.today().strftime("%m-%d") # Mês e dia atual
    if q:
        with engine.connect() as conn:
            query = conn.execute(text("SELECT nome_completo, cpf, data_nascimento FROM clientes WHERE nome_completo ILIKE :q OR cpf LIKE :q"), {"q": f"%{q}%"}).fetchall()
            for r in query:
                nasc_str = r.data_nascimento.strftime("%d/%m") if r.data_nascimento else "--/--"
                is_bday = r.data_nascimento.strftime("%m-%d") == hoje if r.data_nascimento else False
                gift = " <span class='gift-icon' title='Aniversariante do Dia!'>🎁</span>" if is_bday else ""
                
                resultados += f"""<tr>
                    <td>{r.nome_completo}{gift}</td>
                    <td>{nasc_str}</td>
                    <td><form action='/abrir-existente' method='post' style='display:flex; gap:5px;'>
                        <input type='hidden' name='cpf' value='{r.cpf}'>
                        <input name='p' placeholder='Nº Pulseira' required style='margin:0; padding:5px; width:100px;'>
                        <button class='btn-vermelho' style='padding:5px 10px; border-radius:5px; border:none; cursor:pointer;'>ABRIR</button>
                    </form></td>
                </tr>"""
    
    return f"""<html><head>{CSS}</head><body><div class='main-container'><div class='card'>
    <h2>Buscar Cliente {gift if 'gift' in locals() else ''}</h2>
    <form method='get'><input name='q' placeholder='Nome ou CPF...' value='{q}'><button class='btn btn-azul'>PESQUISAR</button></form>
    <table><tr><th>Nome</th><th>Nasc.</th><th>Ação</th></tr>{resultados if resultados else "<tr><td colspan='3'>Aguardando busca...</td></tr>"}</table>
    <br><a href='/central' style='color:gray;'>Voltar</a></div></div></body></html>"""

@app.post("/abrir-existente")
async def abrir_existente(cpf: str = Form(...), p: str = Form(...)):
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta) VALUES (:p, :c, 7.00)"), {"p": p, "c": cpf})
        return HTMLResponse(f"<script>alert('✅ Comanda {p} aberta!'); window.location.href='/vendas';</script>")
    except: return "Erro: Pulseira já ativa!"

@app.get("/vendas", response_class=HTMLResponse)
async def tela_vendas(cat: str = "Chopps"):
    menu = {
        "Chopps": [("Caneca 350ml", 11.90), ("Tulipa 700ml", 17.90), ("Torre 2.5L", 84.90)],
        "Cervejas": [("Original 600ml", 12.90), ("Spaten LN", 8.90), ("Heineken 600ml", 16.90)],
        "Petiscos": [("Batata Frita", 21.90), ("Frango Passarinho", 28.90), ("Carne de Sol", 54.90)]
    }
    prod_html = "".join([f"<div class='prod-card' onclick='lancar(\"{n}\", {p})'><b>{n}</b><br><span style='color:red'>R$ {p}</span></div>" for n, p in menu.get(cat, [])])

    return f"""<html><head>{CSS}
    <script>
        function lancar(n, v) {{
            let p = prompt("Nº da Pulseira para lançar " + n + ":");
            if(p) window.location.href = `/lancar?p=${{p}}&v=${{v}}&i=${{n}}`;
        }}
    </script>
    </head><body><div class='main-container' style='flex-direction:column;'>
        <div class='card' style='max-width:1000px;'>
            <div style='display:flex; gap:10px; margin-bottom:15px;'>
                <a href='/vendas?cat=Chopps' class='btn btn-azul'>🍺 CHOPPS</a>
                <a href='/vendas?cat=Cervejas' class='btn btn-azul'>🍾 CERVEJAS</a>
                <a href='/vendas?cat=Petiscos' class='btn btn-azul'>🍟 PETISCOS</a>
            </div>
            <div class='b-vendas'>{prod_html}</div>
            <br><a href='/central' class='btn btn-vermelho' style='max-width:200px; margin: 0 auto;'>VOLTAR</a>
        </div>
    </div></body></html>"""

@app.get("/lancar")
async def lancar(p: str, v: float, i: str):
    with engine.begin() as conn:
        conn.execute(text("UPDATE pulseiras SET total_conta = total_conta + :v WHERE numero_pulseira = :p"), {"v": v, "p": p})
    return HTMLResponse(f"<script>alert('✅ {i} lançado na pulseira {p}!'); window.location.href='/vendas';</script>")

@app.get("/cadastro", response_class=HTMLResponse)
async def tela_cadastro():
    return f"""<html><head>{CSS}</head><body><div class='main-container'><div class='card' style='text-align:left;'>
    <h2 style='text-align:center;'>Novo Cadastro</h2>
    <form action='/salvar-novo' method='post'>
        <input name='nome' placeholder='Nome Completo' required>
        <input name='cpf' placeholder='CPF' required>
        <label>Nascimento:</label><input name='nasc' type='date' required>
        <input name='pulseira' placeholder='Nº DA PULSEIRA' required style='border: 2px solid orange;'>
        <button class='btn btn-vermelho'>CADASTRAR E ABRIR COMANDA</button>
    </form><a href='/central' style='display:block; text-align:center; color:gray;'>Voltar</a></div></div></body></html>"""

@app.post("/salvar-novo")
async def salvar_novo(nome: str = Form(...), cpf: str = Form(...), nasc: str = Form(...), pulseira: str = Form(...)):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO clientes (nome_completo, cpf, data_nascimento) VALUES (:n, :c, :d) ON CONFLICT (cpf) DO NOTHING"), {"n":nome, "c":cpf, "d":nasc})
        conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta) VALUES (:p, :c, 7.00)"), {"p":pulseira, "c":cpf})
    return HTMLResponse(f"<script>alert('✅ Cliente e Pulseira {pulseira} ativos!'); window.location.href='/vendas';</script>")
