# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ItIntervention(models.Model):
    _name = 'it.intervention'
    _description = 'Intervention de maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_debut desc'

    name = fields.Char(
        string='Référence',
        required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('it.intervention') or _('New'),
        copy=False,
        readonly=True,
    )

    equipement_id = fields.Many2one('it.equipement', string='Équipement', required=True, ondelete='cascade', tracking=True)
    technicien_id = fields.Many2one('hr.employee', string='Technicien', required=True, tracking=True)

    type_intervention = fields.Selection([
        ('corrective', 'Corrective'),
        ('preventive', 'Préventive'),
    ], string='Type', required=True, default='corrective', tracking=True)

    description = fields.Text(string='Description du problème', required=True)
    rapport = fields.Text(string='Rapport d\'intervention')

    date_debut = fields.Datetime(string='Date de début', required=True, tracking=True)
    date_fin = fields.Datetime(string='Date de fin', tracking=True)
    duree = fields.Float(
        string='Durée (heures)',
        compute='_compute_duree',
        store=True,
        default=0.0,
        help='Durée calculée automatiquement entre la date de début et la date de fin.',
    )

    cout = fields.Float(string='Coût (FCFA)', tracking=True, default=0.0)

    state = fields.Selection([
        ('planifie', 'Planifiée'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminée'),
        ('annule', 'Annulée'),
    ], string='État', default='planifie', tracking=True)

    @api.depends('date_debut', 'date_fin')
    def _compute_duree(self):
        for rec in self:
            if rec.date_debut and rec.date_fin:
                delta = rec.date_fin - rec.date_debut
                rec.duree = delta.total_seconds() / 3600.0
            else:
                rec.duree = 0.0

    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        for rec in self:
            if rec.date_fin and rec.date_debut and rec.date_fin < rec.date_debut:
                raise ValidationError('La date de fin ne peut pas être antérieure à la date de début.')

    def action_demarrer(self):
        for rec in self:
            rec.state = 'en_cours'
            if rec.equipement_id:
                rec.equipement_id.action_mettre_en_maintenance()

    def action_terminer(self):
        for rec in self:
            if not rec.date_fin:
                rec.date_fin = fields.Datetime.now()
            rec.state = 'termine'
            if rec.equipement_id and rec.equipement_id.state == 'in_maintenance':
                rec.equipement_id.state = 'assigned'

    def action_annuler(self):
        for rec in self:
            rec.state = 'annule'

    def get_total_cout(self):
        """
        Utilisé par le rapport PDF maintenances.
        Retourne le coût total des interventions en s'assurant qu'il n'y a pas de None.
        """
        if not self:
            return 0.0
        
        total = 0.0
        for record in self:
            cout = record.cout or 0.0
            total += cout
        
        return total

    def get_total_duree(self):
        """
        Utilisé par le rapport PDF maintenances.
        Retourne la durée totale des interventions en s'assurant qu'il n'y a pas de None.
        """
        if not self:
            return 0.0
        
        total = 0.0
        for record in self:
            duree = record.duree or 0.0
            total += duree
        
        return total