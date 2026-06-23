# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta


class ItEquipement(models.Model):
    _name = 'it.equipement'
    _description = 'Équipement informatique'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char(string='Nom de l\'équipement', required=True, tracking=True)
    num_serie = fields.Char(string='Numéro de série', required=True, tracking=True, copy=False)
    reference_interne = fields.Char(string='Référence interne', copy=False)

    categorie = fields.Selection([
        ('poste_travail', 'Poste de travail'),
        ('serveur', 'Serveur'),
        ('imprimante', 'Imprimante'),
        ('reseau', 'Équipement réseau'),
        ('telephone', 'Téléphone IP'),
        ('autre', 'Autre'),
    ], string='Catégorie', required=True, tracking=True)

    marque = fields.Char(string='Marque', tracking=True)
    modele = fields.Char(string='Modèle', tracking=True)
    description_technique = fields.Text(string='Description technique')

    valeur_achat = fields.Float(string='Valeur d\'achat (FCFA)', tracking=True, default=0.0)
    date_achat = fields.Date(string='Date d\'achat', tracking=True)
    date_garantie = fields.Date(string='Fin de garantie', tracking=True)
    garantie_expired = fields.Boolean(
        string='Garantie expirée',
        compute='_compute_garantie_expired',
        store=True,
    )
    jours_avant_garantie = fields.Integer(
        string='Jours avant fin de garantie',
        compute='_compute_garantie_expired',
        store=True,
    )

    fournisseur_id = fields.Many2one(
        'res.partner',
        string='Fournisseur',
        domain=[('supplier_rank', '>=', 1)],
        tracking=True,
        help="Fournisseur de l'équipement"
    )

    site = fields.Selection([
        ('abidjan_cocody', 'Abidjan - Cocody'),
        ('abidjan_plateau', 'Abidjan - Plateau'),
        ('bouake', 'Bouaké'),
    ], string='Site', tracking=True)

    localisation = fields.Char(string='Localisation', tracking=True)

    employe_id = fields.Many2one('hr.employee', string='Employé affecté', tracking=True, ondelete='set null')
    department_id = fields.Many2one(
        'hr.department',
        string='Département',
        tracking=True,
        related='employe_id.department_id',
        store=True,
    )
    date_affectation = fields.Date(string='Date d\'affectation', tracking=True)

    affectation_ids = fields.One2many('it.equipement.affectation', 'equipement_id', string='Historique des affectations')
    intervention_ids = fields.One2many('it.intervention', 'equipement_id', string='Interventions')
    contrat_ids = fields.Many2many(
        'it.contrat',
        'it_contrat_equipement_rel',
        'equipement_id',
        'contrat_id',
        string='Contrats',
    )
    alerte_ids = fields.One2many('it.alerte', 'equipement_id', string='Alertes')

    nb_interventions = fields.Integer(string='Nb interventions', compute='_compute_nb_interventions')
    cout_total_maintenance = fields.Float(
        string='Coût total maintenance (FCFA)',
        compute='_compute_cout_total_maintenance',
        store=True,
        default=0.0,
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('assigned', 'Affecté'),
        ('in_maintenance', 'En maintenance'),
        ('retired', 'Retiré'),
    ], string='État', default='draft', tracking=True, required=True)

    _sql_constraints = [
        ('num_serie_unique', 'UNIQUE(num_serie)',
         'Ce numéro de série existe déjà. Chaque équipement doit avoir un numéro de série unique.'),
    ]

    @api.depends('date_garantie')
    def _compute_garantie_expired(self):
        today = fields.Date.today()
        for rec in self:
            if rec.date_garantie:
                delta = (rec.date_garantie - today).days
                rec.jours_avant_garantie = delta
                rec.garantie_expired = delta < 0
            else:
                rec.jours_avant_garantie = 0
                rec.garantie_expired = False

    @api.depends('intervention_ids')
    def _compute_nb_interventions(self):
        for rec in self:
            rec.nb_interventions = len(rec.intervention_ids)

    @api.depends('intervention_ids.cout')
    def _compute_cout_total_maintenance(self):
        for rec in self:
            total = 0.0
            for intervention in rec.intervention_ids:
                total += intervention.cout or 0.0
            rec.cout_total_maintenance = total

    def action_affecter(self):
        for rec in self:
            if not rec.employe_id:
                raise UserError('Vous devez affecter un employé avant de passer l\'équipement en état "Affecté".')
            rec.state = 'assigned'
            if not rec.date_affectation:
                rec.date_affectation = fields.Date.today()

    def action_mettre_en_maintenance(self):
        for rec in self:
            rec.state = 'in_maintenance'

    def action_retirer(self):
        for rec in self:
            rec.state = 'retired'
            rec.employe_id = False

    def action_remettre_en_service(self):
        for rec in self:
            rec.state = 'draft'

    @api.model
    def _get_equipements_garantie_expirant(self, delai_jours):
        today = fields.Date.today()
        date_limite = today + timedelta(days=delai_jours)
        return self.search([
            ('date_garantie', '!=', False),
            ('date_garantie', '<=', date_limite),
            ('date_garantie', '>=', today),
            ('state', '!=', 'retired'),
        ])

    def get_etat_display(self):
        return dict(self._fields['state'].selection).get(self.state, '')

    def get_total_valeur(self):
        """
        Utilisé par le rapport PDF inventaire.
        Retourne la valeur totale du parc en s'assurant qu'il n'y a pas de None.
        """
        if not self:
            return 0.0
        
        total = 0.0
        for record in self:
            valeur = record.valeur_achat or 0.0
            total += valeur
        
        return total

    @api.model
    def _get_equipements_by_department(self, department_id):
        return self.search([('department_id', '=', department_id)])

    @api.model
    def _get_equipements_by_category(self, category):
        return self.search([('categorie', '=', category)])

    @api.model
    def _get_equipements_by_state(self, state):
        return self.search([('state', '=', state)])

    def action_export_excel(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'it.wizard.export.inventaire',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_filtre_categorie': 'tous',
                'default_filtre_etat': 'tous',
            }
        }