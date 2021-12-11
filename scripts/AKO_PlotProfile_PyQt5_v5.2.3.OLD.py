# 20201114
# Profile Plot with PyQt5 canvas - v5.2.3 rev 14
# line 134 reached (Drawing Plot)
# LOG
# call MainWindow with 3 args: self, listx, listx
# ERRFIXED line 138: __init__() missing 2 required positional arguments: 'x' and 'y'
# line 66 'FINISHED' reached
# ERR TypeError: QApplication(List[str]): not enough arguments
#   add arg sys.argv --> crash
#   try arg '*args, **kwargs'

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterFile,
    QgsProcessingParameterVectorLayer,
    QgsProject,
    QgsPoint)
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Qt5Agg')
from PyQt5 import (QtCore, 
    QtGui, 
    QtWidgets)
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg, 
    NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
import os
import sys
import processing

class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=18, height=5, dpi=100):
        print('drawing figure')
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, x, y, **kwargs):
        super(MainWindow, self).__init__()#*args, **kwargs)
        
        print('drawing canvas')

        sc = MplCanvas(self, width=18, height=5, dpi=100)
        sc.axes.plot(x, y)

        # Create toolbar, passing canvas as first parament, parent (self, the MainWindow) as second.
        toolbar = NavigationToolbar(sc, self)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(sc)

        # Create a placeholder widget to hold our toolbar and canvas.
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        #self.show()
        print('[FINISHED]')

class PlotProfile20201114(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile('DrillingProgram', 'Drilling Program', behavior=QgsProcessingParameterFile.File, fileFilter='All Files (*.*)', defaultValue=None))
        #self.addParameter(QgsProcessingParameterVectorLayer('xyprofile', 'XY_Profile', types=[QgsProcessing.TypeVectorLine], defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(1, model_feedback)
        results = {}
        outputs = {}
        
        print('\n\nInitializing PLOT PROFILE')
        
        dpfile = parameters['DrillingProgram']
        pathlyr = QgsProject.instance().mapLayersByName('XY_Profile')[0]
        title = dpfile.split('/')[-1] + "  Vessel Route Profile"

        try:
            dp = pd.read_excel(dpfile, usecols = ['Sample_ID', 'Easting', 'Northing', 'Bathymetry', 'Distance'])
            print('[Drilling Program loaded]')
        except:
            print('Could not load Drilling Program\n\tMake sure the table has headings "Sample_ID", "Bathymetry", "Distance"')

        vertlist = []
        for segm in pathlyr.getFeatures():
            vertlist.extend([vert for vert in segm.geometry().vertices()]) #List all vertices
        distances = [v1.distance(v2) for v1,v2 in zip(vertlist, vertlist[1:])] #List distances bewteen vertices 
        distances.append(vertlist[1].distance(vertlist[-2])) #Distance from first to last point (my line has the same start and end point) !!!!
        distances = np.cumsum(distances)

        depth = [v.z() for v in vertlist] #Extract z from each point
        
        #Check if VR.shp starts BEFORE or FROM Seq#1 in DP:
        vr_start = QgsPoint(round(vertlist[0].x()), round(vertlist[0].y()))
        dp_start = QgsPoint(round(dp.loc[0,'Easting']), round(dp.loc[0,'Northing']))
        print('vr_start:', vr_start, '\ndp_start:', dp_start)
        if vr_start == dp_start:
            dp.loc[0,'Distance'] = 0
            print('[VR first vertex equal to DP first vertex]\n[Changing distance to Seq1 to 0]')
        else:
            print('[vr_start =/= dp_start]')
        dp['x'] = np.cumsum(dp['Distance'])
        
        #plt.figure(num=1, figsize=(18, 5)) # window size in inches
        plt.plot(distances, depth, color=(0,0,0,1), linewidth=1)
        plt.xlabel("Distance")
        plt.ylabel("Depth")
        plt.title("Vessel Route Profile")
        x1,x2,y1,y2 = plt.axis()
        ymax = max(depth)+3
        ymin = min(depth)-3
        plt.axis((x1,x2,ymin,ymax))   #bounding values
        plt.grid(b=True, which='major', axis='y',color=(0.2,0.2,0.2,1), linestyle='-.')
        plt.fill_between(distances, depth, -150, color=(0.87,0.87,0.87,1))

        samplelist =[]
        for index, row in dp.iterrows():
            sample = [row['Sample_ID'], row['x'], row['Bathymetry']]
            samplelist.append(sample)

        for sampleid, x, y, in samplelist:
            plt.annotate(sampleid, 
                (x, y), 
                rotation = 60, 
                xycoords='data', 
                xytext=(0, 8), 
                textcoords='offset points', 
                weight='bold', 
                fontsize=12)
            plt.plot(x, y, marker='o', markerfacecolor=(0.88,0.88,0.08,1), 
                markersize=5, markeredgewidth=1, markeredgecolor=(0,0,0,1))#, annotation_clip = True)#, *args, **kwargs)
        
        print('[Drawing Plot . . .]')
        #plt.show()
        w = MainWindow(x=distances, y=depth)
        QtWidgets.QApplication(*args, **kwargs)
        
        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        return {}

    def name(self):
        return 'Plot Profile AKO rev 14'

    def displayName(self):
        return 'Plot Profile AKO rev 14'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return PlotProfile20201114()
