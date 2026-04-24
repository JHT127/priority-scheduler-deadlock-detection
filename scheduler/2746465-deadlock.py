class ResourceAllocationGraph:
    def __init__(self):
        self.processes = {}
        self.resources = {}
        self.waiting = {}
        self.process_priority = {}

    def add_process(self, pid, priority=1):
        if pid not in self.processes:
            self.processes[pid] = set()
            self.waiting[pid] = set()
            self.process_priority[pid] = priority

    def add_resource(self, rid):
        if rid not in self.resources:
            self.resources[rid] = None

    def allocate_resource(self, pid, rid):
        self.add_process(pid)
        self.add_resource(rid)

        if self.resources[rid] is None:
            self.resources[rid] = pid
            self.processes[pid].add(rid)
            return True
        else:
            self.waiting[pid].add(rid)
            if self.detect_deadlock():
                self.recover_from_deadlock()
            return False

    def release_resource(self, pid, rid):
        if rid in self.processes[pid]:
            self.processes[pid].remove(rid)
            self.resources[rid] = None

            for waiting_pid in self.waiting:
                if rid in self.waiting[waiting_pid]:
                    self.waiting[waiting_pid].remove(rid)
                    self.resources[rid] = waiting_pid
                    self.processes[waiting_pid].add(rid)
                    break
            return True
        return False

    def get_wait_for_graph(self):
        wait_for = {}
        for pid in self.processes:
            wait_for[pid] = set()

        for pid in self.waiting:
            for rid in self.waiting[pid]:
                if self.resources[rid] is not None and self.resources[rid] != pid:
                    wait_for[pid].add(self.resources[rid])
        return wait_for

    def detect_cycle(self, graph, start_node, visited, current_path):
        visited.add(start_node)
        current_path.add(start_node)

        for neighbor in graph[start_node]:
            if neighbor not in visited:
                if self.detect_cycle(graph, neighbor, visited, current_path):
                    return True
            elif neighbor in current_path:
                return True

        current_path.remove(start_node)
        return False

    def detect_deadlock(self):
        wait_for = self.get_wait_for_graph()
        visited = set()
        current_path = set()

        for pid in self.processes:
            if pid not in visited:
                if self.detect_cycle(wait_for, pid, visited, current_path):
                    return True
        return False

    def find_deadlocked_processes(self):
        wait_for = self.get_wait_for_graph()
        deadlocked = set()

        def dfs(node, current_path):
            current_path.add(node)
            for neighbor in wait_for[node]:
                if neighbor in current_path:
                    deadlocked.update(current_path)
                elif neighbor not in deadlocked:
                    dfs(neighbor, current_path)
            current_path.remove(node)

        for pid in self.processes:
            if pid not in deadlocked:
                dfs(pid, set())

        return deadlocked

    def recover_from_deadlock(self):
        deadlocked = self.find_deadlocked_processes()
        if not deadlocked:
            return

        victim = 1
        held_resources = self.processes[victim].copy()
        for rid in held_resources:
            self.release_resource(victim, rid)

        self.waiting[victim].clear()
        print(f"\nDeadlock Recovery: Terminated P{victim} to resolve deadlock")
        return victim

    def print_allocation_graph(self):
        print("\nResource Allocation Graph:")
        print("Allocations (Resource → Process):")
        for rid, pid in self.resources.items():
            if pid is not None:
                print(f"R{rid} → P{pid}")

        print("\nWaiting (Process → Resource):")
        for pid, resources in self.waiting.items():
            for rid in resources:
                print(f"P{pid} → R{rid}")

    def print_wait_for_graph(self):
        wait_for = self.get_wait_for_graph()
        print("\nWait-For Graph:")
        for pid, waiting_for in wait_for.items():
            if waiting_for:
                for other_pid in waiting_for:
                    print(f"P{pid} → P{other_pid}")


