# Multi-Droid Task Breakdown

**Date**: 2025-10-01  
**Purpose**: Distribute PyRPL-PyMoDAQ development across multiple Factory droids

---

## 🎯 **Overview**

This document breaks down the three-phase development plan into discrete, parallelizable tasks suitable for multiple droids.

---

## 📋 **Task Organization**

### **Dependency Chain:**
```
Phase 1A → Phase 1B → Phase 1C (Sequential)
                ↓
         Phase 2 (Multiple parallel tasks)
                ↓
         Phase 3 (Multiple parallel tasks)
```

---

## 🤖 **PHASE 1: TCP Architecture (Prototype)**

### **Task 1A: Core TCP Server Infrastructure** ⭐⭐⭐
**Priority**: CRITICAL - Must be done first  
**Estimated Time**: 2-3 hours  
**Dependencies**: None  
**Droid Assignment**: Droid Alpha

**Objective**: Create the foundational TCP server with shared PyRPL singleton

**Deliverables**:
1. `src/pymodaq_plugins_pyrpl/utils/pyrpl_tcp_server.py` - Main server script
   - Implement shared PyRPL singleton with thread-safe locking
   - Create PyRPLModuleServer class inheriting from TCPServer
   - Add command-line argument parsing (--module, --port, --hostname, --config)
   - Implement basic Qt application and event loop setup

2. Documentation:
   - Docstrings for all classes and methods
   - Usage examples in comments

**Acceptance Criteria**:
- [ ] Server starts without errors
- [ ] Accepts --module and --port arguments
- [ ] Creates shared PyRPL instance (singleton pattern verified)
- [ ] Qt event loop runs properly
- [ ] Can be instantiated multiple times (different ports) sharing ONE PyRPL

**Handoff**: Provides working server infrastructure for Task 1B

---

### **Task 1B: Command Protocol Implementation** ⭐⭐⭐
**Priority**: HIGH - Needed for any communication  
**Estimated Time**: 3-4 hours  
**Dependencies**: Task 1A complete  
**Droid Assignment**: Droid Beta

**Objective**: Implement command processing for scope and basic modules

**Deliverables**:
1. Implement `process_cmds()` method in PyRPLModuleServer
   - Handle 'grab_data' command for scope
   - Handle 'configure' command for settings
   - Handle 'move_abs' command for actuators
   - Proper error handling and response formatting

2. Module-specific implementations:
   - Scope: Trigger, wait, return curve data
   - IQ: Return IQ measurement
   - ASG: Set offset/frequency
   - PID: Set setpoint

3. Testing:
   - Create manual test script to verify commands work
   - Test with mock PyRPL (if hardware unavailable)

**Acceptance Criteria**:
- [ ] All command types implemented
- [ ] Proper error responses for invalid commands
- [ ] Data returned in correct format
- [ ] Manual testing shows commands work

**Handoff**: Provides working command protocol for Task 1C

---

### **Task 1C: PyMoDAQ Integration & Testing** ⭐⭐
**Priority**: MEDIUM - Integration testing  
**Estimated Time**: 2-3 hours  
**Dependencies**: Tasks 1A and 1B complete  
**Droid Assignment**: Droid Gamma

**Objective**: Integrate with PyMoDAQ's built-in TCP instruments and validate

**Deliverables**:
1. Server startup scripts:
   - `scripts/start_scope_server.sh`
   - `scripts/start_iq_server.sh`
   - `scripts/start_asg_server.sh`
   - `scripts/start_pid_server.sh`

2. PyMoDAQ configuration guide:
   - Step-by-step instructions for adding DAQ_Viewer_TCP
   - Example configurations for each module
   - Screenshot/documentation of settings

3. Integration testing:
   - Start servers
   - Add TCP instruments in PyMoDAQ dashboard
   - Verify data acquisition works
   - Test concurrent access (multiple modules)

**Acceptance Criteria**:
- [ ] Startup scripts work correctly
- [ ] PyMoDAQ successfully connects to servers
- [ ] Data acquisition works for at least 2 modules
- [ ] Multiple modules can be used simultaneously
- [ ] Documentation clear enough for users

**Handoff**: Phase 1 COMPLETE - Validated prototype ready for Phase 2

---

## 🚀 **PHASE 2: Custom Plugin (Production)**

**Note**: These tasks can be done in PARALLEL once Phase 1 is validated

### **Task 2A: Plugin Base Infrastructure** ⭐⭐⭐
**Priority**: HIGH - Foundation for all plugins  
**Estimated Time**: 2-3 hours  
**Dependencies**: Phase 1 complete  
**Droid Assignment**: Droid Delta

**Objective**: Create shared base class for all PyRPL plugins

**Deliverables**:
1. `src/pymodaq_plugins_pyrpl/utils/pyrpl_plugin_base.py`
   - PyRPLPluginBase class
   - Shared PyRPL singleton management
   - Thread-safe get_pyrpl() method
   - get_module() helper method
   - Common error handling

