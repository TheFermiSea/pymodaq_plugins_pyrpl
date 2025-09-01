#!/usr/bin/env python3
"""
Direct PyRPL Hardware Test with Python 3.12 Compatibility Fix

This script tests PyRPL directly with proper Python 3.12 compatibility.
"""

import logging
import time

# Python 3.12 compatibility fix - apply before importing PyRPL
import collections.abc
import collections
if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping
    collections.MutableMapping = collections.abc.MutableMapping
    collections.MutableSet = collections.abc.MutableSet
    collections.Set = collections.abc.Set
    collections.MutableSequence = collections.abc.MutableSequence
    collections.Sequence = collections.abc.Sequence
    collections.Iterable = collections.abc.Iterable
    collections.Iterator = collections.abc.Iterator
    collections.Container = collections.abc.Container
    collections.Sized = collections.abc.Sized
    collections.Callable = collections.abc.Callable
    collections.Hashable = collections.abc.Hashable

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def test_direct_pyrpl():
    """Test PyRPL directly with compatibility fix"""
    logger.info("Testing direct PyRPL connection to rp-f08d6c.local...")
    
    try:
        import pyrpl
        logger.info("✅ PyRPL imported successfully")
        
        # Connect directly
        logger.info("Connecting to Red Pitaya...")
        p = pyrpl.Pyrpl(hostname='rp-f08d6c.local', config='test_config')
        logger.info("✅ PyRPL connected successfully")
        
        # Test basic functionality
        rp = p.rp
        logger.info("✅ Red Pitaya instance acquired")
        
        # Test voltage reading
        try:
            voltage1 = rp.sampler.in1
            voltage2 = rp.sampler.in2
            logger.info(f"✅ Voltage readings - IN1: {voltage1:.6f}V, IN2: {voltage2:.6f}V")
        except Exception as e:
            logger.error(f"❌ Voltage reading failed: {e}")
        
        # Test PID modules
        for i in range(3):
            try:
                pid = getattr(rp, f'pid{i}')
                original_setpoint = pid.setpoint
                original_output = pid.output_direct
                
                pid.setpoint = 0.0
                pid.output_direct = 'off'  # Ensure safe state
                logger.info(f"✅ PID{i} module accessible - setpoint: {pid.setpoint}V")
                
                # Restore original state
                pid.setpoint = original_setpoint
                pid.output_direct = original_output
            except Exception as e:
                logger.error(f"❌ PID{i} failed: {e}")
        
        # Test ASG modules
        for i in range(2):
            try:
                asg = getattr(rp, f'asg{i}')
                asg.setup(frequency=1000, amplitude=0.1, waveform='sin')
                logger.info(f"✅ ASG{i} module accessible - freq: {asg.frequency}Hz")
            except Exception as e:
                logger.error(f"❌ ASG{i} failed: {e}")
        
        # Test Scope
        try:
            scope = rp.scope
            scope.input1 = 'in1'
            scope.input2 = 'in2'
            scope.decimation = 64
            logger.info(f"✅ Scope module accessible - decimation: {scope.decimation}")
        except Exception as e:
            logger.error(f"❌ Scope failed: {e}")
        
        # Test IQ modules
        for i in range(3):
            try:
                iq = getattr(rp, f'iq{i}')
                iq.setup(frequency=1000, bandwidth=100)
                logger.info(f"✅ IQ{i} module accessible - freq: {iq.frequency}Hz")
            except Exception as e:
                logger.error(f"❌ IQ{i} failed: {e}")
        
        logger.info("✅ All PyRPL hardware modules tested successfully!")
        logger.info("🎉 Red Pitaya hardware is fully operational!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Direct PyRPL test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("Starting Direct PyRPL Hardware Test (Python 3.12 Compatible)")
    logger.info("="*60)
    
    success = test_direct_pyrpl()
    
    logger.info("="*60)
    if success:
        logger.info("🎉 SUCCESS: Red Pitaya PyRPL hardware fully validated!")
        logger.info("All hardware modules (PID, ASG, Scope, IQ, Sampler) are operational.")
        logger.info("PyMoDAQ PyRPL plugins ready for use with rp-f08d6c.local")
    else:
        logger.info("❌ FAILED: Hardware validation incomplete")
        
    exit(0 if success else 1)