# -*- coding: utf-8 -*-
import base64
import io
import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import date_utils

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

_logger = logging.getLogger(__name__)


class WizardExportExcel(models.TransientModel):
    """
    Classe de base pour les exports Excel.
    Héritée par les 3 exports spécifiques.
    """
    _name = 'it.wizard.export.excel'
    _description = 'Export Excel - Classe de base'
    _abstract = True
    _transient_max_hours = 24  # Nettoyage après 24h

    # === CHAMPS COMMUNS ===
    filename = fields.Char(
        string='Nom du fichier',
        default=lambda self: f"export_{fields.Date.today().strftime('%Y%m%d')}.xlsx",
        readonly=True
    )

    file_datas = fields.Binary(
        string='Fichier Excel',
        readonly=True,
        attachment=True
    )

    export_done = fields.Boolean(
        string='Export effectué',
        default=False,
        readonly=True
    )

    # === MÉTHODES UTILITAIRES ===
    def _create_excel_file(self, sheet_name, headers, data_rows, column_widths=None, conditional_formatting=None):
        """
        Crée un fichier Excel avec xlsxwriter.
        
        :param sheet_name: Nom de la feuille
        :param headers: Liste des en-têtes
        :param data_rows: Liste des lignes de données (listes)
        :param column_widths: Dict {col_index: width} optionnel
        :param conditional_formatting: Dict avec les règles de mise en forme
        """
        if not xlsxwriter:
            raise ValidationError(_("La bibliothèque xlsxwriter n'est pas installée. "
                                   "Veuillez exécuter: pip install xlsxwriter"))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#2d6da8',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
        })
        
        number_format = workbook.add_format({
            'border': 1,
            'num_format': '#,##0',
            'valign': 'vcenter',
        })
        
        date_format = workbook.add_format({
            'border': 1,
            'num_format': 'dd/mm/yyyy',
            'valign': 'vcenter',
        })
        
        # Création de la feuille
        sheet_name = sheet_name[:31] if sheet_name else 'Feuille1'  # Max 31 caractères
        worksheet = workbook.add_worksheet(sheet_name)
        
        # En-têtes
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            
            # Largeur de colonne automatique ou spécifiée
            if column_widths and col in column_widths:
                worksheet.set_column(col, col, column_widths[col])
            else:
                width = max(len(str(header)) + 2, 12)
                worksheet.set_column(col, col, width)
        
        # Données
        for row_idx, row_data in enumerate(data_rows, start=1):
            for col_idx, value in enumerate(row_data):
                # Déterminer le format en fonction du type de valeur
                if value is None:
                    worksheet.write(row_idx, col_idx, '', cell_format)
                elif isinstance(value, (int, float)) and col_idx > 0:
                    worksheet.write(row_idx, col_idx, value or 0, number_format)
                elif isinstance(value, datetime):
                    worksheet.write(row_idx, col_idx, value, date_format)
                elif isinstance(value, str) and '/' in value and len(value) == 10:
                    try:
                        date_value = datetime.strptime(value, '%d/%m/%Y')
                        worksheet.write(row_idx, col_idx, date_value, date_format)
                    except:
                        worksheet.write(row_idx, col_idx, value, cell_format)
                else:
                    worksheet.write(row_idx, col_idx, value or '', cell_format)
        
        # Mise en forme conditionnelle
        if conditional_formatting:
            for rule in conditional_formatting:
                if rule.get('type') == 'color_scale':
                    worksheet.conditional_format(
                        rule.get('range', ''),
                        {
                            'type': '2_color_scale',
                            'min_color': rule.get('min_color', '#63BE7B'),
                            'max_color': rule.get('max_color', '#F8696B'),
                        }
                    )
                elif rule.get('type') == 'cell_color':
                    worksheet.conditional_format(
                        rule.get('range', ''),
                        {
                            'type': 'cell',
                            'criteria': rule.get('criteria', 'less than'),
                            'value': rule.get('value', 30),
                            'format': workbook.add_format({
                                'bg_color': rule.get('color', '#FF0000'),
                                'font_color': '#FFFFFF',
                                'bold': True,
                            })
                        }
                    )
        
        workbook.close()
        output.seek(0)
        
        # Encodage en base64
        file_data = base64.b64encode(output.getvalue())
        
        return file_data

    def _get_attachment_domain(self):
        """Domaine pour trouver les pièces jointes existantes"""
        return [
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('mimetype', '=', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        ]

    def action_download(self):
        """Télécharge le fichier Excel"""
        self.ensure_one()
        if not self.file_datas:
            raise ValidationError(_("Aucun fichier à télécharger. Effectuez d'abord l'export."))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.id}?model={self._name}&id={self.id}&filename_field=filename&field=file_datas&download=true',
            'target': 'new',
        }