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

# Default configuration values
DEFAULT_PYRPL_CONFIG = {
    'connection': {
        'default_hostname': 'rp-f08d6c.local',
        'connection_timeout': 10.0,
        'config_name': 'pymodaq_pyrpl',
        'auto_reconnect': True,
        'retry_attempts': 3,
        'retry_delay': 2.0
    },
    'hardware': {
        'voltage_range': 1.0,  # ±1V Red Pitaya limit
        'default_decimation': 64,
        'max_acquisition_time': 10.0,
        'pid_default_gains': {
            'p': 0.1,
            'i': 0.01,
            'd': 0.0
        },
        'asg_defaults': {
            'frequency': 1000.0,
            'amplitude': 0.1,
            'waveform': 'sin'
        },
        'scope_defaults': {
            'decimation': 64,
            'trigger_source': 'immediately',
            'trigger_delay': 0.0,
            'average': 1
        },
        'iq_defaults': {
            'frequency': 1000.0,
            'bandwidth': 100.0,
            'acbandwidth': 10000.0,
            'phase': 0.0,
            'gain': 1.0
        }
    },
    'acquisition': {
        'default_timeout': 2.0,
        'max_retries': 3,
        'sampling_rate': 10.0,
        'max_samples': 16384
    },
    'ui': {
        'update_frequency': 10.0,  # Hz
        'auto_scale': True,
        'show_advanced_settings': False,
        'remember_window_position': True
    },
    'logging': {
        'enable_debug_logging': False,
        'log_hardware_communications': False,
        'log_file_rotation': True,
        'max_log_files': 10
    },
    'mock_mode': {
        'enabled': False,
        'noise_level': 0.005,  # 5mV
        'signal_amplitude': 0.1,  # 100mV
        'update_rate': 100.0  # Hz
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
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize PyRPL configuration.
        
        Parameters:
            config_path: Optional custom path for config files
        """
        super().__init__()
        
        # Use PyMoDAQ's standard config path if not specified
        if config_path is None:
            try:
                config_path = get_set_local_dir()
            except Exception:
                # Fallback to user home directory
                config_path = Path.home() / '.pymodaq' / 'pyrpl_configs'
                
        self.config_path = Path(config_path)
        self.config_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize with defaults
        self._config_data = DEFAULT_PYRPL_CONFIG.copy()
        
        # Load existing configuration
        self.load_config()
        
        logger.info(f"PyRPL configuration initialized at {self.config_path}")
    
    def get_config_file_path(self) -> Path:
        """Get the full path to the configuration file."""
        return self.config_path / f"{self.config_name}.toml"
    
    def load_config(self) -> bool:
        """
        Load configuration from file.
        
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
    
    def get_connection_config(self) -> Dict[str, Any]:
        """Get connection-related configuration."""
        return self._config_data.get('connection', {})
    
    def get_hardware_config(self) -> Dict[str, Any]:
        """Get hardware-related configuration."""
        return self._config_data.get('hardware', {})
    
    def get_acquisition_config(self) -> Dict[str, Any]:
        """Get acquisition-related configuration."""
        return self._config_data.get('acquisition', {})
    
    def get_ui_config(self) -> Dict[str, Any]:
        """Get UI-related configuration."""
        return self._config_data.get('ui', {})
    
    def is_mock_mode_enabled(self) -> bool:
        """Check if mock mode is enabled."""
        return self.get('mock_mode.enabled', False)
    
    def enable_mock_mode(self, enabled: bool = True) -> None:
        """Enable or disable mock mode."""
        self.set('mock_mode.enabled', enabled)
    
    def get_default_hostname(self) -> str:
        """Get default Red Pitaya hostname."""
        return self.get('connection.default_hostname', 'rp-f08d6c.local')
    
    def set_default_hostname(self, hostname: str) -> None:
        """Set default Red Pitaya hostname."""
        self.set('connection.default_hostname', hostname)
    
    def get_pid_defaults(self) -> Dict[str, float]:
        """Get default PID gains."""
        return self.get('hardware.pid_default_gains', {'p': 0.1, 'i': 0.01, 'd': 0.0})
    
    def update_recent_hostname(self, hostname: str) -> None:
        """Add hostname to recent connections."""
        recent = self.get('connection.recent_hostnames', [])
        
        # Remove if already exists
        if hostname in recent:
            recent.remove(hostname)
        
        # Add to front
        recent.insert(0, hostname)
        
        # Keep only last 10
        recent = recent[:10]
        
        self.set('connection.recent_hostnames', recent)
    
    def get_recent_hostnames(self) -> list:
        """Get list of recent hostnames."""
        return self.get('connection.recent_hostnames', [])
    
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