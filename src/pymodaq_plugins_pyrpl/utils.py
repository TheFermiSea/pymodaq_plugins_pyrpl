# -*- coding: utf-8 -*-
"""
Created the 31/08/2023

@author: Sebastien Weber
"""
from pathlib import Path

from pymodaq_utils.config import BaseConfig, USER


class Config(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = Path(__file__).parent.joinpath('resources/config_template.toml')
    
    # Handle package name safely
    if __package__:
        config_name = f"config_{__package__.split('pymodaq_plugins_')[1]}"
    else:
        config_name = "config_pyrpl"
