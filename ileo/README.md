# ILEO

App Home Assistant pour synchroniser votre consommation d'eau ILEO avec le tableau de bord Énergie.

Elle récupère les relevés disponibles depuis votre espace client ILEO, les importe dans les statistiques longue durée de Home Assistant et met à jour les entités `sensor.ileo_water_index_*`.

## Configuration

```yaml
username: votre-email@example.com
password: votre-mot-de-passe
start_date: "current_year"
sync_interval_hours: 4
mode: sync
meter_names: |
  1234567=Compteur principal
  7654321=Compteur secondaire
```

## Options

- `username` : adresse e-mail de votre compte ILEO.
- `password` : mot de passe de votre compte ILEO.
- `start_date` : première date à importer, au format `YYYY-MM-DD`, ou `current_year` pour utiliser le 1er janvier de l'année courante.
- `sync_interval_hours` : fréquence de synchronisation en heures, `4` par défaut.
- `mode` : `sync` pour importer les relevés. `reset` ne supprime rien pour l'instant.
- `meter_names` : optionnel, une ligne `id_compteur=nom affiché` pour personnaliser les noms des compteurs.

## Fonctionnement

Au démarrage, l'app synchronise immédiatement les données disponibles. Lors du premier import Recorder d'un compteur, elle reprend les relevés disponibles depuis `start_date`, crée une base de consommation à `0 L`, puis importe les consommations quotidiennes comme statistiques datées.

Ensuite, elle recommence selon la fréquence configurée avec un décalage stable entre 0 et 30 minutes afin d'éviter que toutes les installations appellent ILEO au même moment. Les synchronisations suivantes ne réimportent que les relevés plus récents que le dernier relevé déjà importé.

Les entités `sensor.ileo_water_index_*` servent à afficher l'état courant. Le tableau de bord Énergie doit utiliser les statistiques Recorder publiées dans le namespace `ileo:`, par exemple `ileo:water_index_1234567`.

## Plusieurs contrats

Si plusieurs contrats ILEO sont attachés au compte, l'app les détecte automatiquement et crée une entité par contrat.

Un contrat sans relevé apparaît avec l'état numérique `0`, marqué par l'attribut `assumed_zero`, jusqu'à la première consommation disponible.

Les entités créées par l'app via l'API d'états Home Assistant n'ont pas de `unique_id`, donc Home Assistant ne permet pas de les renommer depuis l'interface. Utilisez `meter_names` dans la configuration de l'app pour choisir les noms affichés.

## Notes

- Les données dépendent de ce que le portail ILEO expose dans son export.
- L'app n'est pas une intégration officielle ILEO.
- En cas de problème, consultez l'onglet `Journal` de l'app.
