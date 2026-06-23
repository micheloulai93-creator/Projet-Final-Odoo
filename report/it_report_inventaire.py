# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ItReportInventaire(models.AbstractModel):
    _name = 'report.it_parc.report_inventaire'
    _description = 'Rapport Inventaire'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['it.equipement'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'it.equipement',
            'docs': docs,
            'data': data,
        }
