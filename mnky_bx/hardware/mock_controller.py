#  mnky_bx/hardware/mock_controller.py 

"""
Mock Hardware Controller - Testing Without Physical Hardware

Implements BaseController with simulated behavior for development and testing.

Features:
- Simulated button presses (user-triggered or automated)
- Simulated motor movements
- Simulated LED states
- Configurable response delays
- Event recording for test verification
- Failure injection for error testing
"""

import threading
import time
import logging
import random
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime

from mnky_bx.hardware.arduino.base_controller import BaseController, ControllerStats

logger = logging.getLogger(__name__)


@dataclass
class MockEvent:
    """Record of simulated hardware event"""
    timestamp: datetime
    event_type: str  # "button_press", "led_on", "motor_move", etc.
    details: Dict = field(default_factory=dict)
    
    def __repr__(self):
        return (
            f"MockEvent({self.event_type}, "
            f"{self.details}, "
            f "{self.timestamp.strftime('%H:%M:%S')})"
        )


class MockHardwareController(BaseController):
    """
    Mock hardware controller for testing and development.
    
    Simulates all hardware functions without requiring physical devices.
    
    Features:
    - User-controlled button presses (via inject_button_press)
    - Automated button sequences
    - Simulated motor with configurable delays
    - LED state tracking
    - Event recording
    - Failure injection for error testing
    
    Usage:
        # Create mock controller
        controller = MockHardwareController({})
        controller.connect()
        
        # Setup button callback
        def on_button(button, event):
            print(f"Button {button} {event}")
        
        controller.start_button_listener(on_button)
        
        # Inject button press
        controller.inject_button_press("left")
        
        # Test motor
        controller.home_motor()
        controller.move_motor(5.0)
        
        # Check what happened
        events = controller.get_event_log()
        print(events)
    """
    
    def __init__(self, config: Dict = None):
        """
        Args:
            config: Optional configuration dict (usually empty for mock)
        """
        if config is None:
            config = {}
        
        super().__init__(config)
        
        # Motor simulation
        self.motor_position = 0.0
        self.motor_is_moving = False
        self.motor_max_position = config.get("motor_max_position", 10.0)
        self.motor_delay_ms = config.get("motor_delay_ms", 500)
        
        # LED simulation
        self.led_states = {"left": False, "right": False}
        
        # Button simulation
        self.button_thread = None
        self.button_listening = False
        self.stop_listening = threading.Event()
        self.button_queue: List[tuple] = []
        self.button_queue_lock = threading.Lock()
        
        # Event recording
        self.event_log: List[MockEvent] = []
        self.event_log_lock = threading.Lock()
        
        # Automated sequences
        self.button_sequences: List[List[tuple]] = []
        self.sequence_index = 0
        
        # Failure injection
        self.should_fail_next = False
        self.failure_mode = None
        
        logger.info("MockHardwareController initialized")
    
    # ===== Connection =====
    
    def connect(self) -> bool:
        """Connect (mock)"""
        self.is_connected = True
        self.is_running = True
        self._record_event("connect", {"status": "success"})
        logger.info("Mock hardware connected")
        return True
    
    def disconnect(self) -> bool:
        """Disconnect (mock)"""
        self.stop_button_listener()
        
        self.is_connected = False
        self.is_running = False
        self._record_event("disconnect", {"status": "success"})
        logger.info("Mock hardware disconnected")
        return True
    
    def health_check(self) -> Dict:
        """Check mock hardware health"""
        status = {
            "connected": self.is_connected,
            "buttons": True,
            "leds": True,
            "motor": True,
            "errors": []
        }
        
        if not self.is_connected:
            status["errors"].append("Not connected")
        
        self._record_event("health_check", status)
        return status
    
    # ===== Button Control =====
    
    def start_button_listener(self, callback: Callable) -> bool:
        """Start listening for button presses"""
        if self.button_listening:
            logger.warning("Button listener already running")
            return True
        
        self.button_callback = callback
        self.button_listening = True
        self.stop_listening.clear()
        
        # Start background thread
        self.button_thread = threading.Thread(
            target=self._button_listener_thread,
            daemon=True
        )
        self.button_thread.start()
        
        self._record_event("button_listener_start", {})
        logger.info("Button listener started")
        return True
    
    def stop_button_listener(self) -> bool:
        """Stop listening for button presses"""
        if not self.button_listening:
            return True
        
        self.button_listening = False
        self.stop_listening.set()
        
        # Wait for thread
        if self.button_thread and self.button_thread.is_alive():
            self.button_thread.join(timeout=1.0)
        
        self._record_event("button_listener_stop", {})
        logger.info("Button listener stopped")
        return True
    
    def _button_listener_thread(self):
        """Background thread for button listening"""
        logger.debug("Button listener thread started")
        
        while self.button_listening and not self.stop_listening.is_set():
            try:
                # Check for queued button presses
                with self.button_queue_lock:
                    if self.button_queue:
                        button, event = self.button_queue.pop(0)
                        
                        if self.button_callback:
                            self.button_callback(button, event)
                        
                        # Update statistics
                        self.stats.button_presses[button] = \
                            self.stats.button_presses.get(button, 0) + 1
                        
                        self._record_event(
                            "button_pressed",
                            {"button": button, "event": event}
                        )
                
                time.sleep(0.01)  # 10ms poll
            
            except Exception as e:
                logger.error(f"Error in button listener: {e}")
                time.sleep(0.1)
        
        logger.debug("Button listener thread ended")
    
    def inject_button_press(self, button: str, event: str = "pressed"):
        """
        Manually inject button press for testing.
        
        Args:
            button: "left" or "right"
            event: "pressed", "released", or "held"
        """
        if button not in ("left", "right"):
            logger.error(f"Invalid button: {button}")
            return
        
        with self.button_queue_lock:
            self.button_queue.append((button, event))
        
        logger.debug(f"Injected button press: {button} {event}")
    
    def inject_button_sequence(self, buttons: List[tuple]):
        """
        Inject sequence of button presses.
        
        Args:
            buttons: List of (button, event) tuples
            
        Example:
            controller.inject_button_sequence([
                ("left", "pressed"),
                ("left", "released"),
                ("right", "pressed"),
            ])
        """
        for button, event in buttons:
            self.inject_button_press(button, event)
        
        logger.debug(f"Injected sequence: {len(buttons)} button events")
    
    # ===== LED Control =====
    
    def set_led(self, led: str, state: bool) -> bool:
        """Set LED state"""
        if led.lower() not in ("left", "right", "both"):
            logger.error(f"Invalid LED: {led}")
            return False
        
        if led.lower() == "both":
            self.led_states["left"] = state
            self.led_states["right"] = state
        else:
            self.led_states[led.lower()] = state
        
        self._record_event("led_set", {"led": led, "state": state})
        logger.debug(f"LED {led} set to {state}")
        
        self.stats.total_commands += 1
        self.stats.successful_commands += 1
        
        return True
    
    def blink_led(self, led: str, count: int = 1, duration_ms: int = 100) -> bool:
        """Blink LED"""
        for i in range(count):
            self.set_led(led, True)
            time.sleep(duration_ms / 1000.0)
            self.set_led(led, False)
            time.sleep(duration_ms / 1000.0)
        
        self._record_event(
            "led_blink",
            {"led": led, "count": count, "duration_ms": duration_ms}
        )
        logger.debug(f"LED {led} blinked {count} times")
        
        return True
    
    def get_led_state(self, led: str) -> Optional[bool]:
        """Get current LED state"""
        return self.led_states.get(led.lower())
    
    # ===== Motor Control =====
    
    def home_motor(self, timeout_ms: int = 5000) -> bool:
        """Home motor"""
        if self.should_fail_next and self.failure_mode == "motor_home":
            self.should_fail_next = False
            self._record_event("motor_home_failed", {"timeout_ms": timeout_ms})
            logger.error("Motor home failed (injected failure)")
            return False
        
        logger.debug(f"Homing motor (simulated {self.motor_delay_ms}ms)")
        
        self.motor_is_moving = True
        time.sleep(self.motor_delay_ms / 1000.0)
        
        self.motor_position = 0.0
        self.motor_is_moving = False
        self.stats.motor_movements += 1
        
        self._record_event("motor_homed", {"position": 0.0})
        logger.info("Motor homed")
        
        return True
    
    def move_motor(
        self,
        position_mm: float,
        duration_ms: int = 500,
        wait: bool = True
    ) -> bool:
        """Move motor to position"""
        if self.should_fail_next and self.failure_mode == "motor_move":
            self.should_fail_next = False
            self._record_event(
                "motor_move_failed",
                {"position_mm": position_mm, "duration_ms": duration_ms}
            )
            logger.error("Motor move failed (injected failure)")
            return False
        
        # Validate position
        if position_mm < 0 or position_mm > self.motor_max_position:
            logger.error(f"Invalid position: {position_mm}")
            return False
        
        logger.debug(f"Moving motor to {position_mm}mm")
        
        self.motor_is_moving = True
        self.stats.motor_movements += 1
        
        if wait:
            time.sleep(self.motor_delay_ms / 1000.0)
            self.motor_position = position_mm
            self.motor_is_moving = False
        
        self._record_event(
            "motor_moved",
            {"position_mm": position_mm, "duration_ms": duration_ms, "wait": wait}
        )
        
        return True
    
    def get_motor_position(self) -> Optional[float]:
        """Get motor position"""
        return self.motor_position
    
    def is_motor_moving(self) -> bool:
        """Check if motor is moving"""
        return self.motor_is_moving
    
    # ===== Event Recording =====
    
    def _record_event(self, event_type: str, details: Dict = None):
        """Record an event"""
        event = MockEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            details=details or {}
        )
        
        with self.event_log_lock:
            self.event_log.append(event)
        
        logger.debug(f"Event recorded: {event}")
    
    def get_event_log(self) -> List[MockEvent]:
        """Get all recorded events"""
        with self.event_log_lock:
            return list(self.event_log)
    
    def get_events_by_type(self, event_type: str) -> List[MockEvent]:
        """Get events of specific type"""
        with self.event_log_lock:
            return [e for e in self.event_log if e.event_type == event_type]
    
    def clear_event_log(self):
        """Clear event log"""
        with self.event_log_lock:
            self.event_log.clear()
        
        logger.debug("Event log cleared")
    
    def print_event_log(self):
        """Print event log (for debugging)"""
        events = self.get_event_log()
        
        print("\n" + "=" * 80)
        print("MOCK HARDWARE EVENT LOG")
        print("=" * 80)
        
        for i, event in enumerate(events, 1):
            print(f"{i:3d}. {event.timestamp.strftime('%H:%M:%S.%f')[:-3]} | "
                  f"{event.event_type:20s} | {event.details}")
        
        print("=" * 80 + "\n")
    
    # ===== Failure Injection =====
    
    def inject_failure(self, failure_mode: str):
        """
        Inject failure on next operation.
        
        Args:
            failure_mode: "motor_home", "motor_move", etc.
        """
        self.should_fail_next = True
        self.failure_mode = failure_mode
        
        self._record_event("failure_injected", {"mode": failure_mode})
        logger.warning(f"Failure injected: {failure_mode}")
    
    def should_have_failed(self, failure_mode: str) -> bool:
        """
        Check if expected failure occurred.
        
        For test assertions:
            assert controller.should_have_failed("motor_home")
        """
        events = self.get_events_by_type(f"{failure_mode}_failed")
        return len(events) > 0

