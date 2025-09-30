# Control Theory Foundations for PyMoDAQ PyRPL Plugin

This document provides the mathematical foundations underlying the PyMoDAQ PyRPL plugin functionality. It bridges theoretical control concepts with practical implementation, serving both as an educational resource and a comprehensive reference for advanced users.

## Mathematical Notation and Conventions

### Standard Notation
- **s**: Complex frequency variable (Laplace domain)
- **G(s)**: Plant transfer function
- **C(s)**: Controller transfer function
- **R(s)**: Reference/setpoint signal
- **Y(s)**: Plant output/process variable
- **E(s)**: Error signal, E(s) = R(s) - Y(s)
- **U(s)**: Control signal/controller output
- **τ**: Time constant
- **K**: Steady-state gain
- **θ**: Dead time/transport delay
- **ωc**: Critical frequency
- **Kc**: Critical gain

### PyRPL-Specific Variables
- **Kp, Ki, Kd**: Proportional, integral, derivative gains
- **Vin1, Vin2**: Red Pitaya analog inputs (±1V range)
- **Vout1, Vout2**: Red Pitaya analog outputs (±1V range)
- **fs**: Sampling frequency (125 MHz for Red Pitaya)

---

## Chapter 1: PID Control Mathematical Foundations

### 1.1 Classical PID Controller Derivation

The continuous-time PID controller implements the control law:

```
u(t) = Kp·e(t) + Ki·∫₀ᵗ e(τ)dτ + Kd·de(t)/dt
```

Where:
- **u(t)**: Controller output (control signal)
- **e(t)**: Error signal, e(t) = r(t) - y(t)
- **r(t)**: Reference setpoint
- **y(t)**: Process variable (plant output)

### 1.2 Laplace Transform of PID Controller

Taking the Laplace transform of the PID equation:

```
U(s) = Kp·E(s) + Ki·E(s)/s + Kd·s·E(s)
```

Factoring out E(s):

```
U(s) = E(s)·[Kp + Ki/s + Kd·s]
```

Therefore, the **PID controller transfer function** is:

```
C(s) = U(s)/E(s) = Kp + Ki/s + Kd·s = (Kp·s + Ki + Kd·s²)/s
```

### 1.3 Physical Interpretation of PID Terms

#### Proportional Term (Kp)
- **Mathematical Effect**: Provides immediate response proportional to current error
- **Frequency Response**: Constant gain across all frequencies
- **Physical Interpretation**: Like a spring - force proportional to displacement
- **PyRPL Implementation**: `pid.p` parameter, directly multiplies error signal

#### Integral Term (Ki)
- **Mathematical Effect**: Eliminates steady-state error by accumulating error over time
- **Frequency Response**: High gain at low frequencies (1/s response)
- **Physical Interpretation**: Like a fluid accumulator - fills until equilibrium reached
- **PyRPL Implementation**: `pid.i` parameter, digital integration with sampling period

#### Derivative Term (Kd)
- **Mathematical Effect**: Provides damping by responding to rate of error change
- **Frequency Response**: Increasing gain with frequency (s response)
- **Physical Interpretation**: Like a damper - opposes rapid changes
- **PyRPL Implementation**: `pid.d` parameter, digital differentiation with noise filtering

### 1.4 Closed-Loop Transfer Function Analysis

For a unity feedback system with plant G(s) and PID controller C(s):

**Closed-loop transfer function**:
```
T(s) = Y(s)/R(s) = C(s)·G(s)/(1 + C(s)·G(s))
```

**Characteristic equation** (denominator):
```
1 + C(s)·G(s) = 0
```

The stability of the closed-loop system depends on the roots of this characteristic equation.

### 1.5 PyMoDAQ Integration Example

```python
# PyMoDAQ PID plugin parameter mapping to control theory
pid_config = PIDConfiguration(
    setpoint=0.5,           # R(s) = 0.5/s (step input)
    p_gain=1.2,            # Kp = 1.2
    i_gain=0.15,           # Ki = 0.15 rad/s
    d_gain=0.05,           # Kd = 0.05 s
    input_channel=IN1,     # Process variable y(t) from Vin1
    output_channel=OUT1    # Control signal u(t) to Vout1
)

# The resulting controller transfer function becomes:
# C(s) = 1.2 + 0.15/s + 0.05·s
```

