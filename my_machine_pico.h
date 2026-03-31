
#define BOARD_MY_MACHINE2      // Add my_machine_map.h before enabling this!

#ifndef USB_SERIAL_CDC
#define USB_SERIAL_CDC          1 // Serial communication via native USB.
#endif


// UART 0 
#define UART_TX_PIN 0
#define UART_RX_PIN 1



// UART 1 (Modbus)
//#define UART_1_TX_PIN 8
//#define UART_1_RX_PIN 9

#define UART_1_TX_PIN 4
#define UART_1_RX_PIN 5


 


/**/


//ig added for MPG
#define MPG_ENABLE           2 // Enable MPG interface. Requires serial port and one handshake pin unless
                                // KEYPAD_ENABLE is set to 2 when mode switching is done by the CMD_MPG_MODE_TOGGLE (0x8B)
                                // command character. Set both MPG_ENABLE and KEYPAD_ENABLE to 2 to use a handshake pin anyway.

#define SERIAL1_PORT 1 

//igo comment #define KEYPAD_ENABLE        2 // Set to 1 for I2C keypad, 2 for other input such as serial data. If KEYPAD_ENABLE is set to 2 
                                 // and MPG_ENABLE is uncommented then the serial stream is shared with the MPG.
#define VFD_ENABLE             0 // Set to 1 works or 2 for Huanyang VFD spindle. More here https://github.com/grblHAL/Plugins_spindle

#if VFD_ENABLE > 0
#define MODBUS_ENABLE          1 // Set to 1 for auto direction, 2 for direction signal on auxillary output pin.
#define MODBUS_BAUDRATE 2 // 9600
#define SPINDLE0_ENABLE         SPINDLE_HUANYANG1
#else // VFD_ENABLE == 0
#define MODBUS_ENABLE          0
#define SPINDLE_PORT                GPIO_OUTPUT
#define SPINDLE_ENABLE_PIN          AUXOUTPUT0_PIN //2
#define SPINDLE_PWM_PIN             AUXOUTPUT1_PIN //27
#define SPINDLE_DIRECTION_PIN       AUXOUTPUT2_PIN
#endif


#define COMPATIBILITY_LEVEL 2



//ig uncomment

#define PROBE_ENABLE              1 // Default enabled, remove comment to disable probe input.
#define PROBE_PIN             AUXINPUT0_PIN 