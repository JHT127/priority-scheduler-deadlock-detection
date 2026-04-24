import re
from collections import deque
from enum import Enum
from typing import List,Set, Dict, Optional
import copy

class Resource:
    def __init__(self, rid: int):
        self.rid = rid
        self.allocated_to: Optional[int] = None

class ResourceManager:
    def __init__(self, num_resources: int):
            self.resources: Dict[int, Resource] = {i: Resource(i) for i in range(1, num_resources + 1)}
            self.waiting_for: Dict[int, Set[int]] = {}
            self.allocation_matrix: Dict[int, Set[int]] = {}

    def request_resource(self, pid: int, rid: int) -> bool:
        if rid not in self.resources:
            raise ValueError(f"Invalid resource ID: {rid}")

        resource = self.resources[rid]
        if resource.allocated_to is None:
            resource.allocated_to = pid
            if pid not in self.allocation_matrix:
                self.allocation_matrix[pid] = set()
            self.allocation_matrix[pid].add(rid)
            return True
        else:
            if pid not in self.waiting_for:
                self.waiting_for[pid] = set()
            self.waiting_for[pid].add(rid)
            print(f"\nTime {self.current_time}: Process {pid} waiting for resource {rid} held by process {resource.allocated_to}")
            print(f"Current allocations: {self.allocation_matrix}")
            print(f"Waiting relations: {self.waiting_for}")
            return False

    def release_resource(self, pid: int, rid: int):
        if rid not in self.resources:
            raise ValueError(f"Invalid resource ID: {rid}")

        resource = self.resources[rid]
        if resource.allocated_to != pid:
            raise ValueError(f"Process {pid} cannot release resource {rid} as it's not allocated to it")

        resource.allocated_to = None
        if pid in self.allocation_matrix:
            self.allocation_matrix[pid].remove(rid)
            if not self.allocation_matrix[pid]:
                del self.allocation_matrix[pid]

        for process_id in list(self.waiting_for.keys()):
            if rid in self.waiting_for[process_id]:
                self.waiting_for[process_id].remove(rid)
                if not self.waiting_for[process_id]:
                    del self.waiting_for[process_id]

    def get_wait_for_graph(self) -> Dict[int, Set[int]]:
        wait_for_graph = {}

        for pid in set(self.allocation_matrix.keys()) | set(self.waiting_for.keys()):
            wait_for_graph[pid] = set()

        for waiting_pid, waiting_resources in self.waiting_for.items():
            for rid in waiting_resources:
                holding_pid = self.resources[rid].allocated_to
                if holding_pid is not None and holding_pid != waiting_pid:
                    wait_for_graph[waiting_pid].add(holding_pid)

        print("\nWait-for Graph State:")
        print(f"Allocations: {self.allocation_matrix}")
        print(f"Waiting for: {self.waiting_for}")
        print(f"Wait-for graph: {wait_for_graph}")

        return wait_for_graph

    def detect_deadlock(self) -> List[int]:
        graph = self.get_wait_for_graph()
        visited = set()
        rec_stack = set()
        deadlock_processes = set()

        def dfs(pid: int, path: set = None) -> bool:
            if path is None:
                path = set()

            visited.add(pid)
            rec_stack.add(pid)
            path.add(pid)

            for neighbor in graph.get(pid, set()):
                if neighbor not in visited:
                    if dfs(neighbor, path):
                        deadlock_processes.update(path)
                        return True
                elif neighbor in rec_stack:
                    cycle_path = {neighbor}
                    deadlock_processes.update(cycle_path)
                    deadlock_processes.update(path)
                    return True

            rec_stack.remove(pid)
            path.remove(pid)
            return False

        for pid in graph:
            if pid not in visited:
                dfs(pid)

        if deadlock_processes:
            print(f"\nDeadlock detected! Processes involved: {deadlock_processes}")
        return list(deadlock_processes)

    def print_resource_state(self):
        print("\nResource State at time {}:".format(self.current_time))
        print("Resources allocated:", {rid: res.allocated_to for rid, res in self.resources.items() if res.allocated_to is not None})
        print("Processes waiting for resources:", dict(self.waiting_for))
        print("Wait-for graph:", self.get_wait_for_graph())

