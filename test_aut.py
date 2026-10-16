import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import auth
from auth import BLOQUEIO_SEGUNDOS, MAX_TENTATIVAS, ErroAutenticacao, SistemaAuth

auth.ITERACOES = 1_000  # deixa os testes rápidos


class RelogioFalso:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


class TesteCadastroELogin(unittest.TestCase):
    def setUp(self):
        self.relogio = RelogioFalso()
        self.auth = SistemaAuth(":memory:", relogio=self.relogio)

    def test_cadastro_e_login_validos(self):
        self.auth.cadastrar("joao", "senha1234")
        self.assertTrue(self.auth.autenticar("joao", "senha1234"))

    def test_senha_errada(self):
        self.auth.cadastrar("joao", "senha1234")
        self.assertFalse(self.auth.autenticar("joao", "outrasenha"))

    def test_usuario_inexistente(self):
        self.assertFalse(self.auth.autenticar("ninguem", "senha1234"))

    def test_usuario_duplicado(self):
        self.auth.cadastrar("joao", "senha1234")
        with self.assertRaises(ErroAutenticacao):
            self.auth.cadastrar("joao", "senha5678")

    def test_senha_curta(self):
        with self.assertRaises(ErroAutenticacao):
            self.auth.cadastrar("joao", "123")

    def test_usuario_invalido(self):
        with self.assertRaises(ErroAutenticacao):
            self.auth.cadastrar("a b", "senha1234")

    def test_senha_nao_fica_em_texto_puro(self):
        self.auth.cadastrar("joao", "senha1234")
        sal, hash_ = self.auth.conn.execute("SELECT sal, senha_hash FROM usuarios").fetchone()
        self.assertNotIn(b"senha1234", sal + hash_)

    def test_data_criacao(self):
        self.auth.cadastrar("joao", "senha1234")
        self.assertIsNotNone(self.auth.data_criacao("joao"))
        self.assertIsNone(self.auth.data_criacao("ninguem"))


class TesteBloqueio(unittest.TestCase):
    def setUp(self):
        self.relogio = RelogioFalso()
        self.auth = SistemaAuth(":memory:", relogio=self.relogio)
        self.auth.cadastrar("joao", "senha1234")

    def _errar(self, vezes):
        for _ in range(vezes):
            self.assertFalse(self.auth.autenticar("joao", "errada123"))

    def test_bloqueia_apos_max_tentativas(self):
        self._errar(MAX_TENTATIVAS - 1)
        with self.assertRaises(ErroAutenticacao):
            self.auth.autenticar("joao", "errada123")

    def test_conta_bloqueada_recusa_ate_senha_correta(self):
        self._errar(MAX_TENTATIVAS - 1)
        with self.assertRaises(ErroAutenticacao):
            self.auth.autenticar("joao", "errada123")
        with self.assertRaises(ErroAutenticacao):
            self.auth.autenticar("joao", "senha1234")

    def test_desbloqueia_depois_do_tempo(self):
        self._errar(MAX_TENTATIVAS - 1)
        with self.assertRaises(ErroAutenticacao):
            self.auth.autenticar("joao", "errada123")
        self.relogio.t += BLOQUEIO_SEGUNDOS + 1
        self.assertTrue(self.auth.autenticar("joao", "senha1234"))

    def test_login_correto_zera_contador(self):
        self._errar(MAX_TENTATIVAS - 1)
        self.assertTrue(self.auth.autenticar("joao", "senha1234"))
        self._errar(MAX_TENTATIVAS - 1)  # não deve bloquear


class TesteAlterarSenha(unittest.TestCase):
    def setUp(self):
        self.auth = SistemaAuth(":memory:", relogio=RelogioFalso())
        self.auth.cadastrar("joao", "senha1234")

    def test_troca_com_sucesso(self):
        self.auth.alterar_senha("joao", "senha1234", "novasenha99")
        self.assertTrue(self.auth.autenticar("joao", "novasenha99"))
        self.assertFalse(self.auth.autenticar("joao", "senha1234"))

    def test_senha_atual_incorreta(self):
        with self.assertRaises(ErroAutenticacao):
            self.auth.alterar_senha("joao", "errada123", "novasenha99")

    def test_nova_senha_curta(self):
        with self.assertRaises(ErroAutenticacao):
            self.auth.alterar_senha("joao", "senha1234", "123")

    def test_nova_igual_a_atual(self):
        with self.assertRaises(ErroAutenticacao):
            self.auth.alterar_senha("joao", "senha1234", "senha1234")


class TesteAdmin(unittest.TestCase):
    def setUp(self):
        self.relogio = RelogioFalso()
        self.auth = SistemaAuth(":memory:", relogio=self.relogio)
        self.auth.cadastrar("admin", "senha1234")
        self.auth.cadastrar("maria", "senha1234")

    def test_primeiro_usuario_e_admin(self):
        self.assertTrue(self.auth.eh_admin("admin"))
        self.assertFalse(self.auth.eh_admin("maria"))
        self.assertFalse(self.auth.eh_admin("ninguem"))

    def test_admin_lista_usuarios(self):
        nomes = [u["usuario"] for u in self.auth.listar_usuarios("admin")]
        self.assertEqual(nomes, ["admin", "maria"])

    def test_listagem_nao_expoe_senha(self):
        for u in self.auth.listar_usuarios("admin"):
            self.assertFalse({"sal", "senha_hash", "senha"} & u.keys())

    def test_usuario_comum_nao_lista(self):
        with self.assertRaises(ErroAutenticacao):
            self.auth.listar_usuarios("maria")

    def test_admin_desbloqueia_usuario(self):
        for _ in range(MAX_TENTATIVAS - 1):
            self.auth.autenticar("maria", "errada123")
        with self.assertRaises(ErroAutenticacao):
            self.auth.autenticar("maria", "errada123")
        bloqueio = {u["usuario"]: u["bloqueio_restante"] for u in self.auth.listar_usuarios("admin")}
        self.assertGreater(bloqueio["maria"], 0)

        self.auth.desbloquear("admin", "maria")
        self.assertTrue(self.auth.autenticar("maria", "senha1234"))

    def test_usuario_comum_nao_desbloqueia(self):
        with self.assertRaises(ErroAutenticacao):
            self.auth.desbloquear("maria", "admin")

    def test_desbloquear_usuario_inexistente(self):
        with self.assertRaises(ErroAutenticacao):
            self.auth.desbloquear("admin", "ninguem")

    def test_migracao_promove_usuario_mais_antigo(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "antigo.db"
            conn = sqlite3.connect(caminho)
            conn.execute(
                "CREATE TABLE usuarios (usuario TEXT PRIMARY KEY, sal BLOB NOT NULL, "
                "senha_hash BLOB NOT NULL)"
            )
            conn.executemany(
                "INSERT INTO usuarios VALUES (?, ?, ?)",
                [("primeiro", b"s", b"h"), ("segundo", b"s", b"h")],
            )
            conn.commit()
            conn.close()

            sistema = SistemaAuth(caminho)
            self.assertTrue(sistema.eh_admin("primeiro"))
            self.assertFalse(sistema.eh_admin("segundo"))
            sistema.fechar()


if __name__ == "__main__":
    unittest.main()