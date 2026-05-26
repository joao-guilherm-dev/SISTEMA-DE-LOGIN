usuarios = {}

while True:

    print("\n====== SISTEMA ======")
    print("1 - Cadastrar")
    print("2 - Login")
    print("3 - Listar usuários")
    print("4 - Sair")

    opcao = input("Escolha uma opção: ")

    # CADASTRO
    if opcao == "1":

        usuario = input("Crie um usuário: ")
        
        if usuario in usuarios:
            print("Esse usuário já existe!")
        else:
            senha = input("Crie uma senha: ")
            usuarios[usuario] = senha
            print("Usuário cadastrado com sucesso!")

    # LOGIN
    elif opcao == "2":

        usuario = input("Usuário: ")
        senha = input("Senha: ")

        if usuario in usuarios and usuarios[usuario] == senha:
            print(f"Bem-vindo, {usuario}!")
        else:
            print("Usuário ou senha incorretos!")

    # LISTAR USUÁRIOS
    elif opcao == "3":

        if len(usuarios) == 0:
            print("Nenhum usuário cadastrado.")
        else:
            print("\nUsuários cadastrados:")
            for u in usuarios:
                print("-", u)

    # SAIR
    elif opcao == "4":
        print("Sistema encerrado.")
        break

    else:
        print("Opção inválida!")