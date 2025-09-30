# Mock Mode Tutorial: Mathematical Control Theory Through Practice

This tutorial teaches PID control theory using the PyMoDAQ PyRPL plugin's advanced mock mode. You'll learn rigorous control theory through realistic simulations, bridging mathematical concepts with hands-on implementation without requiring physical Red Pitaya hardware.

## What You'll Learn

- **Mathematical PID Theory**: Laplace transforms, transfer functions, and stability analysis
- **Plant Dynamics Modeling**: FOPDT systems, time constants, and dead time effects
- **Rigorous Tuning Methods**: Ziegler-Nichols derivation and systematic optimization
- **Signal Processing Mathematics**: Fourier analysis and lock-in amplifier theory
- **PyMoDAQ Integration**: Professional measurement workflows with theoretical foundation

## Mathematical Prerequisites

Before starting, you should be familiar with:
- **Basic Calculus**: Derivatives, integrals, differential equations
- **Laplace Transforms**: s-domain analysis, transfer functions
- **Complex Numbers**: Frequency response, Bode plots
- **Linear Systems**: Superposition, time invariance

> 💡 **Quick Reference**: See [Control Theory Foundations](CONTROL_THEORY_FOUNDATIONS.md) for complete mathematical derivations and theory.

## Prerequisites

- PyMoDAQ PyRPL plugin installed ([Installation Guide](INSTALLATION.md))
- Basic understanding of control systems (helpful but not required)
- No hardware required - everything runs in simulation

## Tutorial Structure

