from datetime import datetime, timedelta

class AutomationController:
    """
    Logique d'automatisation du CyberGarden.
    """

    def __init__(
        self,
        soil_threshold=35.0,
        air_humidity_threshold=75.0,
        air_humidity_min_threshold=40.0,
        temperature_threshold=28.0,
        watering_duration_seconds=5,
        cooldown_minutes=10,
        min_water_distance_cm=18.0,
    ):
        self.soil_threshold = soil_threshold
        self.air_humidity_threshold = air_humidity_threshold
        self.temperature_threshold = temperature_threshold
        self.air_humidity_min_threshold = air_humidity_min_threshold

        self.watering_duration_seconds = watering_duration_seconds
        self.cooldown_minutes = cooldown_minutes
        self.min_water_distance_cm = min_water_distance_cm

        self.valve_state = 0
        self.fan_state = 0

        # --- NEW: Manual Override Flags ---
        self.valve_manual_override = False
        self.fan_manual_override = False

        self.auto_suspended_until = datetime.now()
        self.valve_close_time = None

    def handle_manual_command(self, target, state):
        """
        Gère l'override manuel depuis le dashboard.
        """
        now = datetime.now()
        
        if target == "valve":
            self.valve_state = state
            if state == 1:
                self.valve_manual_override = True
                self.valve_close_time = None # Empêche la fermeture auto après 5s
            else:
                self.valve_manual_override = False
                # Cooldown pour éviter que l'auto ne le rallume immédiatement
                self.auto_suspended_until = now + timedelta(minutes=self.cooldown_minutes)
                
        elif target == "fan":
            self.fan_state = state
            if state == 1:
                self.fan_manual_override = True
            else:
                self.fan_manual_override = False

    def process_sensor_data(self, data):
        """Analyse les capteurs et génère les commandes automatiques."""
        commands = []
        now = datetime.now()

        temperature = float(data.get("temperature", 0))
        air_humidity = float(data.get("humidite", 0))
        soil_humidity = float(data.get("humidite_sol", 100))
        water_distance = float(data.get("distance", 999))
        water_too_low = water_distance > self.min_water_distance_cm

        # ---------------------------------------------------------
        # 1. GESTION VANNE (ARROSAGE)
        # ---------------------------------------------------------
        if not self.valve_manual_override:
            # Fermeture automatique après durée d'arrosage
            if self.valve_state == 1 and self.valve_close_time is not None:
                if now >= self.valve_close_time:
                    self.valve_state = 0
                    self.valve_close_time = None
                    self.auto_suspended_until = now + timedelta(minutes=self.cooldown_minutes)
                    commands.append({"target": "valve", "state": 0, "reason": "Watering duration reached"})

            # Déclenchement automatique
            if now >= self.auto_suspended_until and self.valve_state == 0:
                if water_too_low:
                    commands.append({"target": "alert", "state": 1, "reason": f"Water level low: {water_distance}cm"})
                elif soil_humidity < self.soil_threshold or air_humidity < self.air_humidity_min_threshold:
                    self.valve_state = 1
                    self.valve_close_time = now + timedelta(seconds=self.watering_duration_seconds)
                    commands.append({"target": "valve", "state": 1, "reason": f"Soil dry ({soil_humidity}%)"})

        # ---------------------------------------------------------
        # 2. GESTION VENTILATEUR
        # ---------------------------------------------------------
        if not self.fan_manual_override:
            fan_required = (air_humidity > self.air_humidity_threshold or temperature > self.temperature_threshold)
            requested_fan_state = 1 if fan_required else 0

            if requested_fan_state != self.fan_state:
                self.fan_state = requested_fan_state
                action_text = "ON" if requested_fan_state == 1 else "OFF"
                reason = f"Fan {action_text}, humidity={air_humidity}%, temp={temperature}°C"
                commands.append({"target": "fan", "state": requested_fan_state, "reason": reason})

        return commands

    def suspend_auto_watering(self):
        self.auto_suspended_until = datetime.now() + timedelta(minutes=self.cooldown_minutes)