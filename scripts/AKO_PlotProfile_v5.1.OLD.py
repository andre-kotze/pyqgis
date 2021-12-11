from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProject
from qgis.core import QgsPoint
#import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import time
import processing


class PlotProfile20201031(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile('DrillingProgram', 'Drilling Program', behavior=QgsProcessingParameterFile.File, fileFilter='All Files (*.*)', defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(1, model_feedback)
        results = {}
        outputs = {}
        
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
        
        print('[Checking Vessel Route]')
        
        #Check if VR.shp starts BEFORE or FROM Seq#1 in DP:
        vr_start = QgsPoint(vertlist[0].x(), vertlist[0].y())
        dp_start = QgsPoint(dp.loc[0,'Easting'], dp.loc[0,'Northing'])
        if vr_start == dp_start:
            dp.loc[0,'Distance'] = 0
        dp['x'] = np.cumsum(dp['Distance'])
        
        print('[Plotting profile. . .]')
        plt.figure(num=1, figsize=(18, 5)) # window size in inches
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

        print('[Checking samples. . .]')
        samplelist =[]
        for index, row in dp.iterrows():
            sample = [row['Sample_ID'], row['x'], row['Bathymetry']]
            samplelist.append(sample)
        
        print('DP Samples to plot:',len(samplelist))
        for sampleid, x, y, in samplelist:
            print('Plotting label:', sampleid)
            plt.annotate(sampleid, 
                (x, y), 
                rotation = 60, 
                xycoords='data', 
                xytext=(0, 8), 
                textcoords='offset points', 
                weight='bold', 
                fontsize=12)
            print('Plotting marker:', sampleid)
            plt.plot(x, y, marker='o', markerfacecolor=(0.88,0.88,0.08,1), 
                markersize=5, markeredgewidth=1, markeredgecolor=(0,0,0,1))#, annotation_clip = True)#, *args, **kwargs)
        
        print('[Showing Plot . . .]')
        
        #plt.savefig('C:/Users/User/Documents/Andre/plot.png')
        plt.show(block = False) #False so show returns immediately
        '''
        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}
        '''
        print('[Finished]')
        time.sleep(3)
        #return {}

    def name(self):
        return 'Plot Profile AKO rev 9'

    def displayName(self):
        return 'Plot Profile AKO rev 9'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return PlotProfile20201031()
