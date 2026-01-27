import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime
import time

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Gestão de Transporte Escolar", layout="wide")

# ==========================================
# GESTÃO DE AUTENTICAÇÃO E SESSÃO
# ==========================================

# Credenciais (Em produção, idealmente isso ficaria em variaveis de ambiente ou banco seguro)
CREDENCIAIS = {
    "escola": {
        "senha": "SenhaTransporte",
        "role": "escola",
        "nome": "Unidade Escolar"
    },
    "supervisor": { # Simplifiquei o user para 'supervisor', mas no label pedimos Supervisor ou PEC
        "senha": "Supersenha",
        "role": "supervisor",
        "nome": "Supervisor / PEC"
    },
    "monicaabreu": {
        "senha": "supersenha2026",
        "role": "admin",
        "nome": "Administradora"
    }
}

def check_login(username, password):
    """Verifica credenciais e retorna o papel (role) se válido"""
    # Tratamento para aceitar 'supervisor' ou 'pec' se o usuário digitar
    user_key = username.lower().strip()
    if user_key == "pec": user_key = "supervisor" 
    
    if user_key in CREDENCIAIS:
        if CREDENCIAIS[user_key]["senha"] == password:
            return CREDENCIAIS[user_key]
    return None

def login_screen():
    st.markdown("<h1 style='text-align: center;'>🔐 Transporte Escolar</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Acesso ao Sistema</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            user = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar")
            
            if submit:
                user_data = check_login(user, password)
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.user_role = user_data["role"]
                    st.session_state.user_name = user_data["nome"]
                    st.session_state.username_login = user # Guarda o login usado
                    st.success("Login realizado com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

# Inicializa variáveis de sessão se não existirem
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None

# ==========================================
# BLOCO PRINCIPAL (SÓ EXECUTA SE LOGADO)
# ==========================================
if not st.session_state.logged_in:
    login_screen()
else:
    # --- CABEÇALHO DO SISTEMA LOGADO ---
    
    # Conectar ao banco V3
    conn = sqlite3.connect('transporte_v3.db', check_same_thread=False)
    c = conn.cursor()

    # Criar tabelas (Mesma estrutura V3)
    c.execute('''
    CREATE TABLE IF NOT EXISTS solicitacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_aluno TEXT, cpf_aluno TEXT, ra_aluno TEXT, cadeirante TEXT, cid TEXT,
        cep_aluno TEXT, logradouro_aluno TEXT, numero_aluno TEXT, municipio_aluno TEXT,
        nome_escola TEXT, cep_escola TEXT, logradouro_escola TEXT, numero_escola TEXT, municipio_escola TEXT,
        sala_recurso TEXT, dias_frequencia TEXT, horario_entrada TEXT, horario_saida TEXT,
        arquivo_medico BLOB, nome_arq_medico TEXT, arquivo_viagem BLOB, nome_arq_viagem TEXT,
        status TEXT DEFAULT 'Pendente', supervisor_nome TEXT, supervisor_cpf TEXT,
        motivo_reprovacao TEXT, arquivo_assinado BLOB, nome_arq_assinado TEXT, data_atualizacao TEXT
    )
    ''')
    conn.commit()

    # Funções Auxiliares
    def buscar_dados_cep(cep):
        cep = cep.replace("-", "").replace(".", "").strip()
        if len(cep) == 8:
            try:
                response = requests.get(f"https://viacep.com.br/ws/{cep}/json/")
                dados = response.json()
                if "erro" not in dados:
                    return dados
            except:
                return None
        return None

    # --- SIDEBAR E PERMISSÕES ---
    st.sidebar.title(f"👤 {st.session_state.user_name}")
    
    # Definir quais menus aparecem para qual perfil
    opcoes_menu = []
    
    # Perfil ESCOLA: Só vê Solicitação
    if st.session_state.user_role == "escola":
        opcoes_menu = ["Escola (Solicitação)"]
        
    # Perfil SUPERVISOR: Vê Solicitação (Leitura) e Avaliação
    elif st.session_state.user_role == "supervisor":
        opcoes_menu = ["Escola (Solicitação)", "Supervisor (Avaliação)"]
        
    # Perfil ADMIN: Vê tudo
    elif st.session_state.user_role == "admin":
        opcoes_menu = ["Escola (Solicitação)", "Supervisor (Avaliação)", "Relatórios e Docs"]
    
    menu = st.sidebar.radio("Navegação:", opcoes_menu)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Sair / Logout"):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.rerun()

    # ==========================================
    # ABA 1: ESCOLA (SOLICITAÇÃO)
    # ==========================================
    if menu == "Escola (Solicitação)":
        st.title("🚌 Transporte Escolar - Solicitação")
        st.markdown("---")

        # Lógica de "Somente Leitura" para Supervisor
        # Se for supervisor, disable_widgets = True
        disable_widgets = True if st.session_state.user_role == "supervisor" else False
        
        if disable_widgets:
            st.warning("🔒 MODO VISUALIZAÇÃO: Seu perfil permite apenas visualizar este formulário.")

        with st.form("form_escola"):
            st.subheader("1. Dados do Aluno")
            col1, col2, col3 = st.columns(3)
            nome = col1.text_input("Nome Completo", disabled=disable_widgets)
            cpf = col2.text_input("CPF", disabled=disable_widgets)
            ra = col3.text_input("R.A.", disabled=disable_widgets)

            col4, col5 = st.columns(2)
            cadeirante = col4.radio("Cadeirante?", ["NÃO", "SIM"], horizontal=True, disabled=disable_widgets)
            cid = col5.text_input("CID", disabled=disable_widgets)

            st.markdown("##### Endereço Residencial")
            col_cep1, col_btn1 = st.columns([2, 1])
            cep_input_aluno = col_cep1.text_input("CEP Residencial", disabled=disable_widgets)
            
            # Busca de CEP (Lógica visual apenas se não estiver desabilitado ou se tiver dados)
            logradouro_suggest = ""
            municipio_suggest = ""
            if not disable_widgets and cep_input_aluno and len(cep_input_aluno) >= 8:
                dados_cep = buscar_dados_cep(cep_input_aluno)
                if dados_cep:
                    logradouro_suggest = f"{dados_cep['logradouro']}, {dados_cep['bairro']}"
                    municipio_suggest = f"{dados_cep['localidade']} - {dados_cep['uf']}"
                    st.caption(f"✅ Endereço encontrado: {logradouro_suggest}")
            
            col_end1, col_num1, col_mun1 = st.columns([3, 1, 2])
            end_aluno = col_end1.text_input("Logradouro", value=logradouro_suggest, disabled=disable_widgets)
            num_aluno = col_num1.text_input("Número", disabled=disable_widgets)
            mun_aluno = col_mun1.text_input("Município", value=municipio_suggest, disabled=disable_widgets)

            st.subheader("2. Dados da Unidade Escolar")
            nome_escola = st.text_input("Nome da Unidade", disabled=disable_widgets)
            
            col_cep2, dummy = st.columns([2, 3])
            cep_input_escola = col_cep2.text_input("CEP Escola", disabled=disable_widgets)
            
            # Busca CEP Escola
            log_esc_sugg = ""
            mun_esc_sugg = ""
            if not disable_widgets and cep_input_escola and len(cep_input_escola) >= 8:
                d_cep_esc = buscar_dados_cep(cep_input_escola)
                if d_cep_esc:
                    log_esc_sugg = f"{d_cep_esc['logradouro']}, {d_cep_esc['bairro']}"
                    mun_esc_sugg = f"{d_cep_esc['localidade']} - {d_cep_esc['uf']}"
                    st.caption(f"✅ Escola encontrada: {log_esc_sugg}")

            col_end2, col_num2, col_mun2 = st.columns([3, 1, 2])
            end_escola = col_end2.text_input("Logradouro Escola", value=log_esc_sugg, disabled=disable_widgets)
            num_escola = col_num2.text_input("Número Escola", disabled=disable_widgets)
            mun_escola = col_mun2.text_input("Município Escola", value=mun_esc_sugg, disabled=disable_widgets)

            st.subheader("3. Frequência")
            sala_recurso = st.radio("Sala de Recurso?", ["NÃO", "SIM"], horizontal=True, disabled=disable_widgets)
            dias_freq = st.multiselect("Dias", ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"], disabled=disable_widgets)
            
            col_h1, col_h2 = st.columns(2)
            hr_entrada = col_h1.time_input("Entrada", value=None, disabled=disable_widgets)
            hr_saida = col_h2.time_input("Saída", value=None, disabled=disable_widgets)

            st.subheader("4. Documentação")
            doc_medico = st.file_uploader("Ficha Médica", type=['pdf', 'jpg', 'png'], disabled=disable_widgets)
            doc_viagem = st.file_uploader("Ficha Viagem", type=['pdf', 'jpg', 'png'], disabled=disable_widgets)

            # Botão de envio some se for supervisor (readonly)
            if not disable_widgets:
                submitted = st.form_submit_button("Enviar Solicitação")
                
                if submitted:
                    if not nome or not cpf or not ra or not num_aluno or not num_escola:
                        st.error("Preencha os campos obrigatórios (Nome, CPF, RA, Números de endereço).")
                    elif not doc_medico or not doc_viagem:
                        st.error("Documentação é obrigatória.")
                    else:
                        dias_str = ", ".join(dias_freq)
                        hr_ent_str = hr_entrada.strftime("%H:%M") if hr_entrada else ""
                        hr_sai_str = hr_saida.strftime("%H:%M") if hr_saida else ""

                        c.execute('''
                            INSERT INTO solicitacoes (
                                nome_aluno, cpf_aluno, ra_aluno, cadeirante, cid, 
                                cep_aluno, logradouro_aluno, numero_aluno, municipio_aluno,
                                nome_escola, cep_escola, logradouro_escola, numero_escola, municipio_escola,
                                sala_recurso, dias_frequencia, horario_entrada, horario_saida,
                                arquivo_medico, nome_arq_medico, arquivo_viagem, nome_arq_viagem
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            nome, cpf, ra, cadeirante, cid, 
                            cep_input_aluno, end_aluno, num_aluno, mun_aluno,
                            nome_escola, cep_input_escola, end_escola, num_escola, mun_escola,
                            sala_recurso, dias_str, hr_ent_str, hr_sai_str,
                            doc_medico.getvalue(), doc_medico.name, doc_viagem.getvalue(), doc_viagem.name
                        ))
                        conn.commit()
                        st.success(f"Solicitação enviada com sucesso! Aluno: {nome}")
            else:
                st.form_submit_button("Enviar Solicitação (Desabilitado)", disabled=True)

    # ==========================================
    # ABA 2: SUPERVISOR (AVALIAÇÃO)
    # ==========================================
    elif menu == "Supervisor (Avaliação)":
        st.title("📋 Painel do Supervisor")
        
        # Lista de Pendentes
        df_pendentes = pd.read_sql("SELECT id, nome_aluno, status FROM solicitacoes WHERE status='Pendente'", conn)
        
        if not df_pendentes.empty:
            opcoes_alunos = df_pendentes.apply(lambda x: f"{x['id']} - {x['nome_aluno']}", axis=1)
            escolha = st.selectbox("Selecione um Aluno Pendente:", opcoes_alunos)
            
            id_aluno_selecionado = int(escolha.split(' - ')[0])
            
            c.execute("SELECT * FROM solicitacoes WHERE id=?", (id_aluno_selecionado,))
            dados = c.fetchone()
            
            if dados:
                st.info(f"Analisando solicitação # {dados[0]}")
                
                # Visualização Dados
                tab_dados, tab_docs = st.tabs(["Dados da Solicitação", "Documentos Anexados"])
                with tab_dados:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("### Aluno")
                        st.write(f"**Nome:** {dados[1]}")
                        st.write(f"**CPF:** {dados[2]} | **RA:** {dados[3]}")
                        st.write(f"**CID:** {dados[5]} | **Cadeirante:** {dados[4]}")
                        st.write(f"**Endereço:** {dados[7]}, Nº {dados[8]} - {dados[9]}")
                    with c2:
                        st.markdown("### Escola")
                        st.write(f"**Instituição:** {dados[10]}")
                        st.write(f"**Endereço:** {dados[12]}, Nº {dados[13]} - {dados[14]}")
                        st.write(f"**Dias:** {dados[16]}")
                        st.write(f"**Horário:** {dados[17]} às {dados[18]}")

                with tab_docs:
                    st.markdown("#### Documentos da Escola")
                    cd1, cd2 = st.columns(2)
                    if dados[19]:
                        cd1.download_button("⬇️ Ficha Médica", data=dados[19], file_name=dados[20] or "medico.pdf")
                    if dados[21]:
                        cd2.download_button("⬇️ Ficha Viagem", data=dados[21], file_name=dados[22] or "viagem.pdf")

                st.markdown("---")
                st.markdown("### ✍️ Parecer Final")
                
                with st.form("form_supervisor"):
                    col_sup1, col_sup2 = st.columns(2)
                    # Preenche automaticamente se o login for de supervisor específico, mas deixa editável
                    nome_sup = col_sup1.text_input("Nome Supervisor / PEC")
                    cpf_sup = col_sup2.text_input("CPF do Supervisor")
                    
                    decisao = st.radio("Parecer:", ["Aprovar Solicitação", "Reprovar Solicitação"])
                    
                    motivo = None
                    if decisao == "Reprovar Solicitação":
                        motivo = st.selectbox("Motivo:", [
                            "Falta de documentação",
                            "Aluno não elegível ao transporte",
                            "Reavaliação da Necessidade do Transporte"
                        ])
                    
                    arquivo_assinado = st.file_uploader("Anexar Ficha Assinada (Obrigatório)", type=['pdf', 'jpg', 'png'])
                    
                    btn_avaliar = st.form_submit_button("Finalizar Processo")
                    
                    if btn_avaliar:
                        if not nome_sup or not cpf_sup:
                            st.error("Identificação é obrigatória.")
                        elif not arquivo_assinado:
                            st.error("Anexe a ficha assinada.")
                        else:
                            status_final = "Aprovado" if decisao == "Aprovar Solicitação" else "Reprovado"
                            motivo_final = motivo if status_final == "Reprovado" else "Aprovado"
                            
                            c.execute('''
                                UPDATE solicitacoes 
                                SET status=?, supervisor_nome=?, supervisor_cpf=?, 
                                    motivo_reprovacao=?, arquivo_assinado=?, nome_arq_assinado=?,
                                    data_atualizacao=?
                                WHERE id=?
                            ''', (status_final, nome_sup, cpf_sup, motivo_final, 
                                  arquivo_assinado.getvalue(), arquivo_assinado.name, 
                                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id_aluno_selecionado))
                            conn.commit()
                            st.success("Avaliação registrada!")
                            st.rerun()
        else:
            st.success("Nenhuma solicitação pendente.")

    # ==========================================
    # ABA 3: RELATÓRIOS (ADMIN E TALVEZ SUPERVISOR)
    # ==========================================
    elif menu == "Relatórios e Docs":
        st.title("🗂️ Relatório Administrativo")
        
        status_filter = st.selectbox("Status:", ["Todos", "Pendente", "Aprovado", "Reprovado"])
        
        query = "SELECT id, nome_aluno, cpf_aluno, nome_escola, status, supervisor_nome, motivo_reprovacao FROM solicitacoes"
        if status_filter != "Todos":
            query += f" WHERE status = '{status_filter}'"
            
        df = pd.read_sql(query, conn)
        st.dataframe(df)
        
        st.markdown("### Acesso Global aos Arquivos")
        c.execute("SELECT id, nome_aluno, arquivo_medico, nome_arq_medico, arquivo_viagem, nome_arq_viagem, arquivo_assinado, nome_arq_assinado, status FROM solicitacoes")
        todos = c.fetchall()
        
        for row in todos:
            # Filtro visual na lista
            if status_filter != "Todos" and row[8] != status_filter: continue
                
            icon = "✅" if row[8] == "Aprovado" else "❌" if row[8] == "Reprovado" else "⏳"
            with st.expander(f"{icon} {row[1]} (ID: {row[0]})"):
                c1, c2, c3 = st.columns(3)
                if row[2]: c1.download_button("📄 Médica", row[2], row[3], key=f"d1_{row[0]}")
                if row[4]: c2.download_button("🚌 Viagem", row[4], row[5], key=f"d2_{row[0]}")
                if row[6]: c3.download_button("✍️ Parecer", row[6], row[7], key=f"d3_{row[0]}")
