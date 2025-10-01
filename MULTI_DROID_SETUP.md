# Multi-Droid Setup Guide

**Date**: 2025-10-01  
**Purpose**: How to spawn and coordinate multiple Factory droids for parallel development

---

## 🤖 **How to Work with Multiple Droids**

### **Method 1: Multiple Browser Sessions (Recommended for Parallel Work)**

The simplest approach for truly parallel work:

1. **Open Multiple Factory Sessions**:
   - Open Factory in multiple browser tabs/windows
   - Each tab = separate droid session
   - All droids can work on the same repository simultaneously

2. **Assign Tasks**:
   - **Tab 1 (Droid Alpha)**: Task 1A - Core TCP Server
   - **Tab 2 (Droid Beta)**: Task 1B - Command Protocol (waits for Alpha)
   - **Tab 3 (Droid Gamma)**: Task 1C - Integration Testing (waits for Beta)

3. **Give Each Droid Context**:
   ```
   In each session, provide this initial prompt:
   
   "You are Droid [Alpha/Beta/Gamma/etc.]. Please read:
   1. DROID_TASK_BREAKDOWN.md
   2. Find your task: Task [1A/1B/1C/etc.]
   3. Complete the deliverables listed
   4. Check off acceptance criteria
   5. Commit your work with clear messages
   
   Your task is: [Task Name]
   
   Start by reading the task requirements from DROID_TASK_BREAKDOWN.md"
   ```

---

### **Method 2: Sequential Handoffs (Simpler, No Parallelization)**

If you prefer one droid at a time:

1. **Start with Droid Alpha** (current session):
   ```
   "Complete Task 1A from DROID_TASK_BREAKDOWN.md"
   ```

2. **Once Task 1A is complete**:
   - Start a new Factory session (or continue in same session)
   - Provide context: "You are Droid Beta. Task 1A is complete. 
     Please complete Task 1B from DROID_TASK_BREAKDOWN.md"

3. **Continue the chain** through all tasks

---

### **Method 3: Factory Multi-Agent Coordination (If Available)**

If Factory has multi-agent features:

1. **Create Agent Team**:
   - Set up multiple agents in Factory workspace
   - Assign each agent to a specific task
   - Configure shared repository access

2. **Coordinate via Git**:
   - Each agent commits to the same branch
   - Use git for coordination and handoffs
   - Monitor progress via commit history

---

## 📋 **Coordination Strategy**

### **For Sequential Tasks (Phase 1):**

**Task 1A → Task 1B → Task 1C**

1. **Droid Alpha** completes Task 1A:
   - Implements TCP server
   - Commits: "Complete Task 1A: Core TCP Server"
   - Updates DROID_TASK_BREAKDOWN.md: `- [x] Task 1A`

2. **Droid Beta** starts (after Alpha):
   - Reads: "Task 1A is complete. Start Task 1B."
   - Implements command protocol
   - Commits: "Complete Task 1B: Command Protocol"
   - Updates DROID_TASK_BREAKDOWN.md: `- [x] Task 1B`

3. **Droid Gamma** starts (after Beta):
   - Reads: "Tasks 1A and 1B complete. Start Task 1C."
   - Performs integration testing
   - Commits: "Complete Task 1C: PyMoDAQ Integration"
   - Updates DROID_TASK_BREAKDOWN.md: `- [x] Task 1C`

---

### **For Parallel Tasks (Phase 2):**

**Task 2A (foundation) → Tasks 2B + 2C (parallel) → Task 2D (integration)**

1. **Droid Delta** completes Task 2A (foundation):
   - Implements PyRPLPluginBase
   - Commits: "Complete Task 2A: Plugin Base"
   - Notifies: "Task 2A complete. Tasks 2B and 2C can start in parallel."

2. **Droids Epsilon & Zeta** work in parallel:
   
   **Session 1 - Droid Epsilon**:
   ```
   "Task 2A is complete. You are Droid Epsilon.
   Complete Task 2B (Viewer Plugins) from DROID_TASK_BREAKDOWN.md.
   Work on files in daq_viewer_plugins/ directory."
   ```
   
   **Session 2 - Droid Zeta** (simultaneously):
   ```
   "Task 2A is complete. You are Droid Zeta.
   Complete Task 2C (Move Plugins) from DROID_TASK_BREAKDOWN.md.
   Work on files in daq_move_plugins/ directory."
   ```
   
   - Different directories = minimal conflicts
   - Both commit independently
   - Both update DROID_TASK_BREAKDOWN.md

3. **Droid Eta** starts (after both 2B and 2C):
   ```
   "Tasks 2B and 2C are complete. You are Droid Eta.
   Complete Task 2D (Integration Testing) from DROID_TASK_BREAKDOWN.md."
   ```

---

## 🔄 **Handoff Protocol**

### **When a Droid Completes Their Task:**

1. **Commit all changes**:
   ```bash
   git add .
   git commit -m "Complete Task [X]: [Task Name]
   
   Deliverables:
   - [List what was implemented]
   
   Acceptance Criteria:
   - [x] Criterion 1
   - [x] Criterion 2
   
   Next: Task [Y] can start"
   ```

