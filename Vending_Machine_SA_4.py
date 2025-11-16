"""
TPRG 2131 - Project 1: Vending Machine
Sebastian Azevedo 100996889
Fall 2025

Version 4

Based on the started file. Modified with the help of Google Gemini.
"""


import FreeSimpleGUI as sg
from time import sleep 
import time as std_time 
import sys

# Hardware pin assignments:

DISPENSE_PIN = 17 # GPIO Pin for dispensing solenoid/moto
BUTTON = 21        # return change physical button: changed to GP21 for ease of wiring
                  
# classes for fake hardware, needed to run in PC mode.
class DummyHardware:
    """Dummy class for PC/testing mode."""
    def when_pressed(self, action): pass
    def close(self): pass
    
# --- RPi.GPIO PIN CLASSES ---
class DispenseOutput:
    """Controls the single dispensing GPIO pin."""
    def __init__(self, pin):
        global GPIO
        self.pin = pin
        
    def activate(self):
        """Sets pin HIGH for 1 second, then LOW."""
        global GPIO
        GPIO.output(self.pin, GPIO.HIGH)
        std_time.sleep(1.0) # 1 second HIGH duration
        GPIO.output(self.pin, GPIO.LOW)

    def close(self): 
        # No specific cleanup needed besides general GPIO.cleanup
        pass

class CustomButton:
    """Wraps RPi.GPIO event detection for the button."""
    def __init__(self, pin, pull_up_down):
        self.pin = pin
        self._when_pressed_callback = None

    def when_pressed(self, action):
        self._when_pressed_callback = action

    def close(self):
        pass

# Define classes globally (Required for pytest to mock inputs. uncomment next 3 lines to get pytest to run)
#CustomButton = None
#DispenseOutput = None
#GPIO = None 

# try to initialize hardware of RPi and default to PC mode if any step fails:
hardware_present = False
try:
    # Attempt to import RPi.GPIO; fails on PC
    import RPi.GPIO as GPIO
    
    # RPi.GPIO Configuration
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Set up pins
    # Button is set up with a pull-up to detect a FALLING edge (pull to ground/LOW)
    GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
    GPIO.setup(DISPENSE_PIN, GPIO.OUT, initial=GPIO.LOW)
    
    # Instantiate RPi.GPIO-wrapped objects
    key1 = CustomButton(BUTTON, GPIO.PUD_UP)
    dispenser = DispenseOutput(DISPENSE_PIN)
    
    hardware_present = True
    print(f"RPi detected and RPi.GPIO initialized!\n")
    
except ModuleNotFoundError:
    print("Not on a Raspberry Pi. Running in PC mode...\n")
    key1 = DummyHardware()
    dispenser = DummyHardware()
    
except Exception as e:
    print(f"GPIO initialization failed. Running in PC mode. Error: {e}")
    key1 = DummyHardware()
    dispenser = DummyHardware()

TESTING = True

def log(s):
    if TESTING:
        print(f"{s}\n")


class VendingMachine(object):
    PRODUCTS = {"diode": ("1N4001 diode", 75),
                "transistor": ("2N3904 BJT", 150),
                "cap": ("0.1uF Capacitor", 50),
                "res": ("10k Resistor", 5), 
                }
    
    INITIAL_STOCK = {"diode": 3, "transistor": 2, "cap": 4, "res": 5}

    COINS = {"5": ("5", 5), "10": ("10", 10),
             "25": ("25", 25),
             "100": ("100", 100), "200":("200", 200) 
             }

    def __init__(self):
        self.state = None      
        self.states = {}       
        self.event = ""        
        self.amount = 0        
        self.change_due = 0    
        self.stock = dict(self.INITIAL_STOCK)
        
        values = []
        for k in self.COINS:
            values.append(self.COINS[k][1])
        self.coin_values = sorted(values, reverse=True)
        log(f"Coin values: {self.coin_values}\n")

        # RPi.GPIO Button Setup: MODIFIED TO SET EVENT = 'RETURN'
        if hardware_present:
            def wrapped_button_action(channel):
                # When the physical button is pressed (pulled low), set the event to 'RETURN'
                self.event = 'RETURN' 
                log("Hardware RETURN button pressed (FALLING edge).")
            
            # NOTE: self.button_action is now only for the GUI button (if needed in a state)
            # The hardware action is handled directly by the callback setting self.event.
            
            GPIO.add_event_detect(
                BUTTON, 
                GPIO.FALLING, # Detects the change when the button is pressed (pulled LOW)
                callback=wrapped_button_action, 
                bouncetime=300
            )


    def add_state(self, state):
        self.states[state.name] = state

    def go_to_state(self, state_name):
        if self.state:
            log(f'Exiting {self.state.name}')
            self.state.on_exit(self)
        self.state = self.states[state_name]
        log(f'Entering {self.state.name}')
        self.state.on_entry(self)

    def update(self):
        if self.state:
            self.state.update(self)

    def add_coin(self, coin):
        self.amount += self.COINS[coin][1]

    # This method is for the GUI button (key='RETURN')
    def button_action(self):
        self.event = 'RETURN'

