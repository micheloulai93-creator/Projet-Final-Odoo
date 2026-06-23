from odoo import models, fields, api
from odoo.exceptions import UserError


class ItContrat(models.Model):
    _name = 'it.contrat'
    _description = 'Contrat fournisseur'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_fin asc'

    # -------------------------------------------------------------------------
    # Identification
    # -------------------------------------------------------------------------
    name = fields.Char(
        string='Référence contrat',
        required=True,
        tracking=True,
    )
    type_contrat = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('licence', 'Licence logicielle'),
        ('support', 'Support technique'),
        ('autre', 'Autre'),
    ], string='Type de contrat', required=True, tracking=True)

    # -------------------------------------------------------------------------
    # Fournisseur
    # -------------------------------------------------------------------------
    fournisseur_id = fields.Many2one(
        'res.partner',
        string='Fournisseur',
        required=True,
        tracking=True,
    )

    # -------------------------------------------------------------------------
    # Période et montant
    # -------------------------------------------------------------------------
    date_debut = fields.Date(
        string='Date de début',
        required=True,
        tracking=True,
    )
    date_fin = fields.Date(
        string='Date de fin',
        required=True,
        tracking=True,
    )
    montant = fields.Float(
        string='Montant (FCFA)',
        tracking=True,
    )

    # -------------------------------------------------------------------------
    # Jours restants (calculé)
    # -------------------------------------------------------------------------
    jours_restants = fields.Integer(
        string='Jours restants',
        compute='_compute_jours_restants',
        store=True,
    )
    is_expired = fields.Boolean(
        string='Expiré',
        compute='_compute_jours_restants',
        store=True,
    )
    is_expiring_soon = fields.Boolean(
        string='Expire bientôt (60j)',
        compute='_compute_jours_restants',
        store=True,
    )

    # -------------------------------------------------------------------------
    # Équipements couverts
    # -------------------------------------------------------------------------
    equipement_ids = fields.Many2many(
        'it.equipement',
        'it_contrat_equipement_rel',
        'contrat_id',
        'equipement_id',
        string='Équipements couverts',
    )

    # -------------------------------------------------------------------------
    # Description
    # -------------------------------------------------------------------------
    description = fields.Text(string='Description / Conditions')

    # -------------------------------------------------------------------------
    # État
    # -------------------------------------------------------------------------
    state = fields.Selection([
        ('actif', 'Actif'),
        ('expire', 'Expiré'),
        ('resilie', 'Résilié'),
    ], string='État', default='actif', tracking=True)

    # -------------------------------------------------------------------------
    # Alertes liées
    # -------------------------------------------------------------------------
    alerte_ids = fields.One2many(
        'it.alerte',
        'contrat_id',
        string='Alertes',
    )

    # -------------------------------------------------------------------------
    # Renouvellement (historique / traçabilité)
    # -------------------------------------------------------------------------
    renouvele_de_id = fields.Many2one(
        'it.contrat',
        string='Renouvelé depuis',
        readonly=True,
        copy=False,
        help="Contrat d'origine dont celui-ci est le renouvellement.",
    )
    contrat_renouvele_id = fields.Many2one(
        'it.contrat',
        string='Renouvelé en',
        readonly=True,
        copy=False,
        help="Nouveau contrat créé lors du renouvellement de celui-ci.",
    )

    # -------------------------------------------------------------------------
    # Calculs
    # -------------------------------------------------------------------------
    @api.depends('date_fin')
    def _compute_jours_restants(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_fin:
                delta = (rec.date_fin - today).days
                rec.jours_restants = delta
                rec.is_expired = delta < 0
                rec.is_expiring_soon = 0 <= delta <= 60
            else:
                rec.jours_restants = 0
                rec.is_expired = False
                rec.is_expiring_soon = False

    # -------------------------------------------------------------------------
    # Transitions
    # -------------------------------------------------------------------------
    def action_resilier(self):
        for rec in self:
            rec.state = 'resilie'

    def action_reactiver(self):
        for rec in self:
            if rec.is_expired:
                raise UserError(
                    'Ce contrat est expiré. Utilisez le wizard de renouvellement.'
                )
            rec.state = 'actif'