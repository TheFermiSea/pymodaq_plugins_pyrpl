"""
PyQtGraph compatibility patch for PyMoDAQ with PyRPL
Adds missing DockLabel class to PyQtGraph 0.12.4 for PyMoDAQ compatibility
"""

def patch_pyqtgraph_for_pymodaq():
    """Add DockLabel compatibility to PyQtGraph 0.12.4"""
    try:
        import pyqtgraph.dockarea as da
        
        # Check if DockLabel already exists
        if hasattr(da, 'DockLabel'):
            return True
            
        # Create minimal DockLabel class
        from qtpy import QtWidgets, QtCore
        
        class DockLabel(QtWidgets.QLabel):
            """Minimal DockLabel implementation for PyMoDAQ compatibility"""
            def __init__(self, text='', orientation='horizontal', forceWidth=True):
                super().__init__(text)
                self.orientation = orientation
                self.forceWidth = forceWidth
                
            def paintEvent(self, event):
                """Override paint to support orientation"""
                if self.orientation == 'vertical':
                    # For vertical orientation, we need to rotate the text
                    from qtpy.QtGui import QPainter, QTransform
                    painter = QPainter(self)
                    painter.setTransform(QTransform().rotate(90))
                    painter.drawText(self.rect(), self.text())
                else:
                    super().paintEvent(event)
        
        # Add to dockarea module
        da.DockLabel = DockLabel
        print("✅ PyQtGraph DockLabel compatibility patch applied")
        return True
        
    except Exception as e:
        print(f"⚠️ PyQtGraph compatibility patch failed: {e}")
        return False

if __name__ == "__main__":
    patch_pyqtgraph_for_pymodaq()