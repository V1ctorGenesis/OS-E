from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os
import locale
# No início do app.py, depois dos imports
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    pass  # Se falhar, continua com formato numérico
from datetime import datetime
from collections import Counter

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui_123'
LOGIN_PASSWORD = 'admin123' # ← MUDE SUA SENHA AQUI

# FORÇA PASTA ESPECÍFICA (HARDCODED)
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # ← Pasta do app.py
BACKUP_FILE = os.path.join(BASE_DIR, 'backup_manutencao.json')
print(f"💾 Backup forçado: {BACKUP_FILE}")

# DADOS GLOBAIS
solicitacoes_data = []

def carregar_backup():
    global solicitacoes_data
    try:
        if os.path.exists(BACKUP_FILE):
            with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
                solicitacoes_data = json.load(f)
            print(f"✅ Carregado: {len(solicitacoes_data)} registros")
        else:
            solicitacoes_data = []
            print("📭 Iniciando vazio")
    except Exception as e:
        print(f"⚠️ Erro: {e}")
        solicitacoes_data = []

def salvar_backup():
    global solicitacoes_data
    try:
        with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(solicitacoes_data, f, ensure_ascii=False, indent=2)
        print(f"💾 SALVO: {len(solicitacoes_data)} registros")
    except Exception as e:
        print(f"❌ ERRO: {e}")

def get_next_id():
    return max([s.get('id', 0) for s in solicitacoes_data] + [0]) + 1

def exige_login():
    """Verifica se usuário está logado"""
    return session.get('logado', False)

def formatar_data_brasileira(data_str):
    """Converte YYYY-MM-DD para DD/MM/YYYY"""
    if not data_str:
        return ''
    try:
        # Se já estiver no formato YYYY-MM-DD HH:MM:SS
        if len(data_str) > 10:
            data_obj = datetime.strptime(data_str[:10], '%Y-%m-%d')
        else:
            data_obj = datetime.strptime(data_str, '%Y-%m-%d')
        return data_obj.strftime('%d/%m/%Y')
    except:
        return data_str

# Registre o filtro para usar nos templates
@app.template_filter('data_br')
def data_br_filter(data_str):
    return formatar_data_brasileira(data_str)

carregar_backup()

# ========== LOGIN/LOGOUT ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        senha = request.form.get('senha')
        if senha == LOGIN_PASSWORD:
            session.permanent = False
            session['logado'] = True
            return redirect(url_for('index'))
        flash('Senha incorreta!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu do sistema!', 'success')
    return redirect(url_for('login'))

# ========== ROTAS PROTEGIDAS ==========
@app.route('/')
@app.route('/index')
def index():
    if not exige_login():
        return redirect(url_for('login'))
    return render_template('manutencao.html')

@app.route('/enviar', methods=['POST'])
def enviar():
    if not exige_login():
        return redirect(url_for('login'))
    try:
        # Pega a data da solicitação ou usa a data atual
        data_solicitacao = request.form.get('data', datetime.now().strftime('%Y-%m-%d'))
        
        nova_solicitacao = {
            'id': get_next_id(),
            'cliente': request.form['cliente'],
            'contato': request.form.get('contato', ''),
            'setor': request.form.get('setor', ''),
            'equipamento': request.form['equipamento'],
            'tipo': request.form['tipo'].lower(),
            'descricao': request.form['descricao'],
            'prioridade': request.form.get('prioridade', ''),
            'tecnico': request.form.get('tecnico', ''),
            'data_solicitacao': data_solicitacao,  # Data da solicitação (não muda)
            'pecas': request.form.get('pecas', ''),
            'data_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Última alteração
            'status': 'Pendente'
        }

        solicitacoes_data.append(nova_solicitacao)
        salvar_backup()
        flash(f'Solicitação #{nova_solicitacao["id"]} OK!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Erro: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/listar')
def listar():
    if not exige_login():
        return redirect(url_for('login'))
    return render_template('listar.html', solicitacoes=solicitacoes_data)

@app.route('/buscar')
def buscar():
    if not exige_login():
        return redirect(url_for('login'))
    filtro = request.args.get('filtro', '').lower()
    filtradas = [s for s in solicitacoes_data if
        filtro in s.get('cliente', '').lower() or
        filtro in s.get('equipamento', '').lower() or
        filtro in s.get('tecnico', '').lower()]
    return render_template('listar.html', solicitacoes=filtradas, filtro=filtro)

@app.route('/detalhes/<int:id>')
def detalhes(id):
    if not exige_login():
        return redirect(url_for('login'))
    solicitacao = next((s for s in solicitacoes_data if s['id'] == id), None)
    if not solicitacao:
        flash('Não encontrada!', 'error')
        return redirect(url_for('listar'))
    return render_template('detalhes.html', solicitacao=solicitacao)

