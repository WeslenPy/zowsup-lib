from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os

from zowsuplib.conf.constants import SysVar


@dataclass
class AppConfig:
    """
    Configuração de alto nível da aplicação.

    Esta classe é uma camada fina por cima de SysVar, oferecendo:
    - carregamento centralizado do arquivo config.conf
    - possibilidade de sobrescrever o caminho via variável de ambiente ZOWSUP_CONFIG
    - acesso tipado aos caminhos principais
    """

    account_path: Path
    download_path: Path
    upload_path: Path
    log_path: Path
    default_env: str
    cmd_wait: Optional[int] = None

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "AppConfig":
        """
        Carrega configuração a partir de um arquivo.

        Ordem de resolução:
        1. Parâmetro config_path, se fornecido
        2. Variável de ambiente ZOWSUP_CONFIG
        3. Caminho padrão (conf/config.conf)
        """
        if config_path is None:
            config_path = os.environ.get("ZOWSUP_CONFIG")

        # Este método inicializa SysVar.* e garante criação de diretórios
        SysVar.loadConfig(config_path)

        return cls(
            account_path=Path(SysVar.ACCOUNT_PATH),
            download_path=Path(SysVar.DOWNLOAD_PATH),
            upload_path=Path(SysVar.UPLOAD_PATH),
            log_path=Path(SysVar.LOG_PATH),
            default_env=SysVar.DEFAULT_ENV,
            cmd_wait=SysVar.CMD_WAIT,
        )

    def apply_to_sysvar(self) -> None:
        """
        Aplica os valores desta configuração de volta em SysVar.

        Útil quando a configuração é criada manualmente em memória e
        queremos que o restante do código legado continue funcionando.
        """
        SysVar.bind_context(
            {
                "ACCOUNT_PATH": str(self.account_path),
                "DOWNLOAD_PATH": str(self.download_path),
                "UPLOAD_PATH": str(self.upload_path),
                "LOG_PATH": str(self.log_path),
                "DEFAULT_ENV": self.default_env,
                "CMD_WAIT": self.cmd_wait,
            }
        )
        SysVar.ensure_dirs()




