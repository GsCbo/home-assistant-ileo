# Changelog

## 0.1.17

- Cree une statistique Recorder `ileo:water_index*` a `0 L` pour les compteurs detectes sans releve.
- Conserve ces statistiques a zero sans marquer de dernier releve importe, afin que le premier vrai releve puisse etre importe correctement ensuite.

## 0.1.16

- Arrete de publier les entites REST `sensor.ileo_water_index*`.
- Garde uniquement les statistiques Recorder `ileo:water_index*` pour le tableau de bord Energie.

## 0.1.15

- Réimporte les statistiques lorsqu'un compteur possède uniquement les anciens marqueurs d'import `sensor.*`.
- Ajoute un marqueur `statistics_id` par compteur pour éviter de manquer les migrations futures d'identifiants statistiques.

## 0.1.14

- Publie les statistiques Recorder dans le namespace externe `ileo:` au lieu d'utiliser directement les entités `sensor.*`.
- Garde les entités `sensor.ileo_water_index_*` comme états visibles sans statistiques automatiques concurrentes.
- Prépare les sources Énergie à pointer vers les statistiques `ileo:water_index_*`, ce qui évite les warnings de classe d'état sur les sensors.

## 0.1.13

- Traite les exports ILEO vides, HTML ou non-CSV comme une absence de relevé pour le compteur concerné.
- Conserve une erreur explicite lorsqu'un vrai CSV perd seulement une partie des colonnes attendues.

## 0.1.12

- Empêche Recorder de générer des statistiques automatiques concurrentes pour le sensor REST ILEO.
- Ajoute des statistiques de maintien à somme constante jusqu'au jour courant pour éviter les consommations négatives.

## 0.1.11

- Corrige le format `mean_type` envoyé à l'API WebSocket `recorder/import_statistics`.

## 0.1.10

- Importe les relevés ILEO historiques dans Recorder via l'API WebSocket `recorder/import_statistics`.
- Crée une base de consommation à `0 L` au `start_date`, puis importe les consommations quotidiennes comme statistiques datées.
- Mémorise la dernière statistique importée par compteur pour ne reprendre ensuite que les nouveaux relevés.
- Accepte `current_year` comme valeur de `start_date` pour utiliser automatiquement le 1er janvier de l'année courante.

## 0.1.9

- Remplace les exemples de compteurs par des identifiants fictifs dans la documentation et les tests.

## 0.1.8

- Publie les compteurs détectés sans relevé avec l'état numérique `0` au lieu de `unknown`.
- Ajoute l'attribut `assumed_zero` pour signaler que la valeur zéro est supposée tant qu'ILEO ne fournit pas de relevé.
- Permet de préparer ces compteurs dans le tableau de bord Énergie sans erreur d'entité indisponible.

## 0.1.7

- Ajoute l'option `meter_names` pour personnaliser les noms affichés des compteurs depuis la configuration de l'app.
- Documente la limite Home Assistant des entités publiées par l'API d'états, qui ne disposent pas d'un `unique_id` modifiable dans l'interface.

## 0.1.6

- Supprime l'appel au service `recorder.import_statistics`, absent des versions récentes de Home Assistant.
- Laisse Home Assistant Recorder créer les statistiques longue durée depuis l'entité `water` publiée.
- Évite les erreurs `400 Bad Request` au démarrage de l'app.

## 0.1.5

- Utilise des identifiants de statistiques compatibles Recorder pour les imports Home Assistant.
- Réessaie une synchronisation après 5 minutes en cas d'erreur au lieu d'attendre le prochain cycle de 4 heures.

## 0.1.4

- Agrandit et recadre les assets ILEO pour l'affichage dans Home Assistant.
- Ajoute un fond clair aux logos pour rester lisible en thème sombre.

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