class Process:
    def __init__(self, pid, arrival_time, priority, bursts):
        self.pid = pid
        self.arrival_time = arrival_time
        self.priority = priority
        self.bursts = bursts
        self.held_resources: Set[int] = set()
        self.waiting_for_resource: Optional[int] = None

    def __str__(self):
        resources_str = f", Held Resources: {self.held_resources}" if self.held_resources else ""
        waiting_str = f", Waiting for: R[{self.waiting_for_resource}]" if self.waiting_for_resource is not None else ""
        return (f"PID: {self.pid}, Arrival: {self.arrival_time}, Priority: {self.priority}, Bursts: {self.bursts}{resources_str}{waiting_str}")

def parse_bursts(bursts_str):
    bursts = []
    pattern = r"(CPU|IO)\{([^}]*)\}"
    matches = re.findall(pattern, bursts_str)

    for burst_type, details in matches:
        if details:
            details = [d.strip() for d in details.split(',')]
            burst_details = []
            for detail in details:
                if detail.startswith('R[') or detail.startswith('F['):
                    burst_details.append(detail)
                elif detail.isdigit():
                    burst_details.append(int(detail))
            bursts.append((burst_type, burst_details))
        else:
            bursts.append((burst_type, []))
    return bursts

def validate_bursts(bursts, pid):
    if not bursts or bursts[0][0] != "CPU" or bursts[-1][0] != "CPU":
        raise ValueError(f"Process {pid} must start and finish with a CPU burst.")

def load_processes(file_path):
    processes = []
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            parts = re.split(r'\s+', line, maxsplit=3)
            pid = int(parts[0])
            arrival_time = int(parts[1])
            priority = int(parts[2])
            bursts_str = parts[3]
            bursts = parse_bursts(bursts_str)
            validate_bursts(bursts, pid)
            if any(process.pid == pid for process in processes):
                raise ValueError(f"No two processes can have the same PID ({pid})!")
            processes.append(Process(pid, arrival_time, priority, bursts))
    return processes

class ProcessState(Enum):
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    FINISHED = "FINISHED"

class ProcessControlBlock:
    def __init__(self, process: Process):
        self.process = process
        self.state = ProcessState.READY
        self.current_burst_index = 0
        self.remaining_time_in_burst = 0
        self.waiting_time = 0
        self.turnaround_time = 0
        self.completion_time = 0
        self.last_queue_entrance_time = process.arrival_time
        self.io_completion_time = 0
        self.current_instruction_index = 0
        self.resource_request_blocked = False
