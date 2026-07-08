# ILEO

App Home Assistant pour synchroniser votre consommation d'eau ILEO avec le tableau de bord Énergie.

Elle récupère les relevés disponibles depuis votre espace client ILEO, les importe dans les statistiques longue durée de Home Assistant et met à jour l'entité `sensor.ileo_water_index`.

## Configuration

```yaml
username: votre-email@example.com
password: votre-mot-de-passe
start_date: "2025-03-01"
sync_interval_hours: 4
mode: sync
```

## Options

- `username` : adresse e-mail de votre compte ILEO.
- `password` : mot de passe de votre compte ILEO.
- `start_date` : première date à importer, au format `YYYY-MM-DD`.
- `sync_interval_hours` : fréquence de synchronisation en heures, `4` par défaut.
- `mode` : `sync` pour importer les relevés. `reset` ne supprime rien pour l'instant.

## Fonctionnement

Au démarrage, l'app attend un décalage stable entre 0 et 30 minutes afin d'éviter que toutes les installations appellent ILEO au même moment.

Ensuite, elle synchronise les données selon la fréquence configurée et les publie comme statistique d'eau compatible avec le tableau de bord Énergie.

## Plusieurs contrats

Si plusieurs contrats ILEO sont attachés au compte, l'app les détecte automatiquement et crée une entité par contrat.

Un contrat sans relevé apparaît avec l'état `unknown` jusqu'à la première consommation disponible. Vous pouvez renommer les entités dans Home Assistant sans casser la synchronisation.

## Notes

- Les données dépendent de ce que le portail ILEO expose dans son export.
- L'app n'est pas une intégration officielle ILEO.
- En cas de problème, consultez l'onglet `Journal` de l'app.
