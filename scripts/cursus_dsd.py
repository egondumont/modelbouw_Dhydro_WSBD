# %% [markdown]
# # Example of generating a 1D2DRR D-HYDRO model - an overview of functionalities
#
# This notebook gives an overview of the functionalities of the D-HyDAMO module, part of the Hydrolib environment.
#
# This notebook is based on previous examples of the python package delft3dfmpy, but now connnected to the Hydrolib-core package, which is used for writing a D-HYDRO model. It contains similar functionalities as delft3dfmpy 2.0.3; input data is expected to be according to HyDAMO DAMO2.2 gpkg-format. The example model used here is based on a part of the Oostrumsche beek in Limburg, added with some fictional dummy data to better illustrate functionalities.
#
# Because of the dummy data and demonstation of certain features, the resulting model is not optimal from a hydrologic point of view.

# %% [markdown]
# ## Jupyter-shortcuts:
# [H]: bekijken van alle shortcuts
#
#
# [SHIFT-Enter]: cel runnen en doorgaan
#
# [CNTRL-Enter]: runnen geselecteerde cellen
#
# [A]: nieuwe cel boven de huidge
#
# [B]: nieuwe cel onder de huidige
#
# [D-D]: cel verwijderen
#
# [SHIFT-TAB]: argumenten van functie weergeven (cel moet eerst gedraaid zijn)

# %% [markdown]
# ## Load Python libraries and Hydrolib-core functionality

# %%
# Basis
import warnings
from pathlib import Path

import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon

warnings.simplefilter(action="ignore", category=FutureWarning)

# %%
# and from hydrolib-core
from hydrolib.core.dflowfm.crosssection.models import CrossDefModel, CrossLocModel
from hydrolib.core.dflowfm.ext.models import ExtModel
from hydrolib.core.dflowfm.friction.models import FrictionModel
from hydrolib.core.dflowfm.inifield.models import DiskOnlyFileModel, IniFieldModel
from hydrolib.core.dflowfm.mdu.models import FMModel
from hydrolib.core.dflowfm.obs.models import ObservationPointModel
from hydrolib.core.dflowfm.onedfield.models import OneDFieldModel
from hydrolib.core.dflowfm.storagenode.models import StorageNodeModel
from hydrolib.core.dflowfm.structure.models import StructureModel
from hydrolib.core.dimr.models import DIMR, FMComponent
from hydrolib.dhydamo.converters.df2hydrolibmodel import Df2HydrolibModel
from hydrolib.dhydamo.core.drr import DRRModel
from hydrolib.dhydamo.core.drtc import DRTCModel

# %%
# Importing relevant classes from Hydrolib-dhydamo
from hydrolib.dhydamo.core.hydamo import HyDAMO
from hydrolib.dhydamo.geometry import mesh
from hydrolib.dhydamo.geometry.viz import plot_network
from hydrolib.dhydamo.io.dimrwriter import DIMRWriter
from hydrolib.dhydamo.io.drrwriter import DRRWriter

# %% [markdown]
# Define in- and output paths

# %%
# path to the package containing the dummy-data
data_path = Path(
    r"d:\projecten\D2508.WBD_modelinstrumentarium\08.cursusmateriaal\D-HYDRO cursus Waterschapsmarkt\Basiscursus_Automatische_Modelgeneratie_met_D-HyDAMO\data"
).resolve()
assert data_path.exists()

# path to write the models
output_path = Path(__file__).parent.resolve()
output_path.mkdir(exist_ok=True, parents=False)
assert output_path.exists()

# %% [markdown]
# Define components that should be used in the model. 1D is used in all cases.

# %%
TwoD = True
RR = True
RTC = True

# %% [markdown]
# This switch defines the mode in which RTC is used. Normally it can handle PID-, interval- and time controllers, but for calibration purposes (for instance) it may be desired to pass historical data, such as actual crest levels, to the model. If True, PID- and interval- and regular (seasonal) time controllers are replaced by time controllers containing a provided time series.
#
# This does require time series to be available. They should be provided as a file from which a dataframe can be read (here CSV), with structure codes as columns and time steps as row index.

# %%
rtc_onlytimeseries = False
rtc_timeseriesdata = data_path / "rtc_timeseries.csv"

# %% [markdown]
# ## Read HyDAMO DAMO2.2 data

# %%
# all data is contained in one geopackage called 'Example model'
gpkg_file = str(data_path / "Example_model.gpkg")

# initialize a hydamo object
hydamo = HyDAMO(extent_file=data_path / "Oostrumschebeek_extent.shp")

# show content
hydamo.branches.show_gpkg(gpkg_file)

# %%
hydamo.branches.read_gpkg_layer(gpkg_file, layer_name="HydroObject", index_col="code")

hydamo.profile.read_gpkg_layer(
    gpkg_file,
    layer_name="ProfielPunt",
    groupby_column="profiellijnid",
    order_column="codevolgnummer",
    id_col="code",
    index_col="code",
)
hydamo.profile_roughness.read_gpkg_layer(gpkg_file, layer_name="RuwheidProfiel")
hydamo.profile_line.read_gpkg_layer(gpkg_file, layer_name="profiellijn")
hydamo.profile_group.read_gpkg_layer(gpkg_file, layer_name="profielgroep")
hydamo.profile.drop("code", axis=1, inplace=True)
hydamo.profile["code"] = hydamo.profile["profiellijnid"]
hydamo.snap_to_branch_and_drop(hydamo.profile, hydamo.branches, snap_method="intersecting", drop_related=True)

# %% [markdown]
# Load branches and profiles.

# %% [markdown]
# In the funtions below, the function 'snap_to_branch_and_drop' compares each object with a geometry to the branches. If the object is outside the specified maximum distance to any branch, the object and all objects related to it are dropped (if 'drop_related' is True).
#
# Moreover there are multiple options to snap:
# - overal: for points, based on minimum distance to the branch;
# - centroid: for lines and polygons, based on the mininimum distance of the objets' centroid to the branch;
# - intersecting: for lines, takes the first branch the object is intersecting (for lines);
# - ends: for lines, based on the cumulative distance of the lines' ends to the branch.

# %% [markdown]
# Load structures

# %%
hydamo.culverts.read_gpkg_layer(gpkg_file, layer_name="DuikerSifonHevel", index_col="code")
hydamo.weirs.read_gpkg_layer(gpkg_file, layer_name="Stuw", index_col="code")
hydamo.opening.read_gpkg_layer(gpkg_file, layer_name="Kunstwerkopening")
hydamo.management_device.read_gpkg_layer(gpkg_file, layer_name="Regelmiddel")
hydamo.snap_to_branch_and_drop(hydamo.culverts, hydamo.branches, snap_method="ends", maxdist=5, drop_related=True)
hydamo.snap_to_branch_and_drop(hydamo.weirs, hydamo.branches, snap_method="overal", maxdist=10, drop_related=True)

hydamo.pumpstations.read_gpkg_layer(gpkg_file, layer_name="Gemaal", index_col="code")
hydamo.pumps.read_gpkg_layer(gpkg_file, layer_name="Pomp", index_col="code")
hydamo.management.read_gpkg_layer(gpkg_file, layer_name="Sturing", index_col="code")
hydamo.snap_to_branch_and_drop(
    hydamo.pumpstations, hydamo.branches, snap_method="overal", maxdist=15, drop_related=True
)

hydamo.bridges.read_gpkg_layer(gpkg_file, layer_name="Brug", index_col="code")
hydamo.snap_to_branch_and_drop(hydamo.bridges, hydamo.branches, snap_method="overal", maxdist=1100, drop_related=True)

# %% [markdown]
# ### Oefening 1

# %%
############Oefening 1##################################################
# Verwijder duiker D_21493 uit het model
# tip gebruik de functie hydamo.culverts.drop(<"duiker code">, inplace=True)
# Vergroot de duiker D_24405 van 0.5 naar 1 m
# tip kijk naar de eigenschappen hoogteopening en breedteopening


###########################################################################

# %%
###########Controle oefening 1###########################################
if "D_21493" in hydamo.culverts.index:
    print("Duiker D_21493 is niet verwijderd")
else:
    print("Duiker D_21493 is succesvol verwijderd")

print(hydamo.culverts.loc["D_24405", :])


# %% [markdown]
# ### Extra oefening

