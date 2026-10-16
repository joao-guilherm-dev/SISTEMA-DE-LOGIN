"""Interface gráfica (tkinter) do sistema de login."""
import math
import tkinter as tk
from tkinter import messagebox, ttk

from auth import ErroAutenticacao, SistemaAuth

BG, FG = "#1e1e1e", "white"


def campo(pai, texto, variavel, oculto=False):
    tk.Label(pai, text=texto, bg=BG, fg=FG).pack()
    entrada = tk.Entry(pai, textvariable=variavel, width=30, show="*" if oculto else "")
    entrada.pack(pady=5)
    return entrada


def botao(pai, texto, cor, comando):
    b = tk.Button(pai, text=texto, bg=cor, fg="white", width=18, command=comando)
    b.pack(pady=4)
    return b


def checkbox_mostrar(pai, entradas):
    var = tk.BooleanVar(value=False)

    def alternar():
        for entrada in entradas:
            entrada.config(show="" if var.get() else "*")

    tk.Checkbutton(
        pai, text="Mostrar senha", variable=var, command=alternar,
        bg=BG, fg=FG, selectcolor=BG, activebackground=BG, activeforeground=FG,
    ).pack()


class TelaLogin(tk.Frame):
    """Alterna entre login e cadastro."""

    def __init__(self, app):
        super().__init__(app, bg=BG)
        self.app = app
        self.modo = "login"
        self.var_usuario = tk.StringVar()
        self.var_senha = tk.StringVar()
        self.var_confirma = tk.StringVar()

        self.titulo = tk.Label(self, font=("Arial", 18, "bold"), bg=BG, fg=FG)
        self.titulo.pack(pady=15)
        campo(self, "Usuário", self.var_usuario)
        self.entrada_senha = campo(self, "Senha", self.var_senha, oculto=True)

        self.frame_confirma = tk.Frame(self, bg=BG)
        self.entrada_confirma = campo(
            self.frame_confirma, "Confirmar senha", self.var_confirma, oculto=True
        )

        checkbox_mostrar(self, [self.entrada_senha, self.entrada_confirma])
        self.botao_acao = botao(self, "", "green", self.acao)
        self.botao_modo = botao(self, "", "blue", self.alternar_modo)
        self.atualizar_textos()

    def alternar_modo(self):
        self.modo = "cadastro" if self.modo == "login" else "login"
        self.var_senha.set("")
        self.var_confirma.set("")
        self.atualizar_textos()

    def atualizar_textos(self):
        if self.modo == "login":
            self.frame_confirma.pack_forget()
            self.titulo.config(text="LOGIN")
            self.botao_acao.config(text="Entrar")
            self.botao_modo.config(text="Criar conta")
        else:
            self.frame_confirma.pack(after=self.entrada_senha)
            self.titulo.config(text="CADASTRO")
            self.botao_acao.config(text="Cadastrar")
            self.botao_modo.config(text="Já tenho conta")

    def acao(self):
        auth = self.app.auth
        usuario, senha = self.var_usuario.get(), self.var_senha.get()
        try:
            if self.modo == "cadastro":
                if senha != self.var_confirma.get():
                    raise ErroAutenticacao("As senhas não coincidem.")
                auth.cadastrar(usuario, senha)
                messagebox.showinfo("Sucesso", "Usuário cadastrado! Faça login.")
                self.alternar_modo()
            elif auth.autenticar(usuario, senha):
                self.app.mostrar_painel(usuario.strip())
            else:
                messagebox.showerror("Erro", "Usuário ou senha incorretos!")
        except ErroAutenticacao as erro:
            messagebox.showerror("Erro", str(erro))


class TelaPainel(tk.Frame):
    """Tela exibida depois do login."""

    def __init__(self, app, usuario):
        super().__init__(app, bg=BG)
        tk.Label(
            self, text=f"Olá, {usuario}!", font=("Arial", 18, "bold"), bg=BG, fg=FG
        ).pack(pady=(40, 5))
        criada = app.auth.data_criacao(usuario)
        if criada:
            tk.Label(
                self, text=f"Conta criada em {criada:%d/%m/%Y}", bg=BG, fg="#aaaaaa"
            ).pack(pady=(0, 25))
        botao(self, "Alterar senha", "#b36b00", lambda: DialogoSenha(app, usuario))
        if app.auth.eh_admin(usuario):
            botao(self, "Administração", "#6a3fa0", lambda: DialogoAdmin(app, usuario))
        botao(self, "Sair", "#a33333", app.mostrar_login)