---

## Chapter 2: Plant Dynamics and System Modeling

### 2.1 First-Order Plus Dead-Time (FOPDT) Model

Many real-world processes can be approximated by the FOPDT model:

```
G(s) = K·e^(-θs)/(τs + 1)
```

Where:
- **K**: Steady-state process gain
- **τ**: Process time constant (time to reach 63.2% of final value)
- **θ**: Dead time (pure transport delay)

### 2.2 Derivation from Physical Systems

#### Step 1: Differential Equation
Consider a first-order linear system with dead time:

```
τ·dy(t)/dt + y(t) = K·u(t-θ)
```

#### Step 2: Laplace Transform
Taking the Laplace transform (assuming zero initial conditions):

```
τ·s·Y(s) + Y(s) = K·U(s)·e^(-θs)
```

#### Step 3: Solve for Transfer Function
```
Y(s)·(τs + 1) = K·U(s)·e^(-θs)

G(s) = Y(s)/U(s) = K·e^(-θs)/(τs + 1)
```

### 2.3 FOPDT Parameter Identification

#### Method 1: Step Response Analysis
1. Apply step input: u(t) = U₀ for t ≥ 0
2. Measure output response y(t)
3. Calculate parameters:
   - **K = Δy_final/Δu** (steady-state gain)
   - **θ**: Time when response begins
   - **τ**: Time constant from exponential curve fitting

#### Method 2: Process Reaction Curve
1. Find point where dy/dt is maximum
2. Draw tangent line at this point
3. **θ**: x-intercept of tangent line
4. **τ**: Time between tangent intercepts

### 2.4 PyRPL Mock Mode Implementation

```python
# Enhanced mock connection implements FOPDT simulation
class PlantParameters:
    def __init__(self):
        self.gain = 1.0          # K (process gain)
        self.time_constant = 2.0  # τ (seconds)
        self.dead_time = 0.1     # θ (seconds)

    def simulate_response(self, input_signal, dt):
        # Discrete-time implementation of FOPDT model
        # Uses finite difference approximation:
        # y[n] = (1-dt/τ)·y[n-1] + (K·dt/τ)·u[n-delay_samples]
        delay_samples = int(self.dead_time / dt)
        alpha = dt / self.time_constant
        y_new = (1 - alpha) * self.y_previous + alpha * self.gain * input_delayed
        return y_new
```

### 2.5 Mock Scenario Mathematical Models

#### Stable System
```
G(s) = 1.0·e^(-0.1s)/(2.0s + 1)
```
- Well-damped response, easy to control
- Suitable for learning basic PID concepts

#### Oscillatory System
```
G(s) = 2.0·e^(-0.05s)/(1.0s + 1)
```
- High gain, low time constant
- Tends to oscillate, requires careful tuning

#### Sluggish System
```
G(s) = 0.5·e^(-0.2s)/(5.0s + 1)
```
- Slow response, high time constant
- Demonstrates need for integral action

#### Integrating Process
```
G(s) = 0.8·e^(-0.1s)/s
```
- Self-integrating (like liquid level in tank)
- No steady-state without control input

---

## Chapter 3: PID Tuning Mathematics

### 3.1 Ziegler-Nichols Ultimate Gain Method

#### Mathematical Foundation
The Ziegler-Nichols method is based on finding the **ultimate gain (Ku)** and **ultimate period (Pu)** where the system exhibits sustained oscillation.

#### Step 1: Find Ultimate Gain
1. Set Ki = 0, Kd = 0 (P-only control)
2. Gradually increase Kp until system oscillates with constant amplitude
3. Record **Ku** (critical gain) and **Pu** (oscillation period)

