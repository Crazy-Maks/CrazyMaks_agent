import asyncio
import re
import logging
import sys
from aiogram import Bot, Dispatcher, types
import ccxt.pro as ccxtpro

# Настройка логирования для корректного отображения в консоли Render
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Переменные конфигурации
BOT_TOKEN = "8458873820:AAGRyzFL3UFMOypG1MxHnV2m3ydAdn_8aek"
ALLOWED_CHAT_ID = -1004295986920

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
active_tasks = []

# Подключение к бирже BingX (Свопы)
exchange = ccxtpro.bingx({'options': {'defaultType': 'swap'}})

def parse_signal(text: str):
    """Парсинг сообщений формата #BTC LONG 65000"""
    match = re.search(r'#([A-Za-z0-9]+).*?(SHORT|LONG).*?(\d+\.\d+|\d+)', text, re.IGNORECASE)
    if match:
        ticker = match.group(1).upper()
        direction = match.group(2).upper()
        level = float(match.group(3))
        return ticker, direction, level
    return None

@dp.message()
async def handle_group_messages(message: types.Message):
    if message.chat.id != ALLOWED_CHAT_ID or not message.text:
        return
        
    parsed = parse_signal(message.text)
    if parsed:
        ticker, direction, level = parsed
        
        # Защита от дубликатов задач
        for task in active_tasks:
            if task['ticker'] == ticker and task['direction'] == direction and task['level'] == level:
                return
                
        new_task = {
            'ticker': ticker,
            'direction': direction,
            'level': level,
            'chat_id': message.chat.id,
            'initial_price': None  # Определяется при первом тике цены
        }
        active_tasks.append(new_task)
        
        await message.reply(
            f"✅ Домашка принята на мониторинг!\n"
            f"🪙 Монета: #{ticker}\n"
            f"📈 Направление: {direction}\n"
            f"🎯 Уровень: {level}\n"
            f"⏳ Жду касания на BingX..."
        )

async def price_checker_loop():
    logging.info("Мониторинг цен BingX запущен.")
    while True:
        if not active_tasks:
            await asyncio.sleep(1)
            continue
            
        tickers_to_watch = list(set([f"{task['ticker']}/USDT:USDT" for task in active_tasks]))
        
        try:
            # Получение данных по WebSocket
            tickers_data = await exchange.watch_tickers(tickers_to_watch)
            
            for task in active_tasks[:]:
                symbol_bingx = f"{task['ticker']}/USDT:USDT"
             if symbol_bingx in tickers_data:
                    current_price = tickers_data[symbol_bingx]['last']
                    
                    # Фиксируем цену на момент добавления, чтобы знать направление движения
                    if task['initial_price'] is None:
                        task['initial_price'] = current_price
                        continue
                        
                    is_triggered = False
                    init_p = task['initial_price']
                    target_p = task['level']
                    
                    # Логика пересечения уровня
                    if init_p < target_p and current_price >= target_p:
                        is_triggered = True  # Пересекла снизу вверх
                    elif init_p > target_p and current_price <= target_p:
                        is_triggered = True  # Пересекла сверху вниз
                    elif current_price == target_p:
                        is_triggered = True  # Точное касание тика в тик

                    if is_triggered:
                        alert_text = (
                            f"⚠️ 🔔 УРОВЕНЬ ДОСТИГНУТ! 🔔 ⚠️\n\n"
                            f"🪙 Монета: #{task['ticker']}\n"
