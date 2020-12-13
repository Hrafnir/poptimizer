"""Обработчики доменных событий."""
import functools
from typing import List

import pandas as pd

import poptimizer.data_di.ports
from poptimizer import config
from poptimizer.data_di.domain import events
from poptimizer.data_di.domain.tables import base
from poptimizer.shared import domain


class UnknownEventError(config.POptimizerError):
    """Для события не зарегистрирован обработчик."""


class EventHandlersDispatcher(domain.AbstractHandler[base.AbstractTable[domain.AbstractEvent]]):
    """Обеспечивает запуск обработчика в соответствии с типом события."""

    @functools.singledispatchmethod
    async def handle_event(
        self,
        event: domain.AbstractEvent,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обработчик для отсутствующих событий."""
        raise UnknownEventError(event)

    @handle_event.register
    async def app_started(
        self,
        event: events.AppStarted,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с торговыми днями."""
        table_id = base.create_id(poptimizer.data_di.ports.TRADING_DATES)
        table = await repo.get(table_id)
        return await table.handle_event(event)

    @handle_event.register
    async def trading_day_ended(
        self,
        event: events.TradingDayEnded,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Запускает обновление необходимых таблиц в конце торгового дня."""
        new_events: List[domain.AbstractEvent] = [
            events.IndexCalculated("MCFTRR", event.date),
            events.IndexCalculated("IMOEX", event.date),
            events.IndexCalculated("RVI", event.date),
        ]

        table_groups = [
            poptimizer.data_di.ports.CPI,
            poptimizer.data_di.ports.SECURITIES,
            poptimizer.data_di.ports.SMART_LAB,
        ]

        for group in table_groups:
            table_id = base.create_id(group)
            table = await repo.get(table_id)
            new_events.extend(await table.handle_event(event))

        return new_events

    @handle_event.register
    async def ticker_traded(
        self,
        event: events.TickerTraded,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицы с котировками и дивидендами."""
        new_events = []

        table_groups = [poptimizer.data_di.ports.QUOTES, poptimizer.data_di.ports.DIVIDENDS]

        for group in table_groups:
            table_id = base.create_id(group, event.ticker)
            table = await repo.get(table_id)
            new_events.extend(await table.handle_event(event))

        return new_events

    @handle_event.register
    async def index_calculated(
        self,
        event: events.IndexCalculated,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с котировками индексов."""
        table_id = base.create_id(poptimizer.data_di.ports.INDEX, event.ticker)
        table = await repo.get(table_id)
        return await table.handle_event(event)

    @handle_event.register
    async def div_expected(
        self,
        event: events.DivExpected,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с котировками."""
        table_id = base.create_id(poptimizer.data_di.ports.DIV_EXT, event.ticker)
        table = await repo.get(table_id)
        return await table.handle_event(event)

    @handle_event.register
    async def update_div(
        self,
        event: events.UpdateDivCommand,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицы с котировками и дивидендами."""
        table_id = base.create_id(poptimizer.data_di.ports.DIVIDENDS, event.ticker)
        table = await repo.get(table_id)
        new_events = await table.handle_event(event)
        new_events.append(events.DivExpected(event.ticker, pd.DataFrame(columns=["SmartLab"])))
        return new_events
