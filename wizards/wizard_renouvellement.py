# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from markupsafe import Markup


class WizardRenouvellement(models.TransientModel):
    """
    Wizard de renouvellement de contrat fournisseur.
    Conforme au CDC - Fonctionnalité 04
    """
    _name = 'it.wizard.renouvellement'
    _description = 'Wizard de renouvellement de contrat'

    # === CHAMPS ===
    contrat_id = fields.Many2one(
        'it.contrat',
        string='Contrat à renouveler',
        required=True,
        help="Contrat à renouveler"
    )

    ancienne_date_fin = fields.Date(
        string='Ancienne date de fin',
        compute='_compute_infos',
        readonly=True
    )

    ancien_montant = fields.Float(
        string='Ancien montant (FCFA)',
        compute='_compute_infos',
        readonly=True
    )

    nouvelle_date_fin = fields.Date(
        string='Nouvelle date de fin',
        required=True,
        help="Nouvelle date d'expiration du contrat"
    )

    nouveau_montant = fields.Float(
        string='Nouveau montant (FCFA)',
        required=True,
        help="Nouveau montant du contrat"
    )

    justificatif = fields.Text(
        string='Justificatif du renouvellement',
        required=True,
        help="Raison du renouvellement (ex: nouvelle offre, prolongation, etc.)"
    )

    commentaire = fields.Text(
        string='Commentaires supplémentaires',
        help="Informations additionnelles"
    )

    # === CHAMPS D'INFORMATION (toujours synchronisés avec contrat_id) ===
    contrat_display = fields.Char(
        string='Contrat (texte)',
        compute='_compute_infos',
        readonly=True
    )

    fournisseur_display = fields.Char(
        string='Fournisseur',
        compute='_compute_infos',
        readonly=True
    )

    @api.depends('contrat_id')
    def _compute_infos(self):
        """
        Récupère les informations en lecture seule du contrat existant.
        Ne touche QUE les champs réellement déclarés comme calculés par
        cette méthode — ne jamais écrire ici dans nouveau_montant /
        nouvelle_date_fin (cf. _onchange_contrat_id).
        """
        for wizard in self:
            contrat = wizard.contrat_id
            if contrat:
                wizard.ancienne_date_fin = contrat.date_fin
                wizard.ancien_montant = contrat.montant
                wizard.contrat_display = contrat.name
                wizard.fournisseur_display = contrat.fournisseur_id.name if contrat.fournisseur_id else ''
            else:
                wizard.ancienne_date_fin = False
                wizard.ancien_montant = 0
                wizard.contrat_display = ''
                wizard.fournisseur_display = ''

    @api.onchange('contrat_id')
    def _onchange_contrat_id(self):
        """
        Pré-remplit les suggestions de nouvelle date / nouveau montant,
        une seule fois, sans jamais écraser une saisie manuelle ultérieure.
        """
        if self.contrat_id:
            if self.contrat_id.date_fin:
                self.nouvelle_date_fin = fields.Date.add(self.contrat_id.date_fin, years=1)
            self.nouveau_montant = self.contrat_id.montant

    @api.onchange('nouvelle_date_fin')
    def _onchange_nouvelle_date_fin(self):
        """Vérifie que la nouvelle date est postérieure à l'ancienne"""
        if self.nouvelle_date_fin and self.ancienne_date_fin:
            if self.nouvelle_date_fin <= self.ancienne_date_fin:
                return {
                    'warning': {
                        'title': _('Attention'),
                        'message': _("La nouvelle date de fin doit être postérieure à l'ancienne date (%s).")
                        % self.ancienne_date_fin.strftime('%d/%m/%Y')
                    }
                }

    # === MÉTHODE D'ACTION ===
    def action_renouveler(self):
        """
        Exécute le renouvellement du contrat :
        1. Vérifie les dates
        2. Trace l'opération dans le chatter de l'ancien contrat
        3. Crée un nouveau contrat avec les nouvelles données et les mêmes équipements
        4. Marque l'ancien contrat comme 'expire' et le relie au nouveau
        """
        self.ensure_one()

        if not self.contrat_id:
            raise ValidationError(_("Veuillez sélectionner un contrat à renouveler."))

        # Vérifications
        if self.nouvelle_date_fin <= self.ancienne_date_fin:
            raise ValidationError(
                _("La nouvelle date de fin doit être postérieure à l'ancienne date (%s).")
                % self.ancienne_date_fin.strftime('%d/%m/%Y')
            )

        if self.nouveau_montant <= 0:
            raise ValidationError(_("Le montant du contrat doit être positif."))

        contrat = self.contrat_id

        # === 1. CRÉER UN HISTORIQUE DANS LE CHATTER ===
        # Markup() est indispensable depuis Odoo 17 : sans ça, message_post()
        # échappe automatiquement le HTML (anti-XSS) et affiche les balises
        # brutes au lieu de les interpréter. Les %s injectés via Markup % (...)
        # restent automatiquement échappés individuellement (sûr), seules les
        # balises du template restent actives.
        message = Markup(
            """<b>Renouvellement de contrat</b>
            <ul>
                <li><b>Contrat :</b> %s</li>
                <li><b>Fournisseur :</b> %s</li>
                <li><b>Ancienne date de fin :</b> %s</li>
                <li><b>Nouvelle date de fin :</b> %s</li>
                <li><b>Ancien montant :</b> %s FCFA</li>
                <li><b>Nouveau montant :</b> %s FCFA</li>
                <li><b>Justificatif :</b> %s</li>
                <li><b>Commentaire :</b> %s</li>
            </ul>"""
        ) % (
            contrat.name,
            contrat.fournisseur_id.name if contrat.fournisseur_id else '',
            self.ancienne_date_fin.strftime('%d/%m/%Y') if self.ancienne_date_fin else '',
            self.nouvelle_date_fin.strftime('%d/%m/%Y'),
            f"{self.ancien_montant:,.0f}",
            f"{self.nouveau_montant:,.0f}",
            self.justificatif,
            self.commentaire or 'Aucun commentaire'
        )
        contrat.message_post(body=message)

        # === 2. CRÉER LE NOUVEAU CONTRAT ===
        equipements_couverts = contrat.equipement_ids

        nouveau_contrat_vals = {
            'name': f"{contrat.name} - Renouvelé le {fields.Date.today().strftime('%d/%m/%Y')}",
            'fournisseur_id': contrat.fournisseur_id.id,
            'type_contrat': contrat.type_contrat,
            'date_debut': fields.Date.today(),
            'date_fin': self.nouvelle_date_fin,
            'montant': self.nouveau_montant,
            'description': f"Renouvellement du contrat {contrat.name}\nJustificatif: {self.justificatif}",
            'equipement_ids': [(6, 0, equipements_couverts.ids)],
            'renouvele_de_id': contrat.id,
        }

        nouveau_contrat = self.env['it.contrat'].create(nouveau_contrat_vals)

        # === 3. MARQUER L'ANCIEN CONTRAT COMME EXPIRÉ ET LE RELIER AU NOUVEAU ===
        contrat.write({
            'state': 'expire',
            'contrat_renouvele_id': nouveau_contrat.id,
        })

        # === 4. MESSAGE SUR LE NOUVEAU CONTRAT ===
        message_nouveau = Markup(
            """<b>Contrat créé par renouvellement</b>
            <ul>
                <li><b>Contrat d'origine :</b> %s</li>
                <li><b>Nouvelle date de fin :</b> %s</li>
                <li><b>Montant :</b> %s FCFA</li>
            </ul>"""
        ) % (
            contrat.name,
            self.nouvelle_date_fin.strftime('%d/%m/%Y'),
            f"{self.nouveau_montant:,.0f}"
        )
        nouveau_contrat.message_post(body=message_nouveau)

        # === 5. OUVRIR LE NOUVEAU CONTRAT ===
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'it.contrat',
            'res_id': nouveau_contrat.id,
            'view_mode': 'form',
            'target': 'current',
            'flags': {'form': {'action_buttons': True}}
        }