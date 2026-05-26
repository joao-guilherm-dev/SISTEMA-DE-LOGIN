umport tkinter as tk
from tkinter import messagebox

usuarios = {}

def cadastrar():
    usuario = entrada_usuario.get()
    senha = entrada_senha.get()

    if usuario in usuarios:
        messagebox.showerror("Erro", "Usuário já existe!")
    else:
        usuarios[usuario] = senha
        messagebox.showinfo("Sucesso", "Usuário cadastrado!")

def login():
    usuario = entrada_usuario.get()
    senha = entrada_senha.get()

    if usuario in usuarios and usuarios[usuario] == senha:
        messagebox.showinfo("Login", f"Bem-vindo, {usuario}!")
    else:
        messagebox.showerror("Erro", "Usuário ou senha incorretos!")

janela = tk.Tk()
janela.title("Sistema de Login")
janela.geometry("350x250")
janela.configure(bg="#1e1e1e")

titulo = tk.Label(
    janela,
    text="SISTEMA LOGIN",
    font=("Arial", 18, "bold"),
    bg="#1e1e1e",
    fg="white"
)
titulo.pack(pady=15)

label_usuario = tk.Label(
    janela,
    text="Usuário",
    bg="#1e1e1e",
    fg="white"
)
label_usuario.pack()

entrada_usuario = tk.Entry(janela, width=30)
entrada_usuario.pack(pady=5)

label_senha = tk.Label(
    janela,
    text="Senha",
    bg="#1e1e1e",
    fg="white"
)
label_senha.pack()

entrada_senha = tk.Entry(janela, show="*", width=30)
entrada_senha.pack(pady=5)

botao_login = tk.Button(
    janela,
    text="Login",
    bg="green",
    fg="white",
    width=15,
    command=login
)
botao_login.pack(pady=10)

botao_cadastro = tk.Button(
    janela,
    text="Cadastrar",
    bg="blue",
    fg="white",
    width=15,
    command=cadastrar
)
botao_cadastro.pack()

janela.mainloop()
