from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def afvoergolf(
    piekafvoer: float,
    start: datetime,
    duur: timedelta,
    nalooptijd: timedelta,
    tijdstap: timedelta = timedelta(hours=1),
) -> pd.Series:
    """Aanmaken van een synthetische afvoerseries voor het testen van modellen.

    Args:
        piekafvoer (float): piekafvoer welke wordt bereikt halverwege de duur (m3/s)
        start (datetime): start van de series
        duur (timedelta): duur van de piek
        nalooptijd (timedelta): nalooptijd van de piek
        tijdstap (timedelta, optioneel): tijdstap van de series. Defaults to timedelta(hours=1)

    Returns:
        pd.Series: afvoergolf
    """
    # index
    end = start + duur + nalooptijd
    index = pd.date_range(start=start, end=end, freq=tijdstap)

    # golf
    t = np.linspace(0, np.pi, int(duur / tijdstap))
    golf = piekafvoer * np.sin(t)
    afvoer = np.zeros(len(index))
    afvoer[0 : len(golf)] = golf

    return pd.Series(data=afvoer, index=index)
