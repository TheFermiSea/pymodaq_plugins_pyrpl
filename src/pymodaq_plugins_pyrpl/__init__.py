from pathlib import Path
from .utils import Config as ConfigClass
# Import Config directly from utils.py to avoid conflicts with utils/ subdirectory
import sys
from pathlib import Path
import importlib.util
utils_file = Path(__file__).parent / 'utils.py'
spec = importlib.util.spec_from_file_location("pyrpl_config", utils_file)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
Config = config_module.Config
from pymodaq_utils.utils import get_version, PackageNotFoundError
from pymodaq_utils.logger import set_logger, get_module_name

config = Config()
try:
    __version__ = get_version(__package__)
except PackageNotFoundError:
    __version__ = '0.0.0dev'



