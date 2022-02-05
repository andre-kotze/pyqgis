# VORONOI CLUSTER ANALYSIS
import numpy as np

# voronoi polygons layer
pathlyr = QgsProject.instance().mapLayersByName('Voronois')[0]
target_field = 'SDII'
tol = 0.05

# 5 classes requires 4 values
# 20, 40, 60 and 80 percentile

values = []
for f in pathlyr.getFeatures():
    values.append(f[target_field])
    
# get class boundaries
classes = [20, 40, 60, 80]
class_boundaries = list(np.percentile(np.array(values), classes, interpolation='linear'))
    
print(class_boundaries)

# classify
pathlyr.dataProvider().addAttributes([QgsField('Class', QVariant.Int),
        QgsField('Cluster', QVariant.Int)])
pathlyr.updateFields()
with edit(pathlyr):
    for f in pathlyr.getFeatures():
        v = f[target_field]
        if v <= class_boundaries[0]:
            f['Class'] = 0
        elif v > class_boundaries[-1]:
            f['Class'] = 4
        else:
            for n in range(len(class_boundaries)):
                if v > class_boundaries[n] and v <= class_boundaries[n+1]:
                    f['Class'] = n+1
                    break
            #else:
            #    f['Class'] = -2
        pathlyr.updateFeature(f)

# neighbour analysis
# Build a spatial index
feature_dict = {f.id(): f for f in pathlyr.getFeatures()}
index = QgsSpatialIndex()
for f in feature_dict.values():
    index.insertFeature(f)
# Loop through all features and find features that touch each feature
print('starting processing')
print('FID, intersects, neighbours, Cluster')
with edit(pathlyr):
    for f in feature_dict.values():
        print(f'{f.id()}, ', end='\t')
        geom = f.geometry()
        intersecting_ids = index.intersects(geom.boundingBox())
        print(len(intersecting_ids), end='\t')
        neighbours = []
        for intersecting_id in intersecting_ids:
            # Look up the feature from the dictionary
            intersecting_f = feature_dict[intersecting_id]
            # if a feature is not disjoint, it is a neighbor.
            if (f != intersecting_f and
                not intersecting_f.geometry().disjoint(geom)):
                neighbours.append(intersecting_f['Class'])
        print(len(neighbours), end='\t')
        if len(neighbours) > 3 and f['Class'] not in neighbours:
            f['Cluster'] = -1
        else:
            f['Cluster'] = f['Class']
        print(f['Cluster'])
        # Update the layer with new attribute values.
        pathlyr.updateFeature(f)

pathlyr.commitChanges()
print('Processing complete.')