2. Unit tests:
   - Test singleton behavior
   - Test thread safety
   - Test module access

**Acceptance Criteria**:
- [ ] Base class implemented with docstrings
- [ ] Singleton pattern verified
- [ ] Thread-safe (concurrent access test)
- [ ] Unit tests pass

**Handoff**: Provides base class for Tasks 2B, 2C, 2D

---

### **Task 2B: Viewer Plugins (Scope & IQ)** ⭐⭐
**Priority**: MEDIUM  
**Estimated Time**: 4-5 hours  
**Dependencies**: Task 2A complete  
**Droid Assignment**: Droid Epsilon

**Objective**: Create viewer plugins for data acquisition modules

**Deliverables**:
1. `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_1D/daq_1Dviewer_PyRPL_Scope.py`
   - Inherits from DAQ_Viewer_base and PyRPLPluginBase
   - Settings tree with scope parameters
   - ini_detector() implementation
   - grab_data() implementation
   - commit_settings() for parameter changes

2. `src/pymodaq_plugins_pyrpl/daq_viewer_plugins/plugins_0D/daq_0Dviewer_PyRPL_IQ.py`
   - Similar structure for IQ module
   - All 3 IQ modules supported (iq0, iq1, iq2)

3. Testing with PyMoDAQ dashboard

**Acceptance Criteria**:
- [ ] Plugins show up in PyMoDAQ detector list
- [ ] Connection to PyRPL works
- [ ] Data acquisition works
- [ ] Settings can be changed via UI
- [ ] Multiple instances work (e.g., iq0 and iq1)

**Handoff**: Working viewer plugins

---

### **Task 2C: Move Plugins (PID & ASG)** ⭐⭐
**Priority**: MEDIUM  
**Estimated Time**: 4-5 hours  
**Dependencies**: Task 2A complete  
**Droid Assignment**: Droid Zeta

**Objective**: Create actuator plugins for control modules

**Deliverables**:
1. `src/pymodaq_plugins_pyrpl/daq_move_plugins/daq_move_PyRPL_PID.py`
   - Inherits from DAQ_Move_base and PyRPLPluginBase
   - Settings tree with PID parameters
   - ini_stage() implementation
   - move_abs(), move_rel() implementations
   - get_actuator_value() implementation
   - commit_settings() for parameter changes

2. `src/pymodaq_plugins_pyrpl/daq_move_plugins/daq_move_PyRPL_ASG.py`
   - Similar structure for ASG module
   - Both ASG modules supported (asg0, asg1)

3. Testing with PyMoDAQ dashboard

**Acceptance Criteria**:
- [ ] Plugins show up in PyMoDAQ actuator list
- [ ] Connection to PyRPL works
- [ ] Move commands work
- [ ] Settings can be changed via UI
- [ ] Multiple instances work (e.g., pid0 and pid1)

**Handoff**: Working move plugins

---

### **Task 2D: Integration Testing & Documentation** ⭐
**Priority**: MEDIUM  
**Estimated Time**: 2-3 hours  
**Dependencies**: Tasks 2B and 2C complete  
**Droid Assignment**: Droid Eta

**Objective**: Validate all plugins work together and document

**Deliverables**:
1. Integration tests:
   - Test all 4 plugin types simultaneously
   - Verify shared PyRPL instance works
   - Test dashboard preset with all modules

2. Documentation:
   - Update README.md with Phase 2 completion
   - Plugin usage guide
   - Installation instructions
   - Example dashboard preset

3. Bug fixes based on integration testing

**Acceptance Criteria**:
- [ ] All plugins work simultaneously
- [ ] Dashboard preset loads successfully
- [ ] Documentation complete and clear
- [ ] Known issues documented

**Handoff**: Phase 2 COMPLETE - Production plugins ready

---

## 🎨 **PHASE 3: GUI Replication (Full UI)**

**Note**: These tasks can be done in PARALLEL

### **Task 3A: PID Advanced UI** ⭐
**Priority**: LOW  
**Estimated Time**: 3-4 hours  
**Dependencies**: Task 2C complete  
**Droid Assignment**: Droid Theta

**Objective**: Add complete PID settings tree matching PyRPL GUI

**Deliverables**:
1. Extended settings tree:
   - All PID parameters (P, I, D, input, output, filter, etc.)
   - Action buttons (reset integrator, enable/disable)
   - Live parameter display (integrator value)

2. commit_settings() implementation for all parameters

3. Testing with real hardware

**Acceptance Criteria**:
- [ ] All PyRPL PID features accessible
- [ ] UI matches PyRPL functionality
- [ ] Action buttons work
- [ ] Live updates work

---

### **Task 3B: Scope Advanced UI** ⭐
**Priority**: LOW  
**Estimated Time**: 3-4 hours  
**Dependencies**: Task 2B complete  
**Droid Assignment**: Droid Iota