# %%
#######Extra oefening######################################################
# verwijder stuwen met een statusobject ongelijk aan gerealiseerd


###########################################################################

# %% [markdown]
# Load boundaries

# %%
# read boundaries
hydamo.boundary_conditions.read_gpkg_layer(gpkg_file, layer_name="hydrologischerandvoorwaarde", index_col="code")
hydamo.boundary_conditions.snap_to_branch(hydamo.branches, snap_method="overal", maxdist=10)

# %% [markdown]
# Catchments and laterals

# %%
# read catchments
hydamo.catchments.read_gpkg_layer(
    gpkg_file, layer_name="afvoergebiedaanvoergebied", index_col="code", check_geotype=False
)

# %%
# read laterals
hydamo.laterals.read_gpkg_layer(gpkg_file, layer_name="lateraleknoop")
hydamo.laterals.snap_to_branch(hydamo.branches, snap_method="overal", maxdist=5000)
hydamo.catchments["boundary_node"] = [
    hydamo.laterals[hydamo.laterals.globalid == c["lateraleknoopid"]].code.values[0]
    for _, c in hydamo.catchments.iterrows()
]

# %%
# plot the model objects
fig, ax = plt.subplots(figsize=(20, 20))
xmin, ymin, xmax, ymax = hydamo.clipgeo.bounds
ax.set_xlim(round(xmin), round(xmax))
ax.set_ylim(round(ymin), round(ymax))

hydamo.branches.geometry.plot(ax=ax)  # , label="Channel", linewidth=2, color="blue")
hydamo.profile.geometry.plot(ax=ax, color="black", label="Cross section", linewidth=4)
hydamo.culverts.geometry.centroid.plot(ax=ax, color="brown", label="Culvert", markersize=40, zorder=10, marker="^")
hydamo.weirs.geometry.plot(ax=ax, color="green", label="Weir", markersize=25, zorder=10, marker="^")

hydamo.bridges.geometry.plot(ax=ax, color="red", label="Bridge", markersize=20, zorder=10, marker="^")
hydamo.pumpstations.geometry.plot(
    ax=ax,
    color="orange",
    label="Pump",
    marker="s",
    markersize=125,
    zorder=10,
    facecolor="none",
    linewidth=2.5,
)
hydamo.boundary_conditions.geometry.plot(
    ax=ax, color="red", label="Boundary", marker="s", markersize=125, zorder=10, facecolor="red", linewidth=0
)
ax.legend()

cx.add_basemap(ax, crs=28992, source=cx.providers.OpenStreetMap.Mapnik)
fig.tight_layout()

# %% [markdown]
# ## Data conversion
#

# %% [markdown]
# At this stage it is necessary to initialize the FM-model to which objects will be added. We also define the start- stop times now to synchronize the modules' time settings.

# %%
fm = FMModel()
# Set start and stop time
fm.time.refdate = 20160601
fm.time.tstop = 2 * 3600 * 24

# %% [markdown]
# ### Structures

# %% [markdown]
# HyDAMO contains methods to convert HyDAMO DAMO data to internal dataframes, which correspond to the D-HYDRO format.
#
# We first import the structures from the HyDAMO-object, since the structures' positions are necessary for defining the 1D-mesh. Structures can also be added without the HyDAMO imports.
#
# Note that for importing most structures multiple objects are needed from the GPKG. For more info on how to add structures (directly or from HyDAMO), see: https://hkvconfluence.atlassian.net/wiki/spaces/DHYD/overview.
#
#  - for weirs, a corresponding profile is looked up in the crossections. If one is found, the weir is implemented as a universal weir. If it is not found, a regular (rectangular) weir will be used. The cross-section ('hydamo.profile') should be related through 'hydamo.profile_line' to a 'hydamo.profile_group', which contains a 'stuwid' column which is equal to the GlobalID of the corresponding weir. The weir object can also include orifices, in that case the field 'overlaatonderlaat' in the 'management_device-object ('regelmiddel') is 'onderlaat'. For weirs it should be 'overlaat'. For regular weirs and orifices the crestlevel is inferred from the 'laagstedoorstroomhoogte' field in the hydamo.opening object. For universal weirs, this is also the case; however if no 'laagstedoorstroomhoogte' is present, or it is None, the crest level is derived from the lowest level of the associated profile.
#
#  - for culverts, a regelmiddel can be used to model a 'schuif' and/or a 'terugslagklep'. This is specified by the field 'soortregelmiddel'. In case of a 'terugslagklep', the flow direction is set to 'positive' instead of 'both'. In case of a 'schuif', a valve is implemented. Note that in DAMO 2.2, an 'afsluitmiddel' can contain the same information. For now, only a regelmiddel (management_device) is implemented.
#
#  - bridges need an associated crosssection. This is idential to universal weirs, but here the 'hydamo.profile_group'-object should contain a field 'brugid'.
#
#  - pumps are composed from 'hydamo.pumpstations', 'hydamo.pumps' and 'hydamo.managmement'. Only suction-side direction is implemented. Maximal capacity should be in m3/min.
#
# In most cases, these 'extra' arguments are optional, i.e. they are not required and can be left out. Some are required:
# - pumps really need all 3 objects ('hydamo.pumpstations', 'hydamo.pumps' and 'hydamo.managmement');
# - bridges really need an associated crosssection (see above);
#
# For more info on the structure definitions one is referred to the D-Flow FM user manual: https://content.oss.deltares.nl/delft3d/manuals/D-Flow_FM_User_Manual.pdf.

# %%
hydamo.structures.convert.weirs(
    weirs=hydamo.weirs,
    profile_groups=hydamo.profile_group,
    profile_lines=hydamo.profile_line,
    profiles=hydamo.profile,
    opening=hydamo.opening,
    management_device=hydamo.management_device,
)

hydamo.structures.convert.culverts(hydamo.culverts, management_device=hydamo.management_device)

hydamo.structures.convert.bridges(
    hydamo.bridges,
    profile_groups=hydamo.profile_group,
    profile_lines=hydamo.profile_line,
    profiles=hydamo.profile,
)

hydamo.structures.convert.pumps(hydamo.pumpstations, pumps=hydamo.pumps, management=hydamo.management)

# %% [markdown]
# Additional methods are available to add structures:

# %% [markdown]
# ### Oefening 2

# %%
########################Oefening 2######################################
# Voeg een stuw toe met de volgende functie met de volgende eigenschappen
# naam extra_weir
# watergang W_2708_0
# chainage 40.0 m
# Crest level 15.00 m NAP
# Crest width 5 m

# gebruik hiervoor onderstaande functie:
# hydamo.structures.add_rweir()


########################################################################


# %%
############Controle oefening 2###########################################
if "extra_weir" in hydamo.structures.rweirs_df.name.tolist():
    print("extra stuw is toegevoegd")
else:
    print("extra stuw is nog niet toegevoegd")


# %% [markdown]
# The resulting dataframes look like this:

# %%
hydamo.structures.rweirs_df

# %% [markdown]
# Indicate structures that are at the same location and should be treated as a compound structure. The D-Hydro GUI does this automatically, but for DIMR-calculations this should be done here.

# %%
cmpnd_ids = ["cmpnd_1", "cmpnd_2", "cmpnd_3"]
cmpnd_list = [["D_24521", "D_14808"], ["D_21450", "D_19758"], ["D_19757", "D_21451"]]
hydamo.structures.convert.compound_structures(cmpnd_ids, cmpnd_list)

# %% [markdown]
# ### Observation points

# %% [markdown]
# Observation points are now written in the new format, where one can discriminate between 1D ('1d') and 2D ('2d') observation points. This can be done using the optional argument 'locationTypes'. If it is omitted, all points are assumed to be 1d. 1D-points are always snapped to a the nearest branch. 2D-observation points are always defined by their X/Y-coordinates.
#
# Note: add_points can be called only once: once dfmodel.observation_points is filled,the add_points-method is not available anymore. Observation point coordinates can be definied eiher as an (x,y)-tuple or as a shapely Point-object.
#
# Observation points need to be defined prior to constructing the 1d mesh, as they will be separated from structures and each other by calculation points.

# %%
hydamo.observationpoints.add_points(
    [Point(199617, 394885), Point(199421, 393769), Point(199398, 393770)],
    ["Obs_BV152054", "ObsS_96684", "ObsO_test"],
    locationTypes=["1d", "1d", "1d"],
    snap_distance=10.0,
)

