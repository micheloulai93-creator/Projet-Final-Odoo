# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from markupsafe import Markup


class WizardReaffectation(models.TransientModel):
    """
    Wizard de réaffectation d'un équipement à un nouvel employé et/ou département.
    Conforme au CDC - Fonctionnalité 02
    """
    _name = 'it.wizard.reaffectation'
    _description = 'Wizard de réaffectation d\'équipement'

    # === CHAMPS DU WIZARD ===
    equipement_id = fields.Many2one(
        'it.equipement',
        string='Équipement',
        required=True,
        help="Équipement à réaffecter"
    )

    employe_id = fields.Many2one(
        'hr.employee',
        string='Nouvel employé',
        required=True,
        help="Employé à qui réaffecter l'équipement"
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Nouveau département',
        required=True,
        help="Département du nouvel employé"
    )

    motif = fields.Text(
        string='Motif de la réaffectation',
        required=True,
        help="Raison du changement d'affectation"
    )

    date_reaffectation = fields.Date(
        string='Date de réaffectation',
        required=True,
        default=fields.Date.today,
        help="Date effective du changement"
    )

    # === CHAMPS D'INFORMATION (lecture seule) ===
    ancien_employe_id = fields.Many2one(
        'hr.employee',
        string='Ancien employé',
        compute='_compute_infos',
        readonly=True
    )

    ancien_department_id = fields.Many2one(
        'hr.department',
        string='Ancien département',
        compute='_compute_infos',
        readonly=True
    )

    equipement_display = fields.Char(
        string='Équipement (texte)',
        compute='_compute_infos',
        readonly=True
    )

    @api.depends('equipement_id')
    def _compute_infos(self):
        """Récupère les informations actuelles de l'équipement"""
        for wizard in self:
            equip = wizard.equipement_id
            if equip:
                wizard.ancien_employe_id = equip.employe_id
                wizard.ancien_department_id = equip.department_id
                wizard.equipement_display = f"{equip.name} ({equip.num_serie or 'N/A'})"
            else:
                wizard.ancien_employe_id = False
                wizard.ancien_department_id = False
                wizard.equipement_display = ""

    @api.onchange('employe_id')
    def _onchange_employe_id(self):
        """Auto-remplit le département en fonction de l'employé sélectionné"""
        if self.employe_id and self.employe_id.department_id:
            self.department_id = self.employe_id.department_id

    # === MÉTHODE D'ACTION ===
    def action_reaffecter(self):
        """
        Exécute la réaffectation :
        1. Vérifie que l'équipement est bien dans un état valide (Affecté ou En maintenance)
        2. Crée un enregistrement d'historique structuré (it.equipement.affectation)
        3. Trace aussi l'opération dans le chatter
        4. Met à jour les champs employe_id, department_id, state
        """
        self.ensure_one()

        equip = self.equipement_id

        if not equip:
            raise ValidationError(_("Veuillez sélectionner un équipement à réaffecter."))

        # Vérifications préalables
        if equip.state in ('draft', 'retired'):
            state_label = dict(equip._fields['state'].selection).get(equip.state)
            raise ValidationError(
                _("Impossible de réaffecter un équipement à l'état '%s'. "
                  "Seuls les équipements 'Affecté' ou 'En maintenance' peuvent être réaffectés.")
                % state_label
            )

        if equip.employe_id == self.employe_id:
            raise ValidationError(_("Cet équipement est déjà affecté à cet employé."))

        # === EXÉCUTION DE LA RÉAFFECTATION ===
        ancien_employe = equip.employe_id
        ancien_departement = equip.department_id

        # 1. Créer l'enregistrement d'historique structuré
        self.env['it.equipement.affectation'].create({
            'equipement_id': equip.id,
            'date_affectation': self.date_reaffectation,
            'ancien_employe_id': ancien_employe.id if ancien_employe else False,
            'nouvel_employe_id': self.employe_id.id,
            'ancien_department_id': ancien_departement.id if ancien_departement else False,
            'nouveau_department_id': self.department_id.id,
            'motif': self.motif,
        })

        # 2. Trace également dans le chatter (lisible directement sur la fiche)
        # Markup() obligatoire depuis Odoo 17 pour que les balises HTML soient
        # interprétées au lieu d'être échappées et affichées brutes.
        message = Markup(
            """<b>Réaffectation</b>
            <ul>
                <li><b>Ancien employé :</b> %s</li>
                <li><b>Nouvel employé :</b> %s</li>
                <li><b>Ancien département :</b> %s</li>
                <li><b>Nouveau département :</b> %s</li>
                <li><b>Motif :</b> %s</li>
                <li><b>Date :</b> %s</li>
            </ul>"""
        ) % (
            ancien_employe.name if ancien_employe else 'Non affecté',
            self.employe_id.name,
            ancien_departement.name if ancien_departement else 'Non défini',
            self.department_id.name,
            self.motif,
            self.date_reaffectation.strftime('%d/%m/%Y')
        )
        equip.message_post(body=message)

        # 3. Mise à jour des champs de l'équipement
        equip.write({
            'employe_id': self.employe_id.id,
            'department_id': self.department_id.id,
            'state': 'assigned',
            'date_affectation': self.date_reaffectation,
        })

        # 4. Retourner à la vue de l'équipement
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'it.equipement',
            'res_id': equip.id,
            'view_mode': 'form',
            'target': 'current',
            'flags': {'form': {'action_buttons': True}}
        }