import paho.mqtt.client as mqtt
from pymongo import MongoClient
import json, os
from datetime import datetime

# ── Connexion MongoDB ─────────────────────────────────────────────────────────
# Lit l'URL depuis la variable d'environnement Docker, sinon localhost par défaut
mongo = MongoClient(os.getenv("MONGO_URL", "mongodb://localhost:27017"))
db = mongo["serre"]          # base de données "serre" (créée auto si inexistante)
mesures = db["mesures"]      # collection pour les données capteurs
actions  = db["actions"]     # collection pour tracer les décisions automatiques

# ── Callback : appelé automatiquement à la connexion MQTT ────────────────────
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        # On s'abonne ici — jamais avant la connexion
        # Le # capture tous les sous-topics : serre/capteurs/temperature, etc.
        client.subscribe("serre/capteurs/#")
        print("Connecté à Mosquitto — abonné à serre/capteurs/#")
    else:
        print(f"Échec connexion MQTT, code : {rc}")

# ── Callback : appelé automatiquement à chaque message reçu ──────────────────
def on_message(client, userdata, msg):
    try:
        # Décode les octets bruts → string → dictionnaire Python
        data = json.loads(msg.payload.decode())

        # Enrichit le document avant stockage
        data["timestamp"] = datetime.utcnow().isoformat()
        data["topic"]     = msg.topic

        # Insertion directe JSON → MongoDB (zéro conversion nécessaire)
        mesures.insert_one(data)
        print(f"Mesure stockée : {data}")

        # ── Règles d'automatisation ───────────────────────────────────────────

        # Règle 1 : arrosage si humidité sol trop basse
        if data.get("humidite_sol", 100) < 30:
            client.publish("serre/actionneurs/vanne", '{"commande":"ON"}')
            actions.insert_one({
                "timestamp":   datetime.utcnow().isoformat(),
                "actionneur":  "vanne",
                "commande":    "ON",
                "declencheur": "auto — humidite_sol < 30%"
            })

        # Règle 2 : alerte si température trop haute
        if data.get("temperature", 0) > 35:
            client.publish("serre/alertes", '{"alerte":"temperature_haute"}')

        # Règle 3 : sécurité réservoir vide → bloquer l'arrosage
        if data.get("niveau_eau", 1) == 0:
            client.publish("serre/actionneurs/vanne", '{"commande":"OFF"}')
            print("SÉCURITÉ : réservoir vide — vanne forcée OFF")

    except json.JSONDecodeError:
        print(f"Message non-JSON reçu sur {msg.topic} : {msg.payload}")
    except Exception as e:
        print(f"Erreur inattendue : {e}")

# ── Initialisation et lancement ───────────────────────────────────────────────
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# MQTT_HOST = "mosquitto" dans Docker (nom du service), "localhost" en local
client.connect(os.getenv("MQTT_HOST", "localhost"), 1883)

# Boucle infinie : maintient la connexion et traite les messages entrants
client.loop_forever()
