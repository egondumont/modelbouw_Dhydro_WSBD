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

## Over deze module
Deze module wordt ontwikkeld door waterschap Brabantse Delta. In het ontwikkeling van deze code is bijgedragen door `Royal HaskoningDHV` en `D2Hydro`. Daarnaast wordt er gebruik gemaakt van `DHyDAMO` en `Hydrolib-core` welke worden ontwikkeld door `HKV` en `Deltares`.

De code is open source en vrij te gebruiken.