# TPRG-2131-Project-1-Sebs-Vending-machine
repository for the Vending Machine File and test file, and associated Documentation

GUI is designed to simulate an electronics supply Vending machine wherein each item button on the GUI will dissapear when it is selected to simulate finite stock, which is can be set in the script.
Use of google gemini was needed to escape some problems, mainly asscociated with how to mock inputs to the main script to allow the pytest to execute. It send me down some bad rabbit holes, however.

The way the script allows its inputs to be mocked with dummy hardware seems to have a bad interaction with gpiozero for unknown reasons, the script requires 3 lines of global variable definition to be commented out to run on both RPi and PC. This will preclude the use pytest in this configuration however.

Use of the servo library from gpiozero proved difficult and easy to break; I could not get all three aspects of the project to run from the same configuration when using them. Instead I chose to use the micropython servo library and implement a servo driver on the Pi Pico W which can be triggered from the Pi400, it is a a work-around which might be transcended by time of projected demonstration. 




