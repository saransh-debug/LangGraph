import asyncio
import threading

class background_main_thread:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop() #creates a single - non ending loop 

        self.thread = threading.Thread(
            target = self._run_loop,
            daemon=True #it is used to allow the thread or the process to exit  , if it is FALSE then it prevents the application or the process to end or exit ,'''If the main program leaves, don't keep the program alive just for me'''.
        )
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop) #creates a loop or sets up a loop

        self.loop.run_forever() #keeps the thread and the event loop running until the process it exited or stopped

    def run(self , coroutine):#it is used to run those processes whose result is needed immediately

        future = asyncio.run_coroutine_threadsafe(coroutine , self.loop)#submitting the coroutine to the current running loop , gives a receipt 

        return future.result()
    def submit(self , coroutine):#it is used to run those processes or functions whose response is not needed immediately , so they keep running in the background
        return asyncio.run_coroutine_threadsafe(coroutine , self.loop)

runtime = background_main_thread()