hydamo.observationpoints.add_points(
    [Point(200198, 396489), Point(201129, 396269), Point(200264, 394761), Point(199665, 395323)],
    ["ObsS_96544", "ObsP_113GIS", "Obs_UWR", "Obs_ORIF"],
    locationTypes=["1d", "1d", "1d", "1d"],
    snap_distance=10.0,
)
hydamo.observationpoints.observation_points.head()

# %% [markdown]
# ### The 1D mesh

# %% [markdown]
# The above structures are collected in one dataframe and in the generation of calculation poins, as structures should be separated by calculation points.

# %%
structures = hydamo.structures.as_dataframe(
    rweirs=True,
    bridges=True,
    uweirs=True,
    culverts=True,
    orifices=True,
    pumps=True,
)

# %% [markdown]
# Include also observation points
#

# %%
objects = pd.concat([structures, hydamo.observationpoints.observation_points], axis=0)

# %% [markdown]
# ### Oefening 3

# %%
#################oefening 3#################
# verander de rekenpunt afstand naar 10 m

mesh.mesh1d_add_branches_from_gdf(
    fm.geometry.netfile.network,
    branches=hydamo.branches,
    branch_name_col="code",
    node_distance=40,
    max_dist_to_struc=None,
    structures=objects,
)

# %% [markdown]
# ### Crosssections

# %% [markdown]
# Add cross-sections to the branches. To do this, many HyDAMO objects might be needed: if parameterised profiles occur, they are taken from hydamo.param_profile and, param_profile_values; if crosssections are associated with structures, those are specified in profile_group and profile lines.
#
# HyDAMO DAMO2.2 data contains two roughness values (high and low); here it can be specified which one to use.
# For branches without a crosssection, a default profile can be defined.

# %% [markdown]
# Partly, missing crosssections can be resolved by interpolating over the main branch. We set all branches with identical names to the same order numbers and assign those to the branches. D-Hydro will then interpolate the cross-sections over the branches.
#

# %%
# Here roughness variant "High" ("ruwheidhoog" in HyDAMO) is chosen. Variant "Low" ("ruwheidlaag" in HyDAMO) can also be chosen
hydamo.crosssections.convert.profiles(
    crosssections=hydamo.profile,
    crosssection_roughness=hydamo.profile_roughness,
    profile_groups=hydamo.profile_group,
    profile_lines=hydamo.profile_line,
    param_profile=hydamo.param_profile,
    param_profile_values=hydamo.param_profile_values,
    branches=hydamo.branches,
    roughness_variant="High",
)

# %% [markdown]
# Check how many branches do not have a profile.

# %%
missing = hydamo.crosssections.get_branches_without_crosssection()
print(f"{len(missing)} branches are still missing a cross section.")

print(
    f"{len(hydamo.crosssections.get_structures_without_crosssection())} structures are still missing a cross section."
)

# %% [markdown]
# We plot the missing ones.

# %%
fig, ax = plt.subplots(figsize=(16, 16))
xmin, ymin, xmax, ymax = hydamo.clipgeo.bounds
ax.set_xlim(round(xmin), round(xmax))
ax.set_ylim(round(ymin), round(ymax))
hydamo.profile.geometry.plot(ax=ax, color="black", label="dwarsprofielen", linewidth=5)
hydamo.branches.loc[missing, :].geometry.plot(ax=ax, color="C4", label="geen dwarsprofiel", linewidth=10)
hydamo.branches.geometry.plot(ax=ax, label="Watergangen")
ax.get_xaxis().set_visible(False)
ax.get_yaxis().set_visible(False)
ax.legend()
cx.add_basemap(ax, crs=28992, source=cx.providers.OpenStreetMap.Mapnik)
fig.tight_layout()
plt.show()

# %% [markdown]
# One way to assign crosssections to branches is to assigning order numbers to branches, so the crosssections are interpolated over branches with the same order number. The functino below aassigns the same order number to branches with a common attribute of hydamo.branches. In this example, all branches with the same 'naam' are given the same order number.
#
# Only branches that are in the 'missing' list (and do not have a crosssection) are taken into account.
#
# There are exceptions: for instance the branch "Retentiebekken Rosmolen" has a name, and therefore an ordernumber, but it cannot be interpolated since it consists of only one segment. Its branch-id is W_1386_0. We pass a list of exceptions like that, making sure that no order numbers will be assigned to those branches.

# %% [markdown]
# Retentiebekken Rosmolen has a name, and therefore an ordernumber, but cannot be interpolated. Set the order to 0, so it gets a default profile.

# %%
missing_after_interpolation = mesh.mesh1d_order_numbers_from_attribute(
    hydamo.branches, missing, order_attribute="naam", network=fm.geometry.netfile.network, exceptions=["W_1386_0"]
)

# %%
print(f"After interpolation, {len(missing_after_interpolation)} branches are still missing a cross section.")

# %%
fig, ax = plt.subplots(figsize=(16, 16))
xmin, ymin, xmax, ymax = hydamo.clipgeo.bounds
ax.set_xlim(round(xmin), round(xmax))
ax.set_ylim(round(ymin), round(ymax))
hydamo.profile.geometry.plot(ax=ax, color="C3", label="dwarsprofielen", linewidth=5)
hydamo.branches.loc[missing, :].geometry.plot(ax=ax, color="C4", label="geen dwarsprofiel", linewidth=10)
hydamo.branches.geometry.plot(ax=ax, label="Watergangen")
ax.get_xaxis().set_visible(False)
ax.get_yaxis().set_visible(False)
ax.legend()
cx.add_basemap(ax, crs=28992, source=cx.providers.OpenStreetMap.Mapnik)
fig.tight_layout()
plt.show()

# %% [markdown]
# For these ones, we apply a default profile. In this case an yz-profile, but it can also be a rectangular or other type or profile.

# %% [markdown]
# ### Oefening 4

# %%
#########################Oefening 4#########################################################
# Pas het standaard yz-profiel aan naar:
# Verbreed de bodem van 5 meter naar 7 meter
# Verdiep het profiel door de bodemhoogte te verlagen van 19 m NAP naar 18 m NAP


# Set a default cross section
profiel = np.array([[0, 21], [2, 19], [7, 19], [9, 21]])
default = hydamo.crosssections.add_yz_definition(
    yz=profiel, thalweg=4.5, roughnesstype="StricklerKs", roughnessvalue=25.0, name="default"
)

hydamo.crosssections.set_default_definition(definition=default, shift=0.0)
hydamo.crosssections.set_default_locations(missing_after_interpolation)

# %%
###########controle oefening 4: controleer je yz-profiel met deze code#################
x = []
y = []
for i in range(len(profiel)):
    x.append(profiel[i][0])
    y.append(profiel[i][1])
plt.plot(x, y, label="nieuw")
plt.xlabel("x")
plt.ylabel("y")
plt.legend()
plt.grid()
plt.show()

# %% [markdown]
# ### Storage nodes

# %% [markdown]
# Storage nodes can be added from a layer with a geometry and a table in CSV of Excel. The geometry can contain polygons or points and is snapped to the nearest branch. The table should contain a code (identical to the one in the geometry) and a series of areas (in m2) and levels (m+NAP)of equal length.

# %%
# geometry
f_storage_areas = data_path / "bergingspolygonen.shp"
hydamo.storage_areas.read_shp(f_storage_areas, index_col="code")
hydamo.storage_areas.snap_to_branch(hydamo.branches, snap_method="centroid", maxdist=1000)

# data
storage_node_data = pd.read_excel(data_path / "storage_data.xls")
storage_node_data = storage_node_data.rename(columns={"GEBIEDID": "code", "OPPERVLAK": "area", "MAAIVELD": "level"})
# they can also contain a name, this will be used in the model if available

hydamo.storage_areas["name"] = hydamo.storage_areas["code"]

# %% [markdown]
# The resulting data frame of geometries can be added to the model at once:

# %%
# convert all storage
hydamo.storagenodes.convert.storagenodes_from_input(
    storagenodes=hydamo.storage_areas, storagedata=storage_node_data, network=fm.geometry.netfile.network
)

# %% [markdown]
# Or an extra storage node can be added from the notebook:

