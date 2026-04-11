"""Custom filter for multilingual button matching."""

from aiogram.filters import BaseFilter
from aiogram.types import Message

from core.i18n import _t


class TextMatch(BaseFilter):
    """Match message text against a translation key in any language."""

    def __init__(self, key: str):
        self.key = key

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        translations = _t.get(self.key, {})
        return message.text in translations.values()