| Section | Topic | Time | Difficulty |
|---------|-------|------|------------|
| [1](#section-1-basic-setup) | Basic Setup | 10 min | Beginner |
| [2](#section-2-first-pid-control) | First PID Control | 15 min | Beginner |
| [3](#section-3-exploring-plant-dynamics) | Plant Dynamics | 20 min | Intermediate |
| [4](#section-4-systematic-tuning) | Systematic Tuning | 25 min | Intermediate |
| [5](#section-5-advanced-scenarios) | Advanced Scenarios | 30 min | Advanced |
| [6](#section-6-multi-plugin-coordination) | Multi-Plugin Use | 20 min | Advanced |

---

## Section 1: Basic Setup

### 1.1 Launch PyMoDAQ Dashboard

```bash
python -m pymodaq.dashboard
```

### 1.2 Add PyRPL PID Plugin

1. Click **"Add"** → **"Move"** → **"DAQ_Move_PyRPL_PID"**
2. Configure plugin:
   - **RedPitaya Host**: `demo.pyrpl.local` (any hostname works in mock mode)
   - **Mock Mode**: `True` ✅
   - **PID Module**: `pid0`

### 1.3 Add Voltage Monitor Plugin

1. Click **"Add"** → **"Detector"** → **"DAQ_0DViewer_PyRPL"**
2. Configure plugin:
   - **RedPitaya Host**: `demo.pyrpl.local` (same as PID plugin)
   - **Mock Mode**: `True` ✅
   - **Monitor IN1**: `True`
   - **Monitor PID**: `True`

### 1.4 Initialize Plugins

Click **"Initialize"** on both plugins. You should see:
- **PID Plugin**: Ready for setpoint control
- **Voltage Monitor**: Displaying simulated voltage readings

**✅ Success Criteria:**
- Both plugins initialize without errors
- Voltage monitor shows realistic voltage values (around 0V initially)
- PID plugin is ready to accept setpoint commands

---

## Section 2: First PID Control

### 2.1 Understanding the Default Scenario

The mock mode starts with a **stable basic** scenario:
- **Plant**: Well-behaved system (gain=1.0, τ=2.0s)
- **PID Settings**: Conservative tuning (P=0.5, I=0.05, D=0.0)
- **Noise**: Minimal measurement noise (0.01V RMS)

### 2.2 Your First Setpoint Change

1. **Set initial setpoint**: Enter `0.2` V in the PID plugin
2. **Observe response**: Watch the voltage monitor
3. **Expected behavior**:
   - Smooth approach to 0.2V
   - Minimal overshoot
   - Settling time ~10-15 seconds

### 2.3 Experiment with Different Setpoints

Try these setpoint sequences:
```
0V → 0.5V → 0V → -0.3V → 0V
```

**Observations to make:**
- How long does it take to reach each setpoint?
- Is there overshoot?
- How well does it track step changes?

### 2.4 Add Oscilloscope for Better Visualization

1. **Add scope plugin**: **"DAQ_1DViewer_PyRPL_Scope"**
2. **Configure**:
   - **RedPitaya Host**: `demo.pyrpl.local`
   - **Mock Mode**: `True`
   - **Input Channel**: `in1`
   - **Decimation**: `64` (for ~2s time window)

3. **Initialize and start continuous acquisition**

**✅ Success Criteria:**
- You can make controlled setpoint changes
- The system responds predictably
- Scope shows clean step responses

---

## Section 3: Exploring Plant Dynamics

### 3.1 Load Different Plant Scenarios

The mock mode includes several predefined scenarios. Let's explore them systematically:

#### 3.1.1 Stable Optimized System

1. **Apply preset**:
   ```python
   # In Python console or script
   from pymodaq_plugins_pyrpl.utils.demo_presets import apply_demo_preset
   apply_demo_preset("stable_optimized", pid_plugin)
   ```

2. **Test step response**: 0V → 0.5V
3. **Observe**: Faster response, some overshoot

#### 3.1.2 Oscillatory Challenge

1. **Apply preset**: `apply_demo_preset("oscillatory_challenge", pid_plugin)`
2. **Test step response**: 0V → 0.3V
3. **Observe**:
   - Oscillatory behavior
   - Need for careful tuning
   - Effect of derivative action

#### 3.1.3 Sluggish Integral System

1. **Apply preset**: `apply_demo_preset("sluggish_integral", pid_plugin)`
2. **Test step response**: 0V → 0.4V
3. **Observe**:
   - Slow response
   - Importance of integral action
   - Steady-state accuracy

### 3.2 Understanding Plant Parameters

Each scenario represents different **First-Order Plus Dead-Time (FOPDT)** models:

```
G(s) = K * e^(-θs) / (τs + 1)
```

| Scenario | K (Gain) | τ (Time Const) | θ (Dead Time) | Characteristics |
|----------|----------|----------------|---------------|-----------------|
| **stable_basic** | 1.0 | 2.0s | 0.1s | Well-behaved, easy to control |
| **stable_optimized** | 1.0 | 2.0s | 0.1s | Same plant, aggressive tuning |
| **oscillatory_challenge** | 2.0 | 1.0s | 0.05s | High gain, low damping |
| **sluggish_integral** | 0.5 | 5.0s | 0.2s | Slow response, needs integral |

### 3.3 Hands-on Exercise: Plant Comparison

**Exercise**: Compare step responses across all scenarios:

1. **Setup measurement protocol**:
   - Same setpoint change: 0V → 0.5V
   - Record settling time, overshoot, steady-state error
   - Use scope to capture full response

2. **Record your observations**:

| Scenario | Settling Time | Overshoot | Steady-State Error | Notes |
|----------|---------------|-----------|-------------------|-------|
| stable_basic | ___s | ___%| ___V | |
| stable_optimized | ___s | ___%| ___V | |
| oscillatory_challenge | ___s | ___%| ___V | |
| sluggish_integral | ___s | ___%| ___V | |

**✅ Success Criteria:**
- You understand how plant dynamics affect control performance
- You can identify which scenarios are easier/harder to control
- You see the trade-offs between speed and stability

---

## Section 4: Rigorous Mathematical Tuning

### 4.1 The Ziegler-Nichols Method: Mathematical Foundation

The Ziegler-Nichols method is based on finding the **ultimate gain (Ku)** and **ultimate period (Pu)** where the characteristic equation has poles on the imaginary axis.

#### Mathematical Theory
At the stability boundary, the characteristic equation becomes:
```
1 + Ku·G(jωu) = 0
```

This means: **Ku·G(jωu) = -1**

Where ωu = 2π/Pu is the **ultimate frequency**.

For our oscillatory plant G(s) = 2.0·e^(-0.05s)/(1.0s + 1):

**Step 1: Calculate Ultimate Frequency**
At the ultimate frequency, the phase shift is exactly -180°:
```
∠G(jωu) = -arctan(ωu·τ) - ωu·θ·(180°/π) = -180°
```

For our parameters (τ = 1.0s, θ = 0.05s):
```
-arctan(ωu) - ωu·0.05·(180°/π) = -180°
```

Solving numerically: **ωu ≈ 1.57 rad/s** → **Pu = 2π/ωu ≈ 4.0s**

**Step 2: Calculate Ultimate Gain**
```
|Ku·G(jωu)| = 1
Ku·|G(jωu)| = 1
Ku·2.0/√(1 + ωu²) = 1
Ku = √(1 + 1.57²)/(2.0) ≈ 0.90
```

**Theoretical Prediction**: Ku ≈ 0.90, Pu ≈ 4.0s

#### Hands-on Verification

1. **Load oscillatory scenario**: `apply_demo_preset("oscillatory_challenge", pid_plugin)`
2. **Set I=0, D=0** (P-only control)
3. **Test theoretical prediction**:
   - Set P = 0.90
   - Observe: Should see sustained oscillation with period ≈ 4.0s
4. **Fine-tune empirically**:
   - Increase P slowly until sustained oscillation
   - Record actual **Ku** and **Pu** values

#### Mathematical Tuning Rules

Classical Ziegler-Nichols PID formulas:
```
Kp = 0.6 × Ku
Ki = 1.2 × Ku / Pu
Kd = 0.075 × Ku × Pu
```

**Theoretical Calculation** (using Ku = 0.90, Pu = 4.0s):
```
Kp = 0.6 × 0.90 = 0.54
Ki = 1.2 × 0.90 / 4.0 = 0.27 rad/s
Kd = 0.075 × 0.90 × 4.0 = 0.27 s
```

#### PID Transfer Function Analysis
The resulting PID controller transfer function becomes:
```
C(s) = 0.54 + 0.27/s + 0.27·s = (0.27s² + 0.54s + 0.27)/s
```

**Closed-loop characteristic equation**:
```
1 + C(s)·G(s) = 0
s·(1.0s + 1) + 0.27s²·2.0·e^(-0.05s) + 0.54s·2.0·e^(-0.05s) + 0.27·2.0·e^(-0.05s) = 0
```

This can be approximated for small dead time using Padé approximation:
```
e^(-0.05s) ≈ (1 - 0.025s)/(1 + 0.025s)
```

### 4.2 Advanced Tuning: Lambda Method

The **Lambda (λ) tuning method** provides more control over closed-loop response time.

#### Mathematical Foundation
Design the closed-loop transfer function as:
```
T(s) = 1/(λs + 1)ⁿ
```

Where λ is the **desired closed-loop time constant**.

For FOPDT plant G(s) = K·e^(-θs)/(τs + 1):

**PI Controller Design**:
```
Kp = τ/(K·(λ + θ))
Ki = 1/(K·(λ + θ))
```

**PID Controller Design**:
```
Kp = (2τ + θ)/(K·(λ + θ))
Ki = 1/(K·(λ + θ))
Kd = τθ/(K·(λ + θ))
```

#### Practical Exercise

**Step 1**: Choose desired response time λ = 1.0s

**Step 2**: Apply Lambda tuning to stable_basic scenario (K=1.0, τ=2.0s, θ=0.1s):
```
Kp = (2×2.0 + 0.1)/(1.0×(1.0 + 0.1)) = 4.1/1.1 = 3.73
Ki = 1/(1.0×(1.0 + 0.1)) = 1/1.1 = 0.91 rad/s
Kd = (2.0×0.1)/(1.0×(1.0 + 0.1)) = 0.2/1.1 = 0.18 s
```

**Step 3**: Test and compare with Ziegler-Nichols:
- Apply Lambda tuning parameters
- Test step response: 0V → 0.5V
- Compare rise time, overshoot, settling time
- **Expected**: Less overshoot, more predictable response than Z-N

### 4.3 Performance Analysis and Optimization

#### Time-Domain Specifications

**Mathematical Definitions**:
- **Rise Time (tr)**: Time for 10% → 90% of final value
- **Settling Time (ts)**: Time to reach ±2% of final value
- **Overshoot (Mp)**: Maximum overshoot percentage
- **Steady-State Error (ess)**: Final tracking error

For second-order underdamped systems:
```
Mp = exp(-ζπ/√(1-ζ²)) × 100%
ts ≈ 4/(ζωn)  [for 2% criterion]
```

#### Frequency-Domain Analysis

**Stability Margins**:
- **Gain Margin (GM)**: |1/G(jωgc)| where ∠G(jωgc) = -180°
- **Phase Margin (PM)**: 180° + ∠G(jωpc) where |G(jωpc)| = 1

**Bandwidth**:
- **Closed-loop bandwidth**: Frequency where |T(jω)| = -3dB

#### Performance Metrics Exercise

Use the scope to measure actual performance:

```python
# Access performance metrics from enhanced mock connection
conn = EnhancedMockPyRPLConnection("demo.pyrpl.local")
metrics = conn.get_performance_metrics()

print(f"Rise time: {metrics['rise_time']:.2f}s")
print(f"Settling time: {metrics['settling_time']:.2f}s")
print(f"Overshoot: {metrics['overshoot_percent']:.1f}%")
print(f"Steady-state error: {metrics['steady_state_error']:.4f}V")

# Compare with theoretical predictions
theoretical_ts = 4/(damping_ratio * natural_frequency)
print(f"Theoretical settling time: {theoretical_ts:.2f}s")
```

#### Optimization Exercise

**Objective**: Minimize a weighted performance index
```
J = w1·tr + w2·ts + w3·Mp + w4·|ess|
```

Where w1, w2, w3, w4 are weighting factors based on application priorities.

**Method**:
1. Define weights based on application (fast response vs. stability)
2. Systematically vary PID gains
3. Calculate performance index for each setting
4. Find optimal parameters

**Mathematical Insight**: This becomes a constrained optimization problem that can be solved using gradient descent or other numerical methods.

### 4.2 Manual Tuning Exercise

**Starting point**: Load `stable_basic` scenario

#### Phase 1: Proportional Action
1. **Start with**: P=0.1, I=0, D=0
2. **Increase P gradually**: 0.2, 0.5, 1.0, 2.0
3. **Observe effects**:
   - Response speed
   - Overshoot
   - Stability

#### Phase 2: Add Integral Action
4. **Best P from Phase 1**: P=___
5. **Add integral**: I=0.01, 0.05, 0.1, 0.2
6. **Observe effects**:
   - Steady-state error elimination
   - Stability changes
   - Settling time

#### Phase 3: Add Derivative Action
7. **Best P,I from Phase 2**: P=___, I=___
8. **Add derivative**: D=0.01, 0.05, 0.1
9. **Observe effects**:
   - Overshoot reduction
   - Noise sensitivity
   - Stability margins

### 4.3 Performance Metrics

Use the scope to measure these performance indicators:

```python
# Access performance metrics
from pymodaq_plugins_pyrpl.utils.enhanced_mock_connection import EnhancedMockPyRPLConnection
conn = EnhancedMockPyRPLConnection("demo.pyrpl.local")
metrics = conn.get_performance_metrics()

print(f"Steady-state error: {metrics['steady_state_error']:.3f}V")
print(f"Settling time: {metrics['settling_time']:.1f}s")
print(f"Overshoot: {metrics['overshoot']:.1f}%")
```

**✅ Success Criteria:**
- You can systematically tune PID controllers
- You understand the effect of each PID term
- You can measure and optimize control performance

---

## Section 5: Advanced Scenarios

### 5.1 Noisy Environment Challenge

#### Scenario Setup
1. **Load noisy scenario**: `apply_demo_preset("noisy_derivative", pid_plugin)`
2. **Observe baseline noise** in voltage monitor
3. **Challenge**: Achieve good control despite noise

#### The Problem with Derivative Action
1. **Start with high D gain**: P=0.8, I=0.1, D=0.2
2. **Observe**: Derivative action amplifies noise
3. **Reduce D gain**: D=0.1, 0.05, 0.02
4. **Find optimal balance**: Control performance vs noise sensitivity

#### Advanced Filtering Techniques
The mock mode simulates realistic derivative filtering. Observe how:
- High D gains → Noisy control output
- Low D gains → Reduced noise but slower response
- The trade-off between performance and noise immunity

### 5.2 Integrating Process (Tank Level Simulation)

#### Understanding Integrating Processes
1. **Load integrating scenario**: `apply_demo_preset("integrating_level", pid_plugin)`
2. **Key characteristics**:
   - System output keeps changing until input = 0
   - Like filling a tank: flow rate determines level change rate
   - Common in chemical processes, thermal systems

#### PI vs PID for Integrating Processes
1. **Try PI control**: P=0.6, I=0.08, D=0.0
2. **Try PID control**: P=0.6, I=0.08, D=0.1
3. **Observe**: Derivative action is often unnecessary or harmful for integrating processes

#### Level Control Exercise
**Scenario**: Simulate controlling liquid level in a tank
1. **Setpoint changes**: 0.2V → 0.5V → 0.3V
2. **Observe**:
   - Smooth level changes
   - No steady-state error with integral action
   - Stable control without derivative

### 5.3 Disturbance Rejection

#### External Disturbances
The mock mode includes realistic process disturbances:
1. **Enable disturbances** (they're always present but subtle)
2. **Use PID to reject disturbances** automatically
3. **Observe**: Good PID tuning provides disturbance immunity

#### Feed-forward Control (Conceptual)
While the mock mode doesn't include feed-forward, understand the concept:
- **Feedback (PID)**: Reacts to errors after they occur
- **Feed-forward**: Predicts disturbances and compensates proactively
- **Combined**: Best performance for predictable disturbances

**✅ Success Criteria:**
- You understand advanced control challenges
- You can handle noisy environments
- You recognize different process types and their control requirements

---

## Section 6: Multi-Plugin Coordination

### 6.1 Complete Measurement System

Set up a comprehensive measurement system with multiple plugins:

#### Add Signal Generation
1. **Add ASG plugin**: **"DAQ_Move_PyRPL_ASG"**
2. **Configure**:
   - **RedPitaya Host**: `demo.pyrpl.local`
   - **Mock Mode**: `True`
   - **ASG Channel**: `asg0`
   - **Frequency**: `1000` Hz
   - **Amplitude**: `0.1` V

#### Add Lock-in Detection
3. **Add IQ plugin**: **"DAQ_0DViewer_PyRPL_IQ"**
4. **Configure**:
   - **RedPitaya Host**: `demo.pyrpl.local`
   - **Mock Mode**: `True`
   - **IQ Module**: `iq0`
   - **Frequency**: `1000` Hz (matching ASG)

### 6.2 Coordinated Simulation

All plugins share the same simulation state:
1. **ASG generates test signals**
2. **PID provides feedback control**
3. **IQ performs lock-in detection**
4. **Scope captures transients**
5. **Voltage monitor provides DC readings**

#### Advanced Exercise: Frequency Response
1. **Setup frequency sweep**:
   - ASG: Sweep frequency 100-10000 Hz
   - IQ: Track magnitude and phase
   - PID: Maintain system stability

2. **Measure control loop response**:
   - How does PID performance change with frequency?
   - What's the closed-loop bandwidth?

### 6.3 PyMoDAQ Scanning Integration

**Advanced Integration** (requires PyMoDAQ scanning extension):

```python
# Example scanning setup
from pymodaq.dashboard import DashBoard

dashboard = DashBoard()

# Add actuator: ASG frequency
dashboard.add_actuator('PyRPL_ASG_Freq', 'DAQ_Move_PyRPL_ASG')

# Add detectors: IQ magnitude + PID setpoint tracking
dashboard.add_detector('PyRPL_IQ_Magnitude', 'DAQ_0DViewer_PyRPL_IQ')
dashboard.add_detector('PyRPL_PID_Tracking', 'DAQ_0DViewer_PyRPL')

# Result: 2D scan (frequency vs IQ response) with PID stabilization
```

**✅ Success Criteria:**
- You can coordinate multiple PyRPL plugins
- You understand shared simulation state
- You see the potential for complex measurement scenarios

---

## Summary and Next Steps

### What You've Learned

✅ **PID Control Fundamentals**
- P, I, D terms and their individual effects
- Systematic tuning approaches (Ziegler-Nichols, manual)
- Performance metrics and trade-offs

✅ **Plant Dynamics Understanding**
- Different system types (stable, oscillatory, sluggish, integrating)
- How plant characteristics affect control difficulty
- Real-world process behavior simulation

✅ **Advanced Control Concepts**
- Noise handling and derivative filtering
- Disturbance rejection
- Multi-variable coordination

✅ **PyMoDAQ Integration**
- Professional measurement workflows
- Multi-plugin coordination
- Scanning and data acquisition

### Real Hardware Transition

When you're ready to use real Red Pitaya hardware:

1. **Hardware setup**: Follow [Installation Guide](INSTALLATION.md) hardware section
2. **Network configuration**: Set up Red Pitaya IP address
3. **Change mock_mode**: Set to `False` in all plugins
4. **Apply learned tuning**: Use knowledge from mock mode
5. **Safety first**: Start with low power and safe voltage ranges

### Advanced Learning Resources

- **PyMoDAQ Documentation**: https://pymodaq.readthedocs.io/
- **Control Theory**: "Feedback Control of Dynamic Systems" by Franklin, Powell, Emami
- **PID Tuning**: "PID Controllers: Theory, Design, and Tuning" by Åström & Hägglund
- **PyRPL Documentation**: https://pyrpl.readthedocs.io/

### Community and Support

- **PyMoDAQ Forum**: https://pymodaq.cnrs.fr/
- **Issues and Questions**: https://github.com/NeogiLabUNT/pymodaq_plugins_pyrpl/issues
- **Contributing**: See [Developer Guide](../README.rst#development-and-testing)

---

## Mathematical Glossary and Symbol Reference

### Control Theory Symbols
| Symbol | Definition | Units |
|--------|------------|-------|
| **s** | Complex frequency variable (Laplace domain) | rad/s |
| **G(s)** | Plant transfer function | - |
| **C(s)** | Controller transfer function | - |
| **T(s)** | Closed-loop transfer function | - |
| **K** | Process steady-state gain | - |
| **τ** | Process time constant | s |
| **θ** | Dead time / transport delay | s |
| **ζ** | Damping ratio | - |
| **ωn** | Natural frequency | rad/s |
| **ωu** | Ultimate frequency | rad/s |
| **Ku** | Ultimate gain | - |
| **Pu** | Ultimate period | s |

### PID Parameters
| Symbol | Definition | PyRPL Parameter | Units |
|--------|------------|-----------------|-------|
| **Kp** | Proportional gain | `pid.p` | - |
| **Ki** | Integral gain | `pid.i` | rad/s |
| **Kd** | Derivative gain | `pid.d` | s |
| **r(t)** | Reference setpoint | `pid.setpoint` | V |
| **y(t)** | Process variable | measured signal | V |
| **e(t)** | Error signal, e(t) = r(t) - y(t) | - | V |
| **u(t)** | Control signal | controller output | V |

### Performance Metrics
| Symbol | Definition | Typical Target |
|--------|------------|----------------|
| **tr** | Rise time (10% to 90%) | < 2τ |
| **ts** | Settling time (±2% criterion) | ≈ 4/(ζωn) |
| **Mp** | Maximum overshoot (%) | < 20% |
| **ess** | Steady-state error | ≈ 0 (with integral action) |
| **GM** | Gain margin | > 6 dB |
| **PM** | Phase margin | > 45° |

### Mathematical Concepts Checkpoint

Before proceeding to real hardware, verify your understanding:

**✅ Concept Check 1: Transfer Functions**
- Can you write the transfer function for a first-order system with time constant τ = 2s and gain K = 1.5?
- **Answer**: G(s) = 1.5/(2s + 1)

**✅ Concept Check 2: PID Controller**
- What is the transfer function of a PID controller with Kp = 0.6, Ki = 0.27, Kd = 0.15?
- **Answer**: C(s) = 0.6 + 0.27/s + 0.15s = (0.15s² + 0.6s + 0.27)/s

**✅ Concept Check 3: Stability Analysis**
- For a system with open-loop transfer function L(s) = C(s)G(s), what condition must be met for closed-loop stability?
- **Answer**: All poles of T(s) = L(s)/(1 + L(s)) must have negative real parts

**✅ Concept Check 4: Performance Trade-offs**
- If you increase the proportional gain Kp, what happens to rise time and overshoot?
- **Answer**: Rise time decreases (faster), overshoot increases (less stable)

**✅ Concept Check 5: Integral Action**
- Why does integral action eliminate steady-state error?
- **Answer**: The integral term continues to grow until error becomes zero, providing infinite gain at DC (s = 0)

---

## Advanced Mathematical Extensions

For users who want to explore beyond this tutorial:

### Frequency Response Analysis
- **Bode Plots**: Study the frequency response of your tuned controllers
- **Nyquist Stability**: Apply the Nyquist criterion for stability analysis
- **Robustness**: Analyze sensitivity and complementary sensitivity functions

### Modern Control Theory
- **State-Space Representation**: x'(t) = Ax(t) + Bu(t), y(t) = Cx(t)
- **Pole Placement**: Design controllers to place closed-loop poles at desired locations
- **Linear Quadratic Regulator (LQR)**: Optimal control theory applications

### Nonlinear Control
- **Gain Scheduling**: Vary PID parameters based on operating point
- **Adaptive Control**: Self-tuning controllers that adapt to plant changes
- **Robust Control**: H∞ and μ-synthesis for uncertain systems

### Digital Implementation
- **Discrete-Time PID**: Difference equations and z-transforms
- **Anti-Windup**: Prevent integral windup in saturated systems
- **Filter Design**: Derivative kick elimination and noise filtering

**Congratulations!** You've completed the comprehensive mathematical mock mode tutorial. You now have both the theoretical foundation and practical experience to tackle real-world control applications with the PyMoDAQ PyRPL plugin system, backed by rigorous control theory understanding.