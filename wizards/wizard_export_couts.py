# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .wizard_export_excel import WizardExportExcel
from datetime import datetime


class WizardExportCouts(models.TransientModel):
    _name = 'it.wizard.export.couts'
    _description = 'Export Excel - Synthèse des coûts de maintenance'
    _inherit = 'it.wizard.export.excel'

    annee = fields.Integer(string='Année', required=True, default=lambda self: fields.Date.today().year)
    par_mois = fields.Boolean(string='Vue détaillée par mois', default=True)

    def action_export(self):
        self.ensure_one()

        date_debut = datetime(self.annee, 1, 1, 0, 0, 0)
        date_fin = datetime(self.annee, 12, 31, 23, 59, 59)

        interventions = self.env['it.intervention'].search([
            ('date_debut', '>=', date_debut),
            ('date_debut', '<=', date_fin),
        ])
        if not interventions:
            raise ValidationError(_("Aucune intervention trouvée pour l'année %s.") % self.annee)

        if self.par_mois:
            headers = ['Équipement', 'Catégorie', 'Fournisseur']
            mois_names = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
            headers.extend(mois_names)
            headers.append('Total Annuel (FCFA)')

            equip_couts = {}
            for interv in interventions:
                key = interv.equipement_id.id
                if key not in equip_couts:
                    equip_couts[key] = {'equip': interv.equipement_id, 'mois': [0] * 12}
                equip_couts[key]['mois'][interv.date_debut.month - 1] += interv.cout or 0

            data_rows = []
            for data in equip_couts.values():
                equip = data['equip']
                row = [equip.name or '', dict(equip._fields['categorie'].selection).get(equip.categorie, ''), equip.fournisseur_id.name or '']
                total_annuel = 0
                for mois_val in data['mois']:
                    row.append(mois_val)
                    total_annuel += mois_val
                row.append(total_annuel)
                data_rows.append(row)
            data_rows.sort(key=lambda x: x[-1], reverse=True)
        else:
            headers = ['Équipement', 'Catégorie', 'Fournisseur', 'Nb interventions', 'Coût total (FCFA)']
            equip_couts = {}
            for interv in interventions:
                key = interv.equipement_id.id
                if key not in equip_couts:
                    equip_couts[key] = {'equip': interv.equipement_id, 'nb_interv': 0, 'total_cout': 0}
                equip_couts[key]['nb_interv'] += 1
                equip_couts[key]['total_cout'] += interv.cout or 0

            data_rows = []
            for data in equip_couts.values():
                equip = data['equip']
                data_rows.append([
                    equip.name or '',
                    dict(equip._fields['categorie'].selection).get(equip.categorie, ''),
                    equip.fournisseur_id.name or '',
                    data['nb_interv'], data['total_cout'],
                ])
            data_rows.sort(key=lambda x: x[-1], reverse=True)

        column_widths = {0: 30, 1: 20, 2: 25}
        if self.par_mois:
            for i in range(12):
                column_widths[3 + i] = 12
            column_widths[15] = 18
        else:
            column_widths[3] = 15
            column_widths[4] = 20

        file_data = self._create_excel_file(
            sheet_name='Coûts maintenance' if self.par_mois else 'Coûts annuels',
            headers=headers, data_rows=data_rows,
            column_widths=column_widths, conditional_formatting=None
        )

        self.write({
            'file_datas': file_data,
            'filename': f"Couts_Maintenance_{self.annee}_{fields.Date.today().strftime('%Y%m%d')}.xlsx",
            'export_done': True
        })

        return {
            'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
            'view_mode': 'form', 'target': 'new', 'flags': {'form': {'action_buttons': False}}
        }