# %% Inladen van AHN data naar een vrt. AHN data wordt door geo gedownload.
# De data wordt in verschillende tegels (vlakjes) opgeslagen en met deze code gezamelijk opgeslagen in 1 vrt.
# Het daadwerkelijk samenvoegen van de tegels in 1 geotiff wordt gedaan in de code 00-bewerk_ahn.

from pathlib import Path

from osgeo import gdal

# %%%
fnames = get_fnames()
ahn_dir = fnames["ahn_dir"]


def create_vrt_file(download_dir: Path):
    # List of your GeoTIFF files
    download_dir = Path(download_dir)
    tif_files = [i.absolute().resolve().as_posix() for i in download_dir.glob("*.tif")]

    # Output VRT filename
    vrt_filename = download_dir / f"{download_dir.name}.vrt"

    # Build VRT
    vrt_options = gdal.BuildVRTOptions(
        resolution="average",
        separate=False,
        addAlpha=False,
        bandList=[1],
    )

    ds = gdal.BuildVRT(destName=vrt_filename.as_posix(), srcDSOrSrcDSTab=tif_files, options=vrt_options)
    ds.FlushCache()


create_vrt_file(ahn_dir)

# %%