# %%
hydamo.storagenodes.add_storagenode(
    id="sto_test",
    xy=(141001, 395030),
    name="sto_test",
    usetable="true",
    levels=" ".join(np.arange(17.1, 19.6, 0.1).astype(str)),
    storagearea=" ".join(np.arange(100, 1000, 900 / 25.0).astype(str)),
    interpolate="linear",
    network=fm.geometry.netfile.network,
)

# %% [markdown]
# Note that if 'usetable=True' an area-waterlevel relation is provided. The alternative, meant for an urban setting, implies constant storage between bedlevel and streetlevel and upwards. For most applications of D-HyDAMO, the first application is most relevant, like the example below.

# %% [markdown]
# ### Boundary conditions

# %% [markdown]
# The HyDAMO database contains constant boundaries. They are added to the model:

# %%
hydamo.external_forcings.convert.boundaries(hydamo.boundary_conditions, mesh1d=fm.geometry.netfile.network)

# %% [markdown]
# However, we also need an upstream discharge boundary, which is not constant. We add a fictional time series, which can be read from Excel as well:

# %%
series = pd.Series(np.sin(np.linspace(2, 8, 120) * -1) + 3.0)
series.index = [pd.Timestamp("2016-06-01 00:00:00") + pd.Timedelta(hours=i) for i in range(120)]
series.plot()
plt.show()

# %% [markdown]
# There is also a fuction to convert laterals, but to run this we also need the RR model. Therefore, see below. It also possible to manually add boundaries and laterals as constants or timeseries. We implement the sinoid above as an upstream streamflow boundary and a lateral:

# %%
hydamo.external_forcings.add_boundary_condition(
    "RVW_01", (197464.0, 392130.0), "dischargebnd", series, fm.geometry.netfile.network
)

# %%
hydamo.dict_to_dataframe(hydamo.external_forcings.boundary_nodes)

# %% [markdown]
# In the same way as for boundaries, it is possible to add laterals using a fuction. Here are two examples. The first one adds a constant flow (1.5 m3/s) to a location on branch W_2399.0:

# %%
hydamo.external_forcings.add_lateral(id="LAT01", branchid="W_2399_0", chainage=100.0, discharge=1.5)

# %% [markdown]
# The second example adds a timeseries, provided as a pandas series-object, to another location on the same branch.It can be read from CSV, but here we pass a hypothetical sine-function.

# %%
series = pd.Series(np.sin(np.linspace(2, 8, 120) * -1) + 2.0)
series.index = [pd.Timestamp("2016-06-01 00:00:00") + pd.Timedelta(hours=i) for i in range(120)]
hydamo.external_forcings.add_lateral(id="LAT02", branchid="W_2399_0", chainage=900.0, discharge=series)

# %% [markdown]
# Set the initial water depth to 0.5 m. It is also possible to set a global water level using the equivalent function "set_initial_waterlevel".

# %%
hydamo.external_forcings.set_initial_waterdepth(1.5)

# %% [markdown]
# ## 2D Mesh

# %% [markdown]
# As explained above, several options exist for mesh generation.
#
# 1. Meshkernel (MK). This is the preferred option: it is platform-independent, supports triangular meshes and has orthogenalization functionality.
# 2. Gridgeom (GG). Older functionality from delft3dfmpy. It is still available in D-HyDAMO but will de depracated and fully replaced by Meshkernel.
# 3. Import a mesh from other software, such as SMS.
#
# To generate a mesh we illustrate the following steps:
#     - Generate grid within a polygon. The polygon is the extent given to the HyDAMO model.
#     - Refine along the main branch
#     - clip the mesh around the branches
#     - Determine altitude from a DEM.
#
# <span style='color:Blue'> Important note: Triangular meshes are created without optimalization of smoothness or orthogonalization. This can be handled in de D-HYDRO GUI. In future we will implement this in D-HyDAMO.  </span>

# %%
# 2d mesh extent
if TwoD:
    extent = gpd.read_file(data_path / "2D_extent.shp").at[0, "geometry"]
    network = fm.geometry.netfile.network
    rasterpath = data_path / "rasters/AHN_2m_clipped_filled.tif"

# %% [markdown]
# Also the creation of a triangular mesh is possible. Note that there are maybe issues with the mesh orthogenality and additional steps in the D-Hydro GUI to orthogenalize the mesh may be necessary. In future we will implement this functionality in D-HyDAMO.

# %%
# if TwoD:
#     mesh.mesh2d_add_triangular(network, extent, edge_length=50.0)

# %% [markdown]
# And a rectangular mesh with an arbitrary 50 m cell size:

# %% [markdown]
# ### Oefening 5

# %%
##############################Oefening 5########################################
# voeg een 2D grid toe met een resolutie van 40 m


if TwoD:
    mesh.mesh2d_add_rectilinear(network, extent, dx=20, dy=20)  # dx en dy aangepast

# %% [markdown]
# Refine the 2D mesh within an arbitrary distance of 50 m from all branches (works on a subselection as well). There are several (optional) arguments to the refinement function, that typically give good results so it is not needed to pass them. For illustration, they are listed here. For more details, see https://deltares.github.io/MeshKernel.

# %%
if TwoD:
    refine_parameters = {
        "refine_intersected": True,
        "use_mass_center_when_refining": True,
        "min_edge_size": 1.0,
        "refinement_type": 2,
        "connect_hanging_nodes": True,
        "account_for_samples_outside_face": True,
        "max_refinement_iterations": 1,
        "smoothing_iterations": 5,
        "max_courant_time": 120.0,
        "directional_refinement": False,
    }

# %%
if TwoD:
    print("Nodes before refinement:", network._mesh2d.mesh2d_node_x.size)
    buffer = Polygon(hydamo.branches.buffer(50.0).unary_union.exterior)
    mesh.mesh2d_refine(network, buffer, 1, refine_parameters)
    print("Nodes after refinement:", network._mesh2d.mesh2d_node_x.size)

# %% [markdown]
# Clip the 2D mesh in a 20m buffer around a number of branches. This is to illustrate the use of both lateral (when the mesh is clipped) ad embedded (without clipping) links.

# %% [markdown]
# ### Oefening 6

# %%
if TwoD:
    print("Nodes before clipping:", network._mesh2d.mesh2d_node_x.size)
    #################Oefening 6#######################################################################
    # Knip de watergang met id "W_242224_0" uit met de functie mesh.mesh2d_clip
    # Gebruik de volgende code om de Oostrumsche beek te selecteren:
    #  branch = hydamo.branches.loc['W_242224_0'].geometry.buffer(40.)

    ###################################################################################################
    print("Nodes after clipping:", network._mesh2d.mesh2d_node_x.size)


# %% [markdown]
# Alternatively, the mesh can be read from a netcdf file:

# %%
# if TwoD:
#     mesh.mesh2d_from_netcdf(network, data_path / "import.nc")

# %% [markdown]
# Add elevation data to the cells

# %%
if TwoD:
    mesh.mesh2d_altitude_from_raster(network, rasterpath, "face", "mean", fill_value=-999)

# %% [markdown]
# To add a mesh, currently 2 options exist:
# 1. The converter can generate a relatively simple mesh, with a rotation or refinement. Note that rotation _and_ refinement is currently not possible. In the section below we generate a refined 2D mesh with the following steps:
#
#     - Generate grid within a polygon. The polygon is the extent given to the HyDAMO model.
#     - Refine along the main branch
#     - clip the mesh around the branches
#     - Determine altitude from a DEM.
#
# <span style='color:Blue'> Important note: Triangular meshes are created without optimalization of smoothness or orthogonalization. This can be handled in de D-HYDRO GUI. In future we will implement this in D-HyDAMO.  </span>

# %% [markdown]
# ### Add 1d-2d links

# %% [markdown]
# Three options exist to add 1d2d links to the network:
#  - from 1d to 2d
#  - from 2d to 1d embedded: allowing overlap (i.e., the 2D cells and 1D branches are allowed to intersect)
#  - from 2d to 1d lateral: there is no overlap and from each cell the closest 1d points are used.
#
#  See https://hkvconfluence.atlassian.net/wiki/spaces/DHYD/pages/601030709/1D2D-links for details.

# %%
if TwoD:
    # mesh.links1d2d_add_links_1d_to_2d()
    mesh.links1d2d_add_links_2d_to_1d_embedded(network)
    mesh.links1d2d_add_links_2d_to_1d_lateral(network, max_length=100.0)
    mesh.links1d2d_remove_1d_endpoints(network)
    mesh.links1d2d_remove_within(network, hydamo.branches.loc["W_1598_0"].geometry.buffer(100.0))

