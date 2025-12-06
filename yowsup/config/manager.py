from ..config.v1.config import Config
from ..config.transforms.dict_keyval import DictKeyValTransform
from ..config.transforms.dict_json import DictJsonTransform
from ..config.v1.serialize import ConfigSerialize
from ..common.tools import StorageTools
from loguru import logger
import os


class ConfigManager(object):
    NAME_FILE_CONFIG = "config"

    TYPE_KEYVAL = 1
    TYPE_JSON = 2

    TYPE_NAMES = {
        TYPE_KEYVAL: "keyval",
        TYPE_JSON: "json"
    }

    MAP_EXT = {
        "yo": TYPE_KEYVAL,
        "json": TYPE_JSON,
    }

    TYPES = {
        TYPE_KEYVAL: DictKeyValTransform,
        TYPE_JSON: DictJsonTransform
    }

    def load(self, path_or_profile_name, profile_only=False):
        # type: (str, bool) -> Config
        """
        Loads a Config instance directly from the unified database (ProfileConfig).

        The argument path_or_profile_name is treated as a logical profile name
        (typically the phone number or phone_deviceid). File-based config
        loading (config.json, .yo, etc.) is no longer used.

        :param path_or_profile_name: logical profile identifier
        :param profile_only: kept for backward compatibility (ignored)
        :return Config instance, or None if no config could be found
        """
        logger.debug(f"load(path_or_profile_name={path_or_profile_name}, profile_only={profile_only})")

        profile_name = path_or_profile_name

        # Load from DB-backed ProfileConfig (JSON only)
        db_cfg = StorageTools.readProfileConfig(profile_name, None)
        if db_cfg:
            logger.debug(f"Loaded config for profile={profile_name} from ProfileConfig DB")
            if isinstance(db_cfg, (bytes, bytearray)):
                data_str = db_cfg.decode()
            else:
                data_str = db_cfg
            datadict = DictJsonTransform().reverse(data_str)
            return self.load_data(datadict)

        logger.error(f"Could not find a config for profile={profile_name} in ProfileConfig DB")

    def _type_to_str(self, type):
        """
        :param type:
        :type type: int
        :return:
        :rtype:
        """
        for key, val in self.TYPE_NAMES.items():
            if key == type:
                return val

    def _load_path(self, path):
        """
        :param path:
        :type path:
        :return:
        :rtype:
        """
        logger.debug(f"_load_path(path={path})")
        if os.path.isfile(path):
            configtype = self.guess_type(path)
            logger.debug(f"Detected config type: {self._type_to_str(configtype)}")
            if configtype in self.TYPES:
                logger.debug("Opening config for reading")
                with open(path, 'r') as f:
                    data = f.read()
                datadict = self.TYPES[configtype]().reverse(data)
                return self.load_data(datadict)
            else:
                raise ValueError("Unsupported config type")
        else:
            logger.debug(f"_load_path couldn't find the path: {path}")

    def load_data(self, datadict):
        logger.debug("Loading config")
        return ConfigSerialize(Config).deserialize(datadict)

    def guess_type(self, config_path):
        dissected = os.path.splitext(config_path)
        if len(dissected) > 1:
            ext = dissected[1][1:].lower()
            config_type = self.MAP_EXT[ext] if ext in self.MAP_EXT else None
        else:
            config_type = None

        if config_type is not None:
            return config_type
        else:
            logger.debug("Trying auto detect config type by parsing")
            with open(config_path, 'r') as f:
                data = f.read()
            for config_type, transform in self.TYPES.items():
                config_type_str = self.TYPE_NAMES[config_type]
                try:
                    logger.debug(f"Trying to parse as {config_type_str}")
                    if transform().reverse(data):
                        logger.debug(f"Successfully detected {config_type_str} as config type for {config_path}")
                        return config_type
                except Exception as ex:
                    logger.debug(f"{config_path} was not parseable as {config_type_str}, reason: {ex}")

    def get_str_transform(self, serialize_type):
        if serialize_type in self.TYPES:
            return self.TYPES[serialize_type]()

    def config_to_str(self, config, serialize_type=TYPE_JSON):
        transform = self.get_str_transform(serialize_type)
        if transform is not None:
            return transform.transform(ConfigSerialize(config.__class__).serialize(config))

        raise ValueError("unrecognized serialize_type=%d" % serialize_type)

    def save(self, profile_name, config, serialize_type=TYPE_JSON, dest=None):
        """
        Persists a Config instance for the given profile_name directly into
        the unified database (ProfileConfig table).

        The dest parameter is kept for backward compatibility but is ignored;
        file-based config saving is no longer supported.
        """
        if dest is not None:
            logger.warning(
                "ConfigManager.save(..., dest=...) is deprecated and ignored; "
                "config is always stored in the database now."
            )

        outputdata = self.config_to_str(config, serialize_type)
        print(outputdata)
        StorageTools.writeProfileConfig(profile_name, outputdata)
