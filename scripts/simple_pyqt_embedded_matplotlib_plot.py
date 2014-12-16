"""Simple example of a Matplotlib plot embedded in a PyQt application."""


import sys

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
from PyQt4.QtGui import QApplication


def main():
    
    app = QApplication(sys.argv)
    
    figure = Figure()
    
    canvas = FigureCanvasQTAgg(figure)
    canvas.setWindowTitle('Matplotlib Plot')
    
    axes = figure.add_subplot(1, 1, 1)
    axes.plot([1, 2, 3])
    
    canvas.show()
    canvas.raise_()
    
    sys.exit(app.exec_())
    
    
if __name__ == '__main__':
    main()
