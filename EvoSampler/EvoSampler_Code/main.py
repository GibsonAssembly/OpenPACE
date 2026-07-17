from machine import Pin, PWM, Timer
from picozero import Button
import utime

#Axis Limit: X, Y, Z=50

#---------------------------------------------------------------------------------------------

# Define the sampling parameters
sampling_duration = 2  # Time to remain at each well for sampling in Minutes (max ~30ml/h --> 4 minutes)
sampling_timer_interval = 60  # Interval between samplings in Minutes

position_A1 = [6, 30] # Define the XY-coordinates of well A1 (top-left corner) in mm [x_mm, y_mm]
well_spacing_mm = 9 # Define the distance between wells of well-plate
num_rows = 8 # Define the number of rows in the plate
num_cols = 12 # Define the number of columns in the plate 
park_position = [140, 30, 0]  # Define the park position, where head is parked in between samplings in mm [x_mm, y_mm, z_mm]

#---------------------------------------------------------------------------------------------

sampling_duration = sampling_duration*1000*60 ## convert to milliseconds
sampling_timer_interval = sampling_timer_interval*1000*60 ## convert to milliseconds

sampling_started = False
# Define the 3 buttons for inputs

Button_Left = Pin(6, Pin.IN, Pin.PULL_UP)
Button_Mid = Pin(4, Pin.IN, Pin.PULL_UP)
Button_Right = Pin(5, Pin.IN, Pin.PULL_UP)

# Define pins for direction, step, enable, and limit switches
ydir = Pin(10, Pin.OUT)
zdir = Pin(13, Pin.OUT)
xdir = Pin(7, Pin.OUT)

ystep_pwm = Pin(11, Pin.OUT)
zstep_pwm = Pin(14, Pin.OUT)
xstep_pwm = Pin(8, Pin.OUT)

yenable = Pin(12, Pin.OUT)
zenable = Pin(15, Pin.OUT)
xenable = Pin(9, Pin.OUT)

xstop = Pin(27, Pin.IN, Pin.PULL_UP)
ystop = Pin(26, Pin.IN, Pin.PULL_UP)
zstop = Pin(22, Pin.IN, Pin.PULL_UP)

step_pins = [xstep_pwm, ystep_pwm, zstep_pwm]
dir_pins = [xdir, ydir, zdir]
enable_pins = [xenable, yenable, zenable]
limit_switches = [xstop, ystop, zstop]

# Define the solenoid trigger pin
solenoid_trigger = Pin(3, Pin.OUT)  # Adjust the pin number as needed
solenoid_trigger.value(0)  # Set solenoid to inactive state (assuming active-low)
solenoid_timer = Timer(-1) ## # Define the timer as software timer

## Set Microstepps:
MS1_1 = Pin(16, Pin.OUT)
MS2_1 = Pin(17, Pin.OUT)

MS1_2 = Pin(18, Pin.OUT)
MS2_2 = Pin(19, Pin.OUT)

MS1_3 = Pin(20, Pin.OUT)
MS2_3 = Pin(21, Pin.OUT)

MS1_1.value(0)
MS2_1.value(0)

MS1_2.value(0)
MS2_2.value(0)

MS1_3.value(0)
MS2_3.value(0)

# Define homing directions for each axis (1 for positive direction, 0 for negative direction)
homing_directions = [1, 0, 0]  # Adjust these values based on your setup
# Set inversion flags for axes: True means “invert the commanded direction”
invert_axis = [True, False, False]  # Invert X, leave Y and Z as is ## in case an axis does not go to the correct direction.
# Define steps per millimeter for each axis
steps_per_mm = 800  # 200 steps per rotation * 8 microsteps / 2 mm per rotation
# Define maximum speed in mm/s
max_speed_mm_per_s = 50  # Adjust this value as needed
# Calculate minimum delay between steps (in microseconds) for the maximum speed
min_delay_us = int(1e6 / (max_speed_mm_per_s * steps_per_mm))
# Define maximum delay for acceleration and deceleration phases
max_delay_us = 1000  # This can be adjusted based on desired acceleration profile
# Global position tracker in steps
current_position_steps = [0, 0, 0]  # Assuming the home position is 0,0,0 steps
# Enable all motors
for enable in enable_pins:
    enable.value(0)

