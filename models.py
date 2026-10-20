class UserProfile:
    """Класс пользователя: демонстрация __init__, атрибутов и инкапсуляции (ЛР 5.2)."""
    def __init__(self, telegram_id: int, name: str, phone: str = None):
        self.telegram_id = telegram_id
        self.name = name
        self.phone = phone
        self._interactions = 0  # Инкапсуляция: защищённый атрибут

    def register_action(self):
        """Метод изменения внутреннего состояния."""
        self._interactions += 1

    def get_info(self, cart_count: int) -> str:
        """Метод генерации отчёта о пользователе."""
        phone_val = self.phone if self.phone else "Не указан"
        return (
            f"👤 Клиент: {self.name}\n"
            f"📞 Телефон: {phone_val}\n"
            f"📊 Запросов к боту: {self._interactions}\n"
            f"🛒 Товаров в корзине: {cart_count} шт."
        )


class BotAnswer:
    """Базовый класс ответа (ЛР 5.2)."""
    def __init__(self, text: str):
        self.text = text

    def reply(self) -> str:
        return self.text


class LoudBotAnswer(BotAnswer):
    """Наследование и переопределение метода: громкий ответ (ЛР 5.2)."""
    def reply(self) -> str:
        return self.text.upper() + "!"


class ServiceBotAnswer(BotAnswer):
    """Наследование: сервисное сообщение с контактами магазина (ЛР 5.2)."""
    def reply(self) -> str:
        return f"{self.text}\n📍 Мы находимся в г. Астана. Доставка курьером в течение дня."