class State(object):
    _NAME = ""
    def __init__(self):
        pass
    @property
    def name(self):
        return self._NAME
    def on_entry(self, machine):
        pass
    def on_exit(self, machine):
        pass
    def update(self, machine):
        pass

class WaitingState(State):
    _NAME = "waiting"
    def on_entry(self, machine):
        print("Waiting for coins. Insert funds or press Return Coins.")

    def update(self, machine):
        if machine.event in machine.COINS:
            machine.add_coin(machine.event)
            machine.go_to_state('add_coins')
        elif machine.event == 'RETURN':
            # This handles the case where RETURN is pressed in Waiting State (change_due is 0)
            machine.event = "" 

class AddCoinsState(State):
    _NAME = "add_coins"
    def on_entry(self, machine):
        print(f"Current Balance: ${machine.amount / 100:.2f}. Select item or press RETURN COINS.\n")

    def update(self, machine):
        if machine.event == "RETURN":
            # This logic is triggered by BOTH the GUI button and the physical button
            machine.change_due = machine.amount  
            machine.amount = 0
            machine.go_to_state('count_change')
        elif machine.event in machine.COINS:
            machine.add_coin(machine.event)
            self.on_entry(machine) 
        
        elif isinstance(machine.event, str) and '_' in machine.event:
            product_key = machine.event.rsplit('_', 1)[0]
            
            if product_key in machine.PRODUCTS:
                price = machine.PRODUCTS[product_key][1]
                
                if machine.stock[product_key] <= 0:
                    print(f"{product_key.capitalize()} is out of stock.")
                
                elif machine.amount >= price:
                    machine.selected_button_key = machine.event 
                    machine.event = product_key
                    machine.go_to_state('deliver_product')
                else:
                    print(f"Insufficient funds. Need ${price / 100:.2f}.\n")
        
        machine.event = "" 

class DeliverProductState(State):
    _NAME = "deliver_product"
    
    def on_entry(self, machine):
        product_key = machine.event 
        
        if machine.stock.get(product_key, 0) > 0:
            machine.stock[product_key] -= 1
            
            product_name = machine.PRODUCTS[product_key][0]
            price = machine.PRODUCTS[product_key][1]
            
            machine.change_due = machine.amount - price
            machine.amount = 0
            
            print(f"Dispensing {product_name}...\n")
            sleep(0.5)
            print(f"{product_name} successfully dispensed! \n Stock remaining: {machine.stock[product_key]}\n")

            if hardware_present:
                log("Activating Dispense Pin (1 second HIGH)")
                dispenser.activate() # Simple HIGH/LOW call
                log("Dispense cycle complete.")
            
            machine.vend_successful = True

        else:
            print(f"Error: {product_key.capitalize()} is out of stock.\n Returning to AddCoins.\n")
            machine.vend_successful = False
            if hasattr(machine, 'selected_button_key'): del machine.selected_button_key 


    def on_exit(self, machine):
        pass 
        
    def update(self, machine):
        if machine.change_due > 0:
            machine.go_to_state('count_change')
        else:
            machine.go_to_state('waiting')

