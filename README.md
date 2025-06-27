# WBD tools voor het bouwen van DHydro modellen

Een workflow voor het bouwen van DHydro modellen binnen waterschap Brabantse Delta, inclusief:
- Het afleiden van afwaterende eenheden op basis van het AHN en deelstroomgebieden
- Het voorbewerken van DAMO data naar valide en gevulde HyDAMO data
- Het converteren van HyDAMO data naar een DHydro model

## Installatie

### Clonen repositories
Clone deze repository en daarnaast de branch `hkv_dhydamo_development` van HYDROLIB: [https://github.com/deltares/hydrolib](https://github.com/deltares/hydrolib)

### Conda environment
Maak de juiste conda-environment aan op basis van `environment.yml`

```
conda env create -f environment.yml
```

### Toevoegen python-packages
Activeer je environment (`conda activate WBD`) en navigeer achtereenvolgens naar de root (locatie waar `pyproject.toml` staat) van de hydrolib én deze repository en installeer deze met

```
pip install -e .
```

N.B. met `-e` (editable) worden de de paden van de modules gelinkt, waardoor wijzigingen in de code direct beschikbaar zijn zonder het opnieuw uitvoeren van de installatie


## Environment en bestanden
In de root van deze repository dien je een `.env` bestand aan te maken, je kunt deze aanmaken door de inhoud van het bestand `.env_default` te kopieren naar `.env`. Hierin staan de paden goed voor het draaien van code binnen de omgeving van Brabantse Delta.

### AFWATERINGSEENHEDEN_DIR
Hierin staan alle paden voor het afleiden van afwateringseenheden

```
AFWATERINGSEENHEDEN_DIR/
├── data/
│   ├── clusters/
│   │   └── afwateringseenheden_25m_15clusters_fixed.shp
│   ├── hoogtekaart/
│   │   ├── ahn_tif_bestanden.tif
│   │   └── .....tif
│   ├── objecten/
│   │   └── feature_files_met_damo_objecten.shp
│   └── waterlopen/
│       ├── a_waterlopen/
│       │   └── Legger_waterlopen_A.shp
│       └── b_waterlopen/
│           └── Legger_waterlopen_B.shp
└── out/
    ├── waterlopen_verwerkt.gpkg
    ├── afwateringseenheden.gpkg
    └── clusters
```

### MODELLEN_DIR
Hierin staan alle paden voor het bouwen van DHYDRO modellen

```
MODELLEN_DIR/
└── data/
    ├── acceptatiedatabase.gdb
    └── modelgebieden.gpkg
```

### RASTERS_DIR
Hierin zitten rasters opgeslagen die gebruikt worden in `2_D-HyDAMO_driver.py` en bij het afleiden van afwateringseenheden

Let op (!) vanuit reature/RR-modellering kunnen hier straks ook landgebruik, bodemtypen, kwel/wegzijging en neerslag/verdamping in.
Deze worden in de huidige master nog niet aangegrepen.

```
RASTERS_DIR/
├── ahn/
│   ├── dtm_2m.tif
├── ....tif
└── ....tif
```

### DIMR_BAT
Optionele verwijzing naar de DHydro DIMR (Deltares Integrated Model Runner).

## Over deze module
Deze module wordt ontwikkeld door waterschap Brabantse Delta. In het ontwikkeling van deze code is bijgedragen door `Royal HaskoningDHV` en `D2Hydro`. Daarnaast wordt er gebruik gemaakt van `DHyDAMO` en `Hydrolib-core` welke worden ontwikkeld door `HKV` en `Deltares`.

De code is open source en vrij te gebruiken.