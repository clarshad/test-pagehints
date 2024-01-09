def post_worker_init(worker):
    import atexit
    from multiprocessing.util import _exit_function
    atexit.unregister(_exit_function)
    worker.log.info("worker post_worker_init done, (pid: {})".format(worker.pid))