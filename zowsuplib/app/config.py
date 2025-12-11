from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import configparser

from zowsuplib.settings.conf import settings


@dataclass
class AppConfig:
    """
    Configuração de alto nível da aplicação.

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
        2. Settings.config (ZOWSUP_CONFIG ou valor padrão)
        3. Caminho padrão (conf/config.conf)
        """
        if config_path is None:
            config_path = settings.config

        cfg = configparser.ConfigParser()
        read_ok = cfg.read(config_path)
        if not read_ok:
            # fallback para defaults
            return cls(
                account_path=Path(settings.account_path),
                download_path=Path(settings.download_path),
                upload_path=Path(settings.upload_path),
                log_path=Path(settings.log_path),
                default_env=settings.default_env,
                cmd_wait=settings.cmd_wait,
            )

        def _get(key: str, default: str) -> str:
            return cfg.get("SysVar", key, fallback=default)

        account_path = Path(_get("ACCOUNT_PATH", "/data/account/"))
        download_path = Path(_get("DOWNLOAD_PATH", "/data/download/"))
        upload_path = Path(_get("UPLOAD_PATH", "/data/upload/"))
        log_path = Path(_get("LOG_PATH", "/data/log/"))
        default_env = _get("DEFAULT_ENV", "android")

        for p in (account_path, download_path, upload_path, log_path):
            p.mkdir(parents=True, exist_ok=True)

        cmd_wait_raw = _get("CMD_WAIT", "")
        cmd_wait = int(cmd_wait_raw) if cmd_wait_raw.isdigit() else None

        return cls(
            account_path=account_path,
            download_path=download_path,
            upload_path=upload_path,
            log_path=log_path,
            default_env=default_env,
            cmd_wait=cmd_wait,
        )

