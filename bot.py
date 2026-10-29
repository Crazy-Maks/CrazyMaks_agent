import asyncio, re, logging, aiohttp; from aiogram import Bot, Dispatcher, types; logging.basicConfig(level=logging.INFO); bot = Bot(token="8458873820:AAGRyzFL3UFMOypG1MxHnV2m3ydAdn_8aek"); dp = Dispatcher(); active_tasks = []; parse_signal = lambda text: (match := re.search(r"#([A-Za-z0-9]+).*?(SHORT|LONG).*?(\d+\.\d+|\d+)", text, re.IGNORECASE)) and (match.group(1).upper(), match.group(2).upper(), float(match.group(3))); @dp.message()
async def _(msg: types.Message):
 if msg.chat.id == -1004295986920 and msg.text and (parsed := parse_signal(msg.text)):
  t, d, l = parsed
  if not any(x["ticker"] == t and x["direction"] == d and x["level"] == l for x in active_tasks):
   active_tasks.append({"ticker": t, "direction": d, "level": l, "chat_id": msg.chat.id}); await msg.reply(f"✅ **Домашка принята на мониторинг!**\n🪙 Монета: #{t}\n📈 Направление: {d}\n🎯 Уровень: {l}\n⏳ Жду касания на BingX...")
async def checker():
 async with aiohttp.ClientSession() as s:
  while True:
   if active_tasks:
    try:
     async with s.get("https://bingx.com") as r:
      if r.status == 200:
       data = await r.json(); ticks = data.get("data", []); prices = {t["symbol"].replace("-USDT", ""): float(t["lastPrice"]) for t in ticks if "symbol" in t}
       for task in active_tasks[:]:
        ticker = task["ticker"]
        if ticker in prices:
         cp = prices[ticker]; trig = (task["direction"] == "SHORT" and cp <= task["level"]) or (task["direction"] == "LONG" and cp >= task["level"])
         if trig: await bot.send_message(task["chat_id"], f"⚠️ 🔔 **УРОВЕНЬ ДОСТИГНУТ!** 🔔 ⚠️\n\n🪙 Монета: #{ticker}\n📊 Направление: {task['direction']}\n🎯 Ваш уровень: {task['level']}\n🔥 Текущая цена на BingX: {cp}"); active_tasks.remove(task)
    except: pass
   await asyncio.sleep(3)
async def main(): asyncio.create_task(checker()); await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
