# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .wizard_export_excel import WizardExportExcel


class WizardExportInventaire(models.TransientModel):
    _name = 'it.wizard.export.inventaire'
    _description = 'Export Excel - Inventaire complet'
    _inherit = 'it.wizard.export.excel'

    filtre_departement_id = fields.Many2one('hr.department', string='Filtrer par département')

    filtre_categorie = fields.Selection([
        ('poste_travail', 'Postes de travail'),
        ('serveur', 'Serveurs'),
        ('imprimante', 'Imprimantes'),
        ('reseau', 'Équipements réseau'),
        ('telephone', 'Téléphones'),
        ('autre', 'Autres'),
        ('tous', 'Tous les types'),
    ], string='Filtrer par catégorie', default='tous')

    filtre_etat = fields.Selection([
        ('tous', 'Tous les états'),
        ('draft', 'Brouillon'),
        ('assigned', 'Affecté'),
        ('in_maintenance', 'En maintenance'),
        ('retired', 'Retiré'),
    ], string='Filtrer par état', default='tous')

    include_garantie_info = fields.Boolean(string='Inclure les infos de garantie', default=True)
    include_cout_maintenance = fields.Boolean(string='Inclure le coût total de maintenance', default=True)

    def action_export(self):
        self.ensure_one()

        domain = []
        if self.filtre_departement_id:
            domain.append(('department_id', '=', self.filtre_departement_id.id))
        if self.filtre_categorie != 'tous':
            domain.append(('categorie', '=', self.filtre_categorie))
        if self.filtre_etat != 'tous':
            domain.append(('state', '=', self.filtre_etat))

        equipements = self.env['it.equipement'].search(domain)
        if not equipements:
            raise ValidationError(_("Aucun équipement ne correspond aux critères sélectionnés."))

        headers = ['N°', 'Nom', 'Catégorie', 'Numéro de série', 'Marque', 'Modèle',
                   'État', 'Employé', 'Département', 'Localisation']
        if self.include_garantie_info:
            headers.extend(['Date garantie', 'Garantie expirée ?'])
        if self.include_cout_maintenance:
            headers.append('Coût maintenance (FCFA)')
        headers.extend(["Valeur d'achat (FCFA)", 'Fournisseur'])

        data_rows = []
        for idx, equip in enumerate(equipements, start=1):
            row = [
                idx, equip.name or '',
                dict(equip._fields['categorie'].selection).get(equip.categorie, ''),
                equip.num_serie or '', equip.marque or '', equip.modele or '',
                dict(equip._fields['state'].selection).get(equip.state, ''),
                equip.employe_id.name or 'Non affecté',
                equip.department_id.name or '', equip.localisation or '',
            ]
            if self.include_garantie_info:
                row.append(equip.date_garantie.strftime('%d/%m/%Y') if equip.date_garantie else 'Non renseignée')
                row.append('OUI' if equip.garantie_expired else 'NON')
            if self.include_cout_maintenance:
                row.append(sum(equip.intervention_ids.mapped('cout')))
            row.append(equip.valeur_achat or 0)
            row.append(equip.fournisseur_id.name or '')
            data_rows.append(row)

        column_widths = {0: 5, 1: 25, 2: 20, 3: 18, 4: 15, 5: 15, 6: 15, 7: 25, 8: 20, 9: 20}
        if self.include_garantie_info:
            column_widths[10] = 15
            column_widths[11] = 15
        if self.include_cout_maintenance:
            column_widths[12 if self.include_garantie_info else 10] = 20

        file_data = self._create_excel_file(
            sheet_name='Inventaire', headers=headers, data_rows=data_rows,
            column_widths=column_widths, conditional_formatting=None
        )

        self.write({
            'file_datas': file_data,
            'filename': f"Inventaire_{fields.Date.today().strftime('%Y%m%d')}.xlsx",
            'export_done': True
        })

        return {
            'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
            'view_mode': 'form', 'target': 'new', 'flags': {'form': {'action_buttons': False}}
        }