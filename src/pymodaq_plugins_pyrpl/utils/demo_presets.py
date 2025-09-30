# -*- coding: utf-8 -*-
"""
Demonstration Presets for PyMoDAQ PyRPL Mock System

This module provides pre-configured settings and scenarios for demonstrating
the PyRPL PID control system in mock mode. These presets are designed for
educational purposes and system evaluation.

Classes:
    DemoPreset: Configuration container for demonstration scenarios
    DemoPresetManager: Manager for loading and applying demo configurations

Author: PyMoDAQ PyRPL Plugin Development
License: MIT
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from .mock_simulation import ScenarioType

logger = logging.getLogger(__name__)


@dataclass
class DemoPreset:
    """
    Configuration preset for PyMoDAQ PyRPL demonstration scenarios.

    This class encapsulates all the settings needed to configure the PyRPL
    plugins for specific demonstration scenarios, including PID parameters,
    plant characteristics, and display settings.
    """
    name: str
    description: str
    scenario_type: ScenarioType

    # PID Controller Settings
    pid_p_gain: float = 1.0
    pid_i_gain: float = 0.1
    pid_d_gain: float = 0.0

    # Simulation Settings
    mock_hostname: str = "demo.pyrpl.local"

    # Display Settings
    measurement_channels: List[str] = None
    scope_decimation: int = 64
    scope_trigger: str = "immediately"

    # Expected Performance
    expected_settling_time: float = 10.0
    expected_overshoot: float = 20.0

    def __post_init__(self):
        """Initialize default measurement channels if not provided."""
        if self.measurement_channels is None:
            self.measurement_channels = ["Process Variable", "Controller Output", "Setpoint"]

    def to_dict(self) -> Dict[str, Any]:
        """Convert preset to dictionary format."""
        result = asdict(self)
        result['scenario_type'] = self.scenario_type.value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DemoPreset':
        """Create preset from dictionary data."""
        if 'scenario_type' in data and isinstance(data['scenario_type'], str):
            data['scenario_type'] = ScenarioType(data['scenario_type'])
        return cls(**data)


class DemoPresetManager:
    """
    Manager for PyMoDAQ PyRPL demonstration presets.

    This class provides methods to load, save, and apply demonstration
    configurations for educational and evaluation purposes.
    """

    def __init__(self):
        """Initialize preset manager with default configurations."""
        self._presets: Dict[str, DemoPreset] = {}
        self._create_default_presets()

    def _create_default_presets(self):
        """Create standard demonstration presets."""

        # Stable System - Good for beginners
        self._presets["stable_basic"] = DemoPreset(
            name="Stable System - Basic PID",
            description="Well-behaved plant with conservative PID tuning. Good for learning basic control concepts.",
            scenario_type=ScenarioType.STABLE_SYSTEM,
            pid_p_gain=0.5,
            pid_i_gain=0.05,
            pid_d_gain=0.0,
            expected_settling_time=8.0,
            expected_overshoot=5.0
        )

        # Stable System - Optimized
        self._presets["stable_optimized"] = DemoPreset(
            name="Stable System - Optimized PID",
            description="Well-behaved plant with aggressive tuning for fast response.",
            scenario_type=ScenarioType.STABLE_SYSTEM,
            pid_p_gain=1.2,
            pid_i_gain=0.15,
            pid_d_gain=0.05,
            expected_settling_time=4.0,
            expected_overshoot=15.0
        )

        # Oscillatory System - Demonstrates challenges
        self._presets["oscillatory_challenge"] = DemoPreset(
            name="Oscillatory System - Control Challenge",
            description="High gain, low damping plant that tends to oscillate. Demonstrates need for careful tuning.",
            scenario_type=ScenarioType.OSCILLATORY_SYSTEM,
            pid_p_gain=0.3,
            pid_i_gain=0.02,
            pid_d_gain=0.1,
            expected_settling_time=15.0,
            expected_overshoot=30.0
        )

        # Sluggish System - Demonstrates integral action
        self._presets["sluggish_integral"] = DemoPreset(
            name="Sluggish System - Integral Action Demo",
            description="Slow responding plant requiring strong integral action to eliminate steady-state error.",
            scenario_type=ScenarioType.SLUGGISH_SYSTEM,
            pid_p_gain=2.0,
            pid_i_gain=0.4,
            pid_d_gain=0.0,
            expected_settling_time=20.0,
            expected_overshoot=10.0
        )

        # Noisy Environment - Demonstrates derivative filtering
        self._presets["noisy_derivative"] = DemoPreset(
            name="Noisy Environment - Derivative Filtering",
            description="Plant with significant measurement noise. Shows importance of derivative filtering.",
            scenario_type=ScenarioType.NOISY_ENVIRONMENT,
            pid_p_gain=0.8,
            pid_i_gain=0.1,
            pid_d_gain=0.02,  # Low D-gain due to noise
            expected_settling_time=12.0,
            expected_overshoot=25.0
        )

        # Integrating Process - Level control
        self._presets["integrating_level"] = DemoPreset(
            name="Integrating Process - Level Control",
            description="Self-integrating plant (like tank level). Demonstrates PI control without derivative.",
            scenario_type=ScenarioType.INTEGRATING_PROCESS,
            pid_p_gain=0.6,
            pid_i_gain=0.08,
            pid_d_gain=0.0,  # No derivative for integrating processes
            expected_settling_time=25.0,
            expected_overshoot=0.0  # PI control should not overshoot
        )

        logger.info(f"Created {len(self._presets)} default demonstration presets")

    def get_preset(self, name: str) -> Optional[DemoPreset]:
        """Get preset by name."""
        return self._presets.get(name)

    def list_presets(self) -> List[str]:
        """Get list of available preset names."""
        return list(self._presets.keys())

    def get_preset_info(self, name: str) -> Optional[Dict[str, str]]:
        """Get basic information about a preset."""
        preset = self._presets.get(name)
        if preset is None:
            return None

        return {
            'name': preset.name,
            'description': preset.description,
            'scenario': preset.scenario_type.value,
            'pid_settings': f"P={preset.pid_p_gain}, I={preset.pid_i_gain}, D={preset.pid_d_gain}"
        }

    def apply_preset_to_pid_plugin(self, preset_name: str, pid_plugin) -> bool:
        """
        Apply preset configuration to a PID move plugin.

        Parameters:
            preset_name: Name of the preset to apply
            pid_plugin: Instance of DAQ_Move_PyRPL_PID plugin

        Returns:
            True if successfully applied, False otherwise
        """
        preset = self.get_preset(preset_name)
        if preset is None:
            logger.error(f"Preset '{preset_name}' not found")
            return False

        try:
            # Apply mock configuration
            pid_plugin.settings.child('connection', 'mock_mode').setValue(True)
            pid_plugin.settings.child('connection', 'redpitaya_host').setValue(preset.mock_hostname)
            pid_plugin.settings.child('mock_scenario').setValue(preset.scenario_type.value)

            # Apply PID gains
            pid_plugin.settings.child('pid_gains', 'p_gain').setValue(preset.pid_p_gain)
            pid_plugin.settings.child('pid_gains', 'i_gain').setValue(preset.pid_i_gain)
            pid_plugin.settings.child('pid_gains', 'd_gain').setValue(preset.pid_d_gain)

            logger.info(f"Applied preset '{preset_name}' to PID plugin")
            return True

        except Exception as e:
            logger.error(f"Failed to apply preset '{preset_name}': {e}")
            return False

    def apply_preset_to_viewer_plugin(self, preset_name: str, viewer_plugin) -> bool:
        """
        Apply preset configuration to a viewer plugin.

        Parameters:
            preset_name: Name of the preset to apply
            viewer_plugin: Instance of PyRPL viewer plugin

        Returns:
            True if successfully applied, False otherwise
        """
        preset = self.get_preset(preset_name)
        if preset is None:
            logger.error(f"Preset '{preset_name}' not found")
            return False

        try:
            # Apply mock configuration
            viewer_plugin.settings.child('connection', 'mock_mode').setValue(True)
            viewer_plugin.settings.child('connection', 'redpitaya_host').setValue(preset.mock_hostname)

            # Apply scope settings if applicable
            if hasattr(viewer_plugin, 'settings') and 'scope_settings' in viewer_plugin.settings.childNames():
                viewer_plugin.settings.child('scope_settings', 'decimation').setValue(preset.scope_decimation)
                viewer_plugin.settings.child('scope_settings', 'trigger_source').setValue(preset.scope_trigger)

            logger.info(f"Applied preset '{preset_name}' to viewer plugin")
            return True

        except Exception as e:
            logger.error(f"Failed to apply preset '{preset_name}' to viewer: {e}")
            return False

    def create_demo_scenario_guide(self) -> str:
        """
        Create a text guide describing all demonstration scenarios.

        Returns:
            Formatted text describing each preset and its educational purpose
        """
        guide_lines = [
            "PyMoDAQ PyRPL Mock Demonstration Scenarios",
            "=" * 45,
            "",
            "This guide describes the available demonstration presets for",
            "learning PID control concepts using the PyMoDAQ PyRPL plugins.",
            ""
        ]

        for preset_name in sorted(self._presets.keys()):
            preset = self._presets[preset_name]
            guide_lines.extend([
                f"Preset: {preset_name}",
                "-" * (8 + len(preset_name)),
                f"Name: {preset.name}",
                f"Description: {preset.description}",
                f"Plant Type: {preset.scenario_type.value.replace('_', ' ').title()}",
                f"PID Settings: P={preset.pid_p_gain}, I={preset.pid_i_gain}, D={preset.pid_d_gain}",
                f"Expected Performance: Settling={preset.expected_settling_time}s, Overshoot={preset.expected_overshoot}%",
                ""
            ])

        guide_lines.extend([
            "Usage Instructions:",
            "-" * 19,
            "1. Set plugin to mock_mode = True",
            "2. Load desired preset using DemoPresetManager",
            "3. Initialize plugins and start demonstration",
            "4. Observe system response and performance metrics",
            "5. Try different presets to compare control strategies",
            ""
        ])

        return "\n".join(guide_lines)


# Global preset manager instance
_preset_manager = None

def get_demo_preset_manager() -> DemoPresetManager:
    """Get global demo preset manager instance."""
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = DemoPresetManager()
    return _preset_manager


def list_demo_presets() -> List[str]:
    """Convenience function to list available demo presets."""
    return get_demo_preset_manager().list_presets()


def apply_demo_preset(preset_name: str, plugin, plugin_type: str = "auto") -> bool:
    """
    Convenience function to apply demo preset to a plugin.

    Parameters:
        preset_name: Name of preset to apply
        plugin: Plugin instance
        plugin_type: Type of plugin ("pid", "viewer", or "auto" for auto-detection)

    Returns:
        True if successfully applied, False otherwise
    """
    manager = get_demo_preset_manager()

    if plugin_type == "auto":
        # Auto-detect plugin type
        class_name = plugin.__class__.__name__
        if "Move" in class_name and "PID" in class_name:
            plugin_type = "pid"
        elif "Viewer" in class_name:
            plugin_type = "viewer"
        else:
            logger.error(f"Cannot auto-detect plugin type for {class_name}")
            return False

    if plugin_type == "pid":
        return manager.apply_preset_to_pid_plugin(preset_name, plugin)
    elif plugin_type == "viewer":
        return manager.apply_preset_to_viewer_plugin(preset_name, plugin)
    else:
        logger.error(f"Unknown plugin type: {plugin_type}")
        return False


if __name__ == "__main__":
    # Demo script for testing presets
    manager = get_demo_preset_manager()

    print("Available Demo Presets:")
    print("=" * 30)
    for preset_name in manager.list_presets():
        info = manager.get_preset_info(preset_name)
        print(f"{preset_name}: {info['name']}")
        print(f"  {info['description']}")
        print(f"  Settings: {info['pid_settings']}")
        print()

    print("\nDemo Scenario Guide:")
    print(manager.create_demo_scenario_guide())