# %%
# plot the network
if TwoD:
    network = fm.geometry.netfile.network
    fig, axs = plt.subplots(figsize=(13.5, 6), ncols=2, constrained_layout=True)
    plot_network(network, ax=axs[0])
    plot_network(network, ax=axs[1], links1d2d_kwargs=dict(lw=3, color="k"))
    axs[0].autoscale_view()
    axs[1].set_xlim(200000, 200500)
    axs[1].set_ylim(395750, 396250)

    sc = axs[1].scatter(
        x=network._mesh2d.mesh2d_face_x,
        y=network._mesh2d.mesh2d_face_y,
        c=network._mesh2d.mesh2d_face_z,
        s=10,
        vmin=22,
        vmax=27,
    )
    cb = plt.colorbar(sc, ax=axs[1])
    cb.set_label("Face level [m+NAP]")

    plt.show()

# %% [markdown]
# For finalizing the FM-model, we also need the coupling to the other modules. Therefore, we will do that first.

# %% [markdown]
# # Add an RTC model

# %% [markdown]
# RTC contains many different options. Three are now implemented in D-HyDAMO:
# - a PID controller (crest level is determined by water level at an observation point);
# - a time controller (a time series of crest level is provided);
# - the possibility for the users to provide their own XML-files for more complex cases. Depending on the complexity, the integration might not yet work for all cases.

# %% [markdown]
# First, initialize a DRTCModel-object. The input is hydamo (for the data), fm (for the time settings), a path where the model will be created (typically an 'rtc' subfolder), a timestep (default 60 seconds) and, optionally, a folder where the user can put 'custom' XML code that will be integrated in the RTC-model. These files will be parsed now and be integrated later.
#
# These files can, for example, be obtained by schematizing a control group in DHYDRO and export it to a DIMR model. The RTC XML-code can then be parsed by D-HyDAMO.
#
# if rtc_onlytimesries is True, supplied timeseries (of observed crest levels, for instance) will be used to replace PID- and intervan controllers by time controllers. This is useful in model calibration, for instance.

# %%
if RTC:
    if rtc_onlytimeseries:
        timeseries = pd.read_csv(rtc_timeseriesdata, sep=",", index_col="Time", parse_dates=True)
        drtcmodel = DRTCModel(
            hydamo,
            fm,
            output_path=output_path,
            rtc_timestep=60.0,
            rtc_onlytimeseries=True,
            rtc_timeseriesdata=timeseries,
        )
    else:
        drtcmodel = DRTCModel(
            hydamo,
            fm,
            output_path=output_path,
            rtc_timestep=60.0,
            complex_controllers_folder=data_path
            / "complex_controllers",  # location where user defined XLM-code should be located
        )


# %% [markdown]
# If PID controllers are present, they need settings that are not included in the HyDAMO DAMO2.2 data. We define those in a dictionary. They can be specified for each structure - in that case the key of the dictionary should match the key in the HyDAMO DAMO2.2 'sturing'-object. If no separate settings are provided the 'global' settings are used.

# %% [markdown]
# If PID- or interval controllers are present, they need settings that are not included in the HyDAMO DAMO2.2 data. We define those in dictionaries. They can be specified for each structure - in that case the key of the dictionary should match the key in the HyDAMO DAMO2.2 'sturing'-object. If no separate settings are provided the 'global' settings are used.
#
# Note that it is also possible to add RTC objects individually, in that case the settings should provided in the correct function as shown below. When interval controllers are converted from HyDAMO data, the settings above and below the deadband are taken from the min- and max setting.

# %% [markdown]
# PID- and interval controllers shoud have an observation location. We added those before, but we can check them here:

# %%
hydamo.observationpoints.observation_points.head()

# %%
if RTC and not rtc_onlytimeseries:
    pid_settings = {}
    interval_settings = {}

    pid_settings["global"] = {
        "ki": 0.001,
        "kp": 0.00,
        "kd": 0.0,
        "maxspeed": 0.00033,
    }
    interval_settings["global"] = {
        "deadband": 0.2,
        "maxspeed": 0.00033,
    }
    pid_settings["kst_pid"] = {
        "ki": 0.001,
        "kp": 0.0,
        "kd": 0.0,
        "maxspeed": 0.00033,
    }

# %% [markdown]
# The function 'from_hydamo' converts the controllers that are specified in the HyDAMO DAMO2.2 data. The extra input consists of the settings for PID controllers (see above) and a dataframe with time series for the time controllers.

# %%
if RTC and not rtc_onlytimeseries:
    if not hydamo.management.typecontroller.empty:
        timeseries = pd.read_csv(data_path / "timecontrollers.csv")
        timeseries.index = timeseries.Time

        drtcmodel.from_hydamo(pid_settings=pid_settings, interval_settings=interval_settings, timeseries=timeseries)


# %% [markdown]
# Additional controllers, that are not included in D-HyDAMO DAMO2.2 might be specified like this:

# %%
if RTC and not rtc_onlytimeseries:
    drtcmodel.add_time_controller(
        structure_id="S_96548", steering_variable="Crest level (s)", data=timeseries.loc[:, "S_96548"]
    )

# %% [markdown]
# Additional controllers, that are not included in D-HyDAMO DAMO2.2 might be specified like this:

# %%
if RTC:
    drtcmodel.add_time_controller(
        structure_id="S_96548", steering_variable="Crest level (s)", data=timeseries.loc[:, "S_96548"]
    )

# %% [markdown]
# ### Oefening 7

# %%
#######################Oefening 7##############################
# gebruik onderstaande functie om een pid controller toe te voegen voor stuw S_96544. Het meetpunt heet ObsS_96544 en het streefpeil is 13.2 m+NAP.

# if RTC:
#     drtcmodel.add_pid_controller(structure_id=,
#                                 observation_location=,
#                                 steering_variable=,
#                                 target_variable=,
#                                 setpoint=,
#                                 upper_bound=,
#                                 lower_bound=,
#                                 ki=0.001,
#                                 kp=0.0,
#                                 kd=0.0,
#                                 max_speed=0.00033)

# %%
####################### Controle oefening 7#####################
if "S_96544" in list(drtcmodel.pid_controllers.keys()):
    print("extra controller is toegevoegd")
else:
    print("extra controller is nog niet toegevoegd")
drtcmodel.pid_controllers

# %% [markdown]
# ## Add a rainfall runoff model

# %% [markdown]
# RR has not changed yet compared to delft3dfmpy. Initialize a model:

# %%
if RR:
    drrmodel = DRRModel()

# %% [markdown]
# Catchments are provided in the HyDAMO DAMO2.2 format and included in the GPKG. They can also be read from other formats using 'read_gml', or 'read_shp'. Note that in case of shapefiles column mapping is necessary because the column names are truncated.
#
# Note that when catchments have a "MultiPolygon' geometry, the multipolygons are 'exploded' into single polygon geometries. A warning of this is isued, and a suffix is added to every polygons ID to prevent duplicates.
#
# For every catchment, the land use areas will be calculated and if appopriate a maximum of four RR-nodes will be created per catchment:
#  - unpaved (based on the Ernst concept)
#  - paved
#  - greenhouse
#  - open water (not the full Sobek2 open water, but only used to transfer (net) precipitation that falls on open water that is schematized in RR to the 1D/2D network.
#
# At the moment, two options exist for the schematisation of the paved area:
#  1) simple: the paved fraction of each catchment is modelled with a paved node, directly connected to catchments' boundary node
#  <br>
#  2) more complex: sewer area polygons and overflow points are used a input as well. For each sewer area, the overlapping paved area is the distributed over the overflows that are associated with the sewerarea (the column 'lateraleknoopcode') using the area fraction (column 'fractie') for each overflow. In each catchment, paved area that does not intersect with a sewer area gets an unpaved node as in option (1).
#

# %% [markdown]
# Load data and settings. RR-parameters can be derived from a raster (using zonal statistics per catchment), or provided as a standard number. Rasters can be in any format that is accepted by the package rasterio: https://gdal.org/drivers/raster/index.html. All common GIS-formats (.asc, .tif) are accepted.

