"""Shared Controller execution mechanics; assignment semantics stay in each Controller."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from type_define.graph import Task
from tracer import current_tracer, safe_emit


class ControllerExecution:
    """Internal runtime shared by the legacy Full and Tiny public classes."""

    def _initialize_execution(self, max_workers: int) -> None:
        """Allocate execution state; invalid executor sizes raise ValueError."""
        self.task_list = [Task]
        self.query_interval = 1
        self.task_list_lock = threading.Lock()
        self.result_list_lock = threading.Lock()
        self.task_queue = []
        self.result_queue = []
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.max_task_time = 60 * 30
        self.shutdown = False

    def _worker_should_stop(self) -> bool:
        return self.shutdown

    def _worker_offline(self) -> None:
        self.logger.info("Some agents are offline!")
        self.shutdown = True

    def _stop_before_submit(self) -> bool:
        return False

    def _task_submitted(self, agent) -> None:
        self.logger.info(f"Agent {agent.name} is executing task now ...")

    def _after_submit(self) -> None:
        pass

    def worker(self) -> None:
        """Poll and submit tasks in legacy order; failures propagate to the worker thread."""
        while True:
            if self._worker_should_stop():
                break
            if self.env.agents_ping()["status"] == False:
                self._worker_offline()
                break
            with self.task_list_lock:
                if not self.task_queue:
                    time.sleep(self.query_interval)
                    continue
                while self.task_queue:
                    agent, task = self.task_queue.pop(0)
                    if self._stop_before_submit():
                        break
                    future = self.executor.submit(agent.step, task)
                    self._task_submitted(agent)
                    with self.result_list_lock:
                        self.result_queue.append((future, agent, task, time.time()))
                    self._after_submit()

    def set_task_status(self, task_id, status, feedback) -> None:
        safe_emit(current_tracer(), "AC", "task.status", task_id=str(task_id), result_status=str(status))
        for task in self.task_manager.graph.vertex:
            if task.id == task_id:
                if task.status == Task.success and status == Task.failure:
                    if status == Task.failure:
                        task.status = status
                else:
                    task.status = status

                if type(feedback) == dict and type(task.reflect) == None:
                    task.reflect = feedback
                elif type(feedback) == str and type(task.reflect) == None:
                    task.reflect = feedback
                elif type(feedback) == dict and type(task.reflect) == dict:
                    task.reflect = [task.reflect, feedback]
                elif type(feedback) == str and type(task.reflect) == str:
                    task.reflect = [task.reflect, feedback]
                elif type(task.reflect) == list:
                    task.reflect.append(feedback)
                else:
                    task.reflect = feedback
                break


    def get_task_by_id(self, task_id) -> Task | None:
        for task in self.task_manager.graph.vertex:
            if task.id == task_id:
                return task
        return None


    def run(self) -> None:
        try:
            # generate threads
            task_thread = threading.Thread(target=self.execute_tasks)
            worker_thread = threading.Thread(target=self.worker)
            result_thread = threading.Thread(target=self.process_completed_tasks)
            # start threads
            task_thread.start()
            worker_thread.start()
            result_thread.start()
            # wait for threads to finish
            task_thread.join()
            worker_thread.join()
            result_thread.join()
        except KeyboardInterrupt:
            # force to shutdown
            self.shutdown = True
            self.task_manager = None
            self.data_manager = None
            # shutdown thread pool
            self.executor.shutdown(wait=False)
            # raise exception
            raise Exception("Interrupted by user")


