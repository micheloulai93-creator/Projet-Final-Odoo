# IT Parc - Gestion du parc informatique

Module Odoo 18.0 pour la gestion complète du parc informatique : équipements, affectations, interventions, contrats fournisseurs, alertes et tableau de bord.

Version : 18.0.1.0.0
Licence : MIT

---

## Table des matières

1. [Présentation](#1-présentation)
2. [Fonctionnalités](#2-fonctionnalités)
3. [Architecture du module](#3-architecture-du-module)
4. [Installation](#4-installation)
5. [Configuration](#5-configuration)
6. [Utilisation](#6-utilisation)
7. [Rapports PDF](#7-rapports-pdf)
8. [Exports Excel](#8-exports-excel)
9. [Dépendances](#9-dépendances)
10. [Auteurs](#10-auteurs)
11. [Licence](#11-licence)

---

## 1. Présentation

IT Parc centralise la gestion de l'infrastructure informatique interne d'une entreprise directement dans Odoo. Le module couvre l'inventaire des équipements, leur affectation aux employés et départements, le suivi des interventions de maintenance, la gestion des contrats fournisseurs et la génération d'alertes automatiques (garanties, contrats).

Public cible :
- Administrateurs systèmes et réseaux
- Responsables du parc informatique (IT Manager)
- Techniciens IT (IT Technicien)

---

## 2. Fonctionnalités

### Gestion des équipements
- Fiche équipement : numéro de série unique, catégorie, marque, modèle, valeur d'achat, date de garantie
- Workflow à quatre états : Brouillon, Affecté, En maintenance, Retiré
- Historique complet des affectations par employé et département

### Gestion des interventions
- Enregistrement des interventions correctives et préventives
- Calcul automatique de la durée (date de début / date de fin)
- Suivi du coût par intervention et par équipement
- Vue calendrier des interventions planifiées

### Gestion des contrats fournisseurs
- Suivi des contrats de maintenance, licence et support
- Calcul automatique des jours restants avant expiration
- Wizard de renouvellement avec traçabilité du contrat d'origine
- Association de plusieurs équipements à un même contrat

### Gestion des alertes
- Génération automatique d'alertes pour les garanties et contrats expirant dans un délai paramétrable
- Tâche planifiée quotidienne (ir.cron) et wizard de scan manuel
- Suivi du traitement de chaque alerte (nouvelle, en traitement, traitée, ignorée)

### Tableau de bord
- Vue d'ensemble du parc (total, affectés, en maintenance, retirés)
- Indicateurs de pilotage : taux d'immobilisation, coût total de possession, équipements en fin de vie
- Indicateurs d'anticipation : alertes actives, garanties et contrats arrivant à échéance
- Graphique des coûts de maintenance sur 6 mois
- Répartition des équipements par catégorie
- Liste des alertes les plus urgentes à traiter

### Rapports et exports
- Trois rapports PDF imprimables (QWeb)
- Trois exports Excel téléchargeables (xlsxwriter)

---

## 3. Architecture du module

```
it_parc/
├── __init__.py
├── __manifest__.py
├── README.md
├── data/                              Séquences et tâches planifiées
│   ├── ir_cron_data.xml
│   ├── ir_sequence_data.xml
│   └── it_parc_demo.xml
├── models/                            Modèles de données
│   ├── __init__.py
│   ├── it_equipement.py
│   ├── it_intervention.py
│   ├── it_contrat.py
│   ├── it_alerte.py
│   └── it_equipement_affectation.py
├── views/                             Vues et menus
│   ├── it_equipement_views.xml
│   ├── it_intervention_views.xml
│   ├── it_contrat_views.xml
│   ├── it_alerte_views.xml
│   ├── it_parc_dashboard_views.xml
│   └── menus.xml
├── report/                            Rapports PDF
│   ├── it_report_inventaire.py
│   ├── it_report_inventaire.xml
│   ├── it_report_maintenances.py
│   ├── it_report_maintenances.xml
│   └── it_report_fiche_equipement.xml
├── wizards/                           Assistants
│   ├── __init__.py
│   ├── wizard_export_excel.py
│   ├── wizard_export_inventaire.py
│   ├── wizard_export_couts.py
│   ├── wizard_export_contrats.py
│   ├── wizard_import_csv.py
│   ├── wizard_reaffectation.py
│   ├── wizard_renouvellement.py
│   ├── wizard_scan_alertes.py
│   └── it_wizard_*.xml
├── security/                          Droits d'accès
│   ├── ir.model.access.csv
│   └── it_parc_security.xml
└── static/src/components/dashboard/   Composant OWL du tableau de bord
    ├── it_parc_dashboard.js
    ├── it_parc_dashboard.scss
    └── it_parc_dashboard.xml
```

---

## 4. Installation

### Prérequis

- Odoo 18.0 Enterprise
- Python 3.11 ou supérieur
- wkhtmltopdf (génération des rapports PDF)
- xlsxwriter (génération des exports Excel)

### Étapes

1. Cloner le dépôt :
   ```bash
   git clone https://github.com/micheloulai93-creator/Projet-Final-Odoo.git
   ```

2. Copier le module dans le dossier des addons Odoo :
   ```bash
   cp -r Projet-Final-Odoo /chemin/vers/odoo/addons/it_parc
   ```

3. Installer la dépendance Python :
   ```bash
   pip install xlsxwriter
   ```

4. Installer wkhtmltopdf si nécessaire :
   ```bash
   # Linux
   sudo apt-get install wkhtmltopdf

   # Windows : télécharger depuis https://wkhtmltopdf.org/downloads.html
   ```

5. Redémarrer Odoo en mettant à jour le module :
   ```bash
   ./odoo-bin --addons-path=addons -u it_parc
   ```

6. Activer le module dans l'interface :
   - Se connecter à Odoo
   - Aller dans **Apps**
   - Rechercher **IT Parc - Gestion de parc informatique**
   - Cliquer sur **Installer**

---

## 5. Configuration

### Séquences

Le module crée automatiquement les séquences pour :
- Les numéros d'équipements
- Les références des interventions
- Les numéros de contrats

### Groupes d'utilisateurs

| Groupe | Droits |
| --- | --- |
| IT Technicien | Lecture et création des interventions |
| IT Manager | Accès complet à tous les modèles du module |

Aucune vue n'est accessible sans appartenance à l'un de ces deux groupes.

### Tâches planifiées (ir.cron)

- Scan quotidien des garanties expirant dans le délai configuré
- Scan quotidien des contrats expirant dans le délai configuré

---

## 6. Utilisation

### Gestion des équipements

**Créer un équipement**
1. Aller dans **IT Parc > Équipements**
2. Cliquer sur **Créer**
3. Renseigner : nom, catégorie, numéro de série, marque, modèle, valeur d'achat, date d'achat, date de garantie
4. Enregistrer

**Affecter un équipement**
1. Sélectionner un équipement
2. Cliquer sur **Affecter**
3. Choisir l'employé et le département
4. Confirmer

### Gestion des interventions

**Créer une intervention**
1. Aller dans **IT Parc > Interventions**
2. Cliquer sur **Créer**
3. Renseigner : équipement concerné, type (corrective/préventive), technicien, date de début, description
4. Enregistrer

**Suivre une intervention**
1. Sélectionner l'intervention
2. Cliquer sur **Démarrer** puis **Terminer**
3. La durée est calculée automatiquement à la clôture

### Gestion des contrats

**Créer un contrat**
1. Aller dans **IT Parc > Contrats**
2. Cliquer sur **Créer**
3. Renseigner : type de contrat, fournisseur, dates de début et de fin, montant
4. Associer les équipements couverts
5. Enregistrer

---

## 7. Rapports PDF

| Rapport | Contenu |
| --- | --- |
| Inventaire complet | Vue d'ensemble du parc, statistiques par catégorie, valeur totale, filtrable par département ou catégorie |
| Historique des maintenances | Liste des interventions sur une période, coûts et durées, coût total |
| Fiche équipement | Caractéristiques détaillées, historique des affectations, interventions et contrats liés |

---

## 8. Exports Excel

| Export | Contenu |
| --- | --- |
| Inventaire | Liste complète des équipements, toutes colonnes |
| Coûts de maintenance | Synthèse des coûts par équipement et par mois |
| Contrats expirant | Contrats arrivant à échéance dans les 60 jours, avec mise en couleur conditionnelle |

---

## 9. Dépendances

### Modules Odoo
- `base`
- `mail`
- `hr`
- `stock`
- `purchase`
- `account`
- `maintenance`
- `contacts`
- `web`

### Bibliothèques Python
- `xlsxwriter` — génération des fichiers Excel
- `wkhtmltopdf` — génération des rapports PDF

---

## 10. Auteurs

TECHPARK CI — développement initial
Responsable technique : micheloulai93-creator

---

## 11. Licence

Ce projet est distribué sous licence MIT. Voir le fichier `LICENSE` pour le détail des termes.