# %%
if RR:
    lu_file = data_path / "rasters" / "sobek_landuse.tif"
    ahn_file = data_path / "rasters" / "AHN_2m_clipped_filled.tif"
    soil_file = data_path / "rasters" / "sobek_soil.tif"
    surface_storage = 10.0  # [mm]
    infiltration_capacity = 100.0  # [mm/hr]
    initial_gwd = 1.2  # water level depth below surface [m]
    runoff_resistance = 1.0  # [d]
    infil_resistance = 300.0  # [d]
    layer_depths = [0.0, 1.0, 2.0]  # [m]
    layer_resistances = [30, 200, 10000]  # [d]

# %% [markdown]
# A different meteo-station can be assigned to each catchment, of a different shape can be provided. Here, 'meteo_areas' are assumed equal to the catchments.

# %%
if RR:
    meteo_areas = hydamo.catchments

# %% [markdown]
# ### Configuration of greenhouse_areas

# %% [markdown]
# Similar to sewage areas and overflows for paved nodes, known greenhouse areas and greenhouse discharge locations can be assigned. Two extra shapefiles or geopackage layers are needed:
# - contains polygons with greenhouse areas, with a column 'code' containing the ID. They are read into the object 'greenhouse_areas'. These areas are converted to greenhouse nodes irrespective of the underlying landuse in the landuse raster;
# - greenhouse outflow points: with a column 'codegerelateerdobject' to couple it with the right polygon. They are read into the object 'greenhouse_laterals';
#
# By adding columns to greenhouse_areas their parameters can be specified: roof_storage_mm is the storage on the roof, basin_storage_class is the above-ground storageclass that is used in D-RR. It discreminates in 10 classes each with different basin storage capacities (in m3/ha).  If no specific numbers per greenhouse provided per greenhouse_are provided uniform values can be provided.
#
# These storage classes identified by 'basin_storage_class' are as follows:
#  1. 0-500 m3/ha;
#  2. 500-1000 m3/ha;
#  3. 1000-1500 m3/ha;
#  4. 1500-2000 m3/ha;
#  5. 2000-2500 m3/ha;
#  6. 2500-3000 m3/ha;
#  7. 3000-4000 m3/ha;
#  8. 4000-5000 m3/ha;
#  9. 5000-6000 m3/ha;
# 10. more than 600 m3/ha.

# %%
if RR:
    roof_storage = 5.0  # [mm]
    basin_storage_class = 3  # default class
    hydamo.greenhouse_areas.read_gpkg_layer(data_path / "greenhouses.gpkg", layer_name="greenhouses", index_col="code")
    hydamo.greenhouse_laterals.read_gpkg_layer(data_path / "greenhouse_laterals.gpkg", layer_name="laterals")
    hydamo.greenhouse_laterals.snap_to_branch(hydamo.branches, snap_method="overal", maxdist=1100)
    hydamo.greenhouse_areas["roof_storage_mm"] = roof_storage
    hydamo.greenhouse_areas["basin_storage_class"] = [i + 1 for i in range(hydamo.greenhouse_areas.shape[0])]

# %%
hydamo.greenhouse_areas.head()

# %% [markdown]
# ## Unpaved nodes

# %% [markdown]
# For land use and soil type a coding is prescribed. For landuse, the legend of the map is expected to be as follows: <br>
#  1 potatoes  <br>
#  2 wheat<br>
#  3 sugar beet<br>
#  4 corn       <br>
#  5 other crops <br>
#  6 bulbous plants<br>
#  7 orchard<br>
#  8 grass  <br>
#  9 deciduous forest  <br>
# 10 coniferous forest<br>
# 11 nature<br>
# 12 barren<br>
# 13 open water<br>
# 14 built-up<br>
# 15 greenhouses<br>
#
# For classes 1-12, the areas are calculated from the provided raster and remapped to the classification in the Sobek RR-tables.
#
#
# The coding for the soil types:<br>
# 1 'Veengrond met veraarde bovengrond'<br>
#  2 'Veengrond met veraarde bovengrond, zand'<br>
#  3 'Veengrond met kleidek'<br>
#  4 'Veengrond met kleidek op zand'<br>
#  5 'Veengrond met zanddek op zand'<br>
#  6 'Veengrond op ongerijpte klei'<br>
#  7 'Stuifzand'<br>
#  8 'Podzol (Leemarm, fijn zand)'<br>
#  9 'Podzol (zwak lemig, fijn zand)'<br>
# 10 'Podzol (zwak lemig, fijn zand op grof zand)'<br>
# 11 'Podzol (lemig keileem)'<br>
# 12 'Enkeerd (zwak lemig, fijn zand)'<br>
# 13 'Beekeerd (lemig fijn zand)'<br>
# 14 'Podzol (grof zand)'<br>
# 15 'Zavel'<br>
# 16 'Lichte klei'<br>
# 17 'Zware klei'<br>
# 18 'Klei op veen'<br>
# 19 'Klei op zand'<br>
# 20 'Klei op grof zand'<br>
# 21 'Leem'<br>
#
#
# And surface elevation needs to be in m+NAP.

# %%
if RR:
    drrmodel.unpaved.io.unpaved_from_input(
        hydamo.catchments,
        lu_file,
        ahn_file,
        soil_file,
        surface_storage,
        infiltration_capacity,
        initial_gwd,
        meteo_areas,
        greenhouse_areas=hydamo.greenhouse_areas,
    )
    drrmodel.unpaved.io.ernst_from_input(
        hydamo.catchments,
        depths=layer_depths,
        resistance=layer_resistances,
        infiltration_resistance=infil_resistance,
        runoff_resistance=runoff_resistance,
    )

# %% [markdown]
# ## Paved nodes

# %%
if RR:
    street_storage = 5.0  # [mm]
    sewer_storage = 5.0  # [mm]
    pumpcapacity = 0.2  # [m3/s]

# %% [markdown]
# For paved areas, two options are allowed.
# 1) simply assign a paved noded to the catchment area that is paved in the landuse map.

# %%
# if RR:
#     drrmodel.paved.io.paved_from_input(
#             catchments=hydamo.catchments,
#             landuse=lu_file,
#             surface_level=ahn_file,
#             street_storage=street_storage,
#             sewer_storage=sewer_storage,
#             pump_capacity=pumpcapacity,
#             meteo_areas=meteo_areas,
#             zonalstats_alltouched=True,
#         )


# %% [markdown]
#  2. Also use sewer-areas and overflows by providing them to the function. In that case, the 'overflows' shapefile should have a field 'codegerelateerdobject' that contains the 'code' of the sewer area it is linked to, and a 'fraction' (float) that contains the fraction of the sewer area that drains through that overflow.
#
# For every overflow, a paved node is created, containing the fraction of the sewer area. The paved area of the catchment that intersects the sewer-area is corrected for this; for the remaining paved area a seperate paved node is created.|

# %%
if RR:
    hydamo.sewer_areas.read_shp(
        str(data_path / "rioleringsgebieden.shp"),
        index_col="code",
        column_mapping={"Code": "code", "Berging_mm": "riool_berging_mm", "POC_m3s": "riool_poc_m3s"},
    )
    hydamo.overflows.read_shp(
        str(data_path / "overstorten.shp"), column_mapping={"codegerela": "codegerelateerdobject"}
    )
    hydamo.overflows.snap_to_branch(hydamo.branches, snap_method="overal", maxdist=1100)

# %%
hydamo.sewer_areas

# %%
if RR:
    drrmodel.paved.io.paved_from_input(
        catchments=hydamo.catchments,
        landuse=lu_file,
        surface_level=ahn_file,
        sewer_areas=hydamo.sewer_areas,
        overflows=hydamo.overflows,
        street_storage=street_storage,
        sewer_storage=sewer_storage,
        pump_capacity=pumpcapacity,
        meteo_areas=meteo_areas,
        zonalstats_alltouched=True,
    )

# %% [markdown]
# ## Greenhouse nodes

# %% [markdown]
# Also for greenhouses two options exist. <br>
# Option 1: use both the land use map and supply separate greenhouse areas and laterals.

# %%
if RR:
    # greenhouse with additional greenhouse nodes
    drrmodel.greenhouse.io.greenhouse_from_input(
        catchments=hydamo.catchments,
        landuse=lu_file,
        surface_level=ahn_file,
        greenhouse_areas=hydamo.greenhouse_areas,
        greenhouse_laterals=hydamo.greenhouse_laterals,
        roof_storage=roof_storage,
        basin_storage_class=basin_storage_class,
        meteo_areas=meteo_areas,
        zonalstats_alltouched=True,
    )

