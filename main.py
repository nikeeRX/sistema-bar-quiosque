from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, text

app = FastAPI()

# --- URL PÚBLICA COM PORTA 5432 ---
DATABASE_URL = "postgresql://postgres:GNlZnHiuKAcFnpgXhwILfigqKCNkaHqx@interchange.proxy.rlwy.net:44559/railway"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


@app.get("/", response_class=HTMLResponse)
async def area_estoque():
    lista_html = ""
    status_conexao = "<b style='color:green;'>✅ Banco Conectado</b>"
    
    try:
        # Tenta buscar os produtos no banco da Railway
        with engine.connect() as conn:
            produtos = conn.execute(text("SELECT * FROM produtos ORDER BY nome")).fetchall()
            if not produtos:
                lista_html = "<tr><td colspan='4' style='padding:15px; text-align:center;'>Nenhum item cadastrado ainda.</td></tr>"
            for p in produtos:
                lista_html += f"""
                <tr style='border-bottom: 1px solid #ddd;'>
                    <td style='padding:12px;'>{p.codigo_barras}</td>
                    <td style='padding:12px;'><b>{p.nome}</b></td>
                    <td style='padding:12px; color:#28a745; font-weight:bold;'>R$ {p.preco_venda}</td>
                    <td style='padding:12px;'>{p.estoque_atual} un.</td>
                </tr>
                """
    except Exception as e:
        # Se der erro, ele avisa na tela o motivo
        status_conexao = f"<b style='color:red;'>❌ Erro de Conexão: {str(e)[:40]}...</b>"
        lista_html = "<tr><td colspan='4' style='padding:20px; color:red;'>Erro ao ler o banco. Verifique se a tabela 'produtos' foi criada.</td></tr>"

    return f"""
    <body style="background:#f0f2f5; color:#333; font-family: 'Segoe UI', Arial; padding:20px; margin:0;">
        <div style="max-width:900px; margin:auto; background:white; padding:30px; border-radius:15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:3px solid #004795; padding-bottom:15px; margin-bottom:25px;">
                <h1 style="color:#004795; margin:0;">🍻 Quiosque Smart - Estoque</h1>
                <div>{status_conexao}</div>
            </div>
            
            <h3 style="color:#555;">Novo Produto</h3>
            <form action="/cadastrar" method="post" style="display:grid; grid-template-columns: 2fr 2fr 1fr 1fr 1fr; gap:10px; margin-bottom:30px;">
                <input name="cod" placeholder="Cód. Barras" required style="padding:12px; border:1px solid #ccc; border-radius:5px;">
                <input name="nome" placeholder="Nome do Item" required style="padding:12px; border:1px solid #ccc; border-radius:5px;">
                <input name="preco" placeholder="Preço (ex: 12,50)" required style="padding:12px; border:1px solid #ccc; border-radius:5px;">
                <input name="qtd" type="number" placeholder="Qtd" required style="padding:12px; border:1px solid #ccc; border-radius:5px;">
                <button style="background:#28a745; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">CADASTRAR</button>
            </form>

            <h3 style="color:#555;">Produtos no Sistema</h3>
            <table style="width:100%; border-collapse:collapse; background:white;">
                <thead>
                    <tr style="background:#004795; color:white; text-align:left;">
                        <th style="padding:12px;">Código</th>
                        <th style="padding:12px;">Nome</th>
                        <th style="padding:12px;">Preço Venda</th>
                        <th style="padding:12px;">Qtd Estoque</th>
                    </tr>
                </thead>
                <tbody>
                    {lista_html}
                </tbody>
            </table>
        </div>
    </body>
    """

@app.post("/cadastrar")
async def cadastrar(cod: str = Form(...), nome: str = Form(...), preco: str = Form(...), qtd: int = Form(...)):
    try:
        # TRATAMENTO: Aceita vírgula e transforma em ponto para o banco entender
        preco_formatado = float(preco.replace(',', '.'))
        
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO produtos (codigo_barras, nome, preco_venda, estoque_atual) VALUES (:c, :n, :p, :q)"),
                {"c": cod, "n": nome, "p": preco_formatado, "q": qtd}
            )
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        return f"""
        <body style="font-family:Arial; text-align:center; padding:50px;">
            <h2 style="color:red;">Erro ao salvar produto!</h2>
            <p>{str(e)}</p>
            <a href="/" style="background:#004795; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;">Voltar e Corrigir</a>
        </body>
        """
