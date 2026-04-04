from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware
from datetime import date
import json

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_mall_2024")

DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

MENU_INICIAL = {
    "CHOPP": [("Caneca 350ml", 11.9), ("Descartável 500ml", 13.9), ("Tulipa 700ml", 17.9), ("Torre 2.5L", 84.9), ("Torre 3.5L", 99.9)],
    "CERVEJAS": [("Original 600ml", 12.9), ("Amstel 600ml", 12.0), ("Brahma Duplo Malte", 12.0), ("Heineken 600ml", 16.9), ("Spaten LN", 8.9), ("Corona LN", 10.0), ("Heineken LN", 10.0), ("Stella LN", 8.9), ("Heineken Zero", 10.0)],
    "PETISCOS": [("Fritas", 21.9), ("Fritas c/ Queijo", 25.9), ("Fritas Cheddar/Bacon", 27.9), ("Kibe 10un", 34.9), ("Kibe c/ Queijo", 37.9), ("Frango Passarinho", 28.9), ("Carne Sol c/ Fritas", 54.9), ("Calabresa Acebolada", 22.9), ("Tábua Frios", 34.9)],
    "BEBIDAS": [("Caipirinha", 14.9), ("Caipiroska Absolut", 16.9), ("Gin Tônica", 24.9), ("Gin Tropical", 26.9), ("Cozumel 600ml", 14.9), ("Refri Lata", 4.9), ("Soda Italiana", 13.9), ("Suco Lata", 5.9), ("Red Bull", 13.0), ("Água", 3.9)]
}

