# Sistema de Login em Python

Aplicativo desktop de cadastro e login feito com **Python**, **tkinter** e **SQLite**, usando apenas a biblioteca padrão.

## Funcionalidades

- **Cadastro** com validação (usuário de 3 a 20 caracteres, senha com no mínimo 8) e confirmação de senha
- **Senhas protegidas:** hash PBKDF2-SHA256 com sal aleatório por usuário (nunca em texto puro) e comparação em tempo constante
- **Bloqueio por tentativas:** após 5 senhas erradas, a conta fica bloqueada por 5 minutos
- **Tela pós-login** com saudação e data de criação da conta
- **Troca de senha** exigindo a senha atual
- **Painel de administração:** o primeiro usuário cadastrado vira administrador e pode listar usuários e desbloquear contas bloqueadas
- Persistência dos usuários em SQLite (`usuarios.db`), com migração automática de bancos antigos
- Interface escura, com opção "Mostrar senha" e atalho Enter
- Lógica separada da interface e coberta por testes unitários

## Como executar

```bash
git clone https://github.com/joao-guilherm-dev/SISTEMA-DE-LOGIN.git
cd SISTEMA-DE-LOGIN
python app.py
```

Requer Python 3.8+ (o tkinter já vem com o instalador oficial; no Linux: `sudo apt install python3-tk`).

## Testes

```bash
python -m unittest discover tests
```

Os testes de bloqueio usam um relógio falso, então não é preciso esperar 5 minutos.

## Estrutura

```
├── app.py              # interface gráfica: login/cadastro, painel, troca de senha e administração
├── auth.py             # hash de senha, bloqueio, troca de senha, perfis e SQLite
├── tests/test_auth.py
└── README.md
```

## Ideias futuras

- Recuperação de senha por e-mail
- Empacotar como executável com PyInstaller