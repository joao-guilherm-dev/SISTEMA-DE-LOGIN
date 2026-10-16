"""Lógica de autenticação, independente da interface gráfica."""
import hashlib
import hmac
import math
import os
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB_PADRAO = Path(__file__).with_name("usuarios.db")
ITERACOES = 200_000
TAMANHO_MIN_SENHA = 8
MAX_TENTATIVAS = 5
BLOQUEIO_SEGUNDOS = 300
USUARIO_RE = re.compile(r"^[A-Za-z0-9_.-]{3,20}$")


class ErroAutenticacao(Exception):
    """Erro de validação, de cadastro ou de bloqueio de conta."""


def _hash_senha(senha: str, sal: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, ITERACOES)


def _validar_senha(senha: str) -> None:
    if len(senha) < TAMANHO_MIN_SENHA:
        raise ErroAutenticacao(
            f"A senha deve ter pelo menos {TAMANHO_MIN_SENHA} caracteres."
        )


class SistemaAuth:
    def __init__(self, caminho_db=DB_PADRAO, relogio=time.time):
        self._agora = relogio  # injetável para testar o bloqueio sem esperar
        self.conn = sqlite3.connect(caminho_db)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS usuarios (
                   usuario    TEXT PRIMARY KEY,
                   sal        BLOB NOT NULL,
                   senha_hash BLOB NOT NULL
               )"""
        )
        self._migrar()
        self.conn.commit()

    def _migrar(self) -> None:
        """Adiciona colunas novas em bancos criados por versões anteriores."""
        existentes = {l[1] for l in self.conn.execute("PRAGMA table_info(usuarios)")}
        novas = {
            "tentativas": "INTEGER NOT NULL DEFAULT 0",
            "bloqueado_ate": "REAL NOT NULL DEFAULT 0",
            "criado_em": "REAL NOT NULL DEFAULT 0",
            "admin": "INTEGER NOT NULL DEFAULT 0",
        }
        for nome, ddl in novas.items():
            if nome not in existentes:
                self.conn.execute(f"ALTER TABLE usuarios ADD COLUMN {nome} {ddl}")
        # Banco antigo sem administrador: o usuário mais antigo assume o papel.
        if not self.conn.execute("SELECT 1 FROM usuarios WHERE admin = 1").fetchone():
            self.conn.execute(
                "UPDATE usuarios SET admin = 1 "
                "WHERE rowid = (SELECT MIN(rowid) FROM usuarios)"
            )

    def cadastrar(self, usuario: str, senha: str) -> None:
        usuario = usuario.strip()
        if not USUARIO_RE.match(usuario):
            raise ErroAutenticacao(
                "Usuário deve ter de 3 a 20 caracteres (letras, números, _ . -)."
            )
        _validar_senha(senha)
        sal = os.urandom(16)
        # O primeiro usuário cadastrado vira administrador.
        primeiro = self.conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO usuarios (usuario, sal, senha_hash, criado_em, admin) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (usuario, sal, _hash_senha(senha, sal), self._agora(), int(primeiro)),
                )
        except sqlite3.IntegrityError:
            raise ErroAutenticacao("Usuário já existe!") from None

    def autenticar(self, usuario: str, senha: str) -> bool:
        """True se as credenciais estão certas, False se erradas.

        Lança ErroAutenticacao se a conta estiver bloqueada por excesso de tentativas.
        """
        usuario = usuario.strip()
        linha = self.conn.execute(
            "SELECT sal, senha_hash, tentativas, bloqueado_ate "
            "FROM usuarios WHERE usuario = ?",
            (usuario,),
        ).fetchone()
        if linha is None:
            _hash_senha(senha, bytes(16))  # gasta o mesmo tempo, não revela se o usuário existe
            return False

        sal, esperado, tentativas, bloqueado_ate = linha
        agora = self._agora()
        if bloqueado_ate > agora:
            minutos = math.ceil((bloqueado_ate - agora) / 60)
            raise ErroAutenticacao(
                f"Conta bloqueada. Tente novamente em {minutos} min."
            )

        if hmac.compare_digest(_hash_senha(senha, sal), esperado):
            if tentativas:
                self._atualizar_bloqueio(usuario, 0, 0)
            return True

        tentativas += 1
        if tentativas >= MAX_TENTATIVAS:
            self._atualizar_bloqueio(usuario, 0, agora + BLOQUEIO_SEGUNDOS)
            raise ErroAutenticacao(
                f"Muitas tentativas. Conta bloqueada por {BLOQUEIO_SEGUNDOS // 60} minutos."
            )
        self._atualizar_bloqueio(usuario, tentativas, 0)
        return False

    def _atualizar_bloqueio(self, usuario: str, tentativas: int, bloqueado_ate: float) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE usuarios SET tentativas = ?, bloqueado_ate = ? WHERE usuario = ?",
                (tentativas, bloqueado_ate, usuario),
            )

    def alterar_senha(self, usuario: str, senha_atual: str, nova_senha: str) -> None:
        usuario = usuario.strip()
        if not self.autenticar(usuario, senha_atual):
            raise ErroAutenticacao("Senha atual incorreta.")
        _validar_senha(nova_senha)
        if nova_senha == senha_atual:
            raise ErroAutenticacao("A nova senha deve ser diferente da atual.")
        sal = os.urandom(16)
        with self.conn:
            self.conn.execute(
                "UPDATE usuarios SET sal = ?, senha_hash = ? WHERE usuario = ?",
                (sal, _hash_senha(nova_senha, sal), usuario),
            )

    def data_criacao(self, usuario: str):
        """Data de criação da conta, ou None se desconhecida."""
        linha = self.conn.execute(
            "SELECT criado_em FROM usuarios WHERE usuario = ?", (usuario.strip(),)
        ).fetchone()
        if not linha or not linha[0]:
            return None
        return datetime.fromtimestamp(linha[0])

    # ---------- administração ----------

    def eh_admin(self, usuario: str) -> bool:
        linha = self.conn.execute(
            "SELECT admin FROM usuarios WHERE usuario = ?", (usuario.strip(),)
        ).fetchone()
        return bool(linha and linha[0])

    def _exigir_admin(self, solicitante: str) -> None:
        if not self.eh_admin(solicitante):
            raise ErroAutenticacao("Acesso negado: apenas administradores.")

    def listar_usuarios(self, solicitante: str) -> list:
        """Lista os usuários (sem dados sensíveis). Somente administradores."""
        self._exigir_admin(solicitante)
        agora = self._agora()
        linhas = self.conn.execute(
            "SELECT usuario, admin, criado_em, bloqueado_ate "
            "FROM usuarios ORDER BY usuario COLLATE NOCASE"
        ).fetchall()
        return [
            {
                "usuario": nome,
                "admin": bool(admin),
                "criado_em": datetime.fromtimestamp(criado) if criado else None,
                "bloqueio_restante": max(0.0, bloqueado_ate - agora),
            }
            for nome, admin, criado, bloqueado_ate in linhas
        ]

    def desbloquear(self, solicitante: str, usuario: str) -> None:
        """Remove o bloqueio e zera as tentativas de um usuário. Somente administradores."""
        self._exigir_admin(solicitante)
        with self.conn:
            cur = self.conn.execute(
                "UPDATE usuarios SET tentativas = 0, bloqueado_ate = 0 WHERE usuario = ?",
                (usuario.strip(),),
            )
        if cur.rowcount == 0:
            raise ErroAutenticacao("Usuário não encontrado.")

    def fechar(self) -> None:
        self.conn.close()