#### Step 2: Calculate PID Parameters
```
Classical PID:
Kp = 0.6 × Ku
Ki = 2 × Kp / Pu = 1.2 × Ku / Pu
Kd = Kp × Pu / 8 = 0.075 × Ku × Pu

Some Overshoot PID:
Kp = 0.33 × Ku
Ki = 2 × Kp / Pu = 0.66 × Ku / Pu
Kd = Kp × Pu / 3 = 0.11 × Ku × Pu

No Overshoot PID:
Kp = 0.2 × Ku
Ki = 2 × Kp / Pu = 0.4 × Ku / Pu
Kd = Kp × Pu / 3 = 0.067 × Ku × Pu
```

### 3.2 Mathematical Derivation of Ziegler-Nichols Rules

#### Theoretical Foundation
The method assumes the process can be approximated as:
```
G(s) = K·e^(-Ls)/(Ts + 1)
```

At the ultimate gain, the Nyquist plot passes through the (-1, 0) point, giving:
```
Ku·G(jωu) = -1
```

Where ωu = 2π/Pu is the ultimate frequency.

#### Worked Example with PyRPL Mock Mode

Using the oscillatory scenario (K=2.0, τ=1.0s, θ=0.05s):

**Step 1**: Find Ultimate Gain
- Start with Kp = 0.1, increase gradually
- System oscillates at Ku ≈ 0.8, Pu ≈ 2.5s

**Step 2**: Calculate PID Parameters
```
Classical PID tuning:
Kp = 0.6 × 0.8 = 0.48
Ki = 1.2 × 0.8 / 2.5 = 0.384 rad/s
Kd = 0.075 × 0.8 × 2.5 = 0.15 s

# PyMoDAQ parameter implementation:
pid_config = PIDConfiguration(
    p_gain=0.48,
    i_gain=0.384,
    d_gain=0.15
)
```

### 3.3 Performance Metrics and Optimization

#### Time-Domain Specifications
- **Rise Time (tr)**: Time to reach 90% of final value
- **Settling Time (ts)**: Time to stay within ±2% of final value
- **Overshoot (Mp)**: Maximum overshoot as percentage of final value
- **Steady-State Error (ess)**: Final tracking error

#### Mathematical Relationships
For a second-order underdamped system:
```
Mp = exp(-ζπ/√(1-ζ²)) × 100%
tr ≈ (1.8/ωn) for ζ = 0.5
ts ≈ 4/(ζωn) for 2% criterion
```

Where ζ is damping ratio and ωn is natural frequency.

### 3.4 PyRPL Performance Monitoring Implementation

```python
# Performance metrics calculation in mock mode
class PerformanceMonitor:
    def calculate_metrics(self, response_data):
        final_value = response_data[-1]

        # Rise time (10% to 90%)
        val_10 = 0.1 * final_value
        val_90 = 0.9 * final_value
        t_10 = self.find_crossing_time(response_data, val_10)
        t_90 = self.find_crossing_time(response_data, val_90)
        rise_time = t_90 - t_10

        # Overshoot
        max_value = np.max(response_data)
        overshoot_percent = 100 * (max_value - final_value) / final_value

        # Settling time (±2% band)
        settling_band = 0.02 * final_value
        settling_time = self.find_settling_time(response_data, final_value, settling_band)

        return {
            'rise_time': rise_time,
            'overshoot_percent': overshoot_percent,
            'settling_time': settling_time,
            'steady_state_error': abs(setpoint - final_value)
        }
```

---

## Chapter 4: Signal Processing and Lock-in Amplification

### 4.1 Fourier Transform Foundations

#### Mathematical Definition
The Fourier Transform decomposes a signal into its frequency components:

```
X(ω) = ∫₋∞^∞ x(t)·e^(-jωt) dt
```

For digital signals (Red Pitaya implementation):
```
X[k] = Σₙ₌₀^(N-1) x[n]·e^(-j2πkn/N)
```

#### Physical Interpretation
- **Time Domain**: Signal amplitude vs time
- **Frequency Domain**: Signal power vs frequency
- **Lock-in Detection**: Extracts signal components at specific frequencies

### 4.2 Lock-in Amplifier Mathematical Principle

#### Signal Model
Consider a weak signal buried in noise:
```
s(t) = A·sin(ωref·t + φ) + n(t)
```