**Objective**: Add complete Scope settings tree matching PyRPL GUI

**Deliverables**:
1. Extended settings tree:
   - All trigger options
   - All input sources
   - Display modes (rolling, XY)
   - Averaging settings

2. Advanced features:
   - Trigger configuration
   - Dual-channel mode
   - XY plotting

**Acceptance Criteria**:
- [ ] All PyRPL scope features accessible
- [ ] Trigger modes work
- [ ] Display modes work

---

### **Task 3C: ASG Advanced UI** ⭐
**Priority**: LOW  
**Estimated Time**: 2-3 hours  
**Dependencies**: Task 2C complete  
**Droid Assignment**: Droid Kappa

**Objective**: Add complete ASG settings tree matching PyRPL GUI

**Deliverables**:
1. Extended settings tree:
   - All waveform types
   - Arbitrary waveform loading
   - Burst mode
   - Trigger settings

2. Implementation of advanced features

**Acceptance Criteria**:
- [ ] All waveform types work
- [ ] Arbitrary waveforms loadable
- [ ] Burst mode works

---

### **Task 3D: IQ Advanced UI** ⭐
**Priority**: LOW  
**Estimated Time**: 2-3 hours  
**Dependencies**: Task 2B complete  
**Droid Assignment**: Droid Lambda

**Objective**: Add complete IQ settings tree matching PyRPL GUI

**Deliverables**:
1. Extended settings tree:
   - Frequency settings
   - Bandwidth settings
   - Quadrature settings
   - Output routing

2. Live IQ display

**Acceptance Criteria**:
- [ ] All IQ parameters accessible
- [ ] Live I/Q values displayed
- [ ] Output routing works

---

## 📊 **Task Assignment Summary**

| Droid | Phase | Task | Priority | Estimated Time | Can Start When |
|-------|-------|------|----------|----------------|----------------|
| Alpha | 1A | Core TCP Server | CRITICAL | 2-3h | Immediately |
| Beta | 1B | Command Protocol | HIGH | 3-4h | After Alpha |
| Gamma | 1C | PyMoDAQ Integration | MEDIUM | 2-3h | After Beta |
| Delta | 2A | Plugin Base | HIGH | 2-3h | After Phase 1 validated |
| Epsilon | 2B | Viewer Plugins | MEDIUM | 4-5h | After Delta |
| Zeta | 2C | Move Plugins | MEDIUM | 4-5h | After Delta (parallel with Epsilon) |
| Eta | 2D | Integration Testing | MEDIUM | 2-3h | After Epsilon & Zeta |
| Theta | 3A | PID Advanced UI | LOW | 3-4h | After Zeta |
| Iota | 3B | Scope Advanced UI | LOW | 3-4h | After Epsilon (parallel with Theta) |
| Kappa | 3C | ASG Advanced UI | LOW | 2-3h | After Zeta (parallel) |
| Lambda | 3D | IQ Advanced UI | LOW | 2-3h | After Epsilon (parallel) |

---

## 🔄 **Handoff Protocol**

### **Between Sequential Tasks:**
1. Completing droid commits all code with clear commit messages
2. Updates this document with completion status
3. Runs basic tests to verify deliverables
4. Notifies next droid via commit message or separate communication

### **For Parallel Tasks:**
1. All droids work on separate files (minimal conflicts)
2. Coordinate through shared base classes (Task 2A)
3. Integration droid (Task 2D) combines and tests

---

## ✅ **Task Tracking**

### **Phase 1:**
- [ ] Task 1A: Core TCP Server (Droid Alpha)
- [ ] Task 1B: Command Protocol (Droid Beta)
- [ ] Task 1C: PyMoDAQ Integration (Droid Gamma)

### **Phase 2:**
- [ ] Task 2A: Plugin Base (Droid Delta)
- [ ] Task 2B: Viewer Plugins (Droid Epsilon)
- [ ] Task 2C: Move Plugins (Droid Zeta)
- [ ] Task 2D: Integration Testing (Droid Eta)

### **Phase 3:**
- [ ] Task 3A: PID Advanced UI (Droid Theta)
- [ ] Task 3B: Scope Advanced UI (Droid Iota)
- [ ] Task 3C: ASG Advanced UI (Droid Kappa)
- [ ] Task 3D: IQ Advanced UI (Droid Lambda)

---

## 📝 **Notes for Task Distribution**

1. **Context Sharing**: Each droid should read:
   - This file (DROID_TASK_BREAKDOWN.md)
   - PHASED_DEVELOPMENT_PLAN.md
   - README.md

2. **Avoid deprecated_docs/**: All historical documentation is obsolete

3. **Communication**: Use git commit messages to communicate progress

4. **Testing**: Each droid responsible for testing their own deliverables

5. **Documentation**: Each droid updates relevant docs with their changes

---

**Use this breakdown to assign tasks to individual Factory droids for parallel development!**
