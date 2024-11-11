from typing import Any, Dict, Optional

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.models.FSM import StorageDataORM as StorageData
from database.models.FSM import StorageStateORM as StorageState


class SqlAlchemyStorage(BaseStorage):
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self._session_maker = session_maker

    async def close(self) -> None:
        pass

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        tuple_key = (key.bot_id, key.chat_id, key.user_id, key.destiny)

        async with self._session_maker() as session:
            if state is not None:
                new_state = StorageState(
                    bot_id=key.bot_id,
                    chat_id=key.chat_id,
                    user_id=key.user_id,
                    destiny=key.destiny,
                    state=state.state if isinstance(state, State) else state,
                )  # type: ignore
                await session.merge(new_state)
            else:
                state_orm = await session.get(StorageState, tuple_key)
                if state_orm:
                    await session.delete(state_orm)
            await session.commit()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        key_tuple = (key.bot_id, key.chat_id, key.user_id, key.destiny)

        async with self._session_maker() as session:
            state_orm = await session.get(StorageState, key_tuple)
            if state_orm:
                return state_orm.state

            return None

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        tuple_key = (key.bot_id, key.chat_id, key.user_id, key.destiny)

        async with self._session_maker() as session:
            if data is not None:
                new_data_orm = StorageData(
                    bot_id=key.bot_id,
                    chat_id=key.chat_id,
                    user_id=key.user_id,
                    destiny=key.destiny,
                    data=data,
                )  # type: ignore
                await session.merge(new_data_orm)
            else:
                data_orm = await session.get(StorageData, tuple_key)
                if data_orm:
                    await session.delete(data_orm)
            await session.commit()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        key_tuple = (key.bot_id, key.chat_id, key.user_id, key.destiny)

        async with self._session_maker() as session:
            data_orm = await session.get(StorageData, key_tuple)
            if data_orm:
                return data_orm.data or {}

            return {}

    async def update_data(
        self, key: StorageKey, data: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        tuple_key = (key.bot_id, key.chat_id, key.user_id, key.destiny)

        async with self._session_maker() as session:
            data_orm = await session.get(StorageData, tuple_key)
            if not data_orm:
                await self.set_data(key, data)
                return data

            new_data: dict = data_orm.data or {}
            new_data.update(data)
            await self.set_data(key, new_data)
            return new_data
