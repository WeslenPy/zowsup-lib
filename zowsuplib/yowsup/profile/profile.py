from ..config.manager import ConfigManager
from ..config.v1.config import Config
from ..axolotl.manager import AxolotlManager
from ..axolotl.factory import AxolotlManagerFactory
from loguru import logger


class YowProfile(object):
    def __init__(self, profile_name, config=None):
        # type: (str, Config) -> None
        """
        :param profile_name:  profile name
        :param config: A supplied config will disable loading configs using the Config manager and provide that config
        instead
        """
        logger.debug(f"Constructed Profile(profile_name={profile_name})")
        self._profile_name = profile_name
        self._config = config
        self._config_manager = ConfigManager()
        self._axolotl_manager = None

    def __str__(self):
        return "YowProfile(profile_name=%s)" % self._profile_name

    def _load_config(self):
        # type: () -> Config
        logger.debug(f"load_config for {self._profile_name}")
        return self._config_manager.load(self._profile_name)

    def _load_axolotl_manager(self):
        # type: () -> AxolotlManager
        return AxolotlManagerFactory().get_manager(self._profile_name, self.username)

    def write_config(self, config):
        # type: (Config) -> None
        logger.debug(f"write_config for {self._profile_name}")
        self._config_manager.save(self._profile_name, config)

    @property
    def config(self):
        if self._config is None:
            self._config = self._load_config()
        return self._config

    @property
    def axolotl_manager(self):
        if self._axolotl_manager is None:
            self._axolotl_manager = self._load_axolotl_manager()
        return self._axolotl_manager

    @property
    def username(self):
        config = self.config
        return config.login or config.phone or self._profile_name


