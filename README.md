# Priority Scheduler Deadlock Detection

> CPU process scheduler with multi-level priority queues, Round Robin arbitration, IO burst handling, and wait-for graph deadlock detection — implemented from scratch in Python.

---


**Partners** : Joud Thaher & Labiba Sharia


## What Was Built

| Module | What It Is |
|---|---|
| `scheduler/scheduler.py` | Full CPU scheduler: priority queues, Round Robin, IO bursts, resource tracking, integrated deadlock detection and recovery |
| `scheduler/deadlock.py` | Standalone `ResourceAllocationGraph` — isolated deadlock detection and recovery with 4 test cases |
| `docs/report.pdf` | Test case documentation covering both scheduling scenarios and deadlock scenarios |

> **Note on the two files:** The deadlock detection integrated inside `scheduler.py` does not behave correctly when combined with the scheduler's resource state during scheduling. `deadlock.py` is a standalone, correct implementation of deadlock detection and recovery used to verify deadlock test cases independently. See [Known Limitations](#known-limitations) for the root cause.

---

## Architecture Overview

### Scheduling Algorithm

```
Non-preemptive Priority Scheduling + Round Robin (same-priority tie-breaking)

                    ┌─────────────────────────────────┐
New arrival ───────►│        Ready Queues             │
                    │  Priority 0: [P3, P5]           │
                    │  Priority 1: [P1, P2] ◄── RR   │◄── IO completion
                    │  Priority 2: [P4]               │
                    └──────────────┬──────────────────┘
                                   │  get_highest_priority_process()
                                   ▼
                    ┌──────────────────────────────────┐
                    │          CPU (Running)           │
                    │  execute burst instructions:     │
                    │  • integer → decrement timer     │
                    │  • R[n]    → request resource    │
                    │  • F[n]    → release resource    │
                    └───┬──────────────┬──────────────┘
                        │              │
               burst done           IO burst
                        │              │
                        ▼              ▼
                    FINISHED      IO Wait List
                                  (completion_time, pcb)
```

**Round Robin arbitration rule:** activated only when two or more processes share both the same priority level and the same arrival time. RR quantum is configurable (`time_quantum` parameter). Outside of these ties, scheduling is strictly non-preemptive priority.

---

### Process Input Format

Processes are loaded from a plain-text file (`input.txt`), one process per line:

```
<PID> <arrival_time> <priority> <burst_sequence>
```

**Burst sequence syntax:**

| Token | Meaning |
|---|---|
| `CPU{<duration>}` | CPU burst of given duration |
| `CPU{<duration>, R[n]}` | CPU burst — request resource `n` at that instruction |
| `CPU{<duration>, F[n]}` | CPU burst — release resource `n` |
| `IO{<duration>}` | IO burst (process moves to IO wait list) |

**Constraints:**
- Every process must start and end with a CPU burst (enforced by `validate_bursts()`)
- No two processes may share the same PID

**Example input:**
```
1  0  1  CPU{5, R[1]} IO{3} CPU{4, F[1]}
2  0  1  CPU{3, R[2]} IO{2} CPU{5, F[2]}
3  2  2  CPU{6}
```

---

### Data Structures

| Structure | Type | Purpose |
|---|---|---|
| `process_queues` | `Dict[int, deque]` | One deque per priority level |
| `pcbs` | `Dict[int, ProcessControlBlock]` | State tracking per process |
| `io_processes` | `List[tuple[int, PCB]]` | `(completion_time, pcb)` pairs |
| `allocation_matrix` | `Dict[int, Set[int]]` | Resources currently held per process |
| `waiting_for` | `Dict[int, Set[int]]` | Resources each process is waiting on |
| `gantt_chart` | `List[tuple[int, int]]` | `(time, pid)` pairs for output |

---

### Deadlock Detection & Recovery

**Detection method:** DFS-based cycle detection on a wait-for graph.

```
Wait-for graph construction:
  for each process P waiting on resource R:
    if R is held by process Q:
      add edge P → Q

Cycle detection:
  DFS with recursion stack tracking
  cycle found → all nodes in cycle path added to deadlocked set
```

**Recovery method:** Victim selection by highest priority (largest `priority` value), with PID as tiebreaker. Victim's held resources are released, its burst sequence is reset to the beginning, and it re-enters the ready queue. Other deadlocked processes are unblocked and also re-queued.

```
handle_deadlock(deadlocked_pids):
  victim = max(deadlocked_pids, key=priority desc, pid asc)
  release all resources held by victim
  reset victim: burst_index=0, instruction_index=0, remaining_time=first_burst
  re-add victim to ready queue
  unblock and re-queue all other deadlocked processes
```

**Standalone deadlock module (`deadlock.py`):**

`ResourceAllocationGraph` implements the same wait-for graph approach with an explicit `detect_cycle()` / `find_deadlocked_processes()` / `recover_from_deadlock()` separation. Victim is always P1 in the standalone version (hardcoded — see Limitations).

---

### Scheduler Main Loop

