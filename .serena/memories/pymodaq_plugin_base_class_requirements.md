# PyMoDAQ Plugin Base Class Requirements

## Required Base Classes and Abstract Methods

### For DAQ_Move Plugins:
```python
from pymodaq.control_modules.move_utility_classes import DAQ_Move_Base

class DAQ_Move_MyDevice(DAQ_Move_Base):
    # Required class attributes
    controller = None  # Hardware controller object
    params = [...]     # Parameter tree definition
    
    # Required abstract methods to implement:
    def init_hardware(self):
        """Initialize hardware connection"""
        # 1. Get connection settings from parameter tree
        # 2. Create controller object (serial, visa, etc.)
        # 3. Store in self.controller
        # 4. Query initial hardware state
        # 5. Update parameter tree with current values
        # 6. Set self.status.initialized = True
        # 7. Emit status signal
        
    def close(self):
        """Clean shutdown of hardware"""
        if self.controller is not None:
            self.controller.close()
            
    def commit_settings(self, param):
        """Handle parameter changes from GUI"""
        if param.name() == 'speed':
            # Send speed change to hardware
        elif param.name() == 'axis':
            # Configure hardware axis
            
    def move_abs(self, value):
        """Absolute move to position"""
        # Send absolute move command to hardware
        
    def move_rel(self, value):
        """Relative move by amount"""  
        # Send relative move command to hardware
        
    def move_home(self):
        """Home the actuator"""
        # Send homing command to hardware
        
    def get_actuator_value(self):
        """Get current actuator position"""
        # Query hardware and return current position
        return current_position
```

### For DAQ_Viewer Plugins:
```python
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_Base

class DAQ_2DViewer_MyCamera(DAQ_Viewer_Base):
    # Required class attributes  
    controller = None
    params = [...]
    
    # Required abstract methods:
    def init_hardware(self):
        """Initialize camera hardware"""
        # Similar to DAQ_Move but for detector
        
    def close(self):
        """Clean shutdown"""
        if self.controller is not None:
            self.controller.close()
            
    def commit_settings(self, param):
        """Handle camera parameter changes"""
        if param.name() == 'exposure_time':
            # Set camera exposure
        elif param.name() == 'roi':
            # Set camera ROI
            
    def grab_data(self, Naverage=1, **kwargs):
        """Acquire data from detector"""
        # 1. Trigger hardware acquisition
        # 2. Wait for/read raw data
        # 3. Package into PyMoDAQ data objects
        # 4. Emit data signal
        
        from pymodaq.utils.data import Axis, DataFromPlugins, DataToExport
        
        # Get raw data from hardware
        raw_data = self.controller.get_image()
        
        # Create axes for 2D data
        x_axis = Axis(data=np.arange(raw_data.shape[1]), label='X', units='pixels')
        y_axis = Axis(data=np.arange(raw_data.shape[0]), label='Y', units='pixels')
        
        # Package data
        dte = DataToExport(name='Camera_Image', 
                          data=[raw_data],
                          axes=[x_axis, y_axis])
        dfp = DataFromPlugins(name='My Camera', data=[dte])
        
        # Emit data signal (CRITICAL)
        self.data_grabed_signal.emit([dfp])
```

## Key Implementation Rules:
1. ALWAYS inherit from correct base class
2. ALWAYS implement ALL abstract methods
3. ALWAYS use self.controller to store hardware connection
4. ALWAYS emit proper signals for status and data
5. ALWAYS handle cleanup in close() method
6. NEVER create custom GUI widgets - use ParameterTree only