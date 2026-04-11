from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.user import User
from core.i18n import t


class AuthMiddleware(BaseMiddleware):
    """Load user from DB, set lang, block if blocked."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession = data["session"]
        telegram_user = data.get("event_from_user")

        if not telegram_user:
            return await handler(event, data)

        result = await session.execute(
            select(User).where(User.telegram_id == telegram_user.id)
        )
        user = result.scalar_one_or_none()
        data["db_user"] = user

        # Determine language: user DB → FSM state → default
        lang = "uz"
        if user:
            lang = user.language or "uz"
        else:
            # Check FSM state for registration lang
            state: FSMContext | None = data.get("state")
            if state:
                try:
                    state_data = await state.get_data()
                    lang = state_data.get("reg_lang", "uz")
                except Exception:
                    pass
        data["lang"] = lang

        if user and user.is_blocked:
            if isinstance(event, Message):
                await event.answer(t("blocked", lang))
                return
            elif isinstance(event, CallbackQuery):
                await event.answer(t("blocked", lang), show_alert=True)
                return

        return await handler(event, data)