2. **Update task tracking**:
   - Edit DROID_TASK_BREAKDOWN.md
   - Check off completed task: `- [x] Task 1A`
   - Commit: "Update: Mark Task 1A complete"

3. **Push to repository**:
   ```bash
   git push origin feature/command-id-multiplexing
   ```

4. **Notify next droid** (if sequential):
   - If using multiple sessions: Switch to next session
   - If using same session: Continue with next task
   - Provide context: "Task [X] is complete. Start Task [Y]."

---

## 🎯 **Practical Example: Starting Phase 1**

### **Step 1: Start Droid Alpha (Current Session)**

**Your prompt to current droid**:
```
You are Droid Alpha. Complete Task 1A from DROID_TASK_BREAKDOWN.md:
- Core TCP Server Infrastructure
- Create src/pymodaq_plugins_pyrpl/utils/pyrpl_tcp_server.py
- Implement shared PyRPL singleton
- Follow acceptance criteria in DROID_TASK_BREAKDOWN.md

Start by reading the task requirements.
```

### **Step 2: When Task 1A is Complete**

**Option A - New Session (Parallel Capable)**:
- Open new Factory tab
- Provide this prompt:
  ```
  You are Droid Beta. Task 1A (Core TCP Server) is complete.
  Complete Task 1B from DROID_TASK_BREAKDOWN.md:
  - Command Protocol Implementation
  - Implement process_cmds() method
  - Follow acceptance criteria
  
  Start by reviewing what Droid Alpha implemented, then proceed.
  ```

**Option B - Same Session (Sequential)**:
- Continue with: "Task 1A complete. Now complete Task 1B..."

### **Step 3: Continue Through Tasks**

Repeat the pattern for each subsequent task.

---

## 🛠️ **Tools for Coordination**

### **1. Git Commit Messages**
Each droid communicates via commit messages:
```bash
git log --oneline --graph
# Shows what each droid has completed
```

### **2. DROID_TASK_BREAKDOWN.md**
Central tracking document:
- Check off completed tasks
- See what's remaining
- Understand dependencies

### **3. GitHub Issues (Optional)**
If using GitHub:
- Create issue for each task
- Assign to milestone (Phase 1, 2, or 3)
- Close when complete

---

## ⚠️ **Important Guidelines**

### **To Avoid Conflicts:**

1. **Work on different files** when parallel:
   - Task 2B: daq_viewer_plugins/
   - Task 2C: daq_move_plugins/
   - Minimal overlap = no conflicts

2. **Pull before starting**:
   ```bash
   git pull origin feature/command-id-multiplexing
   ```

3. **Commit frequently**:
   - Small, atomic commits
   - Clear messages
   - Push regularly

4. **Coordinate on shared files**:
   - If two droids need same file: do sequentially
   - Or coordinate very carefully

---

## 📊 **Progress Tracking**

### **Check Overall Status**:

```bash
# View commit history
git log --oneline --graph --all

# View task completion
cat DROID_TASK_BREAKDOWN.md | grep "\[x\]"

# View current branch status
git status
```

### **Central Dashboard (This File)**:

Update this section as tasks complete:

**Phase 1 Progress**:
- [ ] Task 1A: Core TCP Server (Droid Alpha)
- [ ] Task 1B: Command Protocol (Droid Beta)
- [ ] Task 1C: Integration Testing (Droid Gamma)

**Phase 2 Progress**:
- [ ] Task 2A: Plugin Base (Droid Delta)
- [ ] Task 2B: Viewer Plugins (Droid Epsilon)
- [ ] Task 2C: Move Plugins (Droid Zeta)
- [ ] Task 2D: Integration Testing (Droid Eta)

**Phase 3 Progress**:
- [ ] Task 3A: PID Advanced UI (Droid Theta)
- [ ] Task 3B: Scope Advanced UI (Droid Iota)
- [ ] Task 3C: ASG Advanced UI (Droid Kappa)
- [ ] Task 3D: IQ Advanced UI (Droid Lambda)

---

## 🚀 **Quick Start Commands**

### **For Each New Droid:**

```
You are Droid [Name]. 

1. Read DROID_TASK_BREAKDOWN.md
2. Find your task: Task [X]
3. Read task requirements and acceptance criteria
4. Check dependencies are complete
5. Implement deliverables
6. Test your implementation
7. Commit with clear message
8. Update task tracking
9. Notify next droid if sequential

Your task: [Task Name]
Dependencies: [List or "None"]

Start now.
```

---

## 💡 **Tips for Success**

1. **Clear Context**: Always tell each droid their identity and task
2. **Check Dependencies**: Ensure prerequisite tasks are complete
3. **Small Commits**: Commit frequently with clear messages
4. **Test Before Handoff**: Verify your work before passing to next droid
5. **Update Tracking**: Keep DROID_TASK_BREAKDOWN.md current
6. **Communicate**: Use commit messages to communicate status

---

**You're ready to spawn multiple droids and coordinate their work!** 🤖✨
