from aiofile import async_open
from aiopath import AsyncPath
import asyncio
import logging
import websockets
import names
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK
from datetime import datetime

import main

LOG_PATH = ".\\server-log.log"

logging.basicConfig(level=logging.INFO)


class Server:
    clients = set()

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distribute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

    async def logging_command(self, client, message: str):
        path = AsyncPath(LOG_PATH)
        async with async_open(path, 'a', encoding='utf-8') as file:
            await file.write(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: {client} - {message}\n')

    def prittify_json_meessage(self, json) -> str:
        html = '<table border="1">'
        html += '<tr><th>Date</th><th>Currency</th><th>Sale</th><th>Purchase</th></tr>'
        for entry in json:
            for date, currencies in entry.items():
                for currency, rates in currencies.items():
                    sale = rates['sale']
                    purchase = rates['purchase']
                    html += f'<tr><td>{date}</td><td>{currency}</td><td>{sale}</td><td>{purchase}</td></tr>'
        return html

    async def distribute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            # логування будь якої команди, що прийшла від клієнта
            await self.logging_command(ws.name, message)

            command, *params = message.split(" ")
            if command.lower() == "exchange":
                days, currencies = main.get_parameters(params)
                res_json = await main.exchange_handler(days, currencies)
                message = self.prittify_json_meessage(res_json)
            await self.send_to_clients(f"{ws.name}: {message}")


async def server_main():
    server = Server()
    async with websockets.serve(server.ws_handler, 'localhost', 8080):
        await asyncio.Future()  # run forever

if __name__ == '__main__':
    asyncio.run(server_main())
