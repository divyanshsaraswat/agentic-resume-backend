import asyncio

class NotificationManager:
    def __init__(self):
        self._queues = {}

    async def subscribe(self, user_id: str):
        if user_id not in self._queues:
            self._queues[user_id] = []
        queue = asyncio.Queue()
        self._queues[user_id].append(queue)
        try:
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        finally:
            if user_id in self._queues:
                self._queues[user_id].remove(queue)
                if not self._queues[user_id]:
                    del self._queues[user_id]

    async def notify(self, user_id: str, data: str = "update"):
        if user_id in self._queues:
            for queue in self._queues[user_id]:
                await queue.put(data)

# Global instances for the app
notifier = NotificationManager()
