# -*- coding: utf-8 -*-
"""
Created the 31/08/2023

@author: Sebastien Weber
"""
from pathlib import Path

from pymodaq_utils.config import BaseConfig, USER


class Config(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_name = "config_pyrpl"  # Simplified name to avoid __package__ issues
    
    @property
    def config_template_path(self):
        """Path to the configuration template file"""
        return Path(__file__).parent.joinpath('resources/config_template.toml')
