# -*- coding: utf-8 -*-
import base64
import io
import csv
import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class WizardImportCSV(models.TransientModel):
    """
    Wizard d'import en masse d'équipements depuis un fichier CSV.
    Conforme au CDC - Fonctionnalité 06
    """
    _name = 'it.wizard.import.csv'
    _description = 'Wizard d\'import CSV d\'équipements'

    # === CHAMPS DU WIZARD ===
    csv_file = fields.Binary(
        string='Fichier CSV',
        required=True,
        help="Fichier CSV contenant l'inventaire à importer"
    )

    filename = fields.Char(
        string='Nom du fichier',
        help="Nom du fichier importé"
    )

    import_options = fields.Selection([
        ('create_only', 'Créer uniquement les nouveaux équipements'),
        ('create_update', 'Créer ou mettre à jour les équipements existants'),
    ], string='Options d\'import', default='create_only', required=True)

    separator = fields.Selection([
        (';', 'Point-virgule (;)'),
        (',', 'Virgule (,)'),
        ('\t', 'Tabulation'),
    ], string='Séparateur', default=';', required=True)

    # === CHAMPS DE RÉSULTAT (remplis après exécution) ===
    lignes_importees = fields.Integer(
        string='Lignes importées',
        default=0,
        readonly=True
    )

    lignes_ignorees = fields.Integer(
        string='Lignes ignorées',
        default=0,
        readonly=True
    )

    lignes_erreur = fields.Integer(
        string='Lignes en erreur',
        default=0,
        readonly=True
    )

    rapport_lignes = fields.Text(
        string='Rapport détaillé',
        readonly=True,
        help="Détail des lignes créées, ignorées ou en erreur"
    )

    import_fait = fields.Boolean(
        string='Import effectué',
        default=False,
        readonly=True
    )

    # === MÉTHODE D'ACTION ===
    def action_importer(self):
        """
        Importe le fichier CSV et crée les équipements manquants.
        Gère la détection des doublons par numéro de série.
        """
        self.ensure_one()

        if not self.csv_file:
            raise ValidationError(_("Veuillez sélectionner un fichier CSV."))

        # === 1. LECTURE DU FICHIER CSV ===
        try:
            file_data = base64.b64decode(self.csv_file)

            # Gestion robuste de l'encodage : Excel exporte souvent en
            # Windows-1252/latin-1, surtout avec des accents (é, à, ô...).
            # 'utf-8-sig' gère aussi le BOM ajouté par Excel en UTF-8.
            try:
                text = file_data.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = file_data.decode('latin-1')

            file_io = io.StringIO(text)
            reader = csv.DictReader(file_io, delimiter=self.separator)

            # Vérification des colonnes obligatoires
            required_columns = ['nom', 'categorie', 'num_serie']
            colonnes = reader.fieldnames or []

            for col in required_columns:
                if col not in colonnes:
                    raise ValidationError(
                        _("La colonne '%s' est obligatoire dans le fichier CSV. "
                          "Colonnes trouvées : %s") % (col, ', '.join(colonnes))
                    )

        except ValidationError:
            raise
        except Exception as e:
            raise UserError(_("Erreur lors de la lecture du fichier CSV : %s") % str(e))

        # === 2. PRÉPARATION DES DONNÉES ===
        equipement_obj = self.env['it.equipement']
        created_count = 0
        ignored_count = 0
        error_count = 0
        details_created = []
        details_ignored = []
        details_errors = []

        for row_num, row in enumerate(reader, start=2):
            try:
                num_serie = (row.get('num_serie') or '').strip()
                nom = (row.get('nom') or '').strip()

                # Vérification des champs obligatoires
                if not num_serie:
                    error_count += 1
                    details_errors.append(f"Ligne {row_num}: Numéro de série manquant")
                    continue

                if not nom:
                    error_count += 1
                    details_errors.append(f"Ligne {row_num}: Nom de l'équipement manquant")
                    continue

                # === 3. DÉTECTION DES DOUBLONS ===
                existing = equipement_obj.search([('num_serie', '=', num_serie)], limit=1)

                if existing:
                    if self.import_options == 'create_only':
                        ignored_count += 1
                        details_ignored.append(
                            f"Ligne {row_num}: Équipement '{nom}' (Série: {num_serie}) déjà existant - ignoré"
                        )
                        continue
                    else:
                        vals = self._prepare_equipment_vals(row)
                        existing.write(vals)
                        created_count += 1
                        details_created.append(
                            f"Ligne {row_num}: Équipement '{nom}' (Série: {num_serie}) mis à jour"
                        )
                        continue

                # === 4. CRÉATION D'UN NOUVEL ÉQUIPEMENT ===
                vals = self._prepare_equipment_vals(row)
                equipement_obj.create(vals)
                created_count += 1
                details_created.append(
                    f"Ligne {row_num}: Équipement '{nom}' (Série: {num_serie}) créé avec succès"
                )

            except Exception as e:
                error_count += 1
                details_errors.append(f"Ligne {row_num}: Erreur - {str(e)}")

        # === 5. MISE À JOUR DES CHAMPS DE RÉSULTAT ===
        self.write({
            'lignes_importees': created_count,
            'lignes_ignorees': ignored_count,
            'lignes_erreur': error_count,
            'import_fait': True,
            'rapport_lignes': self._build_rapport(details_created, details_ignored, details_errors)
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'it.wizard.import.csv',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'flags': {'form': {'action_buttons': False}}
        }

    def _parse_date(self, date_str):
        """
        Convertit une date texte en objet date Odoo.
        Accepte le format français JJ/MM/AAAA (le plus courant en sortie
        d'Excel) ainsi que le format ISO AAAA-MM-JJ (format natif Odoo).
        Retourne False si la valeur est vide ou ne correspond à aucun format.
        """
        if not date_str:
            return False
        date_str = date_str.strip()
        if not date_str:
            return False

        for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        # Aucun format reconnu : on ne bloque pas tout l'import pour ça,
        # on signale juste que la garantie n'a pas pu être lue.
        _logger.warning("Format de date non reconnu pour 'date_garantie': %s", date_str)
        return False

    def _prepare_equipment_vals(self, row):
        """
        Prépare le dictionnaire de valeurs pour la création/mise à jour d'un équipement.
        """
        vals = {
            'name': (row.get('nom') or '').strip(),
            'num_serie': (row.get('num_serie') or '').strip(),
            'categorie': self._get_categorie(row.get('categorie', 'autre')),
            'marque': (row.get('marque') or '').strip(),
            'modele': (row.get('modele') or '').strip(),
            'valeur_achat': float(row.get('valeur_achat', 0) or 0),
            'date_garantie': self._parse_date(row.get('date_garantie')),
            'fournisseur_id': self._get_fournisseur_id(row.get('fournisseur')),
            'state': 'draft',
        }

        # Gestion de l'affectation si les colonnes existent
        if row.get('employe'):
            employe = self._get_employe_by_name(row.get('employe'))
            if employe:
                vals['employe_id'] = employe.id
                vals['state'] = 'assigned'

        if row.get('departement'):
            dept = self._get_departement_by_name(row.get('departement'))
            if dept:
                vals['department_id'] = dept.id

        if row.get('site'):
            vals['site'] = self._get_site(row.get('site'))

        if row.get('localisation'):
            vals['localisation'] = row.get('localisation').strip()

        return vals

    def _get_categorie(self, cat_val):
        """Convertit la catégorie depuis le CSV"""
        mapping = {
            'poste_de_travail': 'poste_travail',
            'poste de travail': 'poste_travail',
            'poste': 'poste_travail',
            'serveur': 'serveur',
            'imprimante': 'imprimante',
            'reseau': 'reseau',
            'réseau': 'reseau',
            'switch': 'reseau',
            'routeur': 'reseau',
            'telephone': 'telephone',
            'téléphone': 'telephone',
            'autre': 'autre'
        }
        return mapping.get((cat_val or '').lower().strip(), 'autre')

    def _get_site(self, site_val):
        """Convertit le site depuis le CSV"""
        mapping = {
            'abidjan_cocody': 'abidjan_cocody',
            'cocody': 'abidjan_cocody',
            'abidjan_plateau': 'abidjan_plateau',
            'plateau': 'abidjan_plateau',
            'bouake': 'bouake',
            'bouaké': 'bouake',
        }
        return mapping.get((site_val or '').lower().strip(), 'abidjan_cocody')

    def _get_employe_by_name(self, name):
        """Récupère un employé par son nom"""
        if not name:
            return False
        employes = self.env['hr.employee'].search([('name', 'ilike', name.strip())], limit=1)
        return employes[0] if employes else False

    def _get_departement_by_name(self, name):
        """Récupère un département par son nom"""
        if not name:
            return False
        depts = self.env['hr.department'].search([('name', 'ilike', name.strip())], limit=1)
        return depts[0] if depts else False

    def _get_fournisseur_id(self, fournisseur_name):
        """Récupère ou crée un fournisseur"""
        if not fournisseur_name:
            return False

        partner = self.env['res.partner'].search([
            ('name', 'ilike', fournisseur_name.strip()),
            ('supplier_rank', '>=', 1)
        ], limit=1)

        if not partner:
            partner = self.env['res.partner'].create({
                'name': fournisseur_name.strip(),
                'supplier_rank': 1,
                'is_company': True,
            })
            _logger.info("Création d'un nouveau fournisseur: %s", fournisseur_name)

        return partner.id

    def _build_rapport(self, created, ignored, errors):
        """Construit le rapport textuel détaillé"""
        rapport = "=== RAPPORT D'IMPORT ===\n\n"

        rapport += f"📊 Résumé :\n"
        rapport += f"  - Lignes créées : {len(created)}\n"
        rapport += f"  - Lignes ignorées : {len(ignored)}\n"
        rapport += f"  - Lignes en erreur : {len(errors)}\n\n"

        if created:
            rapport += "✅ Lignes créées ou mises à jour :\n"
            for line in created[:50]:
                rapport += f"   • {line}\n"
            if len(created) > 50:
                rapport += f"   ... et {len(created) - 50} autres\n"
            rapport += "\n"

        if ignored:
            rapport += "⏭️ Lignes ignorées (doublons) :\n"
            for line in ignored[:20]:
                rapport += f"   • {line}\n"
            if len(ignored) > 20:
                rapport += f"   ... et {len(ignored) - 20} autres\n"
            rapport += "\n"

        if errors:
            rapport += "❌ Lignes en erreur :\n"
            for line in errors[:20]:
                rapport += f"   • {line}\n"
            if len(errors) > 20:
                rapport += f"   ... et {len(errors) - 20} autres\n"

        return rapport

    def action_telecharger_rapport(self):
        """Télécharge le rapport d'import en format texte"""
        if not self.rapport_lignes:
            raise ValidationError(_("Aucun rapport disponible. Effectuez d'abord un import."))

        attachment = self.env['ir.attachment'].create({
            'name': f"rapport_import_{fields.Date.today()}.txt",
            'datas': base64.b64encode(self.rapport_lignes.encode('utf-8')),
            'mimetype': 'text/plain',
            'res_model': 'it.wizard.import.csv',
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }