"""Обрезка данных для различных источников по дивидендам."""
from typing import Tuple

import pandas as pd

import poptimizer.data_di.ports
from poptimizer.data_di.app import bootstrap, viewers
from poptimizer.data_di.domain import events
from poptimizer.data_di.domain.tables import base


def div_ext(
    ticker: str,
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> pd.DataFrame:
    """Сводная информация из внешних источников по дивидендам."""
    df = viewer.get_df(poptimizer.data_di.ports.DIV_EXT, ticker)
    return df.loc[bootstrap.START_DATE :]  # type: ignore


def dividends(
    ticker: str,
    force_update: bool = False,
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> pd.DataFrame:
    """Дивиденды для данного тикера."""
    if force_update:
        command = events.UpdateDivCommand(ticker)
        bootstrap.BUS.handle_event(command)
    df = viewer.get_df(poptimizer.data_di.ports.DIVIDENDS, ticker)
    return df.loc[bootstrap.START_DATE :]  # type: ignore


def dividends_all(
    tickers: Tuple[str, ...],
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> pd.DataFrame:
    """Дивиденды по заданным тикерам после уплаты налогов.

    Значения для дат, в которые нет дивидендов у данного тикера (есть у какого-то другого),
    заполняются 0.
    """
    dfs = viewer.get_dfs(poptimizer.data_di.ports.DIVIDENDS, tickers)
    dfs = [df.loc[bootstrap.START_DATE :] for df in dfs]  # type: ignore

    df = pd.concat(dfs, axis=1)
    df = df.reindex(columns=tickers)
    df = df.fillna(0, axis=0)
    return df.mul(bootstrap.AFTER_TAX)