```
while unfinished processes exist:
  1. update_io_processes()     — move completed IO → ready queue
  2. check_new_arrivals()      — add processes that have arrived
  3. if no running process:
       get_highest_priority_process()
       apply RR if same-priority/same-arrival group detected
  4. execute one instruction from current burst:
       int  → decrement remaining_time, decrement quantum
       R[n] → request resource; if blocked → detect deadlock → handle or wait
       F[n] → release resource
  5. if remaining_time == 0 → handle_burst_completion()
  6. if quantum exhausted and RR active → preempt → re-queue
  7. update_waiting_times()
  8. current_time += 1
```

---

## Test Cases

### Without Deadlock

| Test | Description | Scheduling Mode |
|---|---|---|
| 1 | Provided base case | Priority + RR |
| 2 | Provided extended case | Priority + RR |
| 3 | 5 processes: P1&P2 same arrival/priority, P4&P5 same arrival/priority | RR within groups; tested at quantum=4 and quantum=10 |
| 4 | 4 processes: 3 share arrival time and priority | 3-way RR; tested at quantum=5 |
| 5 | Mixed priority, sequential arrivals | Pure priority scheduling |

### With Deadlock

| Test | Description | Detected | Recovered |
|---|---|---|---|
| 1 (provided) | P1↔P2 circular wait | ✅ | ✅ via victim termination |
| 2 (designed) | Multi-process cycle | ✅ (standalone) | ✅ (standalone) |

> See `docs/report.pdf` for Gantt chart output and process metrics for each test case.

---

## Known Limitations

**Integrated deadlock + scheduling interaction bug**
- Root cause: When the scheduler's `handle_deadlock()` is triggered mid-burst, the resource state in `ResourceManager` and the PCB's `current_instruction_index` can fall out of sync. Specifically, after victim reset, the instruction pointer is restored to 0 but the resource `allocation_matrix` may still carry stale entries from partially-executed burst instructions, causing incorrect resource availability on the next request
- Effect: Deadlock test cases run through `scheduler.py` produce incorrect scheduling output — wrong Gantt chart, wrong process metrics
- Workaround: `deadlock.py` implements deadlock detection and recovery correctly in isolation. Deadlock test cases are verified there
- Fix path: Decouple resource state snapshots from the scheduler tick loop; take a full state snapshot before processing each instruction and roll back cleanly on deadlock recovery rather than partial reset

**Victim selection in `deadlock.py` is hardcoded**
- `recover_from_deadlock()` always terminates P1 regardless of priority
- The scheduler's `handle_deadlock()` implements correct priority-based victim selection; the standalone module does not

**No preemption outside RR groups**
- A newly arrived high-priority process will not preempt a currently running lower-priority process mid-burst
- This is by design (non-preemptive), but means high-priority processes can experience higher-than-expected waiting times if they arrive while a long low-priority burst is executing

**Single-unit resource model**
- Each resource has exactly one instance; no support for multiple instances of the same resource type
- Banker's algorithm (safe state detection) is not implemented — only cycle detection after the fact

**`current_time` referenced in `ResourceManager` without being set**
- `ResourceManager.print_resource_state()` references `self.current_time` which is never initialised in `ResourceManager` — it exists on `Scheduler`, not `ResourceManager`
- Calling `print_resource_state()` directly will raise `AttributeError`

---

## How to Run

### Scheduler

```bash
cd scheduler

# Create your input.txt in the same directory, then:
python scheduler.py
```

Input file format — one process per line:
```
<PID> <arrival> <priority> CPU{<n>} IO{<n>} CPU{<n>}
```

Resource instructions inside CPU bursts:
```
1  0  2  CPU{3, R[1], 2, F[1]}  IO{4}  CPU{2}
```

Output includes:
- Gantt chart (time axis + process axis)
- Per-process table: arrival, completion, turnaround, waiting times
- Average turnaround and average waiting time

### Deadlock Standalone

```bash
cd scheduler
python deadlock.py
```

Runs 4 built-in test cases automatically:
- Test 1: Basic P0↔P1 circular wait
- Test 2: Time quantum scenario
- Test 3: 3-way circular wait (P0→P1→P2→P0)
- Test 4: Priority-based scenario

No input file required.

---

## Skills Demonstrated

| What Was Built | Technical Domain |
|---|---|
| Multi-level priority queue scheduler | Operating systems, process scheduling |
| Round Robin arbitration within priority groups | Concurrent process management |
| IO burst modelling with completion time tracking | CPU/IO overlap simulation |
| Resource request/release instruction parsing | Instruction-level process modelling |
| Wait-for graph construction from allocation state | Graph algorithms, deadlock theory |
| DFS cycle detection with recursion stack | Depth-first search, cycle detection |
| Deadlock recovery via victim selection | OS resource management |
| Gantt chart generation from scheduler state | Simulation output, scheduling visualisation |
| Honest root-cause documentation of integration bug | Engineering rigour |

---

## Repository Structure

```
priority-scheduler-deadlock-detection/
├── scheduler/
│   ├── scheduler.py
│   ├── deadlock.py
│   └── input.txt          ← create your own; see format above
├── docs/
│   └── report.pdf
└── README.md
```

---

*Operating System Concepts (ENCS3390) — Electrical and Computer Engineering, Birzeit University, 2024–2025*