# Initialize well counter
current_well_index = 0

# List of wells (96 in total)
wells = [(row, col) for row in range(num_rows) for col in range(num_cols)]

def configure_pwm(pwm, frequency):
    pwm.freq(frequency)
    pwm.duty_u16(32768)  # 50% duty cycle

def disable_pwm(pwm):
    pwm.duty_u16(0)

def step_one(axis, delay_us=100):  # Adjust delay_us to match your motor and driver requirements
    step_pins[axis].high()  # Set PWM to high
    utime.sleep_us(delay_us)
    step_pins[axis].low()  # Set PWM to low
    utime.sleep_us(delay_us)

def home_axis(axis, homing_direction, initial_speed=100, final_speed=250):
    dir_pins[axis].value(homing_direction)  # Set direction towards the limit switch
    enable_pins[axis].value(0)  # Enable the axis prior to homing
    while limit_switches[axis].value() == 1:
        step_one(axis, delay_us=initial_speed)
    dir_pins[axis].value(not homing_direction)  # Move back a bit
    for _ in range(4000):
        step_one(axis, delay_us=initial_speed)
    dir_pins[axis].value(homing_direction)  # Re-home slowly
    while limit_switches[axis].value() == 1:
        step_one(axis, delay_us=final_speed)
    enable_pins[axis].value(1)  # Disable the axis after homing

def home_all(homing_directions):
    home_axis(2, homing_directions[2], initial_speed=100, final_speed=250)  # Home Z-axis first with increased speed
    for axis in [0, 1]:  # Home X and Y axes simultaneously
        home_axis(axis, homing_directions[axis], initial_speed=100, final_speed=250)

def move_axes(steps, directions):
    global current_position_steps
    max_steps = max(steps)

    # Set directions and enable each axis
    for axis in range(3):
        # If this axis is inverted, flip the commanded direction.
        commanded_direction = directions[axis]
        if invert_axis[axis]:
            commanded_direction = 0 if directions[axis] == 1 else 1
        dir_pins[axis].value(commanded_direction)
        enable_pins[axis].value(0)

    # Execute the stepping loop.
    for current_step in range(max_steps):
        for axis in range(3):
            if current_step < steps[axis]:
                step_one(axis)

    # Disable axes and update current_position_steps based on the actual move
    for axis in range(3):
        enable_pins[axis].value(1)
        # For inverted axes, reverse the update relative to the computed direction.
        if invert_axis[axis]:
            if directions[axis] == 1:
                # Although the computed direction was “positive,” we sent the opposite command,
                # so the actual physical move is to the right.
                current_position_steps[axis] += steps[axis]
            else:
                current_position_steps[axis] -= steps[axis]
        else:
            if directions[axis] == 1:
                current_position_steps[axis] += steps[axis]
            else:
                current_position_steps[axis] -= steps[axis]

def move_to_position(target_mm):
    global current_position_steps
    # Convert target positions from mm to steps
    target_steps = [int(target_mm[i] * steps_per_mm) for i in range(3)]
    print(f"Moving to positions: {target_mm} mm, which corresponds to {target_steps} steps")

    # Calculate the number of steps to move and directions
    steps_to_move = [abs(target_steps[axis] - current_position_steps[axis]) for axis in range(3)]
    directions = [1 if target_steps[axis] > current_position_steps[axis] else 0 for axis in range(3)]

    # Set directions and enable each axis
    for axis in range(3):
        dir_pins[axis].value(directions[axis])
        enable_pins[axis].value(0)  # Ensure the axis is enabled

    # Move the axes simultaneously
    move_axes(steps_to_move, directions)
    
    print(f"Current position (steps): {current_position_steps}")

