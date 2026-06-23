# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WizardScanAlertes(models.TransientModel):
    """
    Wizard de scan manuel des alertes (garanties et contrats).
    Conforme au CDC - Fonctionnalité 05
    """
    _name = 'it.wizard.scan.alertes'
    _description = 'Wizard de scan des alertes'

    delai_alerte = fields.Integer(
        string='Délai d\'alerte (jours)',
        default=30,
        required=True,
        help="Nombre de jours avant l'expiration pour déclencher une alerte"
    )

    types_alerte = fields.Selection([
        ('garantie', 'Garanties uniquement'),
        ('contrat', 'Contrats uniquement'),
        ('tous', 'Tous (garanties + contrats)'),
    ], string='Type d\'alerte', default='tous', required=True)

    resultat_scan = fields.Text(string='Résultat du scan', readonly=True)
    alertes_creees = fields.Integer(string='Alertes créées', default=0, readonly=True)
    scan_effectue = fields.Boolean(string='Scan effectué', default=False, readonly=True)

    def action_scanner(self):
        self.ensure_one()

        if self.delai_alerte <= 0:
            raise ValidationError(_("Le délai d'alerte doit être supérieur à 0."))

        alerte_obj = self.env['it.alerte']
        today = fields.Date.today()
        created_count = 0
        rapport_lines = []

        if self.types_alerte in ('garantie', 'tous'):
            equipements = self.env['it.equipement'].search([
                ('date_garantie', '!=', False),
                ('state', 'not in', ['retired']),
            ])
            for equip in equipements:
                jours = (equip.date_garantie - today).days
                if 0 <= jours <= self.delai_alerte:
                    existing = alerte_obj.search([
                        ('equipement_id', '=', equip.id),
                        ('type_alerte', '=', 'garantie'),
                        ('state', 'not in', ['traitee', 'ignoree']),
                    ], limit=1)

                    if not existing:
                        alerte_obj.create({
                            'name': f"Garantie expirant - {equip.name}",
                            'equipement_id': equip.id,
                            'type_alerte': 'garantie',
                            'date_echeance': equip.date_garantie,
                        })
                        created_count += 1
                        rapport_lines.append(
                            f"✅ Alerte garantie créée pour : {equip.name} (expire le {equip.date_garantie.strftime('%d/%m/%Y')})"
                        )
                    else:
                        rapport_lines.append(f"⏭️ Alerte garantie déjà existante pour : {equip.name}")

        if self.types_alerte in ('contrat', 'tous'):
            contrats = self.env['it.contrat'].search([
                ('date_fin', '!=', False),
                ('state', '=', 'actif'),
            ])
            for contrat in contrats:
                jours = (contrat.date_fin - today).days
                if 0 <= jours <= self.delai_alerte:
                    existing = alerte_obj.search([
                        ('contrat_id', '=', contrat.id),
                        ('type_alerte', '=', 'contrat'),
                        ('state', 'not in', ['traitee', 'ignoree']),
                    ], limit=1)

                    if not existing:
                        alerte_obj.create({
                            'name': f"Contrat expirant - {contrat.name}",
                            'contrat_id': contrat.id,
                            'type_alerte': 'contrat',
                            'date_echeance': contrat.date_fin,
                        })
                        created_count += 1
                        rapport_lines.append(
                            f"✅ Alerte contrat créée pour : {contrat.name} (expire le {contrat.date_fin.strftime('%d/%m/%Y')})"
                        )
                    else:
                        rapport_lines.append(f"⏭️ Alerte contrat déjà existante pour : {contrat.name}")

        rapport = "=== RAPPORT DE SCAN DES ALERTES ===\n\n"
        rapport += "📊 Résumé :\n"
        rapport += f"  - Délai d'alerte : {self.delai_alerte} jours\n"
        rapport += f"  - Type scanné : {dict(self._fields['types_alerte'].selection).get(self.types_alerte)}\n"
        rapport += f"  - Alertes créées : {created_count}\n\n"

        if rapport_lines:
            rapport += "📝 Détail :\n"
            for line in rapport_lines:
                rapport += f"  {line}\n"
        else:
            rapport += "ℹ️ Aucune nouvelle alerte n'a été créée.\n"
            rapport += "\n💡 Conseil : Vérifiez les dates de garantie et de contrats dans vos équipements."

        self.write({
            'resultat_scan': rapport,
            'alertes_creees': created_count,
            'scan_effectue': True
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'it.wizard.scan.alertes',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'flags': {'form': {'action_buttons': False}}
        }

    def action_voir_alertes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'it.alerte',
            'view_mode': 'list,form',
            'domain': [('state', 'not in', ['traitee', 'ignoree'])],
            'target': 'current',
        }