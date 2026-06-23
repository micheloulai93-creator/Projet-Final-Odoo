# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .wizard_export_excel import WizardExportExcel
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class WizardExportContrats(models.TransientModel):
    _name = 'it.wizard.export.contrats'
    _description = 'Export Excel - Contrats expirant'
    _inherit = 'it.wizard.export.excel'

    delai_jours = fields.Integer(
        string='Délai (jours)',
        default=60,
        required=True,
        help="Nombre de jours avant l'expiration pour rechercher les contrats"
    )
    
    only_active = fields.Boolean(
        string='Uniquement les contrats actifs',
        default=True,
        help="Ne prendre en compte que les contrats actifs"
    )
    
    include_equipements = fields.Boolean(
        string='Inclure les équipements couverts',
        default=True,
        help="Inclure la liste des équipements liés au contrat"
    )

    def action_export(self):
        """Génère l'export Excel des contrats expirant"""
        self.ensure_one()

        # Récupération des contrats
        contrats = self._get_contrats()
        
        if not contrats:
            raise ValidationError(_("Aucun contrat expirant dans les %s jours.") % self.delai_jours)

        # Préparation des données
        headers = self._get_headers()
        data_rows = self._prepare_data_rows(contrats)
        column_widths = self._get_column_widths()
        conditional_formatting = self._get_conditional_formatting(len(data_rows))

        # Création du fichier Excel
        file_data = self._create_excel_file(
            sheet_name='Contrats expirant',
            headers=headers,
            data_rows=data_rows,
            column_widths=column_widths,
            conditional_formatting=conditional_formatting
        )

        # Mise à jour des champs
        self.write({
            'file_datas': file_data,
            'filename': f"Contrats_Expirant_{fields.Date.today().strftime('%Y%m%d')}.xlsx",
            'export_done': True
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'flags': {'form': {'action_buttons': False}}
        }

    def _get_contrats(self):
        """Récupère les contrats selon les filtres"""
        date_limite = fields.Date.today() + timedelta(days=self.delai_jours)
        
        domain = [
            ('date_fin', '!=', False),
            ('date_fin', '<=', date_limite)
        ]
        
        if self.only_active:
            domain.append(('state', '=', 'actif'))

        return self.env['it.contrat'].search(domain, order='date_fin ASC')

    def _get_headers(self):
        """Définit les en-têtes du fichier Excel"""
        headers = [
            'Contrat',
            'Fournisseur',
            'Type',
            'Date début',
            'Date fin',
            'Jours restants',
            'Statut',
            'Montant (FCFA)'
        ]
        
        if self.include_equipements:
            headers.append('Équipements couverts')
        
        return headers

    def _prepare_data_rows(self, contrats):
        """Prépare les lignes de données"""
        data_rows = []
        today = fields.Date.today()

        for contrat in contrats:
            jours_restants = (contrat.date_fin - today).days
            
            # Détermination du statut avec codes couleur
            if jours_restants < 0:
                status = 'EXPIRÉ'
            elif jours_restants <= 30:
                status = 'Urgent'
            elif jours_restants <= 60:
                status = 'Proche'
            else:
                status = 'OK'

            row = [
                contrat.name or '',
                contrat.fournisseur_id.name or '',
                dict(contrat._fields['type_contrat'].selection).get(contrat.type_contrat, ''),
                contrat.date_debut.strftime('%d/%m/%Y') if contrat.date_debut else '',
                contrat.date_fin.strftime('%d/%m/%Y') if contrat.date_fin else '',
                jours_restants,
                status,
                contrat.montant or 0.0,
            ]
            
            if self.include_equipements:
                equipements = contrat.equipement_ids
                equipements_noms = ', '.join(equipements.mapped('name')) if equipements else 'Aucun'
                row.append(equipements_noms)
            
            data_rows.append(row)

        return data_rows

    def _get_column_widths(self):
        """Définit les largeurs des colonnes"""
        widths = {
            0: 30,  # Contrat
            1: 25,  # Fournisseur
            2: 15,  # Type
            3: 15,  # Date début
            4: 15,  # Date fin
            5: 15,  # Jours restants
            6: 15,  # Statut
            7: 18,  # Montant
        }
        
        if self.include_equipements:
            widths[8] = 50  # Équipements couverts
        
        return widths

    def _get_conditional_formatting(self, nb_lignes):
        """Définit la mise en forme conditionnelle pour les jours restants"""
        if nb_lignes == 0:
            return []

        # La colonne "Jours restants" est à l'index 5 (colonne F)
        range_jours = f'F2:F{nb_lignes + 1}'
        
        # La colonne "Statut" est à l'index 6 (colonne G)
        range_statut = f'G2:G{nb_lignes + 1}'

        return [
            # EXPIRÉ (jours < 0)
            {
                'type': 'cell_color',
                'range': range_jours,
                'criteria': 'less than',
                'value': 0,
                'color': '#FF0000',
            },
            # Urgent (0 à 30 jours)
            {
                'type': 'cell_color',
                'range': range_jours,
                'criteria': 'between',
                'value': '0,30',
                'color': '#FF9800',
            },
            # Proche (31 à 60 jours)
            {
                'type': 'cell_color',
                'range': range_jours,
                'criteria': 'between',
                'value': '31,60',
                'color': '#FFEB3B',
            },
            # Mise en forme du statut
            {
                'type': 'cell_color',
                'range': range_statut,
                'criteria': 'equal to',
                'value': 'EXPIRÉ',
                'color': '#FF0000',
            },
            {
                'type': 'cell_color',
                'range': range_statut,
                'criteria': 'equal to',
                'value': 'Urgent',
                'color': '#FF9800',
            },
            {
                'type': 'cell_color',
                'range': range_statut,
                'criteria': 'equal to',
                'value': 'Proche',
                'color': '#FFEB3B',
            },
        ]

    @api.model
    def default_get(self, fields_list):
        """Définit les valeurs par défaut"""
        defaults = super(WizardExportContrats, self).default_get(fields_list)
        
        # Valeurs par défaut supplémentaires si nécessaire
        if 'delai_jours' in fields_list and not defaults.get('delai_jours'):
            defaults['delai_jours'] = 60
            
        if 'only_active' in fields_list and 'only_active' not in defaults:
            defaults['only_active'] = True
            
        if 'include_equipements' in fields_list and 'include_equipements' not in defaults:
            defaults['include_equipements'] = True
            
        return defaults

    def action_download(self):
        """Télécharge le fichier Excel - override pour ajouter des vérifications"""
        self.ensure_one()
        if not self.file_datas:
            raise ValidationError(_("Aucun fichier à télécharger. Effectuez d'abord l'export."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.id}?model={self._name}&id={self.id}&filename_field=filename&field=file_datas&download=true',
            'target': 'new',
        }