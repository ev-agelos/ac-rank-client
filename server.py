from queue import Queue
from threading import Thread


MESSAGES = Queue()  # info to be shown in the ac app
TASKS = Queue()


def handle_response(response, msg_on_success=None, msg_on_failure=None):
    """Handle the response of a request."""
    if response.status_code != 200:
        if msg_on_failure is not None:
            MESSAGES.put(msg_on_failure)
        else:
            MESSAGES.put(response.reason)
    else:
        result = response.json()
        if isinstance(result, dict) and result.get('errors'):
            MESSAGES.put(result['errors'])
        elif isinstance(result, dict) and 'message' in result:
            MESSAGES.put(result['message'])
        elif msg_on_success is not None:  # if custom msg was given
            MESSAGES.put(msg_on_success)


def _process_tasks():
    while 1:
        if TASKS.empty():
            continue
        task = TASKS.get()
        Thread(target=task['func'], args=task.get('args'),
               kwargs=task.get('kwargs')).start()

# FIXME: tasks need to finish before closing the game otherwise unhandled
# exceptions are raised
Thread(target=_process_tasks, daemon=True).start()