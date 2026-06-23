from odoo import models, fields, api


class ItAlerte(models.Model):
    _name = 'it.alerte'
    _description = 'Alerte garantie / contrat'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_alerte asc'

    # -------------------------------------------------------------------------
    # Identification
    # -------------------------------------------------------------------------
    name = fields.Char(
        string='Libellé',
        required=True,
        tracking=True,
    )
    type_alerte = fields.Selection([
        ('garantie', 'Expiration de garantie'),
        ('contrat', 'Expiration de contrat'),
    ], string='Type d\'alerte', required=True, tracking=True)

    # -------------------------------------------------------------------------
    # Relations (une alerte concerne soit un équipement, soit un contrat)
    # -------------------------------------------------------------------------
    equipement_id = fields.Many2one(
        'it.equipement',
        string='Équipement concerné',
        ondelete='cascade',
        tracking=True,
    )
    contrat_id = fields.Many2one(
        'it.contrat',
        string='Contrat concerné',
        ondelete='cascade',
        tracking=True,
    )

    # -------------------------------------------------------------------------
    # Dates et délais
    # -------------------------------------------------------------------------
    date_alerte = fields.Date(
        string='Date de l\'alerte',
        required=True,
        default=fields.Date.today,
    )
    date_echeance = fields.Date(
        string='Date d\'échéance',
        tracking=True,
        help='Date de fin de garantie ou de fin de contrat.',
    )
    jours_restants = fields.Integer(
        string='Jours restants',
        compute='_compute_jours_restants',
        store=True,
    )

    # -------------------------------------------------------------------------
    # État
    # -------------------------------------------------------------------------
    state = fields.Selection([
        ('nouvelle', 'Nouvelle'),
        ('en_traitement', 'En traitement'),
        ('traitee', 'Traitée'),
        ('ignoree', 'Ignorée'),
    ], string='État', default='nouvelle', tracking=True)

    # -------------------------------------------------------------------------
    # Responsable
    # -------------------------------------------------------------------------
    responsable_id = fields.Many2one(
        'res.users',
        string='Responsable',
        default=lambda self: self.env.user,
        tracking=True,
    )

    # -------------------------------------------------------------------------
    # Notes
    # -------------------------------------------------------------------------
    note = fields.Text(string='Notes / Actions à mener')

    # -------------------------------------------------------------------------
    # Calculs
    # -------------------------------------------------------------------------
    @api.depends('date_echeance')
    def _compute_jours_restants(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_echeance:
                rec.jours_restants = (rec.date_echeance - today).days
            else:
                rec.jours_restants = 0

    # -------------------------------------------------------------------------
    # Transitions
    # -------------------------------------------------------------------------
    def action_prendre_en_charge(self):
        for rec in self:
            rec.state = 'en_traitement'

    def action_marquer_traitee(self):
        for rec in self:
            rec.state = 'traitee'

    def action_ignorer(self):
        for rec in self:
            rec.state = 'ignoree'

    # -------------------------------------------------------------------------
    # Méthode appelée par le ir.cron (Phase 3)
    # -------------------------------------------------------------------------
    @api.model
    def _cron_scanner_alertes(self, delai_jours=30):
        """
        Tâche planifiée : scanne les garanties et contrats
        et crée des alertes pour ceux expirant dans 'delai_jours' jours.
        Appelée automatiquement par ir_cron_data.xml.
        """
        today = fields.Date.today()

        # -- Alertes garantie équipements --
        equipements = self.env['it.equipement'].search([
            ('date_garantie', '!=', False),
            ('state', 'not in', ['retired']),
        ])
        for eq in equipements:
            jours = (eq.date_garantie - today).days
            if 0 <= jours <= delai_jours:
                existing = self.search([
                    ('equipement_id', '=', eq.id),
                    ('type_alerte', '=', 'garantie'),
                    ('state', 'not in', ['traitee', 'ignoree']),
                ])
                if not existing:
                    self.create({
                        'name': f'Garantie expirante — {eq.name} ({jours}j)',
                        'type_alerte': 'garantie',
                        'equipement_id': eq.id,
                        'date_echeance': eq.date_garantie,
                    })

        # -- Alertes contrats fournisseurs --
        contrats = self.env['it.contrat'].search([
            ('date_fin', '!=', False),
            ('state', '=', 'actif'),
        ])
        for ct in contrats:
            jours = (ct.date_fin - today).days
            if 0 <= jours <= delai_jours:
                existing = self.search([
                    ('contrat_id', '=', ct.id),
                    ('type_alerte', '=', 'contrat'),
                    ('state', 'not in', ['traitee', 'ignoree']),
                ])
                if not existing:
                    self.create({
                        'name': f'Contrat expirant — {ct.name} ({jours}j)',
                        'type_alerte': 'contrat',
                        'contrat_id': ct.id,
                        'date_echeance': ct.date_fin,
                    })
