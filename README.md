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
meter_names: |
  1234567=Compteur principal
  7654321=Compteur secondaire
```

### Options

| Option | Description |
| --- | --- |
| `username` | Adresse e-mail de votre compte ILEO. |
| `password` | Mot de passe de votre compte ILEO. |
| `start_date` | Première date à importer, au format `YYYY-MM-DD`. |
| `sync_interval_hours` | Fréquence de synchronisation, en heures. La valeur par défaut est `4`. |
| `mode` | `sync` pour synchroniser. `reset` existe pour préparer une remise à zéro, mais ne supprime rien pour l'instant. |
| `meter_names` | Optionnel. Une ligne `id_compteur=nom affiché` pour personnaliser les noms publiés dans Home Assistant. |

## Fonctionnement

Au démarrage, l'app :

1. lit sa configuration ;
2. se connecte à votre espace ILEO ;
3. télécharge l'export CSV de consommation ;
4. met à jour l'entité `sensor.ileo_water_index` ;
5. recommence toutes les `sync_interval_hours` heures, avec un décalage stable entre 0 et 30 minutes pour éviter que toutes les installations appellent ILEO en même temps.

Le décalage entre deux synchronisations est stable par installation. Si votre instance ajoute 12 minutes aujourd'hui, elle gardera le même ordre de grandeur aux prochains cycles.

## Plusieurs contrats ou compteurs

Si votre compte ILEO contient plusieurs contrats, l'app les détecte dans le menu de l'espace client et synchronise chaque contrat séparément.

Le comportement par défaut est volontairement automatique :

- tous les contrats détectés sont importés ;
- chaque contrat obtient sa propre entité Home Assistant ;
- le contrat courant garde l'ancien comportement si c'est le seul contrat visible ;
- un contrat sans consommation apparaît quand même avec l'état numérique `0`, marqué par l'attribut `assumed_zero`, puis basculera sur le relevé ILEO réel dès qu'il sera disponible.

Exemples d'entités :

```text
sensor.ileo_water_index
sensor.ileo_water_index_1234567
sensor.ileo_water_index_7654321
```

Ces entités n'ont pas de `unique_id`, car elles sont publiées par l'app via l'API d'états Home Assistant. Home Assistant ne permet donc pas de les renommer depuis l'interface. Utilisez `meter_names` dans la configuration de l'app pour choisir les noms affichés.

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
- L'app mémorise le dernier relevé vu par compteur dans `/data/last_sync.json`.
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
