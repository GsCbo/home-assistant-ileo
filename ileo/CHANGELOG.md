# Changelog

## 0.1.3

- Préserve l'environnement Supervisor au démarrage de l'app.
- Corrige l'erreur `SUPERVISOR_TOKEN is required` au lancement.

## 0.1.2

- Lance une synchronisation immédiatement au démarrage de l'app.
- Applique le décalage stable uniquement entre les synchronisations suivantes.
- Évite l'attente initiale de plusieurs minutes après installation ou mise à jour.

## 0.1.1

- Ajoute la détection automatique des contrats ILEO attachés au compte.
- Synchronise chaque contrat séparément.
- Crée une entité Home Assistant par contrat, y compris pour un contrat sans relevé encore disponible.
- Accepte les dates CSV ILEO au format `YYYY-MM-DD` et `DD/MM/YYYY`.
- Ajoute les assets officiels ILEO pour l'affichage dans Home Assistant.
- Corrige le build Supervisor en utilisant le paquet Alpine `py3-aiohttp`.

## 0.1.0

- Première version de l'app Home Assistant ILEO.
- Connexion au compte ILEO.
- Import des relevés d'eau dans les statistiques longue durée Home Assistant.
- Publication d'une entité compatible avec le tableau de bord Énergie.
