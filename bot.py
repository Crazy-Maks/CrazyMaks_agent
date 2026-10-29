import os
import asyncio
import re
import logging
from aiogram import Bot, Dispatcher, types
import ccxt.pro as ccxtpro

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8458873820:AAGRyzFL3UFMOypG1MxHnV2m3ydAdn_8aek"
ALLOWED_CHAT_ID = -1004295986920

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
active_tasks = []

exchange = ccxtpro.bingx({'options': {'defaultType': 'swap'}})

def parse_signal(text: str):
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
        for task in active_tasks:
            if task['ticker'] == ticker and task['direction'] == direction and task['level'] == level:
                return
        new_task = {
            'ticker': ticker,
            'direction': direction,
            'level': level,
            'chat_id': message.chat.id
        }
        active_tasks.append(new_task)
        await message.reply(
            f"✅ **Домашка принята на мониторинг!**\n"
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
            tickers_data = await exchange.watch_tickers(tickers_to_watch)
            for task in active_tasks[:]:
                symbol_bingx = f"{task['ticker']}/USDT:USDT"
                if symbol_bingx in tickers_data:
                    current_price = tickers_data[symbol_bingx]['last']
                    is_triggered = False
                    if task['direction'] == 'SHORT' and current_price <= task['level']:
                        is_triggered = True
                    elif task['direction'] == 'LONG' and current_price >= task['level']:
                        is_triggered = True
                    if is_triggered:
                        alert_text = (
                            f"⚠️ 🔔 **УРОВЕНЬ ДОСТИГНУТ!** 🔔 ⚠️\n\n"
                            f"🪙 Монета: #{task['ticker']}\n"
                            f"📊 Направление: {task['direction']}\n"
                            f"🎯 Ваш уровень: {task['level']}\n"
                            f"🔥 Текущая цена на BingX: {current_price}"
                        )
                        await bot.send_message(chat_id=task['chat_id'], text=alert_text)
                        active_tasks.remove(task)
        except Exception as e:
            await asyncio.sleep(2)
        await asyncio.sleep(0.5)

async def main():
    asyncio.create_task(price_checker_loop())
    
    from aiohttp import web
    async def handle(request):
        return web.Response(text="Bot is running!")
    
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    await dp.start_polling(bot)

if__name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
