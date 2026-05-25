# CyberGarden 

**Projet de serre autonome, connectée et automatisée** - *Réalisé par l'Équipe 6 (CPE-LYON)*

Le projet **CyberGarden** part d'un constat simple : la majorité des étudiants ou citadins souhaitent végétaliser leur intérieur, mais manquent de temps et de connaissances botaniques. L'objectif de ce projet est de concevoir une mini-serre autonome capable de pallier ces manques grâce à l'automatisation, un système de sécurité hydraulique innovant, et la supervision à distance via le Cloud.

---

## Fonctionnalités Principales

* **Acquisition multi-physique haute fréquence :** Surveillance exhaustive de l'environnement (température, humidité de l'air, luminosité, humidité du sol, niveau du réservoir d'eau).
* **Communication Hybride (Edge-to-Cloud) :** Transmission fiable des données sans fil via Bluetooth en local, puis relais vers le Cloud (AWS) via un tunnel MQTT sécurisé.
* **Historisation des données (Time-Series) :** Sauvegarde et structuration de l'historique des capteurs dans une base de données NoSQL (MongoDB) pour analyse des tendances.
* **Tableau de bord dynamique (IHM) :** Application Web "From Scratch" (Vanilla JS/HTML/CSS) permettant la Data-Visualisation (Chart.js), la personnalisation des seuils d'alerte, et le forçage manuel des actionneurs (arrosage, ventilation).
* **Asservissement "Fail-Safe" et Gravitaire :** Irrigation par pression hydrostatique (sans pompe) contrôlée par une électrovanne normalement fermée (NC) pour éviter toute inondation en cas de coupure de courant.

---

## Architecture du Système

Le flux de données bidirectionnel est structuré ainsi :
**Capteurs ➔ STM32 ➔ Bluetooth ➔ Raspberry Pi (Edge Gateway) ➔ MQTT ➔ AWS (Cloud) ➔ IHM Web**

1. **Acquisition (STM32F303) :** Le microcontrôleur collecte les données, gère la conversion analogique/numérique, pilote les relais (isolation galvanique) et sérialise les données en trames JSON.
2. **Réseau Local (Raspberry Pi 3B) :** Agit comme passerelle Edge. Conteneurisé via Docker, il intercepte les trames Bluetooth via un script Python et les publie sur le broker MQTT. L'outil *AutomationController* gère la logique de décision locale (cooldown, sécurité).
3. **Cloud (AWS EC2) :** Héberge le broker Mosquitto distant, la base de données MongoDB, et une API REST (FastAPI) pour l'exposition des historiques et la réception des commandes.
4. **Frontend (Web) :** Application structurée en MVC, communiquant avec l'API Cloud de manière asynchrone pour afficher l'état de la plante et relayer les commandes de l'utilisateur.

---

## Technologies et Matériel

### Logiciel & Réseau

* **Embarqué :** C (STM32CubeIDE, HAL)
* **Edge/Scripting :** Python, Docker & Docker Compose
* **Réseau/IoT :** Bluetooth (SPP), MQTT (Mosquitto), API REST (FastAPI)
* **Base de données :** MongoDB (Time-Series)
* **Frontend :** HTML5, CSS3 (Variables natives), Vanilla JavaScript (MVC, Fetch API), Chart.js
* **Modélisation 3D :** Autodesk Fusion 360

### Matériel Électronique & Mécanique

* **Microcontrôleur :** STM32F303 Discovery
* **Passerelle :** Raspberry Pi 3B
* **Capteurs :** DHT11 (Temp/Humidité air), HW-101 (Humidité sol capacitif), BPW21R + LM358 (Photodiode), HC-SR04 (Ultrasons niveau d'eau).
* **Actionneurs :** Électrovanne 12V, Ventilateur 12V PC, Relais (SRD-05VDC-SL-C & Axicom D2n), MOSFET BS170.
* **Connectivité :** Module Bluetooth RN42XVP-I

---

## L'équipe et Répartition des Tâches

* **Pierre Aubailly** *(Électronique et Acquisition bas-niveau)* : Gestion matérielle, développement C sur STM32, conversion analogique, conception du circuit de puissance et relais.
* **Xavier Broussolle** *(Edge Computing, Réseau local et MQTT)* : Conteneurisation Docker sur RPi, script Receiver Python, gestion du broker Mosquitto et du routage MQTT-TCP.
* **George Stresna** *(Architecture Cloud et Backend API)* : Déploiement de l'instance AWS, base de données MongoDB, développement de l'API REST sous FastAPI.
* **Romane Chanteperdrix** *(Informatique et Dashboard IHM)* : Architecture de l'application Web MVC from scratch, logique métier client, design responsive, intégration Chart.js.
* **Maxime Bornard** *(Modélisation et Automatisation logique)* : Modélisation CAO Fusion 360, conception du système gravitaire, développement de l'AutomationController en Python.

---

## Installation & Déploiement

### 1. Raspberry Pi (Edge)

Le RPi utilise Docker pour isoler ses processus (MQTT et Python Receiver).

```bash
# Lancer l'environnement local
cd edge-gateway
docker-compose up -d
2. Cloud (AWS)
Le serveur AWS déploie MongoDB, le broker MQTT et l'API FastAPI.

Bash
# Sur l'instance EC2
cd cloud-backend
docker-compose up -d
3. Microcontrôleur (STM32)
Flasher le firmware CyberGarden_Firmware.elf sur la carte STM32F303 via STM32CubeIDE.

4. Interface Web
Ouvrir index.html via un serveur web local ou un navigateur (les routes API doivent pointer vers l'IP de l'instance AWS).
