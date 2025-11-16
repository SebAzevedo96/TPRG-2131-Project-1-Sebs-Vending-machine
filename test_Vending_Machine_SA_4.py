import pytest
from unittest.mock import MagicMock, patch

# Mock FreeSimpleGUI and hardware classes which are not needed for core logic tests
# ⭐ UPDATED IMPORT PATH to use the new file name: Vending_Machine_SA
with patch('Vending_Machine_SA.sg', new=MagicMock()), \
     patch('Vending_Machine_SA.PiGPIOFactory', new=MagicMock()), \
     patch('Vending_Machine_SA.Button', new=MagicMock()), \
     patch('Vending_Machine_SA.Servo', new=MagicMock()), \
     patch('Vending_Machine_SA.log', new=MagicMock()), \
     patch('Vending_Machine_SA.hardware_present', new=False):
    # Import the classes from the main script after mocking dependencies
    from Vending_Machine_SA import VendingMachine, WaitingState, AddCoinsState, DeliverProductState, CountChangeState

# Define the initial stock and prices for easy reference in tests
INITIAL_STOCK = {"diode": 3, "transistor": 2, "cap": 4, "res": 5}
PRICES = {"diode": 75, "transistor": 150, "cap": 50, "res": 5}

@pytest.fixture
def machine():
    """Fixture to create a fresh VendingMachine instance for each test."""
    # ⭐ UPDATED PATCH PATH
    with patch('Vending_Machine_SA.sleep', return_value=None):
        v = VendingMachine()
        # Ensure the machine starts in the waiting state
        v.add_state(WaitingState())
        v.add_state(AddCoinsState())
        v.add_state(DeliverProductState())
        v.add_state(CountChangeState())
        v.go_to_state('waiting')
        return v

## Test Initialization and States
# -----------------------------------

def test_initial_state_and_stock(machine):
    """Verify machine starts in the waiting state with correct initial stock."""
    assert machine.state.name == 'waiting'
    assert machine.amount == 0
    assert machine.change_due == 0
    assert machine.stock == INITIAL_STOCK

## Test Coin Insertion and Return
# -----------------------------------

def test_add_coins_and_transition(machine):
    """Test inserting a coin and transitioning from waiting to add_coins."""
    machine.event = '25' # Insert 25 cents
    machine.update()
    
    assert machine.amount == 25
    assert machine.state.name == 'add_coins'

def test_insert_multiple_coins(machine):
    """Test inserting multiple coins while in the add_coins state."""
    # Manually transition to add_coins state first
    machine.go_to_state('add_coins')
    
    machine.event = '100' # $1.00
    machine.update()
    machine.event = '5'   # $0.05
    machine.update()
    
    assert machine.amount == 105
    assert machine.state.name == 'add_coins'

def test_return_coins_from_add_coins(machine):
    """Test returning coins and transitioning to count_change."""
    machine.amount = 175 # $1.75 inserted
    machine.go_to_state('add_coins')
    
    machine.event = 'RETURN'
    machine.update()
    
    assert machine.amount == 0
    assert machine.change_due == 175
    assert machine.state.name == 'count_change'

def test_return_coins_from_count_change(machine):
    """Test state transition from count_change back to waiting."""
    machine.change_due = 175
    machine.go_to_state('count_change')
    
    # Update is called in count_change to dispense change and transition
    machine.update() 
    
    assert machine.change_due == 0
    assert machine.state.name == 'waiting'

## Test Product Vending Logic
# -----------------------------------

def test_successful_vend_with_exact_change(machine):
    """Test buying an item with exact change, leading to waiting state."""
    # Price: Diode is 75 cents
    machine.amount = 75
    machine.go_to_state('add_coins')
    
    # Use the specific button key for the first diode item
    machine.event = 'diode_0' 
    machine.update() 
    
    assert machine.state.name == 'deliver_product'
    
    # After delivery state runs
    machine.update() 
    
    assert machine.amount == 0
    assert machine.change_due == 0
    assert machine.stock['diode'] == 2 # Stock reduced
    assert machine.state.name == 'waiting'

def test_successful_vend_with_change_due(machine):
    """Test buying an item with excess money, leading to change state."""
    # Price: Capacitor (cap) is 50 cents
    machine.amount = 100 # $1.00 inserted
    machine.go_to_state('add_coins')
    
    # Use the specific button key for the first cap item
    machine.event = 'cap_0'
    machine.update() 
    
    assert machine.state.name == 'deliver_product'
    
    # After delivery state runs
    machine.update() 
    
    assert machine.amount == 0
    assert machine.change_due == 50 # 100 - 50 = 50 cents change
    assert machine.stock['cap'] == 3 # Stock reduced
    assert machine.state.name == 'count_change'
    
    # Finish dispensing change
    machine.update()
    assert machine.state.name == 'waiting'

def test_insufficient_funds(machine, caplog):
    """Test attempting to buy an item without enough money."""
    # Price: Transistor is 150 cents ($1.50)
    machine.amount = 100 # $1.00 inserted
    machine.go_to_state('add_coins')
    
    machine.event = 'transistor_0'
    machine.update()
    
    # Should remain in add_coins state
    assert machine.amount == 100
    assert machine.stock['transistor'] == 2 # Stock unchanged
    assert machine.state.name == 'add_coins'
    # Check console output for the error message
    assert "Insufficient funds." in caplog.text

def test_out_of_stock_item(machine, caplog):
    """Test attempting to buy an item that is out of stock."""
    # Manually zero out the stock for 'res' (10k Resistor)
    machine.stock['res'] = 0 
    machine.amount = 100 
    machine.go_to_state('add_coins')
    
    machine.event = 'res_0' # Try to buy
    machine.update()
    
    # Should remain in add_coins state
    assert machine.amount == 100
    assert machine.state.name == 'add_coins'
    # Check console output for the error message
    assert "Res is out of stock." in caplog.text

def test_button_action_return(machine):
    """Test the hardware button action (which acts as 'RETURN')."""
    machine.amount = 25
    machine.go_to_state('add_coins')
    
    # Simulate hardware button press
    machine.button_action() 
    
    # Since button_action calls update, the state change should occur immediately
    assert machine.amount == 0
    assert machine.change_due == 25
    assert machine.state.name == 'count_change'

# Run this file using the command: `pytest test_vending_machine.py`