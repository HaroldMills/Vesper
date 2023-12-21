from queue import Empty, Queue
from threading import Thread
import asyncio


_DEFAULT_SLEEP_PERIOD = 1


class AsyncTaskThread(Thread):


    def __init__(self, sleep_period=_DEFAULT_SLEEP_PERIOD):
        super().__init__(daemon=True)
        self._sleep_period = sleep_period
        self._task_queue = Queue()


    @property
    def sleep_period(self):
        return self._sleep_period
    

    def submit(self, task):
        self._task_queue.put(task)


    def run(self):
        asyncio.run(self._run())


    async def _run(self):
        
        while True:
            
            try:
                task = self._task_queue.get_nowait()

            except Empty:
                await asyncio.sleep(self._sleep_period)

            else:
                await task.run()


# The one and only `AsyncTaskThread` instance for the Vesper Recorder.
instance = AsyncTaskThread()
instance.start()