# %% [markdown]
# Option 2: base greenhouse areas only on the land use map.

# %%
# if RR:
#     drrmodel.greenhouse.io.greenhouse_from_input(
#         hydamo.catchments, lu_file, ahn_file, roof_storage, meteo_areas, zonalstats_alltouched=True
#     )

# %% [markdown]
# ## Open water

# %% [markdown]
# As opposed to Sobek, in D-Hydro open water is merely an interface for precpitation and evaporation. No management and water levels are included.

# %%
# RR
if RR:
    drrmodel.openwater.io.openwater_from_input(hydamo.catchments, lu_file, meteo_areas, zonalstats_alltouched=True)

# %% [markdown]
# ## RR boundaries

# %% [markdown]
# The overflows argument is optional and only needed if overflow and sewer areas are included above.

# %%
if RR:
    drrmodel.external_forcings.io.boundary_from_input(
        hydamo.laterals,
        hydamo.catchments,
        drrmodel,
        overflows=hydamo.overflows,
        greenhouse_laterals=hydamo.greenhouse_laterals,
    )

# %% [markdown]
# ### External forcings
#
# Three types of external forcing need to be provided:<br>
# - Seepage/drainage
# - Precipitation
# - Evaporation
#
# All are assumed to be spatially variable and thus need to pe provided as rasters per time step. Only the locations of the folders containing the rasters need to be provided; the time step is then derived from the file names.
#
# Precipitation and evaporation are assumed to be in mm/d. As for evaporation only one meteostation is used, the meteo_areas are dissolved. For seepage, as the use of Metaswap-rasters is allowed, the unit is assumed to m3/grid cell/timestep.
#
# Rastertypes can be any type that is recognized by rasterio (in any case Geotiff and ArcASCII rasters). If the file extension is 'IDF', as is the case in Modflow output, the raster is read using the 'imod'-package.
#
# IMPORTANT: time steps are extracted from the file names. Therefore, the names should cohere to some conditions:
# The filename should consist of at least two parts, separated by underscores. The second part needs to contain time information, which should be formatted as YYYYMMDDHHMMSS (SS may be omitted). Or, for daily data YYYYMMDD.
#
# For example: 'precip_20200605151500.tif'
#
# Extracting meteo-data from rasters can be time consuming. If precip_file and evap_file are specified, meteo-files are copied from an existing location.

# %%
if RR:
    seepage_folder = data_path / "rasters" / "seepage"
    precip_file = str(data_path / "DEFAULT.BUI")
    evap_folder = data_path / "rasters" / "evaporation"
    drrmodel.external_forcings.io.seepage_from_input(hydamo.catchments, seepage_folder)
    drrmodel.external_forcings.io.precip_from_input(meteo_areas, precip_folder=None, precip_file=precip_file)
    drrmodel.external_forcings.io.evap_from_input(meteo_areas, evap_folder=evap_folder, evap_file=None)

# %% [markdown]
# Add the main parameters:

# %%
if RR:
    drrmodel.d3b_parameters["Timestepsize"] = 300
    drrmodel.d3b_parameters["StartTime"] = "'2016/06/01;00:00:00'"  # should be equal to refdate for D-HYDRO
    drrmodel.d3b_parameters["EndTime"] = "'2016/06/03;00:00:00'"
    drrmodel.d3b_parameters["RestartIn"] = 0
    drrmodel.d3b_parameters["RestartOut"] = 0
    drrmodel.d3b_parameters["RestartFileNamePrefix"] = "Test"
    drrmodel.d3b_parameters["UnsaturatedZone"] = 1
    drrmodel.d3b_parameters["UnpavedPercolationLikeSobek213"] = -1
    drrmodel.d3b_parameters["VolumeCheckFactorToCF"] = 100000


# %% [markdown]
# Laterals are different for the case with and without RR. There can be three options:
# 1) laterals from the RR model (RR=True). There will be real-time coupling where RR and FM are calculated in parallel. Note that, again, the overflows are needed because there are extra boundaries. If there are no overflows, it does not have to be provided.
# 2) timeseries: lateral_discharges can be a dataframe with the code of the lateral as column headers and timesteps as index
# 3) constant: lateral_discharges can be a pandas Series with the code of the lateral as the index. This is the case in the example when RR=False.

# %%
if RR:
    hydamo.external_forcings.convert.laterals(
        hydamo.laterals,
        overflows=hydamo.overflows,
        greenhouse_laterals=hydamo.greenhouse_laterals,
        lateral_discharges=None,
        rr_boundaries=drrmodel.external_forcings.boundary_nodes,
    )
else:
    lateral_discharges = hydamo.laterals["afvoer"]
    lateral_discharges.index = hydamo.laterals.code
    hydamo.external_forcings.convert.laterals(
        hydamo.laterals, lateral_discharges=lateral_discharges, rr_boundaries=None
    )


# %% [markdown]
# ### Plot the RR model


# %%
def node_geometry(dict):
    # Function to put the node geometries in geodataframes
    from shapely.geometry import LineString, Point

    geoms = []
    links = []
    for i in dict.items():
        if "ar" in i[1]:
            if np.sum([float(s) for s in i[1]["ar"].split(" ")]) > 0:
                geoms.append(Point((float(i[1]["px"]), float(i[1]["py"]))))
                links.append(
                    LineString(
                        (
                            Point(float(i[1]["px"]), float(i[1]["py"])),
                            Point(
                                float(drrmodel.external_forcings.boundary_nodes[i[1]["boundary_node"]]["px"]),
                                float(drrmodel.external_forcings.boundary_nodes[i[1]["boundary_node"]]["py"]),
                            ),
                        )
                    )
                )
        else:
            geoms.append(Point((float(i[1]["px"]), float(i[1]["py"]))))
    return ((gpd.GeoDataFrame(geoms, columns=["geometry"])), gpd.GeoDataFrame(links, columns=["geometry"]))


# %%
if RR:
    import matplotlib.patches as mpatches

    fig, ax = plt.subplots(figsize=(10, 10))

    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    xmin, ymin, xmax, ymax = hydamo.clipgeo.bounds
    ax.set_xlim(round(xmin), round(xmax))
    ax.set_ylim(round(ymin), round(ymax))

    hydamo.catchments.geometry.plot(ax=ax, label="Catchments", edgecolor="black", facecolor="pink", alpha=0.5)
    hydamo.branches.geometry.plot(ax=ax, label="Channel")
    node_geometry(drrmodel.unpaved.unp_nodes)[0].plot(ax=ax, markersize=30, marker="s", color="green", label="Unpaved")
    node_geometry(drrmodel.unpaved.unp_nodes)[1].plot(ax=ax, color="black", linewidth=0.5)
    node_geometry(drrmodel.paved.pav_nodes)[0].plot(ax=ax, markersize=20, marker="s", color="red", label="Paved")
    node_geometry(drrmodel.paved.pav_nodes)[1].plot(ax=ax, color="black", linewidth=0.5)
    node_geometry(drrmodel.greenhouse.gh_nodes)[0].plot(ax=ax, markersize=15, color="yellow", label="Greenhouse")
    node_geometry(drrmodel.greenhouse.gh_nodes)[1].plot(ax=ax, color="black", linewidth=0.5)
    node_geometry(drrmodel.openwater.ow_nodes)[0].plot(ax=ax, markersize=10, color="blue", label="Openwater")
    node_geometry(drrmodel.openwater.ow_nodes)[1].plot(ax=ax, color="black", linewidth=0.5, label="RR-link")
    node_geometry(drrmodel.external_forcings.boundary_nodes)[0].plot(
        ax=ax, markersize=15, color="purple", label="RR Boundary"
    )

    # manually add handles for polygon plot
    handles, labels = ax.get_legend_handles_labels()
    poly = mpatches.Patch(facecolor="pink", edgecolor="black", alpha=0.5)
    ax.legend(handles=handles.append(poly), labels=labels.append("Catchments"))
    cx.add_basemap(ax, crs=28992, source=cx.providers.OpenStreetMap.Mapnik)
    fig.tight_layout()

# %% [markdown]
# ## Writing the model

