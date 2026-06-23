{
    'name': 'IT Parc - Gestion de parc informatique',
    'version': '18.0.1.0.0',
    'category': 'Technical',
    'summary': 'Gestion complète du parc informatique de TECHPARK CI',
    'description': """
        Module de gestion du parc informatique interne d'Odoo 18.
        Fonctionnalités : équipements, affectations, interventions,
        contrats fournisseurs, alertes automatiques, rapports et dashboard OWL.
        
        Conforme au Cahier des Charges TECHPARK CI - Juin 2026
    """,
    'author': 'TECHPARK CI',
    'website': 'https://www.techparkci.com',
    'license': 'LGPL-3',

    # ============================================================
    # DÉPENDANCES PYTHON EXTERNES
    # ============================================================
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },

    # ============================================================
    # DÉPENDANCES MODULES ODOO
    # ============================================================
    'depends': [
        'base',
        'hr',                    # Pour les employés et départements
        'mail',                  # Pour mail.thread et activités
        'contacts',              # Pour les fournisseurs (res.partner)
        'web',                   # Pour les assets OWL
        'purchase',              # Pour les achats (optionnel)
        'stock',                 # Pour la gestion de stock (optionnel)
    ],

    # ============================================================
    # DONNÉES (ordre de chargement CRITIQUE)
    # ============================================================
    'data': [
        # --- 1. SÉCURITÉ (toujours en premier) ---
        'security/it_parc_security.xml',      # Groupes et règles
        'security/ir.model.access.csv',       # Droits CRUD

        # --- 2. DONNÉES DE BASE ---
        'data/ir_sequence_data.xml',          # Séquence pour les interventions
        'data/ir_cron_data.xml',              # Tâche planifiée pour les alertes

        # --- 3. MODÈLES (vues) ---
        'views/it_equipement_views.xml',      # Équipements
        'views/it_equipement_affectation_views.xml',
        'views/it_intervention_views.xml',    # Interventions
        'views/it_contrat_views.xml',         # Contrats
        'views/it_alerte_views.xml',          # Alertes
        'views/menus.xml',                    # Menus de navigation
        'views/it_parc_dashboard_views.xml',  # Action + menu du dashboard OWL

        # --- 4. WIZARDS (Phase 2) ---
        'wizards/it_wizard_reaffectation_views.xml',
        'wizards/it_wizard_import_csv_views.xml',
        'wizards/it_wizard_scan_alertes_views.xml',
        'wizards/it_wizard_renouvellement_views.xml',

        # --- 5. RAPPORTS QWEB (Phase 3) ---
        'report/it_report_fiche_equipement.xml',
        'report/it_report_inventaire.xml',
        'report/it_report_maintenances.xml',

        # --- 6. EXPORTS EXCEL (Phase 3) ---
        'wizards/it_wizard_export_inventaire_views.xml',
        'wizards/it_wizard_export_couts_views.xml',
        'wizards/it_wizard_export_contrats_views.xml',
    ],

    # ============================================================
    # DONNÉES DE DÉMONSTRATION
    # ============================================================
    'demo': [
        'data/it_parc_demo.xml',              # 10 équipements, 5 interventions, 3 contrats
    ],

    # ============================================================
    # ASSETS OWL (Phase 4 - Dashboard)
    # ============================================================
    'assets': {
        'web.assets_backend': [
            'it_parc/static/src/components/dashboard/it_parc_dashboard.js',
            'it_parc/static/src/components/dashboard/it_parc_dashboard.xml',
            'it_parc/static/src/components/dashboard/it_parc_dashboard.scss',
        ],
    },

    # ============================================================
    # CONFIGURATION ET INSTALLATION
    # ============================================================
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 100,

    # ============================================================
    # MÉTADONNÉES SUPPLÉMENTAIRES
    # ============================================================
    'maintainer': 'TECHPARK CI',
    'support': 'support@techparkci.com',
    'images': ['static/description/icon.png'],
}