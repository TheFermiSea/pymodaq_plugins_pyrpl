# PyMoDAQ Data Protocol Requirements

## Critical Data Handling Protocol for DAQ_Viewer Plugins

### Data Object Hierarchy (MANDATORY):
```python
from pymodaq.utils.data import Axis, DataFromPlugins, DataToExport
import numpy as np

# 1. Axis Objects - Define data dimensions
x_axis = Axis(data=wavelength_array, label='Wavelength', units='nm')
y_axis = Axis(data=position_array, label='Position', units='mm')

# 2. DataToExport - Container for single dataset  
dte = DataToExport(
    name='MyMeasurement',
    data=[intensity_array],  # List of numpy arrays
    axes=[x_axis]           # List of Axis objects
)

# 3. DataFromPlugins - Top-level wrapper
dfp = DataFromPlugins(
    name='MyInstrument', 
    data=[dte]  # List of DataToExport objects
)

# 4. MANDATORY: Emit via signal
self.data_grabed_signal.emit([dfp])  # List of DataFromPlugins
```

### Data Dimensionality Examples:

#### 0D Data (Single Value):
```python
def grab_data(self, Naverage=1, **kwargs):
    # Get single measurement value
    power_value = self.controller.read_power()
    
    # No axes needed for 0D data
    dte = DataToExport(name='Power', data=[np.array([power_value])])
    dfp = DataFromPlugins(name='PowerMeter', data=[dte])
    self.data_grabed_signal.emit([dfp])
```

#### 1D Data (Spectrum):
```python
def grab_data(self, Naverage=1, **kwargs):
    wavelengths = self.controller.get_wavelengths()
    intensities = self.controller.get_spectrum()
    
    x_axis = Axis(data=wavelengths, label='Wavelength', units='nm')
    dte = DataToExport(name='Spectrum', data=[intensities], axes=[x_axis])
    dfp = DataFromPlugins(name='Spectrometer', data=[dte])
    self.data_grabed_signal.emit([dfp])
```

#### 2D Data (Image):
```python
def grab_data(self, Naverage=1, **kwargs):
    image_data = self.controller.get_image()  # 2D numpy array
    
    x_axis = Axis(data=np.arange(image_data.shape[1]), label='X', units='pixels')
    y_axis = Axis(data=np.arange(image_data.shape[0]), label='Y', units='pixels')
    
    dte = DataToExport(name='CameraImage', 
                      data=[image_data], 
                      axes=[x_axis, y_axis])
    dfp = DataFromPlugins(name='Camera', data=[dte])
    self.data_grabed_signal.emit([dfp])
```

## Critical Rules:
1. **NEVER** return raw numpy arrays from grab_data()
2. **ALWAYS** package data in DataFromPlugins hierarchy
3. **ALWAYS** emit via self.data_grabed_signal.emit()
4. **ALWAYS** include proper Axis objects with labels and units
5. Data arrays must be in a LIST even if single array
6. Axis data must match the dimensions of your data arrays

## Common Mistakes:
- Returning data instead of emitting signal
- Missing Axis objects for multi-dimensional data
- Incorrect data array structure (not in list)
- Missing or incorrect units/labels
- Not following the exact object hierarchy

## Signal Connection:
The data_grabed_signal is automatically connected to:
- Main viewer for plotting
- Data savers for HDF5 export
- Analysis modules for processing
- DAQ_Scan for synchronized acquisition

Without proper data protocol, these connections fail!