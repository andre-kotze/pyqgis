
<h1 align="center"><b>PyQGIS scripts</b></h1>
Scripts for use with QGIS, including some profiling tools, processing models, and geostatistical methods



<!-- comment -->
<h2 id = "contents">Contents</h2>

<details open="open">
  <summary>Contents</summary>
  <ul>
    <li><a href = "#scripts">Scripts</a></li>
    <li><a href = "#models">Models</a></li>
    <li><a href = "#usecases">Use cases</a></li>
  </ul>
</details>

<hr>

<!-- SCRIPTS -->
<h2 id = "scripts">Scripts</h2>

DP_from_VR: Given a sampling route, generates a tabular sampling program (xlsx or csv). 
Vertices (sampling sites) can be made to inherit various location-derived attributes which will be included in the final program.
Additionally, some field refactoring and coordinate transformation can also be done.<br>

PlotProfile: Given a sampling route, sampling program and DEM, generates a Matplot profile with each sampling point plotted and labeled according to the sampling program.<br>

ClusterVoronoi: A script to geostatistically identify possible outliers in a points layer (continuous data).

<hr>

<!-- MODELS -->
<h2 id = "models">Models</h2>


The models are simply the Python scripts wrapped in .model3 files for smoother and more flexible incorporation into QGIS.


<hr>

<!-- USE CASES -->
<h2 id = "usecases">Use cases</h2>

<ul>
  <li>Customisable marked and labelled profiles</li>
  <li>Custom sample tables</li>
</ul>