# Function to move to a specific well position
def move_to_well(row, col, position_A1):
    """
    Move to the specified well position in the grid.
    
    Parameters:
    - row: Row index (0-7 for A-H)
    - col: Column index (0-11 for 1-12)
    - position_A1: Coordinates of well A1 as (x_mm, y_mm)
    """
    # Calculate the target position relative to A1
    target_x_mm = position_A1[0] + col * well_spacing_mm
    target_y_mm = position_A1[1] + row * well_spacing_mm

    # Move to the target position
    move_to_position([target_x_mm, target_y_mm, current_position_steps[2] / steps_per_mm])  # Z remains unchanged

def move_z_axis(distance_mm, direction):
    """
    Move the Z-axis by a specified distance.

    Parameters:
    - distance_mm: Distance to move in millimeters.
    - direction: Direction to move (0 for down, 1 for up).
    """
    # Calculate the number of steps required for the distance
    steps = int(distance_mm * steps_per_mm)
    
    # Set the direction
    dir_pins[2].value(direction)
    
    # Enable the Z-axis motor (if needed)
    enable_pins[2].value(0)
    
    # Move the Z-axis by the calculated number of steps
    for _ in range(steps):
        step_one(2, delay_us=200)
    
    # Optionally disable the Z-axis motor after movement
    enable_pins[2].value(1)

# Example usage to move Z-axis up and down by 40 mm
#move_z_axis(40, 1)  # Move up by 40 mm
#utime.sleep(1)      # Optional pause between movements
#move_z_axis(40, 0)  # Move down by 40 mm

# Function to trigger the solenoid
def trigger_solenoid(timer):
    global current_well_index
    sampling_running = False ## ensure that this function can only be called once
    # Check if all wells have been sampled
    if current_well_index >= len(wells):
        solenoid_timer.deinit()  # Stop the timer
        return

    # Calculate the current well's row and column by row-first order
    row = current_well_index % num_rows
    col = current_well_index // num_rows

    # Move to the current well
    move_to_well(row, col, position_A1)
    move_z_axis(18, 1) ## move into well
    # Trigger solenoid
    solenoid_trigger.value(1)  # Activate solenoid
    utime.sleep_ms(sampling_duration)  # Keep the solenoid activated for sampling_duration
    solenoid_trigger.value(0)  # Deactivate solenoid
    
    move_z_axis(32, 0) ## move out of well
    
    # Increment well index
    current_well_index += 1

    # Move back to park position
    move_to_position(park_position)
    
def start_sampling():
    global sampling_started
    if not sampling_started:
        print("Starting sampling...")
        sampling_started = True
        trigger_solenoid(None)  # Immediately trigger the first sample
        solenoid_timer.init(period=sampling_timer_interval, mode=Timer.PERIODIC, callback=trigger_solenoid)
        
def handle_button_press(pin):
    press_time = utime.ticks_ms()
    while not Button_Left.value():
        if utime.ticks_diff(utime.ticks_ms(), press_time) >= 2000:
            start_sampling()
            break
        
def stop_and_home():
    global sampling_started
    if sampling_started:
        print("Stopping operations and homing axes...")
        solenoid_timer.deinit()  # Stop the sampling timer
        sampling_started = False
        home_all(homing_directions)  # Home all axes

def handle_stop_button_press(pin):
    press_time = utime.ticks_ms()
    while not Button_Right.value():
        if utime.ticks_diff(utime.ticks_ms(), press_time) >= 2000:
            stop_and_home()
            break
        



home_all(homing_directions) ## Start with homing
Button_Left.irq(trigger=Pin.IRQ_FALLING, handler=handle_button_press)
#solenoid_timer.init(period=sampling_timer_interval, mode=Timer.PERIODIC, callback=trigger_solenoid)
Button_Right.irq(trigger=Pin.IRQ_FALLING, handler=handle_stop_button_press)

#while True:
#    pass




