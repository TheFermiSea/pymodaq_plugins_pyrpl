# -*- coding: utf-8 -*-
"""
Configuration Management for PyMoDAQ PyRPL Plugins

This module provides centralized configuration management using PyMoDAQ's
standard configuration system. It handles plugin settings, hardware parameters,
and user preferences in a standardized way.

Classes:
    PyRPLConfig: Main configuration class for PyRPL plugins
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pymodaq_utils.config import BaseConfig
from pymodaq_utils.config import get_set_local_dir

logger = logging.getLogger(__name__)

# Default configuration values - PACKAGE LEVEL SETTINGS ONLY
# NOTE: Plugin parameter defaults (hostnames, gains, etc.) are defined in plugin classes
# This config is for application-level settings: logging, paths, performance tuning
DEFAULT_PYRPL_CONFIG = {
    'logging': {
        'enable_debug_logging': False,
        'log_hardware_communications': False,
        'log_file_rotation': True,
        'max_log_files': 10,
        'log_level': 'INFO'
    },
    'performance': {
        'thread_pool_size': 4,
        'connection_pool_max': 5,
        'cache_timeout': 300  # seconds
    },
    'paths': {
        'config_dir': None,  # Auto-detected if None
        'log_dir': None,     # Auto-detected if None
        'cache_dir': None    # Auto-detected if None
    }
}


class PyRPLConfig(BaseConfig):
    """
    Configuration management for PyMoDAQ PyRPL plugins.
    
    This class handles all configuration aspects of PyRPL plugins including
    hardware settings, connection parameters, and user preferences using
    PyMoDAQ's standard configuration framework.
    
    Attributes:
        config_name: Name of the configuration file
        config_path: Path to configuration directory
    """
    
    config_name = 'pymodaq_plugins_pyrpl'
    
    @property
    def config_template_path(self):
        """Path to the configuration template file"""
        return Path(__file__).parent.joinpath('resources/config_template.toml')
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize PyRPL configuration.
        
        Parameters:
            config_path: Optional custom path for config files
        """
        # Store config path without setting property
        if config_path is not None:
            self._config_path = config_path
        
        super().__init__()
        
        # Use PyMoDAQ's standard config path if not specified
        if config_path is None:
            try:
                config_path = get_set_local_dir()
            except Exception:
                # Fallback to user home directory
                config_path = Path.home() / '.pymodaq' / 'pyrpl_configs'
                
        self._config_path = Path(config_path)
        self._config_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize with defaults
        self._config_data = DEFAULT_PYRPL_CONFIG.copy()
        
        # Load existing configuration
        self.load_config()
        
        logger.info(f"PyRPL configuration initialized at {self.config_path}")
    
    def get_config_file_path(self) -> Path:
        """Get the full path to the configuration file."""
        return self.config_path / f"{self.config_name}.toml"
    
    def load_config(self, config_name=None, config_template_path=None) -> bool:
        """
        Load configuration from file.
        
        Args:
            config_name: Optional config name (for compatibility with BaseConfig)
            config_template_path: Optional template path (for compatibility with BaseConfig)
        
        Returns:
            True if configuration loaded successfully, False otherwise
        """
        config_file = self.get_config_file_path()
        
        if not config_file.exists():
            logger.info(f"No existing config found at {config_file}, using defaults")
            return self.save_config()
        
        try:
            import toml
            with open(config_file, 'r') as f:
                loaded_config = toml.load(f)
            
            # Merge with defaults to ensure all keys exist
            self._merge_config(self._config_data, loaded_config)
            
            logger.info(f"Configuration loaded from {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            logger.info("Using default configuration")
            return False
    
    def save_config(self) -> bool:
        """
        Save current configuration to file.
        
        Returns:
            True if saved successfully, False otherwise
        """
        config_file = self.get_config_file_path()
        
        try:
            import toml
            with open(config_file, 'w') as f:
                toml.dump(self._config_data, f)
            
            logger.info(f"Configuration saved to {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def _merge_config(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> None:
        """
        Recursively merge loaded configuration with defaults.
        
        Parameters:
            default: Default configuration dictionary
            loaded: Loaded configuration dictionary
        """
        for key, value in loaded.items():
            if key in default:
                if isinstance(default[key], dict) and isinstance(value, dict):
                    self._merge_config(default[key], value)
                else:
                    default[key] = value
            else:
                # New configuration key not in defaults
                default[key] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Parameters:
            key_path: Dot-separated path to configuration value
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            keys = key_path.split('.')
            value = self._config_data
            
            for key in keys:
                value = value[key]
            
            return value
            
        except (KeyError, TypeError):
            logger.debug(f"Configuration key '{key_path}' not found, using default: {default}")
            return default
    
    def set(self, key_path: str, value: Any, save: bool = True) -> bool:
        """
        Set configuration value using dot notation.
        
        Parameters:
            key_path: Dot-separated path to configuration value
            value: Value to set
            save: Whether to save configuration immediately
            
        Returns:
            True if set successfully, False otherwise
        """
        try:
            keys = key_path.split('.')
            config = self._config_data
            
            # Navigate to parent dictionary
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            
            # Set the value
            config[keys[-1]] = value
            
            if save:
                self.save_config()
            
            logger.debug(f"Configuration '{key_path}' set to: {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set configuration '{key_path}': {e}")
            return False
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self._config_data.get('logging', {})

    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance tuning configuration."""
        return self._config_data.get('performance', {})

    def get_paths_config(self) -> Dict[str, Any]:
        """Get path configuration."""
        return self._config_data.get('paths', {})

    def is_debug_logging_enabled(self) -> bool:
        """Check if debug logging is enabled."""
        return self.get('logging.enable_debug_logging', False)

    def enable_debug_logging(self, enabled: bool = True) -> None:
        """Enable or disable debug logging."""
        self.set('logging.enable_debug_logging', enabled)

    def get_log_level(self) -> str:
        """Get configured log level."""
        return self.get('logging.log_level', 'INFO')
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults."""
        self._config_data = DEFAULT_PYRPL_CONFIG.copy()
        return self.save_config()
    
    def export_config(self, file_path: Path) -> bool:
        """
        Export configuration to external file.
        
        Parameters:
            file_path: Path to export file
            
        Returns:
            True if exported successfully, False otherwise
        """
        try:
            import toml
            with open(file_path, 'w') as f:
                toml.dump(self._config_data, f)
            
            logger.info(f"Configuration exported to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return False
    
    def import_config(self, file_path: Path) -> bool:
        """
        Import configuration from external file.
        
        Parameters:
            file_path: Path to import file
            
        Returns:
            True if imported successfully, False otherwise
        """
        try:
            import toml
            with open(file_path, 'r') as f:
                imported_config = toml.load(f)
            
            # Merge with existing configuration
            self._merge_config(self._config_data, imported_config)
            
            # Save merged configuration
            self.save_config()
            
            logger.info(f"Configuration imported from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            return False


# Global configuration instance
_pyrpl_config = None

def get_pyrpl_config() -> PyRPLConfig:
    """
    Get the global PyRPL configuration instance.
    
    Returns:
        Global PyRPL configuration instance
    """
    global _pyrpl_config
    if _pyrpl_config is None:
        _pyrpl_config = PyRPLConfig()
    return _pyrpl_config


def reset_pyrpl_config() -> None:
    """Reset the global configuration instance."""
    global _pyrpl_config
    _pyrpl_config = None


if __name__ == '__main__':
    # Test configuration system
    config = PyRPLConfig()
    
    # Test basic operations
    print(f"Default hostname: {config.get_default_hostname()}")
    print(f"PID defaults: {config.get_pid_defaults()}")
    print(f"Mock mode: {config.is_mock_mode_enabled()}")
    
    # Test setting values
    config.set('test.value', 42)
    print(f"Test value: {config.get('test.value')}")
    
    # Test recent hostnames
    config.update_recent_hostname('rp-test1.local')
    config.update_recent_hostname('rp-test2.local')
    print(f"Recent hostnames: {config.get_recent_hostnames()}")
    
    print("Configuration system test completed successfully!")