Where:
- **A**: Signal amplitude (to be measured)
- **ωref**: Reference frequency
- **φ**: Phase shift (to be measured)
- **n(t)**: Broadband noise

#### Mathematical Process

**Step 1: Reference Mixing**
Multiply input signal by reference signals:
```
I(t) = s(t) × cos(ωref·t)
Q(t) = s(t) × sin(ωref·t)
```

**Step 2: Expand the Product**
```
I(t) = A·sin(ωref·t + φ)·cos(ωref·t) + n(t)·cos(ωref·t)
     = (A/2)·[sin(2ωref·t + φ) + sin(φ)] + n(t)·cos(ωref·t)
```

**Step 3: Low-Pass Filtering**
After low-pass filtering to remove 2ωref terms:
```
I_filtered = (A/2)·sin(φ) = (A/2)·cos(π/2 - φ)
Q_filtered = (A/2)·cos(φ)
```

**Step 4: Calculate Magnitude and Phase**
```
Magnitude: R = √(I² + Q²) = A/2
Phase: φ = arctan(I/Q)
```

### 4.3 PyRPL IQ Module Implementation

The Red Pitaya implements this mathematically as:

```python
# IQ demodulation configuration
class IQConfiguration:
    def __init__(self):
        self.frequency = 1000.0      # ωref/(2π) in Hz
        self.bandwidth = 10.0        # Low-pass filter cutoff
        self.phase = 0.0            # Reference phase offset
        self.na_averages = 1        # Number of averages for noise reduction

    def calculate_iq_output(self, input_signal, ref_frequency):
        # Digital implementation of lock-in detection
        t = np.linspace(0, len(input_signal)/fs, len(input_signal))

        # Reference signals
        ref_i = np.cos(2 * np.pi * ref_frequency * t + self.phase)
        ref_q = np.sin(2 * np.pi * ref_frequency * t + self.phase)

        # Mixing
        i_mixed = input_signal * ref_i
        q_mixed = input_signal * ref_q

        # Low-pass filtering (digital implementation)
        i_filtered = self.low_pass_filter(i_mixed, self.bandwidth)
        q_filtered = self.low_pass_filter(q_mixed, self.bandwidth)

        # Calculate magnitude and phase
        magnitude = np.sqrt(i_filtered**2 + q_filtered**2)
        phase = np.arctan2(q_filtered, i_filtered) * 180/np.pi

        return magnitude, phase, i_filtered, q_filtered
```

### 4.4 Noise Analysis and Signal-to-Noise Ratio

#### Theoretical SNR Improvement
Lock-in amplification provides SNR improvement by:

```
SNR_improvement = √(B_noise / B_detection)
```

Where:
- **B_noise**: Noise bandwidth (typically full spectrum)
- **B_detection**: Detection bandwidth (lock-in filter bandwidth)

For broadband noise with bandwidth 1 MHz and detection bandwidth 10 Hz:
```
SNR_improvement = √(1×10⁶ / 10) = √10⁵ = 316 (50 dB improvement)
```

#### PyRPL Implementation Benefits
- **Hardware Implementation**: FPGA-based processing for real-time performance
- **Bandwidth Control**: Adjustable low-pass filter cutoff
- **Phase-Sensitive Detection**: Separate I/Q outputs for complete signal characterization
- **Integration with PID**: Can use lock-in output as PID input for advanced control

### 4.5 Practical Example: Weak Signal Recovery

```python
# Example: Detecting 1 μV signal in 100 mV noise using lock-in
signal_amplitude = 1e-6        # 1 μV signal
noise_amplitude = 100e-3       # 100 mV RMS noise
reference_freq = 1337.0        # Hz (unique frequency)

# Without lock-in: SNR = 1μV / 100mV = -100 dB
# With lock-in (10 Hz bandwidth from 1 MHz noise):
# SNR improvement = 50 dB
# Final SNR = -100 dB + 50 dB = -50 dB (detectable!)

iq_config = IQConfiguration(
    frequency=reference_freq,
    bandwidth=10.0,           # 10 Hz detection bandwidth
    na_averages=100          # Additional averaging for 20 dB improvement
)
# Total SNR = -100 + 50 + 20 = -30 dB (easily measurable)
```