class DialogoSenha(tk.Toplevel):
    def __init__(self, app, usuario):
        super().__init__(app)
        self.app, self.usuario = app, usuario
        self.title("Alterar senha")
        self.geometry("340x360")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.transient(app)

        self.v_atual, self.v_nova, self.v_conf = (tk.StringVar() for _ in range(3))
        tk.Label(self, text="ALTERAR SENHA", font=("Arial", 14, "bold"), bg=BG, fg=FG).pack(pady=12)
        entradas = [
            campo(self, "Senha atual", self.v_atual, oculto=True),
            campo(self, "Nova senha", self.v_nova, oculto=True),
            campo(self, "Confirmar nova senha", self.v_conf, oculto=True),
        ]
        checkbox_mostrar(self, entradas)
        botao(self, "Salvar", "green", self.salvar)
        botao(self, "Cancelar", "gray", self.destroy)
        self.bind("<Return>", lambda _e: self.salvar())
        self.wait_visibility()
        self.grab_set()

    def salvar(self):
        try:
            if self.v_nova.get() != self.v_conf.get():
                raise ErroAutenticacao("As senhas novas não coincidem.")
            self.app.auth.alterar_senha(self.usuario, self.v_atual.get(), self.v_nova.get())
        except ErroAutenticacao as erro:
            messagebox.showerror("Erro", str(erro), parent=self)
            return
        messagebox.showinfo("Sucesso", "Senha alterada!", parent=self)
        self.destroy()


class DialogoAdmin(tk.Toplevel):
    """Lista os usuários e permite desbloquear contas. Só abre para administradores."""

    COLUNAS = (
        ("usuario", "Usuário", 130),
        ("perfil", "Perfil", 90),
        ("criado", "Criado em", 90),
        ("status", "Status", 130),
    )

    def __init__(self, app, usuario):
        super().__init__(app)
        self.app, self.usuario = app, usuario
        self.title("Administração")
        self.geometry("480x400")
        self.configure(bg=BG)
        self.transient(app)

        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure("Treeview", background="#2b2b2b", fieldbackground="#2b2b2b",
                         foreground=FG, rowheight=24)
        estilo.configure("Treeview.Heading", background="#3a3a3a", foreground=FG)
        estilo.map("Treeview", background=[("selected", "#1f6aa5")])

        tk.Label(self, text="USUÁRIOS", font=("Arial", 14, "bold"), bg=BG, fg=FG).pack(pady=10)
        self.tabela = ttk.Treeview(
            self, columns=[c[0] for c in self.COLUNAS],
            show="headings", selectmode="browse", height=10,
        )
        for chave, titulo, largura in self.COLUNAS:
            self.tabela.heading(chave, text=titulo)
            self.tabela.column(chave, width=largura, anchor="w")
        self.tabela.pack(fill="both", expand=True, padx=12)

        botoes = tk.Frame(self, bg=BG)
        botoes.pack(pady=10)
        for texto, cor, comando in (
            ("Desbloquear", "green", self.desbloquear),
            ("Atualizar", "blue", self.atualizar),
            ("Fechar", "gray", self.destroy),
        ):
            tk.Button(botoes, text=texto, bg=cor, fg="white", width=12,
                      command=comando).pack(side="left", padx=4)

        self.atualizar()
        self.wait_visibility()
        self.grab_set()

    def atualizar(self):
        try:
            usuarios = self.app.auth.listar_usuarios(self.usuario)
        except ErroAutenticacao as erro:
            messagebox.showerror("Erro", str(erro), parent=self)
            return
        self.tabela.delete(*self.tabela.get_children())
        for u in usuarios:
            restante = u["bloqueio_restante"]
            status = f"Bloqueado ({math.ceil(restante / 60)} min)" if restante > 0 else "Ativo"
            criado = f"{u['criado_em']:%d/%m/%Y}" if u["criado_em"] else "—"
            self.tabela.insert(
                "", "end", iid=u["usuario"],
                values=(u["usuario"], "Admin" if u["admin"] else "Usuário", criado, status),
            )

    def desbloquear(self):
        selecao = self.tabela.selection()
        if not selecao:
            messagebox.showwarning("Atenção", "Selecione um usuário.", parent=self)
            return
        try:
            self.app.auth.desbloquear(self.usuario, selecao[0])
        except ErroAutenticacao as erro:
            messagebox.showerror("Erro", str(erro), parent=self)
            return
        self.atualizar()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.auth = SistemaAuth()
        self.title("Sistema de Login")
        self.geometry("380x420")
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self.sair)
        self.tela = None
        self.mostrar_login()

    def _trocar(self, tela):
        if self.tela:
            self.tela.destroy()
        self.tela = tela
        tela.pack(fill="both", expand=True)

    def mostrar_login(self):
        self._trocar(TelaLogin(self))
        self.bind("<Return>", lambda _e: self.tela.acao())

    def mostrar_painel(self, usuario):
        self.unbind("<Return>")
        self._trocar(TelaPainel(self, usuario))

    def sair(self):
        self.auth.fechar()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()