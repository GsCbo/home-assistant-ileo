# Home Assistant ILEO

> Une app Home Assistant pour remonter votre consommation d'eau ILEO dans le tableau de bord Énergie.

Cette app s'adresse surtout aux utilisateurs Home Assistant de la Métropole Européenne de Lille qui ont un compte ILEO et qui veulent suivre l'eau au même endroit que l'électricité, le gaz ou le solaire.

Elle se connecte à votre espace ILEO, récupère l'export de consommation disponible, puis publie un index d'eau compatible avec les statistiques longue durée de Home Assistant.

## Prérequis

Pour utiliser cette app, il vous faut :

- une installation Home Assistant avec Supervisor et le store des apps ;
- un compte client ILEO fonctionnel ;
- des identifiants ILEO valides ;
- un peu de patience si le portail ILEO décide de faire sa pause café.

## Installation

Depuis Home Assistant :

1. Ouvrez `Paramètres`.
2. Allez dans `Apps`, puis `Boutique`.
3. Ouvrez le menu en haut à droite, puis `Dépôts`.
4. Ajoutez ce dépôt :

```text
https://github.com/GsCbo/home-assistant-ileo
```

5. Cherchez `ILEO` dans la liste des apps.
6. Installez l'app.
7. Renseignez la configuration, puis démarrez l'app.

## Configuration

Configuration de base :

```yaml
username: votre-email@example.com
password: votre-mot-de-passe
start_date: "2025-03-01"
sync_interval_hours: 4
mode: sync
```

### Options

| Option | Description |
| --- | --- |
| `username` | Adresse e-mail de votre compte ILEO. |
| `password` | Mot de passe de votre compte ILEO. |
| `start_date` | Première date à importer, au format `YYYY-MM-DD`. |
| `sync_interval_hours` | Fréquence de synchronisation, en heures. La valeur par défaut est `4`. |
| `mode` | `sync` pour synchroniser. `reset` existe pour préparer une remise à zéro, mais ne supprime rien pour l'instant. |

## Fonctionnement

Au démarrage, l'app :

1. lit sa configuration ;
2. attend un décalage stable entre 0 et 30 minutes pour éviter que toutes les installations appellent ILEO en même temps ;
3. se connecte à votre espace ILEO ;
4. télécharge l'export CSV de consommation ;
5. importe les nouvelles données dans Home Assistant ;
6. met à jour l'entité `sensor.ileo_water_index` ;
7. recommence toutes les `sync_interval_hours` heures.

Le décalage de démarrage est stable par installation. Si votre instance attend 12 minutes aujourd'hui, elle gardera le même ordre de grandeur aux prochains redémarrages.

## Tableau de bord Énergie

Après une première synchronisation réussie, Home Assistant dispose d'une statistique d'eau basée sur `sensor.ileo_water_index`.

Pour l'ajouter au tableau de bord Énergie :

1. Ouvrez `Paramètres`.
2. Allez dans `Tableaux de bord`, puis `Énergie`.
3. Dans la section eau, ajoutez une consommation.
4. Sélectionnez la statistique ILEO.

L'entité expose les métadonnées attendues par Home Assistant :

- `device_class` : `water`
- `state_class` : `total_increasing`
- unité : `L`

## Bon à savoir

- Les données ILEO ne sont pas forcément disponibles en temps réel.
- L'app dépend du portail ILEO. Si la page de connexion ou le format CSV change, une correction de l'app pourra être nécessaire.
- L'app évite d'importer deux fois les mêmes jours grâce au fichier persistant `/data/last_sync.json`.
- Les appels ILEO sont volontairement espacés pour rester raisonnables côté service.

## Dépannage

En cas de problème :

1. Ouvrez l'app dans Home Assistant.
2. Consultez l'onglet `Journal`.
3. Vérifiez que vos identifiants ILEO fonctionnent bien sur le site officiel.
4. Contrôlez que `start_date` est au format `YYYY-MM-DD`.
5. Redémarrez l'app après modification de la configuration.

Les erreurs de connexion ILEO, de CSV invalide ou de configuration sont journalisées explicitement.

## Développement

Le runtime est en Python et vit dans `ileo/app`.

Commandes utiles :

```bash
python -m py_compile ileo/app/*.py
pytest tests -v
```

## Statut

Projet personnel, fait pour la maison et les gens du coin qui veulent voir leur eau dans Home Assistant sans attendre qu'une intégration officielle tombe du ciel.

