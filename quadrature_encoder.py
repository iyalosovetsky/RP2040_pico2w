from machine import Pin
import time

class Encoder:
    """
    A class to read a quadrature encoder.
    It uses interrupts to track the encoder's position.
    """
    def __init__(self, pin_a, pin_b):
        """
        Initializes the encoder with the two pins it is connected to.
        :param pin_a: The GPIO pin number for channel A.
        :param pin_b: The GPIO pin number for channel B.
        """
        self.pin_a = Pin(pin_a, Pin.IN, Pin.PULL_UP)
        self.pin_b = Pin(pin_b, Pin.IN, Pin.PULL_UP)
        self._count = 0

        # Attach interrupts to both pins
        self.pin_a.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._irq_handler)
        self.pin_b.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._irq_handler)
        
        self.last_a = self.pin_a.value()
        self.last_b = self.pin_b.value()

    def _irq_handler(self, pin):
        """
        Interrupt service routine for encoder pins.
        This uses a simple table-based decoding method.
        """
        current_a = self.pin_a.value()
        current_b = self.pin_b.value()

        # Simple state-machine logic for quadrature decoding
        if current_a != self.last_a or current_b != self.last_b:
            if self.last_a == 0 and self.last_b == 0:
                if current_a == 1: self._count += 1 # CW
                if current_b == 1: self._count -= 1 # CCW
            elif self.last_a == 1 and self.last_b == 0:
                if current_b == 1: self._count += 1 # CW
                if current_a == 0: self._count -= 1 # CCW
            elif self.last_a == 1 and self.last_b == 1:
                if current_a == 0: self._count += 1 # CW
                if current_b == 0: self._count -= 1 # CCW
            elif self.last_a == 0 and self.last_b == 1:
                if current_b == 0: self._count += 1 # CW
                if current_a == 1: self._count -= 1 # CCW

            self.last_a = current_a
            self.last_b = current_b


    def value(self):
        """
        Returns the current encoder count.
        :return: The current count.
        """
        return self._count

    def reset(self):
        """
        Resets the encoder count to zero.
        """
        self._count = 0

# --- Example Usage ---
if __name__ == "__main__":
    # --- Configuration ---
    # Set the GPIO pins connected to the encoder's A and B channels.
    # IMPORTANT: Change these to the actual GPIO pins you are using.
    ENCODER_A_PIN = 14
    ENCODER_B_PIN = 15

    # Create an Encoder instance
    encoder = Encoder(ENCODER_A_PIN, ENCODER_B_PIN)

    print("Encoder reader started. Turn the encoder to see the count change.")
    print("Press Ctrl+C to stop.")

    last_known_count = 0
    try:
        while True:
            current_count = encoder.value()
            if current_count != last_known_count:
                print("Encoder count:", current_count)
                last_known_count = current_count
            time.sleep_ms(100)  # Sleep for a short time to reduce CPU usage
            
    except KeyboardInterrupt:
        print("Encoder reader stopped.")