def test_case_1():
    print("\n=== Test Case 1: Basic Deadlock Scenario ===")
    graph = ResourceAllocationGraph()

    graph.add_process(0, priority=1)
    graph.add_process(1, priority=1)
    graph.add_process(2, priority=0)

    print("\nStep 1: P0 acquires R1")
    graph.allocate_resource(0, 1)
    graph.print_allocation_graph()

    print("\nStep 2: P1 acquires R2")
    graph.allocate_resource(1, 2)
    graph.print_allocation_graph()

    print("\nStep 3: P0 requests R2")
    graph.allocate_resource(0, 2)
    graph.print_allocation_graph()

    print("\nStep 4: P1 requests R1")
    graph.allocate_resource(1, 1)
    graph.print_allocation_graph()
    graph.print_wait_for_graph()


def test_case_2():
    print("\n=== Test Case 2: Time Quantum Scenario ===")
    graph = ResourceAllocationGraph()

    graph.add_process(0, priority=1)
    graph.add_process(1, priority=1)
    graph.add_process(2, priority=0)

    print("\nStep 1: P0 acquires R1")
    graph.allocate_resource(0, 1)

    print("\nStep 2: P0 requests R2")
    graph.allocate_resource(0, 2)

    print("\nStep 3: P1 acquires R2")
    graph.allocate_resource(1, 2)

    print("\nStep 4: P1 requests R1")
    graph.allocate_resource(1, 1)

    graph.print_allocation_graph()
    graph.print_wait_for_graph()

    if graph.detect_deadlock():
        print("\nDeadlock detected!")
        deadlocked = graph.find_deadlocked_processes()
        print(f"Deadlocked processes: {', '.join(f'P{pid}' for pid in deadlocked)}")
        graph.recover_from_deadlock()


def test_case_3():
    print("\n=== Test Case 3: Circular Wait Scenario ===")
    graph = ResourceAllocationGraph()

    graph.add_process(0, priority=1)
    graph.add_process(1, priority=1)
    graph.add_process(2, priority=1)

    print("\nStep 1: P0 acquires R1")
    graph.allocate_resource(0, 1)

    print("\nStep 2: P1 acquires R2")
    graph.allocate_resource(1, 2)

    print("\nStep 3: P2 acquires R3")
    graph.allocate_resource(2, 3)

    print("\nStep 4: P0 requests R2")
    graph.allocate_resource(0, 2)

    print("\nStep 5: P1 requests R3")
    graph.allocate_resource(1, 3)

    print("\nStep 6: P2 requests R1")
    graph.allocate_resource(2, 1)

    graph.print_allocation_graph()
    graph.print_wait_for_graph()

    if graph.detect_deadlock():
        print("\nDeadlock detected!")
        deadlocked = graph.find_deadlocked_processes()
        print(f"Deadlocked processes: {', '.join(f'P{pid}' for pid in deadlocked)}")
        graph.recover_from_deadlock()


def test_case_4():
    print("\n=== Test Case 4: Priority-based Scenario ===")
    graph = ResourceAllocationGraph()

    graph.add_process(0, priority=1)
    graph.add_process(1, priority=2)
    graph.add_process(2, priority=0)

    print("\nStep 1: P0 acquires R2")
    graph.allocate_resource(0, 2)

    print("\nStep 2: P1 acquires R1")
    graph.allocate_resource(1, 1)

    print("\nStep 3: P2 requests R1 and R2")
    graph.allocate_resource(2, 1)
    graph.allocate_resource(2, 2)

    graph.print_allocation_graph()
    graph.print_wait_for_graph()

    if graph.detect_deadlock():
        print("\nDeadlock detected!")
        deadlocked = graph.find_deadlocked_processes()
        print(f"Deadlocked processes: {', '.join(f'P{pid}' for pid in deadlocked)}")
        graph.recover_from_deadlock()


def run_all_tests():
    test_case_1()
    test_case_2()
    test_case_3()
    test_case_4()


if __name__ == "__main__":
    run_all_tests()