---

## Chapter 5: Advanced Topics and Integration

### 5.1 Multi-Variable Control Systems

When using multiple PyRPL modules simultaneously, interaction effects become important:

#### MIMO System Representation
```
[Y₁(s)]   [G₁₁(s)  G₁₂(s)] [U₁(s)]
[Y₂(s)] = [G₂₁(s)  G₂₂(s)] [U₂(s)]
```

Where cross-coupling terms G₁₂(s) and G₂₁(s) represent interaction between loops.

### 5.2 Frequency Response Analysis

#### Bode Plot Interpretation
- **Magnitude Plot**: |G(jω)| vs log(ω)
- **Phase Plot**: ∠G(jω) vs log(ω)
- **Stability Margins**: Gain margin, phase margin from Bode plots

#### Critical Frequencies
- **Bandwidth**: Frequency where |G(jω)| = -3dB of DC gain
- **Crossover**: Frequency where |C(jω)G(jω)| = 0 dB
- **Unity Gain**: Frequency where loop gain magnitude = 1

### 5.3 Digital Implementation Considerations

#### Sampling and Aliasing
Red Pitaya operates at fs = 125 MHz, but practical control loops use much lower rates:

```
Nyquist Frequency: fN = fs/2 = 62.5 MHz
Control Bandwidth: Typically << 1 MHz for most applications
```

#### Digital PID Implementation
```python
# Discrete-time PID with bilinear transform
def digital_pid_output(error, dt):
    # Proportional term
    P_out = Kp * error

    # Integral term (trapezoidal integration)
    I_out += Ki * (error + error_prev) * dt / 2

    # Derivative term (filtered differentiation)
    D_out = Kd * (error - error_prev) / dt

    # Anti-windup for integral term
    if abs(I_out) > I_max:
        I_out = np.sign(I_out) * I_max

    return P_out + I_out + D_out
```

### 5.4 System Identification from Data

#### Frequency Response Estimation
```python
def estimate_plant_response(input_data, output_data, frequencies):
    """Estimate plant frequency response from I/O data"""
    # Use cross-correlation for frequency response
    H_est = []
    for freq in frequencies:
        # Cross power spectral density
        Pxy = np.mean(output_data * np.exp(-1j * 2 * np.pi * freq * t))
        # Auto power spectral density
        Pxx = np.mean(input_data * np.exp(-1j * 2 * np.pi * freq * t))

        # Transfer function estimate
        H_est.append(Pxy / Pxx)

    return np.array(H_est)
```

---

## Mathematical Appendix

### A.1 Laplace Transform Reference

| Function f(t) | Transform F(s) |
|---------------|----------------|
| δ(t) | 1 |
| 1 | 1/s |
| t | 1/s² |
| e^(-at) | 1/(s+a) |
| sin(ωt) | ω/(s²+ω²) |
| cos(ωt) | s/(s²+ω²) |
| te^(-at) | 1/(s+a)² |

### A.2 Control System Stability Criteria

#### Routh-Hurwitz Criterion
For stability, all coefficients in the first column of the Routh array must be positive.

#### Nyquist Stability Criterion
A closed-loop system is stable if the Nyquist plot of the open-loop transfer function does not encircle the (-1, 0) point.

### A.3 Performance Specifications Summary

| Metric | Definition | Typical Values |
|--------|------------|----------------|
| Rise Time | 10% to 90% of final value | < 2τ |
| Settling Time | Within ±2% of final value | ≈ 4/(ζωn) |
| Overshoot | Maximum overshoot % | < 20% |
| Phase Margin | Safety margin from instability | > 45° |
| Gain Margin | Gain safety margin | > 6 dB |

---

This mathematical foundation provides the theoretical understanding necessary to effectively use the PyMoDAQ PyRPL plugin for advanced control applications. Each concept is directly tied to plugin parameters and implementation details, bridging the gap between theory and practice.