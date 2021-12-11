from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
import processing


class DrillingprogramFromVesselroutePro(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('sites', 'Sites', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('topastracklines', 'TOPAS Tracklines', optional=True, types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('vesselroute', 'Vessel Route', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('features', 'Features', optional=True, types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('DrillingProgram', 'Drilling Program', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(11, model_feedback)
        results = {}
        outputs = {}

        # Extract vertices
        alg_params = {
            'INPUT': parameters['vesselroute'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractVertices'] = processing.run('native:extractvertices', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Add sequential indices (Join attributes by nearest)
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELDS_TO_COPY': 'vertex_index',
            'INPUT': parameters['sites'],
            'INPUT_2': outputs['ExtractVertices']['OUTPUT'],
            'MAX_DISTANCE': 5,
            'NEIGHBORS': 1,
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AddSequentialIndicesJoinAttributesByNearest'] = processing.run('native:joinbynearest', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Convert indices to Sequence numbers (Field calculator)
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'Seq',
            'FIELD_PRECISION': 3,
            'FIELD_TYPE': 1,
            'FORMULA': 'vertex_index + 1',
            'INPUT': outputs['AddSequentialIndicesJoinAttributesByNearest']['OUTPUT'],
            'NEW_FIELD': True,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ConvertIndicesToSequenceNumbersFieldCalculator'] = processing.run('qgis:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Add TOPAS lines (Join attributes by nearest)
        # optional: check if present
        if parameters['topastracklines'] is not None:
            alg_params = {
                'DISCARD_NONMATCHING': False,
                'FIELDS_TO_COPY': None,
                'INPUT': outputs['ConvertIndicesToSequenceNumbersFieldCalculator']['OUTPUT'],
                'INPUT_2': parameters['topastracklines'],
                'MAX_DISTANCE': 15,
                'NEIGHBORS': 1,
                'PREFIX': '',
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['AddTopasLinesJoinAttributesByNearest'] = processing.run('native:joinbynearest', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        else:
            outputs['AddTopasLinesJoinAttributesByNearest'] = outputs['ConvertIndicesToSequenceNumbersFieldCalculator']
            
        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Drop field(s)
        alg_params = {
            'COLUMN': 'vertex_index;n;feature_x;feature_y;nearest_x;nearest_y;distance;fid',
            'INPUT': outputs['AddTopasLinesJoinAttributesByNearest']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DropFields'] = processing.run('qgis:deletecolumn', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Add Feature (Join attributes by location)
        # optional: check if present
        if parameters['features'] is not None:
            alg_params = {
                'DISCARD_NONMATCHING': False,
                'INPUT': outputs['DropFields']['OUTPUT'],
                'JOIN': parameters['features'],
                'JOIN_FIELDS': 'Feature',
                'METHOD': 1,
                'PREDICATE': [0,1,4,5],
                'PREFIX': '',
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['AddFeatureJoinAttributesByLocation'] = processing.run('qgis:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        else:
            outputs['AddFeatureJoinAttributesByLocation'] = outputs['DropFields']

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # WGS Lon (Field calculator)
        alg_params = {
            'FIELD_LENGTH': 40,
            'FIELD_NAME': 'WGS Lon',
            'FIELD_PRECISION': 3,
            'FIELD_TYPE': 2,
            'FORMULA': 'substr(\r\nregexp_replace(\r\nto_dm(\r\nx(transform($geometry, \'EPSG:32733\', \'EPSG:4326\')), \r\n\'x\', 6),\r\n\'°\', \' \'),\r\n1, -1)',
            'INPUT': outputs['AddFeatureJoinAttributesByLocation']['OUTPUT'],
            'NEW_FIELD': True,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['WgsLonFieldCalculator'] = processing.run('qgis:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # WGS Lat (Field calculator)
        alg_params = {
            'FIELD_LENGTH': 40,
            'FIELD_NAME': 'WGS Lat',
            'FIELD_PRECISION': 3,
            'FIELD_TYPE': 2,
            'FORMULA': 'substr(\r\nregexp_replace(\r\nto_dm(\r\ny(transform($geometry, \'EPSG:32733\', \'EPSG:4326\')), \r\n\'y\', 6),\r\n\'°\', \' \'),\r\n1, -1)',
            'INPUT': outputs['WgsLonFieldCalculator']['OUTPUT'],
            'NEW_FIELD': True,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['WgsLatFieldCalculator'] = processing.run('qgis:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Reorder Columns (Refactor fields)
        fields_mapping = [
                {'expression': '"Seq"', 'length': 10, 'name': 'Seq', 'precision': 0, 'type': 4}, 
                {'expression': '"Sample_ID"', 'length': 15, 'name': 'Sample_ID', 'precision': 0, 'type': 10}, 
                {'expression': '"Easting"', 'length': 12, 'name': 'Easting', 'precision': 2, 'type': 6}, 
                {'expression': '"Northing"', 'length': 12, 'name': 'Northing', 'precision': 2, 'type': 6}, 
                {'expression': '"WGS Lat"', 'length': 99, 'name': 'WGS Lat', 'precision': 0, 'type': 10}, 
                {'expression': '"WGS Lon"', 'length': 99, 'name': 'WGS Lon', 'precision': 0, 'type': 10}, 
                {'expression': '"Bathymetry"', 'length': 12, 'name': 'Bathymetry', 'precision': 2, 'type': 6}, 
                {'expression': '"SedThick"', 'length': 10, 'name': 'SedThick', 'precision': 2, 'type': 6}
                ]
        # add topas/features if present:
        if parameters['topastracklines'] is not None:
            fields_mapping.append({'expression': '"Topas"', 'length': 99, 'name': 'Topas', 'precision': 0, 'type': 10})
        if parameters['features'] is not None:
            fields_mapping.append({'expression': '"Feature"', 'length': 99, 'name': 'Feature', 'precision': 0, 'type': 10})
        alg_params = {
            'FIELDS_MAPPING': fields_mapping, 
            'INPUT': outputs['WgsLatFieldCalculator']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }

        outputs['ReorderColumnsRefactorFields'] = processing.run('qgis:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Sort by sequence (Order by expression)
        alg_params = {
            'ASCENDING': True,
            'EXPRESSION': '\"Seq\"',
            'INPUT': outputs['ReorderColumnsRefactorFields']['OUTPUT'],
            'NULLS_FIRST': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['SortBySequenceOrderByExpression'] = processing.run('native:orderbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Distance (Field calculator)
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'Distance',
            'FIELD_PRECISION': 2,
            'FIELD_TYPE': 0,
            'FORMULA': 'round( \r\ndistance(\r\n$geometry, \r\ngeometry(get_feature_by_id( @layer , $id -1))\r\n), 2\r\n)',
            'INPUT': outputs['SortBySequenceOrderByExpression']['OUTPUT'],
            'NEW_FIELD': True,
            'OUTPUT': parameters['DrillingProgram']
        }
        outputs['DistanceFieldCalculator'] = processing.run('qgis:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['DrillingProgram'] = outputs['DistanceFieldCalculator']['OUTPUT']
        return results

    def name(self):
        return 'DrillingProgram from VesselRoute Pro'

    def displayName(self):
        return 'DrillingProgram from VesselRoute Pro'

    def group(self):
        return 'SamplingPlanning'

    def groupId(self):
        return 'SamplingPlanning'

    def createInstance(self):
        return DrillingprogramFromVesselroutePro()
