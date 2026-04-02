from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="brahma_riacho_secret")

# --- CONEXÃO OFICIAL ---
DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

CSS = """
<style>
    :root { --azul-brahma: #004795; --vermelho-brahma: #e21c21; --gelo: #e8ecef; }
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a4a8e; margin: 0; overflow: hidden; height: 100vh; color: white; }
    
    /* Layout Principal estilo Imagem */
    .viewport { display: grid; grid-template-columns: 280px 1fr 320px; height: calc(100vh - 60px); padding: 15px; gap: 15px; }
    
    /* Sidebar Lateral Esquerda */
    .sidebar { display: flex; flex-direction: column; gap: 10px; }
    .cat-button { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.3); padding: 15px; border-radius: 12px; 
                  display: flex; align-items: center; color: white; text-decoration: none; font-weight: bold; position: relative; transition: 0.2s; }
    .cat-button:hover, .cat-active { background: white; color: var(--azul-brahma); }
    .cat-button img { width: 40px; margin-right: 15px; }
    .cat-button .shortcut { position: absolute; top: 5px; right: 10px; font-size: 10px; opacity: 0.7; }

    /* Área Central de Produtos */
    .product-grid { background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; display: grid; 
                    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; overflow-y: auto; }
    .product-card { background: white; border-radius: 12px; overflow: hidden; text-align: center; color: #333; position: relative; cursor: pointer; transition: 0.3s; }
    .product-card:hover { transform: translateY(-5px); border: 3px solid var(--vermelho-brahma); }
    .product-card img { width: 100%; height: 140px; object-fit: contain; padding: 10px; box-sizing: border-box; }
    .product-info { background: var(--vermelho-brahma); color: white; padding: 10px; font-weight: bold; }
    .product-info small { display: block; font-size: 10px; opacity: 0.8; }

    /* Painel da Comanda Direita */
    .comanda-panel { background: white; border-radius: 15px; color: #333; display: flex; flex-direction: column; padding: 0; overflow: hidden; }
    .comanda-header { background: var(--azul-brahma); color: white; padding: 15px; text-align: center; font-weight: bold; }
    .comanda-items { flex: 1; overflow-y: auto; padding: 10px; }
    .comanda-row { display: grid; grid-template-columns: 1fr 40px 80px; border-bottom: 1px solid #eee; padding: 8px 0; font-size: 14px; }
    .comanda-footer { background: #f8f9fa; padding: 15px; }
    .total-row { display: flex; justify-content: space-between; font-size: 22px; font-weight: bold; color: var(--azul-brahma); margin-bottom: 10px; }

    /* Rodapé de Funções */
    .function-bar { height: 60px; background: #002d5f; display: flex; align-items: center; justify-content: space-around; font-weight: bold; font-size: 14px; }
</style>
"""

@app.get("/vendas", response_class=HTMLResponse)
async def vendas_interface(cat: str = "Chopp"):
    # Dados baseados no seu cardápio [cite: 17, 19, 88]
    menu_data = {
        "Chopp": [
            {"id": "6", "nome": "Chopp Claro 350ml", "preco": 11.90, "img": "https://brahma.vteximg.com.br/arquivos/ids/155452/copo_caneco_chopp_brahma.png"},
            {"id": "7", "nome": "Chopp Tulipa 700ml", "preco": 17.90, "img": "https://brahma.vteximg.com.br/arquivos/ids/155452/copo_caneco_chopp_brahma.png"},
            {"id": "9", "nome": "Torre Chopp 2.5L", "preco": 84.90, "img": "https://cdn.awsli.com.br/600x450/1447/1447101/produto/62804257/e75685a6a6.jpg"}
        ],
        "Cervejas": [
            {"id": "22", "nome": "Antarctica Original", "preco": 12.90, "img": "https://ambev.vteximg.com.br/arquivos/ids/156475/Antarctica_Original_600ml.png"},
            {"id": "26", "nome": "Heineken 600ml", "preco": 16.90, "img": "https://img.itdg.com.br/tdg/assets/default/beer_bottle.png"}
        ],
        "Petiscos": [
            {"id": "207", "nome": "Batata Frita", "preco": 21.90, "img": "https://img.itdg.com.br/tdg/assets/default/fries.png"},
            {"id": "212", "nome": "Frango Passarinho", "preco": 28.90, "img": "https://img.itdg.com.br/tdg/assets/default/chicken.png"}
        ]
    }

    prod_html = ""
    for p in menu_data.get(cat, []):
        prod_html += f"""
        <div class="product-card" onclick="adicionarItem('{p['nome']}', {p['preco']})">
            <div style="position:absolute; top:5px; right:10px; font-weight:bold; color:var(--azul-brahma)">F{p['id']}</div>
            <img src="{p['img']}">
            <div class="product-info">
                {p['nome']}<br>
                <small>R$ {p['preco']}</small>
            </div>
        </div>"""

    return f"""
    <html><head>{CSS}
    <script>
        function adicionarItem(nome, preco) {{
            let pulseira = prompt("Número da Pulseira?");
            if(pulseira) window.location.href = `/lancar?p=${{pulseira}}&item=${{nome}}&v=${{preco}}`;
        }}
    </script>
    </head><body>
        <div class="viewport">
            <div class="sidebar">
                <a href="/vendas?cat=Chopp" class="cat-button {'cat-active' if cat=='Chopp' else ''}">
                    <span class="shortcut">F1</span>
                    <img src="https://cdn-icons-png.flaticon.com/512/931/931934.png"> CHOPP
                </a>
                <a href="/vendas?cat=Cervejas" class="cat-button {'cat-active' if cat=='Cervejas' else ''}">
                    <span class="shortcut">F2</span>
                    <img src="https://cdn-icons-png.flaticon.com/512/3100/3100600.png"> CERVEJAS
                </a>
                <a href="/vendas?cat=Petiscos" class="cat-button {'cat-active' if cat=='Petiscos' else ''}">
                    <span class="shortcut">F3</span>
                    <img src="https://cdn-icons-png.flaticon.com/512/2713/2713941.png"> PETISCOS
                </a>
            </div>

            <div class="product-grid">
                {prod_html}
            </div>

            <div class="comanda-panel">
                <div class="comanda-header">Comanda Atual (Mesa / Pulseira) <span style="float:right">F5</span></div>
                <div class="comanda-items">
                    <p style="text-align:center; color:#999; margin-top:50px;">Selecione um produto para lançar...</p>
                </div>
                <div class="comanda-footer">
                    <div class="total-row"><span>Total</span><span>R$ 0,00</span></div>
                    <button class="btn btn-vermelho" style="width:100%; border:none; padding:12px; border-radius:8px; color:white; font-weight:bold;">FINALIZAR COMANDA (F10)</button>
                </div>
            </div>
        </div>

        <div class="function-bar">
            <span>F1: Menu Principal</span>
            <span>F2: Consultar Produto</span>
            <span>F3: Novo Cliente</span>
            <span>F12: Ajuda</span>
        </div>
    </body></html>
    """

@app.get("/lancar")
async def lancar_venda(p: str, item: str, v: float):
    with engine.begin() as conn:
        conn.execute(text("UPDATE pulseiras SET total_conta = total_conta + :v WHERE numero_pulseira = :p"), {"v": v, "p": p})
    return RedirectResponse(url="/vendas")