@app.route('/status/<int:id>', methods=['POST'])
@app.route('/alterar_status/<int:id>', methods=['POST'])
def alterar_status(id):
    if not exige_login():
        return redirect(url_for('login'))
    novo_status = request.form.get('status')
    for solicitacao in solicitacoes_data:
        if solicitacao['id'] == id:
            solicitacao['status'] = novo_status
            # Atualiza a data de registro (última alteração)
            solicitacao['data_registro'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            salvar_backup()
            flash(f'{novo_status}! ✅', 'success')
            break
    return redirect(url_for('detalhes', id=id))

@app.route('/excluir/<int:id>', methods=['POST'])
def excluir(id):
    if not exige_login():
        return redirect(url_for('login'))
    global solicitacoes_data
    solicitacoes_data = [s for s in solicitacoes_data if s['id'] != id]
    salvar_backup()
    flash('Solicitação excluída com sucesso!', 'success')
    return redirect(url_for('listar'))

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    if not exige_login():
        return redirect(url_for('login'))
    solicitacao = next((s for s in solicitacoes_data if s['id'] == id), None)
    if not solicitacao:
        flash('Não encontrada!', 'error')
        return redirect(url_for('listar'))
    
    if request.method == 'POST':
        solicitacao.update({
            'cliente': request.form['cliente'],
            'contato': request.form.get('contato', ''),
            'setor': request.form.get('setor', ''),
            'equipamento': request.form['equipamento'],
            'tipo': request.form['tipo'].lower(),
            'descricao': request.form['descricao'],
            'prioridade': request.form.get('prioridade', ''),
            'tecnico': request.form.get('tecnico', ''),
            'data_solicitacao': request.form.get('data', solicitacao.get('data_solicitacao', '')),
            'pecas': request.form.get('pecas', ''),
            # Atualiza a data de registro (última alteração)
            'data_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        salvar_backup()
        flash('Solicitação atualizada com sucesso!', 'success')
        return redirect(url_for('listar'))
    
    return render_template('editar.html', solicitacao=solicitacao)

@app.route('/dashboard')
def dashboard():
    if not exige_login():
        return redirect(url_for('login'))
    
    # Pega o ano selecionado (padrão: ano atual)
    ano_filtro = request.args.get('ano', str(datetime.now().year))
    
    # Estatísticas gerais (considera o filtro de ano se não for "todos")
    if ano_filtro == 'todos':
        solicitacoes_filtradas = solicitacoes_data
    else:
        solicitacoes_filtradas = [
            s for s in solicitacoes_data 
            if s.get('data_solicitacao', '').startswith(ano_filtro)
        ]
    
    total = len(solicitacoes_filtradas)
    pendentes = sum(1 for s in solicitacoes_filtradas if s.get('status') == 'Pendente')
    em_andamento = sum(1 for s in solicitacoes_filtradas if s.get('status') == 'Em andamento')
    concluidas = sum(1 for s in solicitacoes_filtradas if s.get('status') == 'Concluída')
    
    # Dados por tipo de manutenção
    tipos = [s.get('tipo', 'Não especificado').title() for s in solicitacoes_filtradas]
    tipo_counter = Counter(tipos)
    tipo_data = {
        'labels': list(tipo_counter.keys()),
        'values': list(tipo_counter.values())
    }
    
    # Dados por mês - USANDO DATA DA SOLICITAÇÃO
    meses_dict = {}
    for s in solicitacoes_filtradas:
        data_solicitacao = s.get('data_solicitacao', '')
        if data_solicitacao:
            try:
                # Extrai ano e mês da data da solicitação
                data_obj = datetime.strptime(data_solicitacao[:10], '%Y-%m-%d')
                # Formato: "Jan/2025" (mais legível)
                mes_ano = data_obj.strftime('%b/%Y')
                meses_dict[mes_ano] = meses_dict.get(mes_ano, 0) + 1
            except:
                pass
    
    # Ordena os meses cronologicamente
    meses_ordenados = sorted(meses_dict.items(), 
                            key=lambda x: datetime.strptime(x[0], '%b/%Y'))
    
    mes_data = {
        'labels': [item[0] for item in meses_ordenados],
        'values': [item[1] for item in meses_ordenados]
    }
    
    # Lista de anos disponíveis nos dados
    anos_disponiveis = set()
    for s in solicitacoes_data:
        data_sol = s.get('data_solicitacao', '')
        if data_sol:
            try:
                ano = datetime.strptime(data_sol[:10], '%Y-%m-%d').year
                anos_disponiveis.add(ano)
            except:
                pass
    anos_disponiveis = sorted(anos_disponiveis, reverse=True)
    
    return render_template('dashboard.html', 
                         total=total,
                         pendentes=pendentes,
                         em_andamento=em_andamento,
                         concluidas=concluidas,
                         tipo_data=tipo_data,
                         mes_data=mes_data,
                         anos_disponiveis=anos_disponiveis,
                         ano_selecionado=ano_filtro)

if __name__ == '__main__':
    print("🚀 Sistema rodando!")
    app.run(debug=True, host='0.0.0.0', port=5000)