# %% [markdown]
# Now we call Hydrolib-core functionality to write the model. First, we initialize an object that converts all dataframes to Hydrolib-core objects. Then we add these models to the file structure of the FM model.

# %% [markdown]
# Call a function to convert the dataframes to Hydrolib-core classes:

# %%
models = Df2HydrolibModel(hydamo, assign_default_profiles=True)

# %% [markdown]
# And add the classes to the file structure. Each class requires a different approach, and at the moment Hydrolib-core is still in development. The code below is subject to change in future releases.

# %%
fm.geometry.structurefile = [StructureModel(structure=models.structures)]
fm.geometry.crosslocfile = CrossLocModel(crosssection=models.crosslocs)
fm.geometry.crossdeffile = CrossDefModel(definition=models.crossdefs)
fm.geometry.storagenodefile = StorageNodeModel(storagenode=models.storagenodes)

fm.geometry.frictfile = []
for i, fric_def in enumerate(models.friction_defs):
    fric_model = FrictionModel(global_=fric_def)
    fric_model.filepath = f"roughness_{i}.ini"
    fm.geometry.frictfile.append(fric_model)

if hasattr(hydamo.observationpoints, "observation_points"):
    fm.output.obsfile = [ObservationPointModel(observationpoint=models.obspoints)]

extmodel = ExtModel()
extmodel.boundary = models.boundaries_ext
extmodel.lateral = models.laterals_ext
fm.external_forcing.extforcefilenew = extmodel

fm.geometry.inifieldfile = IniFieldModel(initial=models.inifields)

for ifield, onedfield in enumerate(models.onedfieldmodels):
    # eventually this is the way, but it has not been implemented yet in Hydrolib core
    # fm.geometry.inifieldfile.initial[ifield].datafile = OneDFieldModel(global_=onedfield)

    # this is a workaround to do the same
    onedfield_filepath = output_path / "fm" / "initialwaterdepth.ini"
    onedfieldmodel = OneDFieldModel(global_=onedfield)
    onedfieldmodel.save(filepath=onedfield_filepath)
    fm.geometry.inifieldfile.initial[ifield].datafile = DiskOnlyFileModel(filepath=onedfield_filepath)

# %% [markdown]
# Add some setttings to the MDU that are recommened by Deltares.

# %%
fm.geometry.uniformwidth1d = 1.0  # default  breedte
fm.geometry.bedlevtype = 1  # 1: at cell center (tiles xz,yz,bl,bob=max(bl)), 2: at face (tiles xu,yu,blu,bob=blu), 3: at face (using mean node values), 4: at face
fm.geometry.changestructuredimensions = (
    0  # Change the structure dimensions in case these are inconsistent with the channel dimensions.
)

fm.sediment.sedimentmodelnr = 0

fm.numerics.cflmax = 0.7  # Maximum Courant nr.
# the following two settings are not supportedy by hydrolib-core 0.4.1
# fm.numerics.epsmaxlev = 0.0001            # stop criterion for non-linear solver
# fm.numerics.epsmaxlevm = 0.0001           # stop criterion for Nested Newton loop
fm.numerics.advectype = 33  # Adv type, 0=no, 33=Perot q(uio-u) fast, 3=Perot q(uio-u).

fm.volumetables.increment = 0.2  # parameter setting advised by Deltares for better performance
fm.volumetables.usevolumetables = 1  # parameter setting advised by Deltares for better performance

fm.restart.restartfile = None  # Restart file, only from netCDF-file, hence: either *_rst.nc or *_map.nc.
fm.restart.restartdatetime = None  # Restart time [YYYYMMDDHHMMSS], only relevant in case of restart from *_map.nc.
fm.sediment.sedimentmodelnr = 4
fm.output.mapformat = 4  # parameter setting advised by Deltares for better performance
fm.output.ncformat = 4  # parameter setting advised by Deltares for better performance
fm.output.ncnoforcedflush = 1  # parameter setting advised by Deltares for better performance
fm.output.ncnounlimited = 1  # parameter setting advised by Deltares for better performance
fm.output.wrimap_wet_waterdepth_threshold = 0.01  # Waterdepth threshold above which a grid point counts as 'wet'
fm.output.mapinterval = [
    1200.0,
    fm.time.tstart,
    fm.time.tstop,
]  # Map file output, given as 'interval' 'start period' 'end period' [s].
fm.output.rstinterval = [
    86400.0,
    fm.time.tstart,
    fm.time.tstop,
]  # Restart file output, given as 'interval' 'start period' 'end period' [s].
fm.output.hisinterval = [
    300.0,
    fm.time.tstart,
    fm.time.tstop,
]  # History output, given as 'interval' 'start period' 'end period' [s].
fm.output.wrimap_flow_analysis = 1  # write information for flow analysis

# %% [markdown]
# The default sediment model settings raise an error in DIMR. Delete them.

# %%
if hasattr(fm, "sediment"):
    delattr(fm, "sediment")

# %% [markdown]
# In D-Hydro the 1D timestep (dt user) should be at least equal to than the smallest timestep of RR and RTC, otherwise water balance problems may occur.
# The following code sets 'dtuser' equal to the smallest time step.

# %%
# check the timesteps:
timesteps = []
if RR:
    timesteps.append(drrmodel.d3b_parameters["Timestepsize"])
if RTC:
    timesteps.append(drtcmodel.time_settings["step"])
if len(timesteps) > 0 and fm.time.dtuser > np.min(timesteps):
    fm.time.dtuser = np.min(timesteps)

# %% [markdown]
# Now we write the file structure:

# %%
fm.filepath = Path(output_path) / "fm" / "test.mdu"
dimr = DIMR()
dimr.component.append(FMComponent(name="DFM", workingDir=Path(output_path) / "fm", model=fm, inputfile=fm.filepath))
dimr.save(recurse=True)

# %% [markdown]
# The writers for RR and RTC are not yet available in the HYDROLIB-core library. We use the original delft3dfmpy writer for RR and a custom writer for RTC:

# %%
if RTC:
    drtcmodel.write_xml_v1()

# %% [markdown]
# Note that with the WWTP-argument, the coordinates for a (fictional) WWTP are provided. From each paved node, a sewage link is connected to this WWTP.

# %%
if RR:
    rr_writer = DRRWriter(drrmodel, output_dir=output_path, name="test", wwtp=(199000.0, 396000.0))
    rr_writer.write_all()

# %% [markdown]
# A run.bat that will run DIMR is written by the following command. Adjust this with your local D-Hydro Suite version.

# %%
dimr = DIMRWriter(
    output_path=output_path,
    dimr_path=str(
        r"C:\Program Files\Deltares\D-HYDRO Suite 2024.03 1D2D\plugins\DeltaShell.Dimr\kernels\x64\bin\run_dimr.bat"
    ),
)

# %%
if not RR:
    drrmodel = None
if not RTC:
    drtcmodel = None

# %%
dimr.write_dimrconfig(fm, rr_model=drrmodel, rtc_model=drtcmodel)

# %%
dimr.write_runbat()

# %% [markdown]
# Add projection information (Rijksdriehoeksstelsel) to the net.nc-file.

# %%

dimr.add_crs()

# %% [markdown]
# Hydrolib-core schrijft een van de bestanden weg met een absoluut pad, waardoor het model niet meer werkt als het verplaatst wordt. Via onderstaande code repareren we dit en vervangen het pad door een relatief pad.

# %%
with open(output_path / "fm" / "fieldFile.ini", "r") as f:
    lines = f.readlines()
    lines2 = []
    for line in lines:
        if "initialwaterdepth.ini" in line:
            if "\\" in line:
                lines2.append("    datafile    = " + line.split("=")[1].rstrip(" #\n").split("\\")[-1] + "\n")
            elif "/" in line:
                lines2.append("    datafile    = " + line.split("=")[1].rstrip(" #\n").split("/")[-1] + "\n")
        else:
            lines2.append(line)
with open(output_path / "fm" / "fieldFile2.ini", "w") as f:
    f.writelines(lines2)
(output_path / "fm" / "fieldFile.ini").unlink()
(output_path / "fm" / "fieldFile2.ini").rename(output_path / "fm" / "fieldFile.ini")

# %% [markdown]
# Zip the model into a downloadable file.

# %%
import shutil

shutil.make_archive(str(output_path), "zip", output_path)

# %%
print("Done!")

# %%
