# mnky_bx/ui/launcher_ui.py

"""
Launcher GUI - Main kiosk interface

Responsibilities:
- Display available experiments
- Display available subjects
- Allow experiment/subject selection
- Start experiment session
- Basic error handling
"""

import pygame
from pathlib import Path
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class Button:
    """Clickable button for GUI"""
    
    def __init__(
        self,
        x: int, y: int,
        width: int, height: int,
        text: str,
        callback: Callable = None,
        bg_color: tuple = (100, 100, 100),
        text_color: tuple = (255, 255, 255),
        hover_color: tuple = (150, 150, 150)
    ):
        """
        Args:
            x, y: Top-left position
            width, height: Dimensions
            text: Button label
            callback: Function to call on click
            bg_color: Normal background color (RGB)
            text_color: Text color (RGB)
            hover_color: Color when hovering
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.bg_color = bg_color
        self.text_color = text_color
        self.hover_color = hover_color
        self.is_hovered = False
    
    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        """Draw button on surface"""
        # Draw background
        color = self.hover_color if self.is_hovered else self.bg_color
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 2)  # Border
        
        # Draw text
        text_surface = font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)
    
    def check_hover(self, pos: tuple) -> bool:
        """Check if position is over button"""
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered
    
    def check_click(self, pos: tuple) -> bool:
        """Check if position is click on button"""
        if self.rect.collidepoint(pos) and self.callback:
            self.callback()
            return True
        return False


class ListItem:
    """Selectable list item"""
    
    def __init__(
        self,
        x: int, y: int,
        width: int, height: int,
        text: str,
        data: object = None,
        text_color: tuple = (255, 255, 255),
        bg_color: tuple = (50, 50, 50),
        selected_color: tuple = (0, 150, 255)
    ):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.data = data
        self.text_color = text_color
        self.bg_color = bg_color
        self.selected_color = selected_color
        self.is_selected = False
        self.is_hovered = False
    
    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        """Draw list item"""
        # Background
        color = self.selected_color if self.is_selected else self.bg_color
        pygame.draw.rect(surface, color, self.rect)
        
        # Border if hovered
        if self.is_hovered:
            pygame.draw.rect(surface, (100, 255, 100), self.rect, 2)
        
        # Text
        text_surface = font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(midleft=(self.rect.x + 10, self.rect.centery))
        surface.blit(text_surface, text_rect)
    
    def check_hover(self, pos: tuple) -> bool:
        """Check if hovering"""
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered
    
    def check_click(self, pos: tuple) -> bool:
        """Check if clicked"""
        if self.rect.collidepoint(pos):
            self.is_selected = not self.is_selected
            return True
        return False


class LauncherUI:
    """
    Main launcher GUI.
    
    Workflow:
    1. Discover experiments and subjects
    2. User selects experiment and subject
    3. User clicks "Start" button
    4. Session is initialized and experiment runs
    
    Usage:
        launcher = LauncherUI(kiosk_manager)
        experiment, subject, session_path = launcher.run()
    """
    
    def __init__(
        self,
        kiosk_manager,
        screen_width: int = 1920,
        screen_height: int = 1080
    ):
        """
        Args:
            kiosk_manager: KioskManager instance
            screen_width: Display width in pixels
            screen_height: Display height in pixels
        """
        self.kiosk_manager = kiosk_manager
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Colors
        self.bg_color = (30, 30, 30)
        self.fg_color = (255, 255, 255)
        self.accent_color = (0, 150, 200)
        
        # Display setup
        pygame.init()
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("mnky_bx Launcher")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        
        # State
        self.selected_experiment = None
        self.selected_subject = None
        self.state = "main_menu"  # main_menu, select_experiment, select_subject
        
        # UI elements
        self.buttons = []
        self.experiment_items = []
        self.subject_items = []
        
        # Load data
        self.experiments = self.kiosk_manager.list_experiments()
        self.subjects = self.kiosk_manager.list_subjects()
        
        logger.info(
            f"LauncherUI initialized: "
            f"{len(self.experiments)} experiments, "
            f"{len(self.subjects)} subjects"
        )
    
    def setup_main_menu(self):
        """Setup main menu state"""
        self.buttons = []
        
        # Start button
        self.buttons.append(Button(
            x=self.screen_width // 2 - 150,
            y=self.screen_height // 2 - 100,
            width=300, height=80,
            text="Start Experiment",
            callback=self._on_start_clicked,
            bg_color=self.accent_color
        ))
        
        # New Subject button
        self.buttons.append(Button(
            x=self.screen_width // 2 - 150,
            y=self.screen_height // 2 + 50,
            width=300, height=80,
            text="Add Subject",
            callback=self._on_add_subject_clicked
        ))
        
        # Settings button
        self.buttons.append(Button(
            x=self.screen_width // 2 - 150,
            y=self.screen_height // 2 + 200,
            width=300, height=80,
            text="Settings",
            callback=self._on_settings_clicked
        ))
        
        # Quit button
        self.buttons.append(Button(
            x=self.screen_width // 2 - 150,
            y=self.screen_height // 2 + 350,
            width=300, height=80,
            text="Quit",
            callback=self._on_quit_clicked
        ))
    
    def setup_experiment_selection(self):
        """Setup experiment selection state"""
        self.experiment_items = []
        
        item_height = 80
        item_width = self.screen_width - 100
        start_y = 200
        
        for i, experiment in enumerate(self.experiments):
            y = start_y + (i * item_height)
            item = ListItem(
                x=50, y=y,
                width=item_width, height=item_height - 10,
                text=f"{experiment.name}: {experiment.get_description()}",
                data=experiment
            )
            self.experiment_items.append(item)
    
    def setup_subject_selection(self):
        """Setup subject selection state"""
        self.subject_items = []
        
        item_height = 80
        item_width = self.screen_width - 100
        start_y = 200
        
        for i, subject in enumerate(self.subjects):
            y = start_y + (i * item_height)
            metadata = subject.metadata
            label = (
                f"{subject.subject_id} | "
                f"Species: {metadata.get('species', '?')} | "
                f"Weight: {metadata.get('weight_kg', 0)}kg"
            )
            item = ListItem(
                x=50, y=y,
                width=item_width, height=item_height - 10,
                text=label,
                data=subject
            )
            self.subject_items.append(item)
    
    def _on_start_clicked(self):
        """Handle start button click"""
        if self.selected_experiment and self.selected_subject:
            self.state = "ready_to_start"
        else:
            self.state = "select_experiment"
    
    def _on_add_subject_clicked(self):
        """Handle add subject button click"""
        self.state = "add_subject"
    
    def _on_settings_clicked(self):
        """Handle settings button click"""
        logger.info("Settings not yet implemented")
    
    def _on_quit_clicked(self):
        """Handle quit button click"""
        self.state = "quit"
    
    def draw_main_menu(self):
        """Draw main menu"""
        self.screen.fill(self.bg_color)
        
        # Title
        title = self.font_large.render("mnky_bx Kiosk", True, self.fg_color)
        title_rect = title.get_rect(
            centerx=self.screen_width // 2,
            y=50
        )
        self.screen.blit(title, title_rect)
        
        # Subtitle
        subtitle = self.font_small.render(
            f"Kiosk: {self.kiosk_manager.kiosk_id}",
            True,
            (150, 150, 150)
        )
        subtitle_rect = subtitle.get_rect(
            centerx=self.screen_width // 2,
            y=120
        )
        self.screen.blit(subtitle, subtitle_rect)
        
        # Draw buttons
        for button in self.buttons:
            button.draw(self.screen, self.font_medium)
        
        pygame.display.flip()
    
    def draw_experiment_selection(self):
        """Draw experiment selection screen"""
        self.screen.fill(self.bg_color)
        
        # Title
        title = self.font_large.render("Select Experiment", True, self.fg_color)
        title_rect = title.get_rect(
            centerx=self.screen_width // 2,
            y=50
        )
        self.screen.blit(title, title_rect)
        
        # Experiments list
        for item in self.experiment_items:
            item.draw(self.screen, self.font_small)
        
        # Back button
        back_button = Button(
            x=50, y=self.screen_height - 100,
            width=200, height=80,
            text="Back",
            callback=self._on_back_clicked
        )
        back_button.draw(self.screen, self.font_medium)
        
        # Next button
        next_button = Button(
            x=self.screen_width - 250, y=self.screen_height - 100,
            width=200, height=80,
            text="Next" if self.selected_experiment else "Select First",
            callback=self._on_next_clicked if self.selected_experiment else None
        )
        next_button.draw(self.screen, self.font_medium)
        
        pygame.display.flip()
    
    def draw_subject_selection(self):
        """Draw subject selection screen"""
        self.screen.fill(self.bg_color)
        
        # Title
        title = self.font_large.render(
            f"Select Subject for {self.selected_experiment.name}",
            True,
            self.fg_color
        )
        title_rect = title.get_rect(
            centerx=self.screen_width // 2,
            y=50
        )
        self.screen.blit(title, title_rect)
        
        # Subjects list
        for item in self.subject_items:
            item.draw(self.screen, self.font_small)
        
        # Back button
        back_button = Button(
            x=50, y=self.screen_height - 100,
            width=200, height=80,
            text="Back",
            callback=self._on_back_clicked
        )
        back_button.draw(self.screen, self.font_medium)
        
        # Start button
        start_button = Button(
            x=self.screen_width - 250, y=self.screen_height - 100,
            width=200, height=80,
            text="Start" if self.selected_subject else "Select First",
            callback=self._on_start_session if self.selected_subject else None
        )
        start_button.draw(self.screen, self.font_medium)
        
        pygame.display.flip()
    
    def _on_back_clicked(self):
        """Go back to previous state"""
        if self.state == "select_experiment":
            self.state = "main_menu"
        elif self.state == "select_subject":
            self.state = "select_experiment"
            self.selected_experiment = None
    
    def _on_next_clicked(self):
        """Proceed to next state"""
        if self.state == "select_experiment" and self.selected_experiment:
            self.state = "select_subject"
    
    def _on_start_session(self):
        """Start the experiment session"""
        if self.selected_experiment and self.selected_subject:
            self.state = "ready_to_start"
    
    def handle_events(self):
        """Handle mouse and keyboard events"""
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.state = "quit"
                return
            
            if event.type == pygame.MOUSEMOTION:
                # Update hover states
                if self.state == "main_menu":
                    for button in self.buttons:
                        button.check_hover(mouse_pos)
                elif self.state == "select_experiment":
                    for item in self.experiment_items:
                        item.check_hover(mouse_pos)
                elif self.state == "select_subject":
                    for item in self.subject_items:
                        item.check_hover(mouse_pos)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    if self.state == "main_menu":
                        for button in self.buttons:
                            if button.check_click(mouse_pos):
                                break
                    
                    elif self.state == "select_experiment":
                        # Deselect all, then select clicked
                        for item in self.experiment_items:
                            if item.check_click(mouse_pos):
                                for other in self.experiment_items:
                                    if other != item:
                                        other.is_selected = False
                                self.selected_experiment = item.data
                        
                        # Back button
                        if 50 <= mouse_pos[0] <= 250:
                            if self.screen_height - 100 <= mouse_pos[1] <= self.screen_height:
                                self._on_back_clicked()
                        
                        # Next button
                        if self.screen_width - 250 <= mouse_pos[0] <= self.screen_width:
                            if self.screen_height - 100 <= mouse_pos[1] <= self.screen_height:
                                self._on_next_clicked()
                    
                    elif self.state == "select_subject":
                        # Deselect all, then select clicked
                        for item in self.subject_items:
                            if item.check_click(mouse_pos):
                                for other in self.subject_items:
                                    if other != item:
                                        other.is_selected = False
                                self.selected_subject = item.data
                        
                        # Back button
                        if 50 <= mouse_pos[0] <= 250:
                            if self.screen_height - 100 <= mouse_pos[1] <= self.screen_height:
                                self._on_back_clicked()
                        
                        # Start button
                        if self.screen_width - 250 <= mouse_pos[0] <= self.screen_width:
                            if self.screen_height - 100 <= mouse_pos[1] <= self.screen_height:
                                self._on_start_session()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state != "main_menu":
                        self._on_back_clicked()
                    else:
                        self.state = "quit"
    
    def run(self):
        """
        Main launcher loop.
        
        Returns:
            (experiment, subject, session_path) when session started
            or (None, None, None) if quit
        """
        self.state = "main_menu"
        self.setup_main_menu()
        
        running = True
        
        while running:
            self.handle_events()
            
            # Draw current state
            if self.state == "main_menu":
                self.draw_main_menu()
            
            elif self.state == "select_experiment":
                if not self.experiment_items:
                    self.setup_experiment_selection()
                self.draw_experiment_selection()
            
            elif self.state == "select_subject":
                if not self.subject_items:
                    self.setup_subject_selection()
                self.draw_subject_selection()
            
            elif self.state == "ready_to_start":
                # Initialize session and return
                try:
                    session_path = self.kiosk_manager.initialize_session(
                        subject_id=self.selected_subject.subject_id,
                        experiment_name=self.selected_experiment.name
                    )
                    
                    pygame.quit()
                    
                    return (
                        self.selected_experiment,
                        self.selected_subject,
                        session_path
                    )
                
                except Exception as e:
                    logger.error(f"Error starting session: {e}")
                    self.state = "main_menu"
            
            elif self.state == "quit":
                running = False
            
            self.clock.tick(60)  # 60 FPS
        
        pygame.quit()
        return (None, None, None)