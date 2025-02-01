import sys
# import requests
import logging
import platform
import aiohttp
import asyncio
from datetime import datetime, timedelta


logging.basicConfig(level=logging.INFO)
# API_URL = 'https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5'
# "https://api.privatbank.ua/p24api/exchange_rates?json&date=01.01.2025"
API_URL = "https://api.privatbank.ua/p24api/exchange_rates"


class HttpCustomException(Exception):
    pass


def format_rates(saleRate, purchaseRate):
    return {
            'sale': saleRate if saleRate else "null",
            'purchase': purchaseRate if purchaseRate else "null"
        }


async def request_on_date(session, date: str):
    params = {
        "json": "",
        "date": date
    }
    async with session.get(API_URL, params=params) as response:
        # logging.info(f"response status: {response.status}")
        if response.status == 200:
            return await response.json()
        else:
            raise HttpCustomException(f"Issue with response: {response}")


def parse_rates(json, date, currencies):
    result = {}
    for rate in json["exchangeRate"]:
        currency = rate.get('currency')
        if currency in currencies:
            if date not in result:
                result[date] = {}
            result[date][currency] = format_rates(
                    rate.get('saleRate'),
                    rate.get('purchaseRate')
                )
    return result


async def get_exchange_rate(session, date: str, currencies):
    try:
        resp_json = await request_on_date(session, date)
        return parse_rates(resp_json, date, currencies)
    except HttpCustomException as ex:
        logging.error(ex)
        return {}


async def get_exchange_rate_for_period(session, end_date, days, currencies):
    # генеруємо список дат
    dates_lst = [(end_date - timedelta(days=day_index)).strftime("%d.%m.%Y")
                 for day_index in range(days)]
    # створюємо список задач
    tasks = [
        get_exchange_rate(session, date, currencies)
        for date in dates_lst
    ]
    # виконуємо задачі асинхронно
    results = await asyncio.gather(*tasks)
    return results


async def exchange_handler(days: int, currencies: list):
    end_date = datetime.now()
    async with aiohttp.ClientSession() as session:
        results = await get_exchange_rate_for_period(
            session, end_date, days, currencies
        )
        return results


# exchange [days] <list of currencies>
def get_parameters(param_list):
    currs = {"EUR", "USD"}
    try:
        days = int(param_list[0])
        days = 10 if days > 10 else days
        currs.update({curr.upper() for curr in param_list[1:]})
    except Exception:
        days = 10
        logging.error("Invalid value for 'Days' parameter. "
                      "Using default value 10")
    return (days, currs)


if __name__ == "__main__":
    if platform == "windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # sys.argv.append("10")
    days, currencies = get_parameters(sys.argv[1:])
    res = asyncio.run(exchange_handler(days, currencies))
    print(f'Result: {res}')