# --- CRIAÇÃO DAS TABELAS BÁSICAS ---
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS clientes (id SERIAL PRIMARY KEY, nome_completo TEXT NOT NULL, cpf TEXT UNIQUE NOT NULL, data_nascimento DATE, contato TEXT, email TEXT);
        CREATE TABLE IF NOT EXISTS pulseiras (id SERIAL PRIMARY KEY, numero_pulseira TEXT NOT NULL, cliente_cpf TEXT REFERENCES clientes(cpf), total_conta DECIMAL(10,2) DEFAULT 7.00);
        CREATE TABLE IF NOT EXISTS vendas_itens (id SERIAL PRIMARY KEY, pulseira_num TEXT, item_nome TEXT, valor DECIMAL(10,2), data_venda DATE DEFAULT CURRENT_DATE, hora_venda TIME DEFAULT CURRENT_TIME);
    """))

# --- ATUALIZAÇÕES DE COLUNA NAS PULSEIRAS E VENDAS ---
MIGRACOES = [
    "ALTER TABLE pulseiras ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ABERTA';",
    "ALTER TABLE vendas_itens ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ABERTA';",
    "ALTER TABLE pulseiras DROP CONSTRAINT IF EXISTS pulseiras_numero_pulseira_key;"
]
for mig in MIGRACOES:
    try:
        with engine.begin() as conn: conn.execute(text(mig))
    except Exception: pass

# --- O RESET NUCLEAR: GARANTE A TABELA DE PRODUTOS PERFEITA ---
try:
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS produtos CASCADE;"))
        conn.execute(text("""
            CREATE TABLE produtos (
                id SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL,
                categoria TEXT DEFAULT 'OUTROS',
                preco DECIMAL(10,2) DEFAULT 0.00,
                estoque INT DEFAULT 0
            );
        """))
except Exception as e:
    pass

# --- INSERÇÃO DO CARDÁPIO COM ESTOQUE CHEIO (100 UNIDADES) ---
try:
    with engine.begin() as conn:
        for cat, itens in MENU_INICIAL.items():
            for n, p in itens:
                conn.execute(text("INSERT INTO produtos (nome, categoria, preco, estoque) VALUES (:n, :c, :p, 100) ON CONFLICT (nome) DO NOTHING"), {"n": n, "c": cat, "p": p})
except Exception as e:
    pass

CSS = """
<style>
    * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; }
    body { margin: 0; background: #0a3a7a; color: white; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
    .layout-vendas { display: flex; flex: 1; height: 100vh; }
    .menu-lateral { width: 220px; padding: 20px; display: flex; flex-direction: column; gap: 10px; border-right: 1px solid rgba(255,255,255,0.1); background: #082d5e; overflow-y:auto; }
    .btn-menu { background: #0a3a7a; color: white; border: 1px solid #1352a3; padding: 15px; border-radius: 8px; text-align: left; font-weight: bold; font-size: 15px; cursor: pointer; text-decoration: none; display: flex; justify-content: space-between; }
    .btn-menu:hover, .btn-menu.ativo { background: #d31a21; border-color: white; }
    .main-area { flex: 1; padding: 20px; display: flex; flex-direction: column; overflow-y: auto; align-items: center; }
    
    .logo-central { width: 140px; margin-bottom: 20px; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.5)); }
    .logo-peq { width: 100px; margin-bottom: 10px; }
    .logo-css { background: #d31a21; color: white; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 4px solid white; box-shadow: 0 6px 12px rgba(0,0,0,0.5); font-weight: 900; line-height: 1.1; text-transform: uppercase; font-family: 'Arial Black', sans-serif; }
    
    .grid-produtos { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; width: 100%; max-width: 900px; }
    .prod-card { border-radius: 10px; padding: 15px 10px; text-align: center; cursor: pointer; display: flex; flex-direction: column; justify-content: space-between; min-height: 120px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: 0.2s; color: white; border-width: 2px; border-style: solid; }
    .prod-card:hover { transform: scale(1.05); border-color: white; }
    .bg-green { background: linear-gradient(180deg, #28a745 0%, #1e7e34 100%); border-color: #145523; }
    .bg-red { background: linear-gradient(180deg, #d31a21 0%, #9e0b10 100%); border-color: #5a0407; opacity: 0.8; }
    .prod-card b { font-size: 14px; margin-bottom: 8px; text-shadow: 1px 1px 2px rgba(0,0,0,0.6); }
    .prod-card span { font-size: 16px; font-weight: bold; background: rgba(0,0,0,0.3); padding: 5px; border-radius: 5px; }
    .badge-estoque { font-size: 12px; margin-top: 8px; background: rgba(0,0,0,0.4); border-radius: 4px; padding: 3px; font-weight: bold; }
    .comanda-lateral { width: 340px; background: white; color: black; border-left: 5px solid #d31a21; display: flex; flex-direction: column; }
    .comanda-header { background: #d31a21; color: white; padding: 15px; font-weight: bold; text-align: center; font-size: 18px; }
    .comanda-body { flex: 1; overflow-y: auto; padding: 15px; background: #f9f9f9; }
    .secao-titulo { font-size: 12px; color: #666; text-transform: uppercase; font-weight: bold; border-bottom: 1px solid #ccc; margin-bottom: 10px; padding-bottom: 5px; }
    .item-linha { display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 8px; border-bottom: 1px dashed #ddd; padding-bottom: 5px; }
    .comanda-footer { padding: 15px; background: white; border-top: 1px solid #ccc; }
    .btn-acao { display: block; width: 100%; padding: 15px; margin-bottom: 8px; border: none; border-radius: 5px; font-weight: bold; color: white; cursor: pointer; text-align: center; text-decoration: none; font-size: 14px; background: #062b5e; }
    .btn-acao:hover { background: #0d4b9c; }
    .container-center { display: flex; align-items: center; justify-content: center; height: 100vh; padding: 20px; overflow-y: auto; }
    .card-center { background: white; color: #333; padding: 30px; border-radius: 15px; width: 100%; max-width: 650px; text-align: center; box-shadow: 0 8px 20px rgba(0,0,0,0.4); margin: auto; }
    .input-padrao { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; font-size: 16px; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th, td { padding: 8px; border-bottom: 1px solid #eee; text-align: left; vertical-align: middle; }
    
    /* LAYOUT EXATO DA IMPRESSORA TÉRMICA */
    .cupom-bg { background: #555; min-height: 100vh; display: flex; align-items: flex-start; justify-content: center; padding: 20px; margin: 0; font-family: 'Courier New', Courier, monospace; color: black; }
    .cupom { width: 300px; font-size: 12px; font-weight: bold; text-transform: uppercase; background: white; color: black; padding: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
    .cupom-head { text-align: center; margin-bottom: 10px; font-size: 13px; }
    .cupom-row { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .cupom-divider { border-top: 1px dashed #000; margin: 8px 0; }
    .cupom-bold { font-size: 14px; font-weight: 900; }
    .no-print { display: block; width: 300px; margin: 20px auto; text-align: center; background: #d31a21; color: white; padding: 15px; text-decoration: none; border-radius: 5px; font-family: sans-serif; font-size: 16px; font-weight: bold; }
    
    @media print { 
        @page { margin: 0; }
        body, html, .cupom-bg { background: white !important; margin: 0 !important; padding: 0 !important; height: auto; display: block; } 
        .cupom { width: 100% !important; max-width: 100%; border: none !important; box-shadow: none !important; margin: 0 !important; padding: 0 5px !important; }
        .no-print { display: none !important; }
        * { color: black !important; background: transparent !important; }
    }
</style>
"""

IMG_LOGO = """
<div style='display:flex; justify-content:center; margin-bottom:20px;'>
    <img src='https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Brahma_Logo.svg/512px-Brahma_Logo.svg.png' class='logo-central' style='margin:0;' onerror='this.style.display="none"; document.getElementById("fb-logo").style.display="flex";'>
    <div id='fb-logo' class='logo-css' style='display:none; width:130px; height:130px;'>
        <span style='font-size:18px; font-style:italic;'>CHOPP</span>
        <span style='font-size:26px;'>BRAHMA</span>
    </div>
</div>
"""
IMG_LOGO_PEQ = """
<div style='display:flex; justify-content:center; margin-bottom:15px;'>
    <img src='https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Brahma_Logo.svg/512px-Brahma_Logo.svg.png' class='logo-peq' style='margin:0;' onerror='this.style.display="none"; document.getElementById("fb-logo-peq").style.display="flex";'>
    <div id='fb-logo-peq' class='logo-css' style='display:none; width:90px; height:90px;'>
        <span style='font-size:12px; font-style:italic;'>CHOPP</span>
        <span style='font-size:16px;'>BRAHMA</span>
    </div>
</div>
"""

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO}<h2>Acesso Restrito</h2><form action='/login' method='post'><input class='input-padrao' name='user' placeholder='Usuário' required><input class='input-padrao' name='pw' type='password' placeholder='Senha' required><button class='btn-acao' style='padding:15px; font-size:18px;'>ENTRAR</button></form></div></div></body></html>"

@app.post("/login")
async def login(request: Request):
    form = await request.form()
    user = form.get("user", "")
    pw = form.get("pw", "")
    if (user == "admin" and pw == "1234") or (user == "garcom" and pw == "chopp"):
        request.session["user"] = user
        return RedirectResponse(url="/central", status_code=303)
    return RedirectResponse(url="/", status_code=303)

@app.get("/central", response_class=HTMLResponse)
async def central(request: Request):
    if "user" not in request.session: return RedirectResponse(url="/")
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<a href='/cadastro' class='btn-acao' style='background:#d31a21'>➕ NOVO CADASTRO</a><a href='/buscar' class='btn-acao'>🔍 BUSCAR / ABRIR COMANDA</a><a href='/vendas' class='btn-acao' style='background:#28a745'>🛒 CAIXA / VENDAS</a><a href='/estoque' class='btn-acao' style='background:#e67e22'>📦 GESTÃO DE ESTOQUE</a><a href='/fechar_conta' class='btn-acao' style='background:#333'>🔒 FECHAR CONTA</a><br><a href='/logout' style='color:gray'>Sair</a></div></div></body></html>"

@app.get("/estoque", response_class=HTMLResponse)
async def tela_estoque(request: Request):
    if "user" not in request.session or request.session["user"] != "admin": return RedirectResponse(url="/central")
    linhas = ""
    curr_cat = ""
    with engine.connect() as conn:
        prods_db = conn.execute(text("SELECT nome, categoria, preco, estoque FROM produtos ORDER BY categoria, nome")).fetchall()
        for r in prods_db:
            cat_val = r.categoria or "OUTROS"
            p_val = float(r.preco or 0)
            e_val = int(r.estoque or 0)
            if cat_val != curr_cat:
                linhas += f"<tr><td colspan='3' style='background:#082d5e; color:white; font-weight:bold; text-align:center;'>{cat_val}</td></tr>"
                curr_cat = cat_val
            
            acoes = f"""
            <div style='display:flex; gap:5px; align-items:center;'>
                <form action='/att_estoque' method='post' style='margin:0; display:flex; gap:5px;'>
                    <input type='hidden' name='i' value='{r.nome}'>
                    <input type='number' name='q' class='input-padrao' style='width:50px; margin:0; padding:5px;' required>
                    <button class='btn-acao' style='background:#28a745; margin:0; padding:8px; width:auto;' title='Adicionar Estoque'>➕</button>
                </form>
                <button class='btn-acao' style='background:#ffc107; color:black; margin:0; padding:8px; width:auto;' title='Editar' onclick='editarProd("{r.nome}", "{p_val:.2f}")'>✏️</button>
                <form action='/excluir_produto' method='post' style='margin:0;' onsubmit='return confirm("Deseja realmente EXCLUIR o item {r.nome}?");'>
                    <input type='hidden' name='nome' value='{r.nome}'>
                    <button class='btn-acao' style='background:#d31a21; margin:0; padding:8px; width:auto;' title='Excluir'>🗑️</button>
                </form>
            </div>
            """
            linhas += f"<tr><td style='color:black; line-height:1.2;'>{r.nome} <br><small style='color:#666;'>R$ {p_val:.2f}</small></td><td style='color:black; font-weight:bold; font-size:18px;'>{e_val}</td><td>{acoes}</td></tr>"
    
    add_form = f"""<div style='background:#f4f4f4; padding:20px; border-radius:10px; margin-bottom:20px; text-align:left; border:1px solid #ccc;'>
        <h3 style='margin-top:0; color:#d31a21;'>➕ CADASTRAR NOVO PRODUTO</h3>
        <form action='/novo_produto' method='post' style='display:flex; flex-wrap:wrap; gap:10px;'>
            <input name='nome' placeholder='Nome do Produto' class='input-padrao' style='flex:1; min-width:180px;' required>
            <select name='cat' class='input-padrao' style='flex:1; min-width:130px;' required>
                <option value='CHOPP'>CHOPP</option><option value='CERVEJAS'>CERVEJAS</option>
                <option value='PETISCOS'>PETISCOS</option><option value='BEBIDAS'>BEBIDAS</option>
                <option value='OUTROS'>OUTROS</option>
            </select>
            <input name='preco' type='text' placeholder='Preço (Ex: 15.90)' class='input-padrao' style='flex:1; min-width:100px;' required>
            <input name='qtd' type='number' placeholder='Estoque Inicial' class='input-padrao' style='flex:1; min-width:120px;' required>
            <button class='btn-acao' style='background:#062b5e; margin:0; width:100%;'>SALVAR PRODUTO</button>
        </form>
    </div>"""

    return f"""<html><head>{CSS}
    <script>
        function editarProd(nomeAntigo, precoAtual) {{
            let novoNome = prompt("Novo Nome do Produto:", nomeAntigo);
            if (novoNome === null) return;
            
            let novoPreco = prompt("Novo Preço (ex: 15.90 ou 15,90):", precoAtual);
            if (novoPreco === null) return;
            
            let f = document.createElement("form"); f.method = "POST"; f.action = "/editar_produto";
            let i1 = document.createElement("input"); i1.name = "nome_antigo"; i1.value = nomeAntigo; f.appendChild(i1);
            let i2 = document.createElement("input"); i2.name = "nome_novo"; i2.value = novoNome || nomeAntigo; f.appendChild(i2);
            let i3 = document.createElement("input"); i3.name = "preco"; i3.value = novoPreco || precoAtual; f.appendChild(i3);
            
            document.body.appendChild(f); f.submit();
        }}
    </script>
    </head><body><div class='container-center'><div class='card-center'><h2>Gestão de Estoque</h2>{add_form}<div style='max-height:400px; overflow-y:auto; border:1px solid #ddd;'><table><tr><th style='color:black'>Item</th><th style='color:black'>Qtd</th><th style='color:black'>Ação</th></tr>{linhas}</table></div><br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"""

@app.post("/novo_produto")
async def novo_produto(request: Request):
    try:
        form = await request.form()
        nome = form.get("nome", "").strip()
        cat = form.get("cat", "OUTROS")
        preco = form.get("preco", "0").replace(",", ".")
        qtd = form.get("qtd", "0")
        
        if not nome: return RedirectResponse(url="/estoque", status_code=303)
        
        try: p_val = float(preco)
        except: p_val = 0.0
        try: q_val = int(qtd)
        except: q_val = 0
        
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO produtos (nome, categoria, preco, estoque) VALUES (:n, :c, :p, :q)"), {"n": nome, "c": cat, "p": p_val, "q": q_val})
        return RedirectResponse(url="/estoque", status_code=303)
    except Exception as e:
        return HTMLResponse(f"<script>alert('Erro ao salvar produto. Verifique se o nome já existe! Detalhe: {e}'); window.history.back();</script>")

@app.post("/att_estoque")
async def att_estoque(request: Request):
    try:
        form = await request.form()
        i = form.get("i", "")
        q = form.get("q", "0")
        try: q_val = int(q)
        except: q_val = 0
        with engine.begin() as conn: 
            conn.execute(text("UPDATE produtos SET estoque = COALESCE(estoque, 0) + :q WHERE nome = :i"), {"i": i, "q": q_val})
        return RedirectResponse(url="/estoque", status_code=303)
    except Exception: return RedirectResponse(url="/estoque", status_code=303)

@app.post("/editar_produto")
async def editar_produto(request: Request):
    try:
        form = await request.form()
        nome_antigo = form.get("nome_antigo", "")
        nome_novo = form.get("nome_novo", "")
        preco = form.get("preco", "0").replace(",", ".")
        
        if not nome_antigo or not nome_novo: return RedirectResponse(url="/estoque", status_code=303)
        try: p_val = float(preco)
        except: p_val = 0.0
        
        with engine.begin() as conn:
            conn.execute(text("UPDATE produtos SET nome = :n_n, preco = :p WHERE nome = :n_a"), {"n_n": nome_novo.strip(), "p": p_val, "n_a": nome_antigo})
        return RedirectResponse(url="/estoque", status_code=303)
    except Exception as e:
        return HTMLResponse(f"<script>alert('Erro ao editar produto: {e}'); window.history.back();</script>")

@app.post("/excluir_produto")
async def excluir_produto(request: Request):
    try:
        form = await request.form()
        nome = form.get("nome", "")
        if nome:
            with engine.begin() as conn: 
                conn.execute(text("DELETE FROM produtos WHERE nome = :n"), {"n": nome})
    except Exception: pass
    return RedirectResponse(url="/estoque", status_code=303)

@app.get("/vendas", response_class=HTMLResponse)
async def vendas(cat: str = "CHOPP", p: str = ""):
    # Trava de Segurança: Se tentou abrir com pulseira, vamos checar se ela existe MESMO
    if p:
        with engine.connect() as conn:
            chk = conn.execute(text("SELECT id FROM pulseiras WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p}).fetchone()
            if not chk:
                return HTMLResponse(f"<script>alert('A comanda {p} não está ativa ou não existe!'); window.location.href='/vendas?cat={cat}';</script>")

    prods = ""
    with engine.connect() as conn:
        lista_prods = conn.execute(text("SELECT nome, preco, estoque FROM produtos WHERE categoria = :c ORDER BY nome"), {"c": cat}).fetchall()
        for n, v, e in lista_prods:
            v_val = float(v or 0)
            e_val = int(e or 0)
            cor = "bg-green" if e_val > 0 else "bg-red"
            prods += f"<div class='prod-card {cor}' onclick='add(\"{n}\", {v_val}, {e_val})'><b>{n}</b><span>R$ {v_val:.2f}</span><div class='badge-estoque'>Estoque: {e_val}</div></div>"
    
    itens_html = ""
    if p:
        with engine.connect() as conn:
            query_itens = conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": p}).fetchall()
            for r in query_itens: itens_html += f"<div class='item-linha'><span>{r.qtd}x {r.item_nome}</span><span>R$ {float(r.tot or 0):.2f}</span></div>"

    # NOVO LAYOUT DO CABEÇALHO (Campo de digitação numérico com Botão Acessar)
    comanda_display = f"""
        <div class='comanda-header' style='padding-bottom:15px;'>
            <div style='font-size:13px; margin-bottom:8px; color:#ffdddd;'>NÚMERO DA PULSEIRA:</div>
            <input type='number' id='input-pulseira' class='input-padrao' style='margin:0; font-weight:bold; text-align:center; color:black; padding:10px; font-size:20px;' value='{p}' placeholder='Ex: 15'>
            <button class='btn-acao' style='background:white; color:#d31a21; margin-top:10px; padding:10px; font-size:15px;' onclick='acessarComanda()'>ACESSAR COMANDA</button>
        </div>
        <div class='comanda-body'>
            <div class='secao-titulo'>Histórico de Consumo</div>
            {itens_html if p else "<div style='color:#999; text-align:center'>Nenhuma pulseira acessada</div>"}
            <br>
            <div class='secao-titulo' style='color:#d31a21'>Novo Pedido</div>
            <div id='novo-pedido'></div>
        </div>
        <div class='comanda-footer'>
            <div style='display:flex; justify-content:space-between; font-size:18px; font-weight:bold; margin-bottom:10px;'><span>Subtotal Pedido:</span><span id='tot-pedido'>R$ 0.00</span></div>
            <button class='btn-acao' style='background:#28a745; font-size:16px;' onclick='enviarPedido()'>🖨️ FINALIZAR PEDIDO</button>
            <a href='/central' class='btn-acao' style='background:#333'>Voltar</a>
        </div>
    """

    return f"""<html><head>{CSS}
    <script>
        const p_num = new URLSearchParams(window.location.search).get("p") || "";
        // Sistema de Memória Fotográfica mantido!
        let cart = JSON.parse(sessionStorage.getItem("cart_" + p_num)) || []; 
        
        function add(n, v, e){{ 
            if(!p_num) return alert("Acesse uma pulseira no campo acima primeiro!"); 
            let count = cart.filter(x => x.n === n).length;
            if (e <= 0 || count >= e) return alert("❌ Produto esgotado ou sem estoque suficiente!");
            cart.push({{n, v}}); 
            sessionStorage.setItem("cart_" + p_num, JSON.stringify(cart));
            render(); 
        }}
        function render(){{
            let html = ""; let t = 0;
            if(!p_num) return;
            cart.forEach((i, idx) => {{ 
                html += `<div class='item-linha' style='color:#d31a21; font-weight:bold;'><span>${{i.n}}</span><span>R$ ${{i.v.toFixed(2)}} <b onclick='rem(${{idx}})' style='cursor:pointer; color:black; font-size:16px; margin-left:8px;'>X</b></span></div>`; 
                t += i.v; 
            }});
            document.getElementById('novo-pedido').innerHTML = html; 
            document.getElementById('tot-pedido').innerText = "R$ " + t.toFixed(2);
        }}
        function rem(idx) {{ 
            cart.splice(idx, 1); 
            sessionStorage.setItem("cart_" + p_num, JSON.stringify(cart));
            render(); 
        }}
        function enviarPedido() {{
            if(!p_num || cart.length === 0) return alert("Adicione itens ao pedido antes de finalizar!");
            let f = document.createElement("form"); f.method = "POST"; f.action = "/lancar_pedido"; f.target = "_blank";
            let i1 = document.createElement("input"); i1.name = "p"; i1.value = p_num; f.appendChild(i1);
            let i2 = document.createElement("input"); i2.name = "itens"; i2.value = JSON.stringify(cart); f.appendChild(i2);
            document.body.appendChild(f); 
            
            // Limpa a memória após enviar com sucesso
            sessionStorage.removeItem("cart_" + p_num);
            f.submit(); 
            setTimeout(() => window.location.reload(), 1500);
        }}
        function acessarComanda() {{
            let val = document.getElementById('input-pulseira').value;
            if(!val) return alert("Digite o número da pulseira no campo primeiro!");
            window.location.href=`/vendas?cat={cat}&p=${{val}}`;
        }}
        window.onload = render;
    </script>
    </head><body><div class='layout-vendas'>
        <div class='menu-lateral'>
            <a href='/vendas?cat=CHOPP&p={p}' class='btn-menu {"ativo" if cat=="CHOPP" else ""}'>🍺 CHOPP</a>
            <a href='/vendas?cat=CERVEJAS&p={p}' class='btn-menu {"ativo" if cat=="CERVEJAS" else ""}'>🍾 CERVEJAS</a>
            <a href='/vendas?cat=PETISCOS&p={p}' class='btn-menu {"ativo" if cat=="PETISCOS" else ""}'>🍟 PETISCOS</a>
            <a href='/vendas?cat=BEBIDAS&p={p}' class='btn-menu {"ativo" if cat=="BEBIDAS" else ""}'>🍹 BEBIDAS</a>
            <a href='/vendas?cat=OUTROS&p={p}' class='btn-menu {"ativo" if cat=="OUTROS" else ""}'>📦 OUTROS</a>
        </div>
        <div class='main-area'>
            {IMG_LOGO}
            <h2 style='margin-bottom:20px; font-size:24px;'>CARDÁPIO - {cat}</h2>
            <div class='grid-produtos'>{prods}</div>
        </div>
        <div class='comanda-lateral'>{comanda_display}</div>
    </div></body></html>"""

@app.post("/lancar_pedido", response_class=HTMLResponse)
async def lancar_pedido(request: Request):
    form = await request.form()
    p = form.get("p", "")
    itens = form.get("itens", "")
    if not p or not itens: return "Sem itens"
    
    lista = json.loads(itens)
    if not lista: return "Sem itens"
    tot = sum(i['v'] for i in lista)
    linhas_cupom = ""
    
    try:
        with engine.begin() as conn:
            chk = conn.execute(text("SELECT id FROM pulseiras WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p}).fetchone()
            if not chk: return HTMLResponse("<script>alert('Comanda não encontrada ou fechada!'); window.close();</script>")
            conn.execute(text("UPDATE pulseiras SET total_conta = total_conta + :t WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"t": tot, "p": p})
            for i in lista:
                conn.execute(text("INSERT INTO vendas_itens (pulseira_num, item_nome, valor, status) VALUES (:p, :n, :v, 'ABERTA')"), {"p": p, "n": i['n'], "v": i['v']})
                conn.execute(text("UPDATE produtos SET estoque = GREATEST(COALESCE(estoque, 0) - 1, 0) WHERE nome = :n"), {"n": i['n']})
                linhas_cupom += f"<div class='cupom-row'><span>1x {i['n']}</span><span>{float(i['v']):.2f}</span></div>"
    except Exception: pass
    
    return f"""<html class='cupom-bg'><body onload='window.print();'><div class='cupom'>
        <div class='cupom-head'><b>QUIOSQUE CHOPP BRAHMA</b><br>TICKET DE PREPARO<br>PULSEIRA: <b>{p}</b></div>
        <div class='cupom-divider'></div>
        <div class='cupom-row cupom-bold'><span>QTD ITEM</span><span>VALOR</span></div>
        <div class='cupom-divider'></div>
        {linhas_cupom}
        <div class='cupom-divider'></div>
        <div class='cupom-row cupom-bold'><span>TOTAL PEDIDO</span><span>R$ {tot:.2f}</span></div>
        <div class='cupom-divider'></div>
        <div style='text-align:center; margin-top:10px; font-size:11px;'>VIA DE PREPARO</div>
    </div></body></html>"""

@app.get("/fechar_conta", response_class=HTMLResponse)
async def fechar_conta(q: str = ""):
    res = ""
    if q:
        q = q.strip()
        with engine.connect() as conn:
            query = conn.execute(text("SELECT p.numero_pulseira, p.total_conta, c.nome_completo FROM pulseiras p JOIN clientes c ON p.cliente_cpf = c.cpf WHERE (p.numero_pulseira = :q OR c.cpf = :q) AND p.status = 'ABERTA'"), {"q": q}).fetchone()
            if query:
                itens_q = conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": query.numero_pulseira}).fetchall()
                lista = "".join([f"<div class='item-linha'><span>{i.qtd}x {i.item_nome}</span><span>R$ {float(i.tot or 0):.2f}</span></div>" for i in itens_q])
                lista += f"<div class='item-linha'><span>1x Couvert Artístico</span><span>R$ 7.00</span></div>"
                
                subtotal = float(query.total_conta or 0)
                taxa = subtotal * 0.10
                total_final = subtotal + taxa
                res = f"""<div style='background:#f4f4f4; padding:20px; border-radius:10px; color:#333; margin-top:20px; text-align:left;'>
                    <h3 style='text-align:center; margin-bottom:5px;'>{query.nome_completo}</h3>
                    <p style='text-align:center; margin-top:0; font-weight:bold'>Pulseira: {query.numero_pulseira}</p>
                    <div style='background:white; padding:15px; border-radius:8px; max-height:220px; overflow-y:auto; border:1px solid #ddd;'>{lista}</div>
                    <div style='padding-top:15px; font-size:16px;'>
                        <div class='item-linha'><span>Subtotal Consumo:</span><span>R$ {subtotal:.2f}</span></div>
                        <div class='item-linha'><span>Taxa Serviço (10%):</span><span>R$ {taxa:.2f}</span></div>
                        <div class='item-linha' style='font-weight:bold; font-size:20px; color:#d31a21'><span>TOTAL:</span><span>R$ {total_final:.2f}</span></div>
                        <div class='item-linha' style='margin-top:10px;'><span>Dividir por:</span><input type='number' id='divisores' value='1' min='1' style='width:60px; text-align:center; border:1px solid #ccc; border-radius:3px; font-weight:bold;' oninput='calcDiv()'></div>
                        <div class='item-linha' style='font-weight:bold; font-size:18px;'><span>Por Pessoa:</span><span id='val_pessoa'>R$ {total_final:.2f}</span></div>
                    </div>
                    <form action='/confirmar_fechamento' method='post' target='_blank' onsubmit='setTimeout(()=>window.location.href="/central", 1500)'>
                        <input type='hidden' name='p' value='{query.numero_pulseira}'>
                        <input type='hidden' name='divisao' id='input_div' value='1'>
                        <button class='btn-acao' style='background:#28a745; font-size:18px; margin-top:15px;'>🖨️ CONFIRMAR E IMPRIMIR RECIBO</button>
                    </form>
                    <script>
                        function calcDiv() {{
                            let div = parseInt(document.getElementById('divisores').value) || 1;
                            let tot = {total_final}; document.getElementById('val_pessoa').innerText = "R$ " + (tot / div).toFixed(2);
                            document.getElementById('input_div').value = div;
                        }}
                    </script>
                </div>"""
            else: res = "<p style='color:red;'>Nenhuma comanda aberta localizada para essa busca.</p>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Fechar Conta</h2><form method='get'><input class='input-padrao' name='q' placeholder='CPF ou Nº Pulseira' value='{q}' required><button class='btn-acao'>CONSULTAR CONTA</button></form>{res}<br><a href='/central' style='color:gray'>Voltar</a></div></div></body></html>"

@app.post("/confirmar_fechamento", response_class=HTMLResponse)
async def confirmar_fechamento(request: Request):
    form = await request.form()
    p = form.get("p", "")
    divisao = form.get("divisao", "1")
    try: div_val = int(divisao)
    except: div_val = 1
    
    try:
        with engine.begin() as conn: 
            c_info = conn.execute(text("SELECT c.nome_completo, p.total_conta FROM pulseiras p JOIN clientes c ON p.cliente_cpf = c.cpf WHERE p.numero_pulseira = :p AND p.status = 'ABERTA'"), {"p": p}).fetchone()
            if not c_info: return HTMLResponse("<script>alert('Comanda já fechada!'); window.location.href='/central';</script>")
            itens_q = conn.execute(text("SELECT item_nome, COUNT(*) as qtd, SUM(valor) as tot FROM vendas_itens WHERE pulseira_num = :p AND status = 'ABERTA' GROUP BY item_nome"), {"p": p}).fetchall()
            conn.execute(text("UPDATE pulseiras SET status = 'FECHADA' WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p})
            conn.execute(text("UPDATE vendas_itens SET status = 'FECHADA' WHERE pulseira_num = :p AND status = 'ABERTA'"), {"p": p})

        linhas_cupom = ""
        for i in itens_q: linhas_cupom += f"<div class='cupom-row'><span>{i.qtd}x {i.item_nome}</span><span>{float(i.tot or 0):.2f}</span></div>"
        linhas_cupom += f"<div class='cupom-row'><span>1x Couvert Artístico</span><span>7.00</span></div>"
        
        subt = float(c_info.total_conta or 0)
        taxa = subt * 0.10
        tot = subt + taxa
        val_div = tot / div_val

        return f"""<html class='cupom-bg'><body onload='window.print();'><div class='cupom'>
            <div class='cupom-head'><b>QUIOSQUE CHOPP BRAHMA</b><br>CONFERENCIA DE MESA<br>NÃO É DOCUMENTO FISCAL<br><br>CLIENTE: {c_info.nome_completo}<br>PULSEIRA: <b>{p}</b></div>
            <div class='cupom-divider'></div>
            <div class='cupom-row cupom-bold'><span>QTD ITEM</span><span>VALOR</span></div>
            <div class='cupom-divider'></div>
            {linhas_cupom}
            <div class='cupom-divider'></div>
            <div class='cupom-row'><span>SUBTOTAL:</span><span>{subt:.2f}</span></div>
            <div class='cupom-row'><span>TAXA SERVICO 10%:</span><span>{taxa:.2f}</span></div>
            <div class='cupom-divider'></div>
            <div class='cupom-row cupom-bold'><span>TOTAL A PAGAR:</span><span>R$ {tot:.2f}</span></div>
            <div class='cupom-divider'></div>
            <div class='cupom-row' style='margin-top:5px;'><span>DIVIDIDO POR:</span><span>{div_val} PESSOA(S)</span></div>
            <div class='cupom-row cupom-bold'><span>VALOR POR PESSOA:</span><span>R$ {val_div:.2f}</span></div>
            <div style='text-align:center; margin-top:15px; font-size:11px;'><br>OBRIGADO E VOLTE SEMPRE!</div>
        </div>
        <a href='/central' class='no-print'>VOLTAR AO SISTEMA</a>
        </body></html>"""
    except Exception:
        return RedirectResponse(url="/central", status_code=303)

@app.get("/buscar", response_class=HTMLResponse)
async def tela_busca(q: str = ""):
    resultados = ""
    if q:
        with engine.connect() as conn:
            query = conn.execute(text("SELECT nome_completo, cpf, data_nascimento FROM clientes WHERE nome_completo ILIKE :q OR cpf LIKE :q"), {"q": f"%{q}%"}).fetchall()
            for r in query:
                is_bday = r.data_nascimento.strftime("%m-%d") == date.today().strftime("%m-%d") if r.data_nascimento else False
                resultados += f"<tr><td style='color:black'>{r.nome_completo}{' 🎁' if is_bday else ''}</td><td><form action='/abrir' method='post' style='display:flex;gap:5px'><input type='hidden' name='cpf' value='{r.cpf}'><input class='input-padrao' name='p' placeholder='Nº Pulseira' required style='width:100px;margin:0'><button class='btn-acao' style='background:#d31a21;padding:8px;margin:0'>ABRIR</button></form></td></tr>"
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Buscar Cliente</h2><form method='get'><input class='input-padrao' name='q' placeholder='Nome ou CPF' value='{q}'><button class='btn-acao'>PESQUISAR</button></form><table>{resultados}</table><br><a href='/central'>Voltar</a></div></div></body></html>"

@app.post("/abrir")
async def abrir(request: Request):
    form = await request.form()
    cpf = form.get("cpf", "").strip()
    p = form.get("p", "").strip()
    try:
        with engine.begin() as conn:
            chk_cpf = conn.execute(text("SELECT numero_pulseira FROM pulseiras WHERE cliente_cpf = :c AND status = 'ABERTA'"), {"c": cpf}).fetchone()
            if chk_cpf: return HTMLResponse(f"<script>alert('❌ Cliente já possui a comanda {chk_cpf[0]} aberta!'); window.history.back();</script>")
            chk_p = conn.execute(text("SELECT cliente_cpf FROM pulseiras WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": p}).fetchone()
            if chk_p: return HTMLResponse(f"<script>alert('❌ A pulseira {p} já está em uso!'); window.history.back();</script>")
            conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta, status) VALUES (:p, :c, 7.00, 'ABERTA')"), {"p": p, "c": cpf})
    except Exception: pass
    return RedirectResponse(url=f"/vendas?p={p}", status_code=303)

@app.get("/cadastro", response_class=HTMLResponse)
async def tela_cadastro():
    return f"<html><head>{CSS}</head><body><div class='container-center'><div class='card-center'>{IMG_LOGO_PEQ}<h2>Novo Cliente</h2><form action='/salvar' method='post'><input class='input-padrao' name='nome' placeholder='Nome Completo' required><input class='input-padrao' name='cpf' placeholder='CPF' required><input class='input-padrao' name='nasc' type='date' required><input class='input-padrao' name='contato' placeholder='WhatsApp' required><input class='input-padrao' name='email' type='email' placeholder='E-mail (Opcional)'><input class='input-padrao' name='pulseira' placeholder='Nº Pulseira' required><button class='btn-acao' style='background:#d31a21'>SALVAR E ABRIR</button></form><br><a href='/central'>Voltar</a></div></div></body></html>"

@app.post("/salvar")
async def salvar(request: Request):
    form = await request.form()
    nome = form.get("nome", "")
    cpf = form.get("cpf", "").strip()
    nasc = form.get("nasc", "")
    contato = form.get("contato", "")
    email = form.get("email", None)
    pulseira = form.get("pulseira", "").strip()
    
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO clientes (nome_completo, cpf, data_nascimento, contato, email) VALUES (:n, :c, :d, :co, :e) ON CONFLICT (cpf) DO NOTHING"), {"n":nome, "c":cpf, "d":nasc, "co":contato, "e":email})
            chk_cpf = conn.execute(text("SELECT numero_pulseira FROM pulseiras WHERE cliente_cpf = :c AND status = 'ABERTA'"), {"c": cpf}).fetchone()
            if chk_cpf: return HTMLResponse(f"<script>alert('❌ Cliente já possui a comanda {chk_cpf[0]} aberta!'); window.history.back();</script>")
            chk_p = conn.execute(text("SELECT cliente_cpf FROM pulseiras WHERE numero_pulseira = :p AND status = 'ABERTA'"), {"p": pulseira}).fetchone()
            if chk_p: return HTMLResponse(f"<script>alert('❌ A pulseira {pulseira} já está em uso!'); window.history.back();</script>")
            conn.execute(text("INSERT INTO pulseiras (numero_pulseira, cliente_cpf, total_conta, status) VALUES (:p, :c, 7.00, 'ABERTA')"), {"p":pulseira, "c":cpf})
    except Exception: pass
    return RedirectResponse(url=f"/vendas?p={pulseira}", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")