class Scheduler:
    def __init__(self, processes: List[Process], time_quantum: int):
        self.processes = processes
        self.time_quantum = time_quantum
        self.current_time = 0
        self.process_queues: Dict[int, deque] = {}
        self.running_process: Optional[ProcessControlBlock] = None
        self.io_processes: List[tuple[int, ProcessControlBlock]] = []
        self.finished_processes: List[ProcessControlBlock] = []
        self.gantt_chart = []
        self.rr_pair_pids = set()
        self.current_rr_priority = None
        self.completing_burst = False
        self.last_recorded_time = 0

        max_resource_id = 0
        for process in processes:
            for burst in process.bursts:
                for detail in burst[1]:
                    if isinstance(detail, str) and (detail.startswith('R[') or detail.startswith('F[')):
                        resource_id = int(detail[2:-1])
                        max_resource_id = max(max_resource_id, resource_id)
        self.resource_manager = ResourceManager(max_resource_id)

        self.pcbs: Dict[int, ProcessControlBlock] = {}
        for process in processes:
            pcb = ProcessControlBlock(process)
            initial_burst_time = sum(x for x in process.bursts[0][1] if isinstance(x, int))
            pcb.remaining_time_in_burst = initial_burst_time
            self.pcbs[process.pid] = pcb

        self.initialize_queues()

    def initialize_queues(self):
        priorities = set(process.priority for process in self.processes)
        for priority in priorities:
            self.process_queues[priority] = deque()

    def add_to_ready_queue(self, pcb: ProcessControlBlock):
        pcb.state = ProcessState.READY
        pcb.last_queue_entrance_time = self.current_time
        self.process_queues[pcb.process.priority].append(pcb)

    def handle_deadlock(self, deadlocked_pids: List[int]):
        if not deadlocked_pids:
            return

        victim_pid = max(deadlocked_pids, key=lambda pid: (self.pcbs[pid].process.priority, -pid))
        victim_pcb = self.pcbs[victim_pid]

        for rid in list(self.resource_manager.allocation_matrix.get(victim_pid, [])):
            self.resource_manager.release_resource(victim_pid, rid)

        if victim_pid in self.resource_manager.waiting_for:
            del self.resource_manager.waiting_for[victim_pid]

        original_arrival_time = victim_pcb.process.arrival_time
        original_waiting_time = victim_pcb.waiting_time
        victim_pcb.current_burst_index = 0
        victim_pcb.current_instruction_index = 0

        first_cpu_time = sum(x for x in victim_pcb.process.bursts[0][1] if isinstance(x, int))
        victim_pcb.remaining_time_in_burst = first_cpu_time

        victim_pcb.waiting_for_resource = None
        victim_pcb.resource_request_blocked = False
        victim_pcb.state = ProcessState.READY

        for priority_queue in self.process_queues.values():
            try:
                priority_queue.remove(victim_pcb)
            except ValueError:
                pass

        if self.running_process and self.running_process.process.pid == victim_pid:
            self.running_process = None

        self.io_processes = [(t, p) for t, p in self.io_processes if p.process.pid != victim_pid]

        victim_pcb.process.arrival_time = original_arrival_time
        victim_pcb.waiting_time = original_waiting_time
        self.add_to_ready_queue(victim_pcb)

        for pid in deadlocked_pids:
            if pid != victim_pid:
                pcb = self.pcbs[pid]
                if pcb.state == ProcessState.WAITING:
                    pcb.state = ProcessState.READY
                    pcb.waiting_for_resource = None
                    self.add_to_ready_queue(pcb)

    def get_next_process(self) -> Optional[ProcessControlBlock]:
        active_priorities = sorted([p for p, q in self.process_queues.items() if q], reverse=True)
        if not active_priorities:
            return None
        highest_priority = active_priorities[0]
        return self.process_queues[highest_priority].popleft()

    def update_waiting_times(self):
        for priority_queue in self.process_queues.values():
            for pcb in priority_queue:
                pcb.waiting_time += 1

    def update_gantt_chart(self, pid: Optional[int]):
        self.gantt_chart.append((self.current_time, pid if pid else 'IDLE'))

    def check_new_arrivals(self):
        for pid, pcb in self.pcbs.items():
            if (pcb.state == ProcessState.READY and
                    pcb.process.arrival_time <= self.current_time and
                    pcb not in [p for q in self.process_queues.values() for p in q]):
                self.add_to_ready_queue(pcb)

    def update_io_processes(self):
        completed_io = []
        for completion_time, pcb in self.io_processes:
            if completion_time <= self.current_time:
                completed_io.append((completion_time, pcb))
                pcb.current_burst_index += 1
                next_burst_time = sum(x for x in pcb.process.bursts[pcb.current_burst_index][1] if isinstance(x, int))
                pcb.remaining_time_in_burst = next_burst_time
                pcb.current_instruction_index = 0

                should_preempt = True
                if self.running_process and pcb.process.priority == self.running_process.process.priority:
                    if (pcb.process.arrival_time == self.running_process.process.arrival_time and
                            {pcb.process.pid, self.running_process.process.pid}.issubset(self.rr_pair_pids)):
                        should_preempt = False

                if not should_preempt:
                    self.process_queues[pcb.process.priority].append(pcb)
                    pcb.state = ProcessState.READY
                    pcb.last_queue_entrance_time = self.current_time
                else:
                    self.add_to_ready_queue(pcb)

        self.io_processes = [(t, p) for t, p in self.io_processes if (t, p) not in completed_io]

    def get_highest_priority_process(self) -> Optional[ProcessControlBlock]:
        active_priorities = sorted([p for p, q in self.process_queues.items() if q])
        if not active_priorities:
            return None

        if self.current_rr_priority is not None and self.process_queues[self.current_rr_priority]:
            if self.current_rr_priority <= min(active_priorities):
                priority_queue = self.process_queues[self.current_rr_priority]
                if priority_queue:
                    return priority_queue.popleft()

            self.current_rr_priority = None
            self.rr_pair_pids.clear()

        highest_priority = min(active_priorities)
        queue = self.process_queues[highest_priority]

        if queue:
            first_proc = queue[0]
            arrival_time = first_proc.process.arrival_time
            rr_group = []

            for proc in list(queue):
                if proc.process.arrival_time == arrival_time:
                    rr_group.append(proc)

            if len(rr_group) >= 2:
                self.current_rr_priority = highest_priority
                self.rr_pair_pids = {proc.process.pid for proc in rr_group}
                return queue.popleft()

        return queue.popleft()

    def handle_burst_completion(self):
        current_burst_index = self.running_process.current_burst_index
        bursts = self.running_process.process.bursts

        self.running_process.current_burst_index += 1

        if self.running_process.current_burst_index >= len(bursts):
            for rid in list(self.running_process.process.held_resources):
                self.resource_manager.release_resource(self.running_process.process.pid, rid)

            self.running_process.state = ProcessState.FINISHED
            self.running_process.completion_time = self.current_time + 1
            self.running_process.turnaround_time = (self.running_process.completion_time - self.running_process.process.arrival_time)
            self.finished_processes.append(self.running_process)
            if self.running_process.process.pid in self.rr_pair_pids:
                self.rr_pair_pids.discard(self.running_process.process.pid)
            if not self.rr_pair_pids:
                self.current_rr_priority = None
            self.running_process = None
        else:
            next_burst = bursts[self.running_process.current_burst_index]
            if next_burst[0] == "IO":
                io_time = next(x for x in next_burst[1] if isinstance(x, int))
                self.running_process.state = ProcessState.WAITING
                self.running_process.remaining_time_in_burst = io_time
                self.io_processes.append((self.current_time + 1 + io_time, self.running_process))
                if self.running_process.process.pid in self.rr_pair_pids:
                    self.rr_pair_pids.discard(self.running_process.process.pid)
                if not self.rr_pair_pids:
                    self.current_rr_priority = None
                self.running_process = None
            else:
                self.running_process.current_instruction_index = 0
                total_cpu_time = sum(x for x in next_burst[1] if isinstance(x, int))
                self.running_process.remaining_time_in_burst = total_cpu_time

                if (self.running_process.process.pid in self.rr_pair_pids and not self.completing_burst):
                    self.add_to_ready_queue(self.running_process)
                    self.running_process = None

    def run(self):
            quantum_remaining = self.time_quantum
            last_state = None

            while True:
                self.update_io_processes()
                self.check_new_arrivals()

                if not self.running_process:
                    next_process = self.get_highest_priority_process()

                    if not next_process:
                        if not self.gantt_chart or self.gantt_chart[-1][1] != "-":
                            self.gantt_chart.append((self.current_time, "-"))
                        last_state = "-"
                    else:
                        quantum_remaining = self.time_quantum
                        self.running_process = next_process
                        self.running_process.state = ProcessState.RUNNING
                        self.completing_burst = False

                        if not self.current_rr_priority:
                            current_priority = self.running_process.process.priority
                            if current_priority in self.process_queues:
                                for process in self.process_queues[current_priority]:
                                    if (process.process.arrival_time == self.running_process.process.arrival_time and
                                            process.process.priority == self.running_process.process.priority):
                                        self.current_rr_priority = current_priority
                                        self.rr_pair_pids = {self.running_process.process.pid, process.process.pid}
                                        break

                if self.running_process:
                    pid = self.running_process.process.pid
                    current_burst = self.running_process.process.bursts[self.running_process.current_burst_index]

                    if last_state != pid:
                        self.gantt_chart.append((self.current_time, pid))
                        last_state = pid

                    current_burst_details = current_burst[1]
                    if not hasattr(self.running_process, 'current_instruction_index'):
                        self.running_process.current_instruction_index = 0

                    if self.running_process.current_instruction_index < len(current_burst_details):
                        current_item = current_burst_details[self.running_process.current_instruction_index]
                        if isinstance(current_item, str):
                            if current_item.startswith('R['):
                                rid = int(current_item[2:-1])
                                if not self.resource_manager.request_resource(pid, rid):
                                    deadlocked_pids = self.resource_manager.detect_deadlock()
                                    if deadlocked_pids:
                                        self.handle_deadlock(deadlocked_pids)
                                        if self.running_process:
                                            self.add_to_ready_queue(self.running_process)
                                        self.running_process = None
                                        continue
                                    self.running_process.state = ProcessState.WAITING
                                    self.running_process.waiting_for_resource = rid
                                    self.process_queues[self.running_process.process.priority].append(
                                        self.running_process)
                                    self.running_process = None
                                    continue
                            elif current_item.startswith('F['):
                                rid = int(current_item[2:-1])
                                self.resource_manager.release_resource(pid, rid)
                            self.running_process.current_instruction_index += 1
                            continue

                    if self.running_process.remaining_time_in_burst == 0 and self.running_process.current_instruction_index < len(
                            current_burst_details):
                        remaining_time = 0
                        for i in range(self.running_process.current_instruction_index, len(current_burst_details)):
                            if isinstance(current_burst_details[i], int):
                                remaining_time += current_burst_details[i]
                        if remaining_time > 0:
                            self.running_process.remaining_time_in_burst = remaining_time

                    if self.running_process.remaining_time_in_burst > 0:
                        self.running_process.remaining_time_in_burst -= 1
                        quantum_remaining -= 1

                    if self.running_process.remaining_time_in_burst == 0:
                        self.completing_burst = True
                        self.handle_burst_completion()
                    elif (quantum_remaining <= 0 and
                          self.running_process.process.pid in self.rr_pair_pids and
                          len(self.rr_pair_pids) >= 2 and
                          not self.completing_burst):
                        self.add_to_ready_queue(self.running_process)
                        self.running_process = None
                        quantum_remaining = self.time_quantum

                self.update_waiting_times()
                self.current_time += 1

                if len(self.finished_processes) == len(self.processes):
                    if last_state != "-":
                        self.gantt_chart.append((self.current_time, "-"))
                    break

    def print_detailed_results(self):
        print("\nGantt Chart:")
        print("=" * 100)

        time_points = []
        processes_at_time = []

        i = 0
        while i < len(self.gantt_chart):
            current_time = self.gantt_chart[i][0]
            current_pid = self.gantt_chart[i][1]

            next_time = self.current_time
            for j in range(i + 1, len(self.gantt_chart)):
                if self.gantt_chart[j][1] != current_pid:
                    next_time = self.gantt_chart[j][0]
                    break

            time_points.append(current_time)
            processes_at_time.append(current_pid)

            if i < len(self.gantt_chart) - 1:
                next_start = self.gantt_chart[i + 1][0]
                if next_start > next_time:
                    time_points.append(next_time)
                    processes_at_time.append("-")
                    time_points.append(next_start)

            i += 1
            while i < len(self.gantt_chart) and self.gantt_chart[i][1] == current_pid:
                i += 1

        print("Time: ", end="")
        for i in range(len(time_points)):
            print(f"{time_points[i]:^10}", end="")
        print("\n" + "=" * 100)

        print("Proc: ", end="")
        for i in range(len(processes_at_time)):
            if processes_at_time[i] == "-":
                print(f"{'-':^10}", end="")
            else:
                print(f"{'P' + str(processes_at_time[i]):^10}", end="")
        print("\n" + "=" * 100)

        print("\nProcess Metrics:")
        print("=" * 60)
        print(f"{'PID':^10}|{'Arrival':^12}|{'Completion':^12}|{'Turnaround':^12}|{'Waiting':^12}")
        print("-" * 60)

        total_turnaround = 0
        total_waiting = 0

        for pcb in sorted(self.finished_processes, key=lambda x: x.process.pid):
            burst_time = 0
            for burst in pcb.process.bursts:
                for item in burst[1]:
                    if isinstance(item, int):
                        burst_time += item

            waiting_time = pcb.turnaround_time - burst_time
            total_turnaround += pcb.turnaround_time
            total_waiting += waiting_time

            print(f"{pcb.process.pid:^10}|"
                  f"{pcb.process.arrival_time:^12}|"
                  f"{pcb.completion_time:^12}|"
                  f"{pcb.turnaround_time:^12}|"
                  f"{waiting_time:^12}")

        print("-" * 60)
        n_processes = len(self.finished_processes)
        print(f"\nAverage Turnaround Time: {total_turnaround / n_processes:.2f}")
        print(f"Average Waiting Time: {total_waiting / n_processes:.2f}")

if __name__ == "__main__":
    sample_file = "input.txt"
    try:
        processes = load_processes(sample_file)
        scheduler = Scheduler(processes, time_quantum=10)
        scheduler.run()
        scheduler.print_detailed_results()
    except ValueError as e:
        print(f"Validation Error: {e}")
    except Exception as e:
        print(f"Error: {e}")