class CountChangeState(State):
    _NAME = "count_change"
    
    def on_entry(self, machine):
        print("Dispensing Change...\n")
        sleep(0.5)
        print(f"Change due: ${machine.change_due / 100:.2f}\n")
        log(f"Starting change return for: {machine.change_due} cents.\n")
        sleep(0.5)
    def update(self, machine):
        remaining_change = machine.change_due
        
        for coin_value in machine.coin_values:
            while remaining_change >= coin_value:
                print(f"Returning {coin_value} cents coin...\n")
                remaining_change -= coin_value
                sleep(0.6)  
        
        machine.change_due = 0 
        
        if remaining_change == 0:
            machine.go_to_state('waiting') 


# MAIN PROGRAM
if __name__ == "__main__":
    vending = VendingMachine()
    sg.theme_background_color('#1A335F') 

    # --- Coins Column Setup ---
    coin_col = []
    coin_col.append([sg.Text("Insert Coins", font=("Helvetica", 24), background_color='#2196F3', text_color='black', pad=(10, 10))])
    for key, (label, value) in VendingMachine.COINS.items():
        button_text = f"Insert {value}¢"
        button = sg.Button(button_text, key=key, size=(15, 2), font=("Helvetica", 18), button_color=('#1A335F', '#2196F3'))
        coin_col.append([button])

    # --- Products Column Setup ---
    select_col = []
    select_col.append([sg.Text("Select Item", font=("Helvetica", 24), background_color='#2196F3', text_color='black', pad=(10, 10))])
    
    for product_key, (name, price) in VendingMachine.PRODUCTS.items():
        stock_count = vending.INITIAL_STOCK.get(product_key, 0)
        product_buttons = []
        
        for i in range(stock_count):
            button_key = f"{product_key}_{i}"
            button_text = f"{name} #{i+1}\n(${price / 100:.2f})"
            frame = sg.Frame(
                title='', 
                layout=[[
                    sg.Button(button_text, key=button_key, size=(20, 2), font=("Helvetica", 12), button_color=('#1A335F', '#2196F3'))
                ]],
                key=f'FRAME_{button_key}', 
                border_width=0, 
                pad=(2, 2)
            )
            product_buttons.append(frame)
            
        select_col.append([sg.Text(f" {name} ", font=("Helvetica", 16), background_color='#0A1931', text_color='black')])
        select_col.append([sg.Column([product_buttons], element_justification='c')])


    # --- Layout Assembly ---
    layout = [ 
        [
            sg.Column(coin_col, vertical_alignment="TOP", element_justification='c', background_color='#0A1931', pad=(20, 20)),
            sg.VSeparator(),
            sg.Column(select_col, vertical_alignment="TOP", element_justification='c', background_color='#0A1931', pad=(20, 20), scrollable=True, expand_y=True)
        ],
        [sg.HorizontalSeparator()],
        [
            sg.Button("Return Coins", key='RETURN', size=(40, 1), font=("Helvetica", 18), button_color=('white', '#D32F2F'))
        ]
    ]
    window = sg.Window('SAYAL ELECTRONICS Vending Machine', layout, background_color='#0A1931', finalize=True)

    vending.add_state(WaitingState())
    vending.add_state(AddCoinsState())
    vending.add_state(DeliverProductState())
    vending.add_state(CountChangeState())

    vending.go_to_state('waiting')
    
    while True:
        event, values = window.read(timeout=10) 
                
        if event in (sg.WIN_CLOSED, 'Exit'):
            break
            
        # The key is to handle the hardware event here if it was set in the callback
        if vending.event == 'RETURN':
             # The hardware button set this event, now we process it
             pass 
        else:
             # Regular GUI event
             vending.event = event
             
        vending.update()
        
        if vending.state.name != 'deliver_product' and hasattr(vending, 'vend_successful') and vending.vend_successful:
            
            button_to_hide_key = vending.selected_button_key
            frame_to_hide = window[f'FRAME_{button_to_hide_key}']
            
            frame_to_hide.update(visible=False)
            
            vending.vend_successful = False
            del vending.selected_button_key
            
        vending.event = "" 

    window.close()
    
    # RPi.GPIO Cleanup
    if hardware_present:
        GPIO.cleanup()
    
    print("Normal exit")