"""
Importa todas as contas listadas em `accounts_unblocked.txt` (formato 6-parts).

Execução:
    python t_impot.py
"""

from pathlib import Path
from typing import List

from loguru import logger

from zowsuplib.app.api import ZowsupClient
from zowsuplib.settings.conf import settings
from zowsuplib.app.db import SessionLocal, init_db

# Todas as contas serão importadas usando ambiente smb_android
ENV_NAME = "smb_android"
ACCOUNTS_FILE = Path(__file__).parent / "accounts_unblocked.txt"

init_db()


def load_six_parts(file_path: Path) -> List[str]:
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    six_parts_list: List[str] = []
    for raw in file_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 6:
            logger.warning(f"Linha ignorada (esperado 6 campos): {line}")
            continue
        six_parts_list.append(",".join(parts))
    return six_parts_list


def import_accounts(six_parts_list: List[str]) -> None:
    for six in six_parts_list:
        try:
            phone = ZowsupClient.import_account_from_six_parts(
                six_parts_data=six,
                env=ENV_NAME,
            )
            logger.info(f"Conta importada: {phone}")
        except Exception as exc:
            logger.error(f"Falha ao importar conta: {exc}")


def main() -> None:
    logger.info(f"Iniciando importação de contas do arquivo: {ACCOUNTS_FILE}")
    six_parts_list = load_six_parts(ACCOUNTS_FILE)
    if not six_parts_list:
        logger.error("Nenhuma conta válida encontrada.")
        return
    import_accounts(six_parts_list)
    logger.info("Importação concluída.")


if __name__ == "__main__":
    main()

