from ..axolotl.manager import AxolotlManager
from ..axolotl.store.sqlaxolotlstore import SqlAxolotlStore
from loguru import logger


class AxolotlManagerFactory(object):
    """
    Factory that always uses the unified SQLAlchemy-backed Axolotl store.

    All accounts share a single database (see app/db.py), and data is
    linked via foreign keys to the Account table.
    """

    def get_manager(self, profile_name, username):
        logger.debug(f"get_manager(profile_name={profile_name}, username={username})")

        # Unified backend: single DB, multi-account schema
        store = SqlAxolotlStore(username)

        return AxolotlManager(store, username)
