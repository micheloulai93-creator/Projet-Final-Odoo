# -*- coding: utf-8 -*-
from odoo import models, fields


class ItEquipementAffectation(models.Model):
    """
    Historique des affectations successives d'un équipement.
    Conforme au CDC - Fonctionnalité 02 :
    "Historique de toutes les affectations successives."
    Un enregistrement est créé à chaque réaffectation (via le wizard
    it.wizard.reaffectation) ou lors de la première affectation.
    """
    _name = 'it.equipement.affectation'
    _description = 'Historique des affectations d\'équipement'
    _order = 'date_affectation desc, id desc'
    _rec_name = 'equipement_id'

    equipement_id = fields.Many2one(
        'it.equipement',
        string='Équipement',
        required=True,
        ondelete='cascade',
        index=True,
    )

    date_affectation = fields.Date(
        string='Date de l\'affectation',
        required=True,
        default=fields.Date.today,
    )

    ancien_employe_id = fields.Many2one(
        'hr.employee',
        string='Ancien employé',
        help="Vide si l'équipement n'était pas encore affecté.",
    )
    nouvel_employe_id = fields.Many2one(
        'hr.employee',
        string='Nouvel employé',
        required=True,
    )

    ancien_department_id = fields.Many2one(
        'hr.department',
        string='Ancien département',
    )
    nouveau_department_id = fields.Many2one(
        'hr.department',
        string='Nouveau département',
        required=True,
    )

    motif = fields.Text(
        string='Motif',
        help="Raison du changement d'affectation.",
    )

    utilisateur_id = fields.Many2one(
        'res.users',
        string='Effectué par',
        default=lambda self: self.env.user,
        readonly=True,
    )