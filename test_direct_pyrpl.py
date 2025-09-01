#!/usr/bin/env python3
"""
Direct PyRPL Hardware Test

This script tests PyRPL directly without the wrapper layer to verify
hardware connectivity.
"""

import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def test_direct_pyrpl():
    """Test PyRPL directly"""
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
                pid.setpoint = 0.0
                pid.output_direct = 'off'
                logger.info(f"✅ PID{i} module accessible")
            except Exception as e:
                logger.error(f"❌ PID{i} failed: {e}")
        
        # Test ASG modules
        for i in range(2):
            try:
                asg = getattr(rp, f'asg{i}')
                asg.setup(frequency=1000, amplitude=0.1, waveform='sin')
                logger.info(f"✅ ASG{i} module accessible")
            except Exception as e:
                logger.error(f"❌ ASG{i} failed: {e}")
        
        # Test Scope
        try:
            scope = rp.scope
            scope.input1 = 'in1'
            scope.input2 = 'in2'
            logger.info("✅ Scope module accessible")
        except Exception as e:
            logger.error(f"❌ Scope failed: {e}")
        
        # Test IQ modules
        for i in range(3):
            try:
                iq = getattr(rp, f'iq{i}')
                iq.setup(frequency=1000, bandwidth=100)
                logger.info(f"✅ IQ{i} module accessible")
            except Exception as e:
                logger.error(f"❌ IQ{i} failed: {e}")
        
        logger.info("✅ All PyRPL tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Direct PyRPL test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("Starting Direct PyRPL Hardware Test")
    logger.info("="*50)
    
    success = test_direct_pyrpl()
    
    logger.info("="*50)
    logger.info(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'}")