from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui_123'
LOGIN_PASSWORD = 'admin123'  # ← MUDE SUA SENHA AQUI

# FORÇA PASTA ESPECÍFICA (HARDCODED)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # ← Pasta do app.py
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

carregar_backup()

# ========== LOGIN/LOGOUT ==========

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        senha = request.form.get('senha')
        if senha == LOGIN_PASSWORD:
            session.permanent = False  # ← ADICIONE ESTA LINHA
            session['logado'] = True
            return redirect(url_for('index'))
        flash('Senha incorreta!', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()  # ← Limpa TUDO
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
            'data_solicitacao': request.form.get('data', ''),
            'pecas': request.form.get('pecas', ''),
            'data_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
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
            'data_solicitacao': request.form.get('data', ''),
            'pecas': request.form.get('pecas', '')
        })
        salvar_backup()
        flash('Solicitação atualizada com sucesso!', 'success')
        return redirect(url_for('listar'))
    
    return render_template('editar.html', solicitacao=solicitacao)

if __name__ == '__main__':
    print("🚀 Sistema rodando!")
    app.run(debug=True, host='0.0.0.0', port=5000)
